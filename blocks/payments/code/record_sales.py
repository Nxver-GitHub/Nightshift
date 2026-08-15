#!/usr/bin/env python3
"""
record_sales — US-1.2 glue. Every paid sale lands in the CRM ledger.

This is the Surya side of the payments <-> CRM lane seam: Anirudh's side (`pay.py`) never touches
`crm.py`, and this file never touches Stripe. It reads `pay.py sales --json` (the documented,
stdlib-only contract in `blocks/payments/code/pay.py`) and, for every sale not already recorded,
writes a project into `blocks/crm/code/crm.py` by calling crm.py's OWN CLI as a subprocess — the
exact same seam discipline pay.py itself uses for Stripe. `crm.py` is never imported and never
modified; every mutation goes through its documented argument names.

    record_sales.py run [--json] [--providers stripe,whop] [--crm-db PATH] [--state PATH]
    record_sales.py log [--json] [--state PATH]

Design notes:
- **Stateless-ish, like pay.py.** The CRM database IS the ledger of record for revenue. This file
  keeps only a small local journal (`recorded.jsonl` by default) whose sole job is idempotency: a
  session_id already marked "recorded" is never recorded twice, even across runs, even from a
  cron/scheduled-tasks job. That journal is NOT a second source of truth about revenue — it is a
  seen-list, the same role `hires.jsonl` plays in `blocks/labor/code/labor.py`.
- **Company resolution has to be cached, not queried.** crm.py's CLI has no "find company by
  name" command (by design — see crm.py's docstring: companies/contacts/projects, no query verb).
  So the "Direct sales" company is created once via `add-company`, and its id is cached in a tiny
  sidecar file next to the state file (`<state>.company.json`). Every later run reuses that id
  without touching the CRM again for company lookup. If the CRM database is ever reset independently
  of this cache, delete the sidecar file too — that is the one manual step this design asks for.
- **`--stage won` is an OPEN stage in crm.py** (`OPEN_STAGES` includes "won"; only "delivered" and
  "lost" are terminal), so `project-add --stage won` requires `--next` / `--next-date` or crm.py's
  own `_require_next` refuses it ("an open project needs --next and --next-date (nothing sleeps)").
  Every project this tool creates therefore carries a real next action ("fulfil order", due today)
  — that is crm.py's own non-negotiable rule, not an invention here.
- **Partial failure is per-sale, not all-or-nothing.** If crm.py exits nonzero recording one sale
  (e.g. an unparseable amount), that sale is skipped — nothing is appended to the state file for
  it — so it is retried automatically on the next run. Every OTHER sale in the same run still gets
  recorded. The process exits 1 at the end so a scheduler notices, but nothing already-succeeded is
  lost or reprocessed.
- **One rail per `pay.py sales` call — hence `--providers`.** `pay.py sales` answers for exactly
  one provider, whichever `PAYMENT_PROVIDER` names. With Stripe primary and Whop as a second shelf,
  a single call means every Whop sale is invisible to the CRM and the dashboard shows one rail's
  revenue. `--providers stripe,whop` runs the subprocess once per rail with `PAYMENT_PROVIDER` set
  in the child environment, and tags each sale with the rail it came from. Omitting the flag keeps
  the old behaviour exactly: one call, ambient provider, `provider: null` in the journal.
  A rail that cannot answer (Whop with no key) is a per-rail failure, never fatal to the others —
  the primary rail keeps recording and the run exits 1 so a scheduler notices.
- **Idempotency is keyed on (provider, session_id)**, not session_id alone: ids are only unique
  within a provider, and a cross-rail collision must not make a real sale vanish. Journal entries
  written before this flag existed carry no provider; their ids suppress a match on ANY rail, so
  upgrading never re-records history as duplicate revenue. See `already_recorded()`.
- **`--from-file` is a test/ops hook**, not part of the documented seam: it substitutes a JSON file
  (the same shape as `pay.py sales --json`) for the live subprocess call, so tests never touch the
  network and an operator can replay a saved sales dump if `pay.py` is ever unreachable.

Config (names only — values live in the environment, never in this repo):
    PAYMENTS_RECORDED   this block's own state file (default: recorded.jsonl next to this script)
    CRM_DB              honoured by crm.py itself; also settable per-run via --crm-db here
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAY_PY = os.path.join(HERE, "pay.py")
CRM_PY = os.path.abspath(os.path.join(HERE, "..", "..", "crm", "code", "crm.py"))

DIRECT_SALES_COMPANY = "Direct sales"
NEXT_ACTION_TEXT = "Fulfil order"          # crm.py requires a next action for an open stage ("won")
NEXT_ACTION_DAYS = 0                        # due today: a paid retail order should ship immediately
SUBPROCESS_TIMEOUT = 60                     # seconds; a cron job must never hang forever on this seam

COMPANY_ID_RE = re.compile(r"OK company #(\d+)")
PROJECT_ID_RE = re.compile(r"OK project #(\d+)")


class RecordSalesError(Exception):
    """Anything the operator needs to read on stderr. Fatal preconditions only — see main()."""


# ── path resolution ──────────────────────────────────────────────────────────
def resolve_state_path(arg=None):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("PAYMENTS_RECORDED")
    if env:
        return os.path.abspath(env)
    return os.path.join(HERE, "recorded.jsonl")


def company_cache_path(state_path):
    return state_path + ".company.json"


def resolve_crm_db(crm_db_arg):
    """Mirrors crm.py's own `db_path()` precedence (--db arg > $CRM_DB > script-relative default)
    ONLY so this tool can decide whether the database file exists yet (to trigger `init`). This is
    intentionally a tiny duplicate of a five-line pure function, not an import of crm.py — the two
    blocks stay decoupled and every CRM mutation still goes through crm.py's own CLI."""
    if crm_db_arg:
        return os.path.abspath(crm_db_arg)
    env = os.environ.get("CRM_DB")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(CRM_PY), "crm.db")


# ── state file (this block's own seen-list; not a second source of truth) ───
def read_state(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    except OSError:
        return []


def append_state_entry(path, entry):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def today_iso():
    return datetime.date.today().isoformat()


# ── subprocess wrappers — every crm.py mutation goes through its own CLI ────
def crm_invoke(crm_db_arg, args):
    """Run crm.py as a subprocess with the given subcommand args. `--db` is passed through only
    when `--crm-db` was given explicitly here; otherwise crm.py reads $CRM_DB (inherited) or falls
    back to its own default, exactly as crm.py's own precedence documents."""
    cmd = [sys.executable, CRM_PY]
    if crm_db_arg:
        cmd += ["--db", crm_db_arg]
    cmd += args
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
    except OSError as e:
        raise RecordSalesError(f"could not run crm.py ({CRM_PY}): {e}")
    except subprocess.TimeoutExpired:
        raise RecordSalesError(f"crm.py {' '.join(args)} timed out after {SUBPROCESS_TIMEOUT}s")


def ensure_crm_ready(crm_db_arg):
    """crm.py's `connect()` creates its schema with CREATE TABLE IF NOT EXISTS on every command, so
    strictly nothing here is required for correctness — but running `init` explicitly first (a) is
    itself idempotent (see crm.py's cmd_init: it only prints "OK CRM ready"), and (b) fails loudly,
    before any sale-affecting call, if crm.py itself cannot be run at all (bad interpreter, missing
    file, unwritable directory). That is the safer of the two options the story asks to pick between."""
    db_path = resolve_crm_db(crm_db_arg)
    if os.path.exists(db_path):
        return
    proc = crm_invoke(crm_db_arg, ["init"])
    if proc.returncode != 0:
        raise RecordSalesError(
            f"crm.py init failed — cannot record sales without a CRM database: "
            f"{(proc.stderr or proc.stdout).strip()}")


def resolve_company_id(crm_db_arg, state_path):
    """Create-or-reuse the one company retail sales land under. crm.py has no "find company by
    name" verb, so the id is cached next to the state file after the one-time `add-company` call."""
    cache_path = company_cache_path(state_path)
    try:
        with open(cache_path, encoding="utf-8") as f:
            cached = json.load(f)
        cid = cached.get("company_id")
        if isinstance(cid, int):
            return cid
    except (OSError, ValueError):
        pass

    proc = crm_invoke(crm_db_arg, [
        "add-company", "--name", DIRECT_SALES_COMPANY, "--status", "client", "--source", "retail",
    ])
    if proc.returncode != 0:
        raise RecordSalesError(
            f"could not create the '{DIRECT_SALES_COMPANY}' CRM company: "
            f"{(proc.stderr or proc.stdout).strip()}")
    m = COMPANY_ID_RE.search(proc.stdout)
    if not m:
        raise RecordSalesError(
            f"crm.py add-company succeeded but its id could not be parsed from stdout: "
            f"{proc.stdout.strip()!r}")
    cid = int(m.group(1))
    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"company_id": cid, "name": DIRECT_SALES_COMPANY, "created_at": now_iso()}, f)
    return cid


# ── pay.py side ───────────────────────────────────────────────────────────────
# Mirrors the keys of pay.py's own DRIVERS dict. Duplicated deliberately rather than imported:
# this file's whole discipline is that it talks to pay.py through its CLI and never imports it
# (see the module docstring). The cost of the duplication is this list going stale; the check it
# buys is rejecting a typo'd rail name before a single CRM row is written.
KNOWN_PROVIDERS = ("stripe", "whop", "dodo")


def parse_providers(raw):
    """`--providers stripe,whop` -> ["stripe", "whop"]. None means the legacy single-rail path."""
    if raw is None:
        return None
    names = [n.strip().lower() for n in raw.split(",") if n.strip()]
    if not names:
        raise RecordSalesError("--providers was empty — name at least one rail, e.g. stripe,whop")
    unknown = [n for n in names if n not in KNOWN_PROVIDERS]
    if unknown:
        raise RecordSalesError(
            f"unknown provider(s) {', '.join(unknown)} — expected from: {', '.join(KNOWN_PROVIDERS)}")
    seen, ordered = set(), []
    for n in names:                       # order preserved, duplicates dropped: naming a rail
        if n not in seen:                 # twice must not double-scan it
            seen.add(n)
            ordered.append(n)
    return ordered


def _run_pay_sales(pay_py, provider):
    """One `pay.py sales --json` call. `provider` None = inherit the ambient PAYMENT_PROVIDER.

    The fan-out lives here, in the environment of the subprocess: `pay.py sales` answers for exactly
    ONE rail — whichever PAYMENT_PROVIDER names — so reading two rails means running it twice.
    """
    child_env = dict(os.environ)
    if provider is not None:
        child_env["PAYMENT_PROVIDER"] = provider
    try:
        proc = subprocess.run([sys.executable, pay_py, "sales", "--json"],
                               capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT,
                               env=child_env)
    except OSError as e:
        raise RecordSalesError(f"could not run pay.py ({pay_py}): {e}")
    except subprocess.TimeoutExpired:
        raise RecordSalesError(f"pay.py sales timed out after {SUBPROCESS_TIMEOUT}s")
    if proc.returncode != 0:
        raise RecordSalesError(f"pay.py sales failed: {(proc.stderr or proc.stdout).strip()}")
    try:
        data = json.loads(proc.stdout)
    except ValueError as e:
        raise RecordSalesError(f"pay.py sales returned invalid JSON: {e}")
    return data


def _as_sales_list(data, source):
    if not isinstance(data, list):
        raise RecordSalesError(f"{source} JSON must be a list (got {type(data).__name__})")
    return data


def load_sales(from_file, providers=None, pay_py=PAY_PY):
    """Every paid sale across the rails we were asked to read.

    Returns (sales, failures). Each sale carries a `provider` key: the rail it came from, or None
    on the legacy single-rail path (which keeps the ambient PAYMENT_PROVIDER and stays byte-for-byte
    the behaviour it had before this flag existed).

    A rail that fails to answer is collected into `failures` rather than raised — Whop with no key
    must never cost us a Stripe sale. The run still exits 1 so a scheduler notices.
    """
    if from_file:
        try:
            with open(from_file, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise RecordSalesError(f"--from-file {from_file}: {e}")
        return [dict(s, provider=s.get("provider")) for s in
                _as_sales_list(data, f"--from-file {from_file}")], []

    if providers is None:                                   # legacy path: one call, ambient rail
        return [dict(s, provider=None) for s in
                _as_sales_list(_run_pay_sales(pay_py, None), "pay.py sales")], []

    sales, failures = [], []
    for provider in providers:
        try:
            data = _as_sales_list(_run_pay_sales(pay_py, provider), f"pay.py sales [{provider}]")
        except RecordSalesError as e:
            print(f"ERROR: rail '{provider}' could not be read: {e}", file=sys.stderr)
            failures.append({"provider": provider, "error": str(e)})
            continue
        sales.extend(dict(s, provider=provider) for s in data)
    return sales, failures


def short_id(session_id):
    """Last 8 chars of the session id — enough to disambiguate two sales of the same product
    without making the CRM project title unreadable."""
    sid = str(session_id or "")
    return sid[-8:] if len(sid) > 8 else sid


# ── recording ─────────────────────────────────────────────────────────────────
def record_one(crm_db_arg, company_id, sale):
    """Create ONE CRM project for one paid sale via crm.py's real CLI. Returns
    (crm_project_id_or_None, error_or_None) — never raises for a per-sale failure, so the caller
    can continue with the rest of the batch."""
    title = f"{(sale.get('title') or 'Sale').strip()} — {short_id(sale.get('session_id'))}"
    proc = crm_invoke(crm_db_arg, [
        "project-add",
        "--company", str(company_id),
        "--title", title,
        "--stage", "won",
        "--amount", str(sale.get("amount_usd")),
        "--next", NEXT_ACTION_TEXT,
        "--next-date", today_iso(),
    ])
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout).strip() or f"crm.py exited {proc.returncode}"
    m = PROJECT_ID_RE.search(proc.stdout)
    return (int(m.group(1)) if m else None), None


# ── commands ──────────────────────────────────────────────────────────────────
def already_recorded(entries):
    """The idempotency predicate, as a function, because the key changed and the change is subtle.

    Dedupe is on **(provider, session_id)**, not session_id alone: session ids are only unique
    WITHIN a provider, so two rails could in principle collide and one real sale would silently
    vanish. Journal entries written before `--providers` existed carry no provider, so their ids
    also suppress a matching sale on ANY rail — without that, the first run after this upgrade
    would re-record every historical sale into the CRM as a duplicate.
    """
    recorded = [e for e in entries if e.get("status") == "recorded"]
    pairs = {(e.get("provider"), e.get("session_id")) for e in recorded}
    legacy_ids = {e.get("session_id") for e in recorded if e.get("provider") is None}

    def seen(sale):
        sid = sale.get("session_id")
        return (sale.get("provider"), sid) in pairs or sid in legacy_ids

    return seen


def cmd_run(a):
    state_path = resolve_state_path(a.state)
    providers = parse_providers(a.providers)
    ensure_crm_ready(a.crm_db)

    sales, failed = load_sales(a.from_file, providers, a.pay_py or PAY_PY)
    entries = read_state(state_path)
    seen = already_recorded(entries)

    new_sales = [s for s in sales if not seen(s)]

    recorded = []
    if new_sales:
        company_id = resolve_company_id(a.crm_db, state_path)
        for sale in new_sales:
            crm_project_id, err = record_one(a.crm_db, company_id, sale)
            if err is not None:
                print(f"ERROR: could not record sale {sale.get('session_id')}: {err}",
                      file=sys.stderr)
                failed.append({"session_id": sale.get("session_id"), "link_id": sale.get("link_id"),
                                "provider": sale.get("provider"), "error": err})
                continue
            entry = {
                "ts": now_iso(),
                "session_id": sale.get("session_id"),
                "link_id": sale.get("link_id"),
                "provider": sale.get("provider"),   # provenance: which rail this sale came from
                "amount_usd": sale.get("amount_usd"),
                "currency": sale.get("currency"),
                "crm_project_id": crm_project_id,
                "status": "recorded",
            }
            append_state_entry(state_path, entry)   # only AFTER the CRM write succeeded
            recorded.append(entry)

    skipped = sorted({s.get("session_id") for s in sales if seen(s)})

    if a.json:
        print(json.dumps({"recorded": recorded, "already_recorded": skipped, "failed": failed},
                          indent=2))
    else:
        for e in recorded:
            print(f"  OK {e['session_id']}  -> CRM project #{e['crm_project_id']}  "
                  f"(${e['amount_usd']} {(e['currency'] or '').upper()})  [{DIRECT_SALES_COMPANY}]")
        if not new_sales:
            print("No new paid sales.")
        print(f"recorded {len(recorded)}, already recorded {len(skipped)}, failed {len(failed)}")

    return 1 if failed else 0


def cmd_log(a):
    entries = read_state(resolve_state_path(a.state))
    if a.json:
        print(json.dumps(entries, ensure_ascii=False, indent=2))
        return 0
    if not entries:
        print("(no sales recorded yet)", file=sys.stderr)
        return 0
    for e in entries:
        print(f"  {e.get('ts')}  {e.get('session_id')}  ${e.get('amount_usd')} "
              f"{(e.get('currency') or '').upper()}  crm_project=#{e.get('crm_project_id')}  "
              f"[{e.get('status')}]")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        description="US-1.2 glue — every paid sale lands in the CRM ledger.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("run", help="record every new paid sale into the CRM")
    s.add_argument("--json", action="store_true")
    s.add_argument("--crm-db", default=None,
                    help="passed through to crm.py as --db (else crm.py honours $CRM_DB)")
    s.add_argument("--state", default=None,
                    help="override this block's state file (else $PAYMENTS_RECORDED or default)")
    s.add_argument("--providers", default=None,
                    help=f"comma-separated rails to read, e.g. stripe,whop "
                         f"(from: {', '.join(KNOWN_PROVIDERS)}). Omit to read the single rail named "
                         f"by $PAYMENT_PROVIDER, as before.")
    # Test/ops hooks, not part of the documented seam — see module docstring.
    s.add_argument("--from-file", default=None, help=argparse.SUPPRESS)
    s.add_argument("--pay-py", default=None, help=argparse.SUPPRESS)
    s.set_defaults(f=cmd_run)

    s = sub.add_parser("log", help="dump this block's recorded-sales journal")
    s.add_argument("--json", action="store_true")
    s.add_argument("--state", default=None)
    s.set_defaults(f=cmd_log)

    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        sys.exit(a.f(a))
    except RecordSalesError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
