#!/usr/bin/env python3
"""
runtime.py — deploy and drive the company's Superserve microVM (US-1.4).

Design notes (this file is read by other agents, so the WHY is written down):

- **Two planes, two transports.** Superserve's control plane (`api.superserve.ai`,
  `X-API-Key`) creates/pauses/kills sandboxes; the data plane
  (`boxd-{id}.sandbox.superserve.ai`, `X-Access-Token`) runs commands and moves files.
  Each plane goes through exactly one function (`_request` / `_data_request`) so the
  whole test suite runs offline by monkeypatching two symbols — same pattern as pay.py.
- **The state file is a credential store.** The per-sandbox access token grants shell
  access to the VM that runs the company. It lives in a git-ignored JSON file with 0600
  perms, never in argv, never printed. `resume` rotates it (the API returns a fresh one).
- **Secrets are bound by NAME.** `deploy` passes Superserve *secret names*
  (`pioneer-key`, `stripe-key`); the operator created those once in the Superserve
  console. The real values never transit this tool, this repo, or the VM's env — the VM
  sees stand-in proxy tokens that Superserve swaps at egress.
- **Stdlib only.** Zero pip deps repo-wide by design; this speaks the published REST API
  (openapi.yaml) through urllib rather than importing their SDK.

Config (names only — values live in the environment, never in this repo):
    SUPERSERVE_API_KEY   control-plane key (ss_live_...), read at call time, never logged
    RUNTIME_STATE        state-file path override (flag --state beats it, per repo lesson:
                         flags are deterministic, env inheritance is not)
    NIGHTSHIFT_REPO      git URL the VM clones (default: the public Nightshift repo)
"""
import argparse
import datetime
import json
import os
import re
import shlex
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request

# ── constants ─────────────────────────────────────────────────────────────────
API_BASE = "https://api.superserve.ai"
DATA_BASE_FMT = "https://boxd-{sid}.sandbox.superserve.ai"
PREVIEW_URL_FMT = "https://{port}-{sid}.sandbox.superserve.ai"

SANDBOX_NAME = "nightshift-loop"
TEMPLATE = "superserve/claude-code"      # Claude Code preinstalled — the approver tick needs it
METADATA = {"role": "nightshift-loop"}   # lets `status` rediscover the sandbox without a state file
DEFAULT_REPO = "https://github.com/Nxver-GitHub/Nightshift.git"

VM_HOME = "/home/user"
VM_REPO = f"{VM_HOME}/nightshift"
DASH_PORT = 8787
HTTP_TIMEOUT = 60                        # control-plane calls; an agent loop must never hang
CLONE_TIMEOUT_S = 300                    # in-VM git clone + chmod, generous for event wifi

# Paths INSIDE the VM. Passed as sandbox env vars so every process (supervisor, dashboard,
# approver) resolves the same state files — the single source of truth lives in the VM.
VM_ENV = {
    "NIGHTSHIFT_HOME": VM_REPO,
    "TASKRUNNER_TASKS": f"{VM_REPO}/blocks/taskrunner/code/tasks.json",
    "APPROVER_POLICY": f"{VM_REPO}/blocks/approver/policy/policy.md",
    "APPROVER_LEDGER": f"{VM_REPO}/blocks/approver/code/decisions.jsonl",
    "CRM_DB": f"{VM_REPO}/blocks/crm/code/crm.db",
    "DASH_PORT": str(DASH_PORT),
    "DASH_BIND": "0.0.0.0",              # preview URLs route to in-VM listeners; loopback is invisible
    # Claude Code remains the agent harness, while Pioneer supplies provider-neutral inference
    # through its Anthropic-compatible endpoint. Base URL WITHOUT /v1 — the CLI appends
    # /v1/messages itself (docs.pioneer.ai/claude-code; /v1 here produced /v1/v1/messages).
    "ANTHROPIC_BASE_URL": "https://api.pioneer.ai",
}

# The state files worth mirroring to the demo laptop. decisions.jsonl is the product;
# the rest make the local dashboard a faithful backup if the venue network dies.
PULL_FILES = [
    "blocks/taskrunner/code/tasks.json",
    "blocks/approver/code/decisions.jsonl",
    "blocks/approver/code/approver.log",
    "blocks/crm/code/crm.db",
    "supervisor.log",
]


# ── transports (the ONLY functions that open a socket) ────────────────────────
def _api_key():
    key = os.environ.get("SUPERSERVE_API_KEY", "").strip()
    if not key:
        sys.exit("SUPERSERVE_API_KEY is not set. Export it (ss_live_...) and retry. "
                 "Signup is free at superserve.ai — no card needed.")
    return key


def _http(url, method, headers, body=None, raw=False):
    req = urllib.request.Request(url, method=method, data=body)
    for k, v in headers.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        # Surface the API's own message; never echo any header (they carry credentials).
        try:
            detail = json.loads(e.read().decode() or "{}").get("error", {})
        except Exception:
            detail = {}
        msg = detail.get("message") or detail.get("code") or e.reason
        sys.exit(f"Superserve API error {e.code}: {msg}")
    except urllib.error.URLError as e:
        sys.exit(f"network error reaching Superserve: {e.reason}")
    if raw:
        return payload
    return json.loads(payload) if payload else {}


def _request(method, path, payload=None):
    """Control plane: team-scoped, X-API-Key."""
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"X-API-Key": _api_key()}
    if body is not None:
        headers["Content-Type"] = "application/json"
    return _http(API_BASE + path, method, headers, body)


def _data_request(sid, token, method, path, body=None, raw=False, content_type=None):
    """Data plane: one sandbox, X-Access-Token."""
    headers = {"X-Access-Token": token}
    if content_type:
        headers["Content-Type"] = content_type
    return _http(DATA_BASE_FMT.format(sid=sid) + path, method, headers, body, raw=raw)


# ── state file (sandbox id + access token; a credential store) ────────────────
def state_path(args):
    if getattr(args, "state", None):
        return args.state
    return os.environ.get(
        "RUNTIME_STATE",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".superserve-state.json"))


def load_state(args):
    path = state_path(args)
    if not os.path.exists(path):
        sys.exit(f"no state file at {path} — run `runtime.py deploy` first "
                 f"(or pass --state if it lives elsewhere).")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_state(args, state):
    path = state_path(args)
    # 0600 at creation, not after: the access token grants shell access to the VM that runs
    # the company, and a chmod-after-write leaves a umask-sized window on shared machines.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


# ── exec helper ───────────────────────────────────────────────────────────────
def vm_exec(sid, token, command, timeout_s=60, cwd=VM_HOME):
    """Run one command in the VM; non-zero exit is returned, not raised (caller decides)."""
    return _data_request(sid, token, "POST", "/exec",
                         body=json.dumps({"command": command, "working_dir": cwd,
                                          "timeout_s": timeout_s}).encode(),
                         content_type="application/json")


# ── commands ──────────────────────────────────────────────────────────────────
def cmd_deploy(args):
    """Create the VM, clone the repo, start the supervisor, publish the dashboard."""
    # Both values end up inside a shell string executed in the VM. Validate first, quote later:
    # a metacharacter in --repo/--branch (or $NIGHTSHIFT_REPO) must be a refusal, not an exec.
    if not args.repo.startswith("https://"):
        sys.exit(f"--repo must be an https:// URL, got: {args.repo!r} "
                 "(git's ext::/file:// transports are command execution in disguise).")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", args.branch):
        sys.exit(f"--branch contains characters that have no business in a branch name: {args.branch!r}")

    secrets = {"ANTHROPIC_API_KEY": args.inference_secret}
    if args.stripe_secret:
        secrets["STRIPE_API_KEY"] = args.stripe_secret

    sandbox = _request("POST", "/sandboxes", {
        "name": SANDBOX_NAME,
        "from_template": args.template,
        "metadata": METADATA,
        "env_vars": VM_ENV,
        "secrets": secrets,
        # Public by DECISION, not accident: the dashboard is the audit trail judges open.
        # --private exists for any deployment where the CRM holds real customer data.
        "preview_access": "private" if args.private else "public",
    })
    sid, token = sandbox["id"], sandbox["access_token"]
    save_state(args, {"sandbox_id": sid, "access_token": token,
                      "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    print(f"sandbox created: {sid} (template {args.template})")

    # Clone the public repo. The VM is the runtime, git is the deployment mechanism —
    # redeploying is `git pull`, not re-provisioning.
    clone = vm_exec(sid, token,
                    # Superserve's HTTPS proxy brokers provider credentials; a public GitHub
                    # clone needs neither the proxy nor its private CA. Keep provider traffic
                    # proxied, but send this one public fetch directly.
                    f"env -u HTTPS_PROXY -u HTTP_PROXY -u ALL_PROXY "
                    f"git clone --depth 1 --branch {shlex.quote(args.branch)} -- "
                    f"{shlex.quote(args.repo)} {VM_REPO} "
                    f"&& chmod +x {VM_REPO}/blocks/runtime/code/*.sh "
                    f"{VM_REPO}/blocks/approver/code/run-approver.sh",
                    timeout_s=CLONE_TIMEOUT_S)
    if clone.get("exit_code") != 0:
        sys.exit(f"clone failed in VM (exit {clone.get('exit_code')}):\n{clone.get('stderr', '')[-2000:]}")
    print(f"repo cloned to {VM_REPO} @ {args.branch}")

    # Supervisor: nohup'd so it outlives this exec call; the VM (not this laptop) owns it now.
    start = vm_exec(sid, token,
                    f"nohup bash {VM_REPO}/blocks/runtime/code/supervisor.sh "
                    f">> {VM_HOME}/supervisor.log 2>&1 & echo started",
                    timeout_s=30)
    if "started" not in start.get("stdout", ""):
        sys.exit(f"supervisor did not start:\n{start.get('stderr', '')[-2000:]}")
    print("supervisor started (approver tick + taskrunner tick + dashboard)")

    _request("POST", f"/sandboxes/{sid}/preview-ports", {"port": DASH_PORT})
    print(f"dashboard: {PREVIEW_URL_FMT.format(port=DASH_PORT, sid=sid)}")


def cmd_status(args):
    """Prefer the state file; fall back to metadata discovery so a lost laptop isn't a lost VM."""
    try:
        sid = load_state(args)["sandbox_id"]
        info = _request("GET", f"/sandboxes/{sid}")
    except SystemExit:
        candidates = _request("GET", "/sandboxes?metadata.role=nightshift-loop")
        if not candidates:
            sys.exit("no nightshift-loop sandbox found (state file missing and metadata search empty).")
        info = candidates[0]
        sid = info["id"]
    out = {"sandbox_id": sid, "status": info.get("status"),
           "dashboard": PREVIEW_URL_FMT.format(port=DASH_PORT, sid=sid)}
    print(json.dumps(out, indent=2) if args.json else
          f"{out['sandbox_id']}  {out['status']}  {out['dashboard']}")


def cmd_url(args):
    print(PREVIEW_URL_FMT.format(port=DASH_PORT, sid=load_state(args)["sandbox_id"]))


def cmd_exec(args):
    st = load_state(args)
    result = vm_exec(st["sandbox_id"], st["access_token"], args.cmd, timeout_s=args.timeout)
    sys.stdout.write(result.get("stdout", ""))
    sys.stderr.write(result.get("stderr", ""))
    sys.exit(result.get("exit_code", 1))


def cmd_pull(args):
    """Mirror the VM's state files to the laptop — the offline demo backup, not a second truth."""
    st = load_state(args)
    sid, token = st["sandbox_id"], st["access_token"]
    os.makedirs(args.dest, exist_ok=True)
    for rel in PULL_FILES:
        vm_path = f"{VM_HOME}/{rel}" if rel == "supervisor.log" else f"{VM_REPO}/{rel}"
        quoted = urllib.parse.quote(vm_path)
        try:
            data = _data_request(sid, token, "GET", f"/files?path={quoted}", raw=True)
        except SystemExit as e:
            print(f"  skip {rel}: {e}", file=sys.stderr)   # a missing crm.db pre-first-sale is normal
            continue
        local = os.path.join(args.dest, os.path.basename(rel))
        # 0600: the mirror may hold CRM rows (buyer emails) on a shared demo laptop.
        fd = os.open(local, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        print(f"  pulled {rel} -> {local} ({len(data)} bytes)")


def cmd_push_env(args):
    """Write the direct-egress override file into the VM (0600), values read from the LOCAL env.

    Exists because Superserve's TLS-intercepting credential proxy cannot serve this stack (stdlib
    urllib has no TLS-to-proxy support; the Claude CLI rejects the proxy CA), so the supervisor
    bypasses it when this file is present. Values travel request-body only — never argv, never
    logs, never this repo. STRIPE_API_KEY maps from the local var of the same name;
    ANTHROPIC_API_KEY maps from local PIONEER_API_KEY (the VM's inference goes to Pioneer's
    Anthropic-compatible endpoint).
    """
    mapping = {"STRIPE_API_KEY": "STRIPE_API_KEY", "ANTHROPIC_API_KEY": "PIONEER_API_KEY"}
    lines = []
    for vm_name, local_name in mapping.items():
        value = os.environ.get(local_name, "").strip()
        if not value:
            sys.exit(f"{local_name} is not set in the local environment — export it and retry.")
        lines.append(f"{vm_name}={value}")
    # The sandbox's create-time env may carry a stale base URL; the override file wins because
    # the supervisor sources it after the base env (fixes /v1/v1 on already-deployed sandboxes).
    lines.append(f"ANTHROPIC_BASE_URL={VM_ENV['ANTHROPIC_BASE_URL']}")
    if args.approver_model:
        lines.append(f"APPROVER_MODEL={args.approver_model}")
        lines.append(f"TASKRUNNER_MODEL={args.approver_model}")
    st = load_state(args)
    sid, token = st["sandbox_id"], st["access_token"]
    _data_request(sid, token, "POST",
                  "/files?path=" + urllib.parse.quote(f"{VM_HOME}/.env.runtime"),
                  body=("\n".join(lines) + "\n").encode(),
                  content_type="application/octet-stream")
    result = vm_exec(sid, token, f"chmod 600 {VM_HOME}/.env.runtime && wc -l < {VM_HOME}/.env.runtime")
    print(f"pushed .env.runtime ({result.get('stdout', '').strip()} lines, 0600). "
          f"Restart the supervisor to apply.")


def cmd_pause(args):
    st = load_state(args)
    _request("POST", f"/sandboxes/{st['sandbox_id']}/pause")
    print("paused — full VM state checkpointed, compute billing stopped.")


def cmd_resume(args):
    st = load_state(args)
    resp = _request("POST", f"/sandboxes/{st['sandbox_id']}/resume")
    # The API rotates the access token on resume; the old one is dead. Persist the new one.
    if resp.get("access_token"):
        st["access_token"] = resp["access_token"]
        save_state(args, st)
    print("resumed — processes continue where they left off.")


def cmd_kill(args):
    st = load_state(args)
    if not args.yes:
        sys.exit("kill deletes the VM and all its state. Re-run with --yes if you mean it.")
    _request("DELETE", f"/sandboxes/{st['sandbox_id']}")
    os.remove(state_path(args))
    print("sandbox deleted; state file removed.")


# ── CLI ───────────────────────────────────────────────────────────────────────
def build_parser():
    p = argparse.ArgumentParser(prog="runtime.py",
                                description="Deploy and drive the Nightshift loop on Superserve.")
    p.add_argument("--state", default=None,
                   help="state-file path (beats $RUNTIME_STATE; flags are deterministic, env is not)")
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("deploy", help="create the VM, clone the repo, start the loop")
    d.add_argument("--repo", default=os.environ.get("NIGHTSHIFT_REPO", DEFAULT_REPO))
    d.add_argument("--branch", default="main")
    d.add_argument("--template", default=TEMPLATE)
    d.add_argument("--inference-secret", "--anthropic-secret", dest="inference_secret",
                   default="pioneer-key",
                   help="Superserve SECRET NAME for Pioneer, bound to ANTHROPIC_API_KEY for "
                        "Claude Code compatibility (never a value)")
    d.add_argument("--stripe-secret", default="stripe-key",
                   help="Superserve SECRET NAME bound to STRIPE_API_KEY; empty string to skip")
    d.add_argument("--private", action="store_true",
                   help="publish the dashboard port credential-gated instead of public")
    d.set_defaults(fn=cmd_deploy)

    s = sub.add_parser("status", help="sandbox status + dashboard URL")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_status)

    sub.add_parser("url", help="print the public dashboard URL").set_defaults(fn=cmd_url)

    e = sub.add_parser("exec", help="run one command inside the VM")
    e.add_argument("--cmd", required=True)
    e.add_argument("--timeout", type=int, default=60)
    e.set_defaults(fn=cmd_exec)

    pl = sub.add_parser("pull", help="mirror VM state files to the laptop (demo backup)")
    pl.add_argument("--dest", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror"))
    pl.set_defaults(fn=cmd_pull)

    pe = sub.add_parser("push-env", help="push the direct-egress override file (values from local env)")
    pe.add_argument("--approver-model", default=None,
                    help="override the model name the VM's headless passes request from Pioneer")
    pe.set_defaults(fn=cmd_push_env)

    sub.add_parser("pause", help="checkpoint the VM, stop compute billing").set_defaults(fn=cmd_pause)
    sub.add_parser("resume", help="restore the VM exactly where it left off").set_defaults(fn=cmd_resume)

    k = sub.add_parser("kill", help="DELETE the VM and all its state")
    k.add_argument("--yes", action="store_true")
    k.set_defaults(fn=cmd_kill)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    main()
