#!/usr/bin/env python3
"""
record_sales — US-1.2 glue. Every paid sale lands in the CRM ledger.

This is the Surya side of the payments <-> CRM lane seam: Anirudh's side (`pay.py`) never touches
`crm.py`, and this file never touches Stripe. It reads `pay.py sales --json` (the documented,
stdlib-only contract in `blocks/payments/code/pay.py`) and, for every sale not already recorded,
writes a project into `blocks/crm/code/crm.py` by calling crm.py's OWN CLI as a subprocess — the
exact same seam discipline pay.py itself uses for Stripe. `crm.py` is never imported and never
modified; every mutation goes through its documented argument names.

    record_sales.py run [--json] [--from-file PATH] [--crm-db PATH] [--state PATH]
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
def load_sales(from_file):
    """The documented `pay.py sales --json` shape: a list of {link_id, session_id, title,
    amount_usd, currency, paid_at}. `--from-file` (test/ops hook) substitutes a saved JSON dump for
    the live subprocess call — same shape, no network."""
    if from_file:
        try:
            with open(from_file, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise RecordSalesError(f"--from-file {from_file}: {e}")
    else:
        try:
            proc = subprocess.run([sys.executable, PAY_PY, "sales", "--json"],
                                   capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT)
        except OSError as e:
            raise RecordSalesError(f"could not run pay.py ({PAY_PY}): {e}")
        except subprocess.TimeoutExpired:
            raise RecordSalesError(f"pay.py sales timed out after {SUBPROCESS_TIMEOUT}s")
        if proc.returncode != 0:
            raise RecordSalesError(f"pay.py sales failed: {(proc.stderr or proc.stdout).strip()}")
        try:
            data = json.loads(proc.stdout)
        except ValueError as e:
            raise RecordSalesError(f"pay.py sales returned invalid JSON: {e}")
    if not isinstance(data, list):
        raise RecordSalesError(f"pay.py sales JSON must be a list (got {type(data).__name__})")
    return data


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
def cmd_run(a):
    state_path = resolve_state_path(a.state)
    ensure_crm_ready(a.crm_db)

    sales = load_sales(a.from_file)
    entries = read_state(state_path)
    already = {e["session_id"] for e in entries if e.get("status") == "recorded"}

    new_sales = [s for s in sales if s.get("session_id") not in already]

    recorded, failed = [], []
    if new_sales:
        company_id = resolve_company_id(a.crm_db, state_path)
        for sale in new_sales:
            crm_project_id, err = record_one(a.crm_db, company_id, sale)
            if err is not None:
                print(f"ERROR: could not record sale {sale.get('session_id')}: {err}",
                      file=sys.stderr)
                failed.append({"session_id": sale.get("session_id"), "link_id": sale.get("link_id"),
                                "error": err})
                continue
            entry = {
                "ts": now_iso(),
                "session_id": sale.get("session_id"),
                "link_id": sale.get("link_id"),
                "amount_usd": sale.get("amount_usd"),
                "currency": sale.get("currency"),
                "crm_project_id": crm_project_id,
                "status": "recorded",
            }
            append_state_entry(state_path, entry)   # only AFTER the CRM write succeeded
            recorded.append(entry)

    skipped = sorted(already & {s.get("session_id") for s in sales})

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
    # Test/ops hook, not part of the documented seam — see module docstring.
    s.add_argument("--from-file", default=None, help=argparse.SUPPRESS)
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
