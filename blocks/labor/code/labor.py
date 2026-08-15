#!/usr/bin/env python3
"""
labor — the human-judgment supply chain. When the approver hits a question no policy clause covers,
this block buys ONE bounded human judgment and writes the answer back at the same interface.

The hired human is a **substitute approver for one decision**, never a worker. They read the exact
question the taskrunner asked and return a verdict plus one paragraph of reasoning. They never touch
the task, never do the work, never see anything but the question. That boundary is the product: the
company buys judgment by the decision, not labor by the hour (an expert at $60–220/hr as COGS kills
the unit economics; as an escalation path it costs one ceiling-bounded decision).

Where the answer lands matters as much as what it says:
- The **task** gets exactly the two fields a human owner would have typed (`question.answer`,
  `question.answered_at`) — under the taskrunner's own lock, written like `approve.py` writes them,
  so `update_task.py --consume-question` cannot tell the difference. Zero upstream modification.
- The **approver's own ledger** (`decisions.jsonl`) gets the decision with `mode: "human"`. One
  ledger, two kinds of entries. Reading it top to bottom shows where the policy decided and where
  the policy ran out and the company paid for a human — that contrast IS the audit trail.

The money clause is not special-cased. A hire is an outgoing spend, so it obeys the same
`per_action_spend_ceiling_usd` (P2) as every other payment. There is no "but this one is about
judgment" exception — an autonomy layer that exempts its own supply chain from its own spend gate
has no spend gate.

Usage:  python3 labor.py <command> [options]
  pending  [--json]                                  escalations awaiting a human
  submit   --id TASK_ID --cost COST_USD [--context TEXT]
  collect  --id TASK_ID [--answer "approve: reasoning"]
  log      [--json]                                  this block's hire log

Config (names only — values live in the environment, never in this repo):
  LABOR_PROVIDER    manual (default) | terac
  TERAC_API_KEY     reserved for the terac driver; read at call time, never logged
  APPROVER_LEDGER   the approver's decisions.jsonl — read for escalations, appended on collect
  APPROVER_POLICY   the written policy; its frontmatter carries the spend ceiling that gates a hire
  TASKRUNNER_TASKS  the kanban shared with the taskrunner
  LABOR_HIRES       this block's own state: hires.jsonl (default: next to this script)
"""
import argparse
import datetime
import fcntl
import json
import os
import sys
import time
from typing import Optional, TextIO, Tuple

VERDICTS = ["approve", "reject"]
LOCK_TRIES = 50          # same budget as the taskrunner: 50 x 0.1s = 5s before giving up
LOCK_SLEEP = 0.1
DEFAULT_PROVIDER = "manual"
CEILING_KEY = "per_action_spend_ceiling_usd"
ANSWER_SUFFIX = " [via hired expert]"    # every hired answer is labelled ON the card, not just in a log


class LaborError(Exception):
    """Anything the operator must read on stderr. Never carries a key or a key fragment."""


# ── path resolution — identical order to the approver, so both land on the same files ─────────
def resolve_tasks(arg: Optional[str] = None) -> str:
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("TASKRUNNER_TASKS")
    if env:
        return os.path.abspath(env)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "taskrunner", "code", "tasks.json"))


def resolve_ledger() -> str:
    """The APPROVER's ledger, deliberately. This block does not keep a second decision log —
    two ledgers of decisions is how an audit trail stops being one."""
    env = os.environ.get("APPROVER_LEDGER")
    if env:
        return os.path.abspath(env)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "approver", "code", "decisions.jsonl"))


def resolve_hires() -> str:
    env = os.environ.get("LABOR_HIRES")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "hires.jsonl")


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def fmt_usd(value: float) -> str:
    """12.0 -> '12', 12.50 -> '12.5'. The journal line is read by a human, not parsed."""
    return f"{value:g}"


# ── the money gate ────────────────────────────────────────────────────────────────────────────
def parse_ceiling(policy_path: Optional[str] = None) -> float:
    """Read `per_action_spend_ceiling_usd` from the policy's flat 'key: value' frontmatter.

    No YAML parser (stdlib only, and the frontmatter is deliberately flat). A missing policy, a
    missing key or an unreadable value is a HARD failure, never a default: a ceiling this code
    invented would be a ceiling nobody wrote.
    """
    path = policy_path or os.environ.get("APPROVER_POLICY")
    if not path:
        raise LaborError(
            "APPROVER_POLICY is not set — a hire is an outgoing spend and cannot be gated without "
            "the written policy's per_action_spend_ceiling_usd. Refusing to hire.")
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError as e:
        raise LaborError(f"cannot read APPROVER_POLICY ({e}) — refusing to hire without a ceiling.")
    if not lines or lines[0].strip() != "---":
        raise LaborError(
            f"{CEILING_KEY} not found: the policy has no '---' frontmatter block. Refusing to hire.")
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, raw = line.partition(":")
        if key.strip() != CEILING_KEY:
            continue
        try:
            return float(raw.strip())
        except ValueError:
            raise LaborError(f"{CEILING_KEY} in the policy is not a number ('{raw.strip()}').")
    raise LaborError(
        f"{CEILING_KEY} is missing from the policy frontmatter — refusing to hire without a ceiling.")


def parse_cost(raw: str) -> float:
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        raise LaborError(f"--cost must be a number in whole dollars (got '{raw}')")
    if value != value or value in (float("inf"), float("-inf")) or value <= 0:
        raise LaborError(f"--cost must be greater than 0 (got '{raw}')")
    return value


# ── files ─────────────────────────────────────────────────────────────────────────────────────
def read_tasks_soft(path: str) -> list:
    """`pending` must never be blocked by a config gap — warn and show an empty queue instead."""
    try:
        return json.load(open(path)).get("tasks", [])
    except (OSError, ValueError):
        print(f"WARNING: no kanban at {path} — cannot tell which escalations are still open.",
              file=sys.stderr)
        return []


def read_ledger_soft(path: str) -> list:
    try:
        return [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]
    except (OSError, ValueError):
        print(f"WARNING: no approver ledger at {path} — escalations are read from it; nothing to show.",
              file=sys.stderr)
        return []


def read_hires() -> list:
    try:
        return [json.loads(x) for x in open(resolve_hires(), encoding="utf-8") if x.strip()]
    except (OSError, ValueError):
        return []


def append_hire(entry: dict) -> None:
    path = resolve_hires()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def rewrite_hires(entries: list) -> None:
    """A hire's `status` is the one mutable field (submitted -> answered), so this file is rewritten
    atomically rather than appended. The DECISION it produced is immutable — it lives in the
    approver's append-only ledger, which is never rewritten by anything."""
    path = resolve_hires()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def ledger_append(entry: dict) -> None:
    path = resolve_ledger()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def acquire_lock(lock_path: str) -> TextIO:
    """Inter-process lock shared with add_task.py / update_task.py / approve.py."""
    fd = open(lock_path, "w")
    for _ in range(LOCK_TRIES):
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            time.sleep(LOCK_SLEEP)
    print("ERROR: tasks.json locked too long, retry.", file=sys.stderr)
    sys.exit(1)


def is_open_question(t: dict) -> bool:
    q = t.get("question")
    return t.get("status") == "waiting_owner" and bool(q) and q.get("answer") is None


# ── drivers ───────────────────────────────────────────────────────────────────────────────────
# A driver is two functions. `submit` opens the hire with whoever supplies the human; `collect`
# returns (verdict, reasoning). Everything after that — the card, the ledger, the money gate — is
# provider-independent, so adding a rail is filling in two functions, not a refactor.
def manual_submit(task_id: str, question: str, context: str, cost: float) -> None:
    """REAL tonight, and the permanent fallback when any API is down. The 'API' is a human relay."""
    print(f"\nHIRE OPEN — {task_id}   (${fmt_usd(cost)}, one bounded judgment)")
    print("\nRelay this to any human expert. They answer the question; they do NOT do the task.\n")
    print("  QUESTION")
    for line in (question or "(no question text)").splitlines() or [""]:
        print(f"    {line}")
    if context:
        print("\n  CONTEXT")
        for line in context.splitlines():
            print(f"    {line}")
    print("\n  They must return exactly one verdict plus one paragraph of reasoning.")
    print("  Bring it back with:\n")
    print(f"    labor.py collect --id {task_id} --answer '<approve|reject>: <reasoning>'\n")


def manual_collect(task_id: str, answer: Optional[str], cost: float) -> Tuple[str, str]:
    """Parse the expert's verdict prefix. Anything ambiguous is rejected outright rather than
    guessed — a misread verdict would write the WRONG decision onto a live card."""
    if answer is None:
        raise LaborError(
            "the manual driver needs the expert's words: "
            "--answer '<approve|reject>: <reasoning>'")
    verdict, sep, reasoning = answer.partition(":")
    verdict, reasoning = verdict.strip().lower(), reasoning.strip()
    if not sep or verdict not in VERDICTS:
        raise LaborError(
            f"--answer must start with a verdict: \"approve: <reasoning>\" or "
            f"\"reject: <reasoning>\" (got '{answer[:60]}'). Not guessing what the expert meant.")
    if not reasoning:
        raise LaborError(
            "--answer carries a verdict but no reasoning — the reasoning goes on the card and into "
            "the ledger; a verdict without it is not an audit trail.")
    return verdict, reasoning


# Terac offers two integration surfaces (HACKATHON.md): a REST API and an MCP server. Either one
# fills the two functions below — REST from here directly, MCP by having the labor skill call the
# tools and hand the result to `collect --answer`. Structure is ready; only the calls are missing.
def _terac_unavailable(*_args, **_kwargs):
    raise LaborError(
        "terac driver awaits TERAC_API_KEY + API docs (sponsor Slack, 8:30am) — structure ready, "
        "fill submit/collect")


DRIVERS = {
    "manual": {"submit": manual_submit, "collect": manual_collect},
    "terac": {"submit": _terac_unavailable, "collect": _terac_unavailable},
}


def get_driver() -> Tuple[str, dict]:
    name = (os.environ.get("LABOR_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if name not in DRIVERS:
        raise LaborError(
            f"unknown LABOR_PROVIDER '{name}' — expected one of: {', '.join(sorted(DRIVERS))}")
    return name, DRIVERS[name]


# ── commands ──────────────────────────────────────────────────────────────────────────────────
def cmd_pending(a: argparse.Namespace) -> int:
    """An escalation is open when the approver logged it, the task still carries an unanswered
    question, and this block has not already bought an answer for it."""
    entries = read_ledger_soft(resolve_ledger())
    tasks = {t.get("id"): t for t in read_tasks_soft(resolve_tasks(a.tasks))}
    resolved = {h.get("task_id") for h in read_hires() if h.get("status") == "answered"}
    open_hires = {h.get("task_id") for h in read_hires() if h.get("status") == "submitted"}

    rows, seen = [], set()
    for e in reversed(entries):                 # newest escalation wins if a task escalated twice
        tid = e.get("task_id")
        if e.get("verdict") != "escalated" or tid in seen or tid in resolved:
            continue
        t = tasks.get(tid)
        if not t or not is_open_question(t):    # answered or moved on since the escalation
            continue
        seen.add(tid)
        rows.append({
            "id": tid,
            "title": t.get("title", ""),
            "question": (t.get("question") or {}).get("text", "") or e.get("question", ""),
            "escalated_at": e.get("ts"),
            "escalation_reason": e.get("reason", ""),
            "hire_status": "submitted" if tid in open_hires else None,
        })
    rows.reverse()                              # oldest first: the queue a human works top-down

    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("No escalation waiting on a human.")
        return 0
    print(f"\nEscalated — policy could not decide ({len(rows)})")
    for r in rows:
        tail = "  [hire open]" if r["hire_status"] else ""
        print(f"  {r['id']}  {r['title']}{tail}")
        print(f"      escalated {r['escalated_at'] or '—'}: {r['escalation_reason']}")
        head = r["question"].splitlines()[0] if r["question"] else ""
        print(f"      asks: {head}")
    print()
    return 0


def cmd_submit(a: argparse.Namespace) -> int:
    cost = parse_cost(a.cost)

    # THE GATE, before anything else happens. A hire is an outgoing spend like any other, so it
    # obeys the same clause (P2) — the human-judgment supply chain is not exempt from the money
    # rules it exists to serve. Refused here means: nothing printed to an expert, nothing recorded.
    ceiling = parse_ceiling()
    if cost > ceiling:
        raise LaborError(
            f"${fmt_usd(cost)} exceeds the policy's {CEILING_KEY} of ${fmt_usd(ceiling)} (P2) — "
            f"buying human judgment obeys the same spend clause as every other payment. "
            f"No hire opened. Lower the cost, or take this escalation to the founder.")

    tid = a.id
    t = next((t for t in read_tasks_soft(resolve_tasks(a.tasks)) if t.get("id") == tid), None)
    if t is None:
        raise LaborError(f"task {tid} not found.")
    if not is_open_question(t):
        raise LaborError(
            f"task {tid} is '{t.get('status')}' with no unanswered question — there is nothing for "
            f"an expert to decide. Nothing spent.")
    if any(h.get("task_id") == tid and h.get("status") == "submitted" for h in read_hires()):
        raise LaborError(
            f"a hire is already open for {tid} — one bounded judgment per escalation. "
            f"Collect it (labor.py collect --id {tid}) before opening another.")

    question = (t.get("question") or {}).get("text", "")
    provider, driver = get_driver()
    context = (a.context or "").strip()

    # Driver first, record second: a driver that cannot accept the hire must not leave a phantom
    # open hire in the state file blocking every later attempt.
    driver["submit"](tid, question, context, cost)
    append_hire({"ts": now(), "task_id": tid, "question": question, "provider": provider,
                 "cost_usd": cost, "status": "submitted", "answer": None, "answered_at": None})
    print(f"OK {tid} — hire submitted to {provider} at ${fmt_usd(cost)} "
          f"(ceiling ${fmt_usd(ceiling)}). Task untouched until the answer comes back.")
    return 0


def cmd_collect(a: argparse.Namespace) -> int:
    tid = a.id
    hires = read_hires()
    hire = next((h for h in reversed(hires)
                 if h.get("task_id") == tid and h.get("status") == "submitted"), None)
    if hire is None:
        raise LaborError(
            f"no open hire for {tid} — submit one first (labor.py submit --id {tid} --cost N).")

    provider, driver = get_driver()
    cost = float(hire.get("cost_usd") or 0)
    # Obtain the judgment BEFORE taking the lock: a human (or a network) must never be the reason
    # the taskrunner's kanban is held.
    verdict, reasoning = driver["collect"](tid, a.answer, cost)

    tasks_path = resolve_tasks(a.tasks)
    lock_fd = acquire_lock(tasks_path + ".lock")
    try:
        d = json.load(open(tasks_path))   # re-read under lock, just before writing
        t = next((t for t in d["tasks"] if t["id"] == tid), None)
        if t is None:
            print(f"ERROR: task {tid} not found.", file=sys.stderr)
            return 1
        if t.get("status") != "waiting_owner":
            print(f"ABORT: task {tid} is '{t.get('status')}', not 'waiting_owner' — nothing to "
                  f"answer (the task moved; re-read the kanban).", file=sys.stderr)
            return 2
        q = t.get("question")
        if not q:
            print(f"ERROR: task {tid} has no active question.", file=sys.stderr)
            return 1
        if q.get("answer") is not None:
            print(f"ERROR: task {tid} was already answered at {q.get('answered_at') or '—'} — "
                  f"refusing to overwrite an owner's answer.", file=sys.stderr)
            return 1

        # Exactly the two fields a human owner would have typed — nothing else. Not the status:
        # the taskrunner moves the task itself when it consumes the answer.
        verdict_word = "APPROVED" if verdict == "approve" else "REJECTED"
        q["answer"] = f"{verdict_word} — {reasoning}{ANSWER_SUFFIX}"
        q["answered_at"] = now()
        # No setdefault: journal is a schema invariant (add_task.py always creates it).
        t["journal"].append(
            f"{now()} — answered via hired human expert ({provider}, ${fmt_usd(cost)})")

        tmp = tasks_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, tasks_path)      # atomic swap
        question_text = q.get("text", "")
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

    # Same guarantee as approve.py: a decision live on a card with no audit entry breaks this
    # block's whole point, so a ledger failure is loud and distinct (exit 3), never a traceback.
    try:
        ledger_append({"ts": now(), "task_id": tid, "question": question_text, "verdict": verdict,
                       "reason": reasoning, "policy_clauses_cited": [], "mode": "human",
                       "cost_usd": cost, "provider": provider})
    except OSError as e:
        print(f"ERROR: the expert's answer for {tid} IS live in the kanban, but the ledger write "
              f"FAILED: {e} — append this decision to the ledger manually before the next pass.",
              file=sys.stderr)
        return 3

    hire["status"] = "answered"
    hire["answer"] = f"{verdict}: {reasoning}"
    hire["answered_at"] = now()
    rewrite_hires(hires)
    print(f"OK {tid} — {verdict_word} by hired expert ({provider}, ${fmt_usd(cost)}); "
          f"status unchanged: waiting_owner")
    return 0


def cmd_log(a: argparse.Namespace) -> int:
    hires = read_hires()
    if a.json:
        print(json.dumps(hires, ensure_ascii=False, indent=2))
        return 0
    if not hires:
        print("(no hires yet)", file=sys.stderr)
        return 0
    for h in hires:
        print(f"  {h.get('ts')}  {h.get('task_id')}  [{h.get('status')}]  "
              f"{h.get('provider')}  ${fmt_usd(float(h.get('cost_usd') or 0))}  "
              f"{h.get('answer') or '—'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Buy one bounded human judgment when the policy cannot decide.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("pending", help="escalations awaiting a human")
    s.add_argument("--tasks", default=None)
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_pending)

    s = sub.add_parser("submit", help="open a hire for one escalated question")
    s.add_argument("--id", required=True)
    # A string, not type=float: we validate it ourselves so a bad cost exits 1, not argparse's 2.
    s.add_argument("--cost", required=True, metavar="COST_USD",
                   help="what this one judgment costs, in dollars — gated by the policy ceiling")
    s.add_argument("--context", default=None,
                   help="what the expert needs to decide — never a secret, never a credential")
    s.add_argument("--tasks", default=None)
    s.set_defaults(f=cmd_submit)

    s = sub.add_parser("collect", help="write the expert's verdict back onto the card")
    s.add_argument("--id", required=True)
    s.add_argument("--answer", default=None, metavar="TEXT",
                   help="the expert's words: 'approve: <reasoning>' or 'reject: <reasoning>'")
    s.add_argument("--tasks", default=None)
    s.set_defaults(f=cmd_collect)

    s = sub.add_parser("log", help="dump this block's hire log")
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_log)
    return ap


def main(argv=None) -> None:
    a = build_parser().parse_args(argv)
    try:
        sys.exit(a.f(a))
    except LaborError as e:
        # Written, then exit 1 — `sys.exit("msg")` would only print at interpreter shutdown, which
        # an in-process caller never sees. The message never carries a key or a key fragment.
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
