#!/usr/bin/env python3
"""
Answer the taskrunner's `waiting_owner` questions at the exact interface a human would have used.

The taskrunner stops at every irreversible gesture and asks the owner via `question` on the card
(update_task.py --question / --finalize). There is no CLI to answer: a human wrote `question.answer`
and `question.answered_at` straight into tasks.json. This script writes those same two fields, under
the same lock, and NOTHING else — the taskrunner's own loop then consumes the answer
(--consume-question) exactly as it would have from a human. Drop-in, zero modification upstream.

This file is dumb plumbing: it never reads the policy and never decides anything. The reasoning lives
in the `approver` skill; here we only record what was decided, in an append-only ledger.

Usage:  python3 approve.py <command> [options]
  pending  [--tasks PATH] [--json]              questions waiting for an answer
  answer   --id ID --verdict approve|reject --reason TEXT [--policy-ref "P2,P4"] [--tasks PATH]
  escalate --id ID --reason TEXT [--tasks PATH]  ledger only — the task stays untouched for a human
  log      [--json] [--limit N]                  the decision ledger

Config:
  --tasks PATH      kanban file. Default: $TASKRUNNER_TASKS, else the taskrunner's tasks.json.
  APPROVER_LEDGER   append-only JSONL audit trail. Default: decisions.jsonl next to this script.
  APPROVER_POLICY   the written policy the skill reasons from (never read here, only cited).
"""
import json, os, sys, time, fcntl, datetime, argparse
from typing import Optional, TextIO

VERDICTS = ["approve", "reject"]
LOCK_TRIES = 50          # same budget as the taskrunner: 50 x 0.1s = 5s before giving up
LOCK_SLEEP = 0.1


def resolve_tasks(arg: Optional[str]) -> str:
    """Same resolution order as the taskrunner's scripts — the approver must land on the same file."""
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("TASKRUNNER_TASKS")
    if env:
        return os.path.abspath(env)
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", "taskrunner", "code", "tasks.json"))


def resolve_ledger(arg: str = None) -> str:
    """--ledger flag beats env beats default. The flag exists so headless callers can pass every
    path on the command line — env vars don't survive into a `claude -p` session's tool shells."""
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("APPROVER_LEDGER")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "decisions.jsonl")


def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def read_tasks(path: str) -> list:
    """Readers don't lock (matching list_tasks.py): a torn read is impossible — writes land via an
    atomic os.replace, so any open file is a complete previous version."""
    try:
        return json.load(open(path)).get("tasks", [])
    except (OSError, ValueError):
        print(f"(no kanban at {path})", file=sys.stderr)
        sys.exit(1)


def acquire_lock(lock_path: str) -> TextIO:
    """Inter-process lock shared with add_task.py / update_task.py. Held across read-modify-write."""
    fd = open(lock_path, "w")
    for _ in range(LOCK_TRIES):
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            time.sleep(LOCK_SLEEP)
    print("ERROR: tasks.json locked too long, retry.", file=sys.stderr)
    sys.exit(1)


def has_open_finalization(t: dict) -> bool:
    """True when the question gates irreversible gestures (push/email/deploy/archive) not yet run —
    the high-stakes class the skill must never approve on inference."""
    actions = (t.get("finalization") or {}).get("actions") or []
    return any(not x.get("done") for x in actions)


def is_pending(t: dict) -> bool:
    q = t.get("question")
    return t.get("status") == "waiting_owner" and bool(q) and q.get("answer") is None


def ledger_append(entry: dict, ledger_arg: str = None) -> None:
    """Append-only, one JSON object per line: a decision is evidence and is never rewritten."""
    path = resolve_ledger(ledger_arg)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def split_refs(raw: Optional[str]) -> list:
    return [s.strip() for s in (raw or "").split(",") if s.strip()]


def cmd_pending(a: argparse.Namespace) -> int:
    # The skill cannot reason without a written policy; warn loudly but still list, so a human
    # reading the queue is never blocked by a config gap.
    policy = os.environ.get("APPROVER_POLICY")
    if not policy:
        print("WARNING: APPROVER_POLICY is not set — the approver skill has no policy to reason "
              "from; every question will have to be escalated.", file=sys.stderr)
    elif not os.path.isfile(policy):
        print("WARNING: APPROVER_POLICY points at a file that does not exist — the approver skill "
              "has no policy to reason from.", file=sys.stderr)

    rows = [{
        "id": t.get("id"),
        "title": t.get("title", ""),
        "question_text": (t.get("question") or {}).get("text", ""),
        "asked_at": (t.get("question") or {}).get("asked_at"),
        "finalize": has_open_finalization(t),
        "goal": t.get("goal"),
        "priority": t.get("priority", "normal"),
    } for t in read_tasks(resolve_tasks(a.tasks)) if is_pending(t)]

    if a.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("No question waiting for an answer.")
        return 0
    print(f"\nWaiting on owner ({len(rows)})")
    for r in rows:
        flags = []
        if r["finalize"]:
            flags.append("FINALIZE")
        if r["priority"] == "high":
            flags.append("!high")
        if r["goal"]:
            flags.append(f"goal {r['goal']}")
        tail = ("  [" + ", ".join(flags) + "]") if flags else ""
        print(f"  {r['id']}  {r['title']}{tail}")
        print(f"      asked {r['asked_at'] or '—'}: {r['question_text'].splitlines()[0] if r['question_text'] else ''}")
    print()
    return 0


def cmd_answer(a: argparse.Namespace) -> int:
    reason = a.reason.strip()
    if not reason:
        print("ERROR: --reason is empty — the ledger is an audit trail, every verdict needs one.",
              file=sys.stderr)
        return 1
    refs = split_refs(a.policy_ref)

    tasks_path = resolve_tasks(a.tasks)
    lock_fd = acquire_lock(tasks_path + ".lock")
    try:
        d = json.load(open(tasks_path))   # re-read under lock, just before writing
        t = next((t for t in d["tasks"] if t["id"] == a.id), None)
        if t is None:
            print(f"ERROR: task {a.id} not found.", file=sys.stderr)
            return 1
        if t.get("status") != "waiting_owner":
            print(f"ABORT: task {a.id} is '{t.get('status')}', not 'waiting_owner' — nothing to "
                  f"answer (the task moved; re-read the kanban).", file=sys.stderr)
            return 2
        q = t.get("question")
        if not q:
            print(f"ERROR: task {a.id} has no active question.", file=sys.stderr)
            return 1
        if q.get("answer") is not None:
            print(f"ERROR: task {a.id} was already answered at {q.get('answered_at') or '—'} — "
                  f"refusing to overwrite an owner's answer.", file=sys.stderr)
            return 1

        # Write EXACTLY what a human would have written into the card: the answer and its timestamp.
        # Not the status — the taskrunner moves the task itself when it consumes the answer.
        verdict_word = "APPROVED" if a.verdict == "approve" else "REJECTED"
        answer = f"{verdict_word} — {reason}"
        if refs:
            answer += f" [policy: {', '.join(refs)}]"
        q["answer"] = answer
        q["answered_at"] = now()
        # No setdefault: journal is a schema invariant (add_task.py always creates it). A missing
        # key means the kanban is corrupt — crash loudly rather than paper over it.
        t["journal"].append(f"{now()} — answered by approver agent ({a.verdict})")

        tmp = tasks_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, tasks_path)      # atomic swap
        question_text = q.get("text", "")
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

    # Ledger only after the write landed: it records decisions that actually took effect.
    # But a decision live in the kanban with NO audit entry breaks this block's core guarantee —
    # so a ledger failure is loud and distinct (exit 3), never a raw traceback.
    try:
        ledger_append({"ts": now(), "task_id": a.id, "question": question_text, "verdict": a.verdict,
                       "reason": reason, "policy_clauses_cited": refs, "mode": "agent"},
                      getattr(a, "ledger", None))
    except OSError as e:
        print(f"ERROR: answer for {a.id} IS live in the kanban, but the ledger write FAILED: {e} — "
              f"append this decision to the ledger manually before the next pass.", file=sys.stderr)
        return 3
    print(f"OK {a.id} — {verdict_word} (status unchanged: waiting_owner)")
    return 0


def cmd_escalate(a: argparse.Namespace) -> int:
    """No clause covers it → write NOTHING to the task. It stays waiting for the human-labor path,
    which picks escalations up from the ledger."""
    reason = a.reason.strip()
    if not reason:
        print("ERROR: --reason is empty — an escalation must say what the policy did not cover.",
              file=sys.stderr)
        return 1
    t = next((t for t in read_tasks(resolve_tasks(a.tasks)) if t.get("id") == a.id), None)
    if t is None:
        print(f"ERROR: task {a.id} not found.", file=sys.stderr)
        return 1
    # Escalation touches no task state, so a ledger failure here means the escalation simply
    # didn't happen — fail loudly so the skill retries instead of assuming it was recorded.
    try:
        ledger_append({"ts": now(), "task_id": a.id, "question": (t.get("question") or {}).get("text", ""),
                       "verdict": "escalated", "reason": reason, "policy_clauses_cited": [],
                       "mode": "agent"}, getattr(a, "ledger", None))
    except OSError as e:
        print(f"ERROR: ledger write failed — escalation NOT recorded: {e}", file=sys.stderr)
        return 3
    print(f"OK {a.id} escalated — task untouched, still waiting on a human.")
    return 0


def cmd_log(a: argparse.Namespace) -> int:
    path = resolve_ledger(getattr(a, "ledger", None))
    try:
        lines = [json.loads(x) for x in open(path, encoding="utf-8") if x.strip()]
    except OSError:
        print("(no decisions yet)", file=sys.stderr)
        return 0
    if a.limit:
        lines = lines[-a.limit:]
    if a.json:
        print(json.dumps(lines, ensure_ascii=False, indent=2))
        return 0
    for e in lines:
        refs = ", ".join(e.get("policy_clauses_cited") or []) or "—"
        print(f"  {e.get('ts')}  {e.get('task_id')}  [{e.get('verdict')}]  {e.get('reason')}  ({refs})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Answer the taskrunner's owner questions")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("pending", help="questions waiting for an answer")
    s.add_argument("--tasks", default=None)
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_pending)
    s = sub.add_parser("answer", help="write the owner's answer into the card")
    s.add_argument("--id", required=True)
    s.add_argument("--verdict", required=True, choices=VERDICTS)
    s.add_argument("--reason", required=True, help="one sentence — it goes on the card and in the ledger")
    s.add_argument("--policy-ref", default=None, metavar="REFS",
                   help="comma-separated clause ids that justify the verdict, e.g. 'P2,P4'")
    s.add_argument("--tasks", default=None)
    s.add_argument("--ledger", default=None, help="decisions.jsonl path (beats $APPROVER_LEDGER)")
    s.set_defaults(f=cmd_answer)
    s = sub.add_parser("escalate", help="no clause covers it — leave the task for a human")
    s.add_argument("--id", required=True)
    s.add_argument("--reason", required=True)
    s.add_argument("--tasks", default=None)
    s.add_argument("--ledger", default=None, help="decisions.jsonl path (beats $APPROVER_LEDGER)")
    s.set_defaults(f=cmd_escalate)
    s = sub.add_parser("log", help="dump the decision ledger")
    s.add_argument("--json", action="store_true")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--ledger", default=None, help="decisions.jsonl path (beats $APPROVER_LEDGER)")
    s.set_defaults(f=cmd_log)
    return ap


def main() -> None:
    a = build_parser().parse_args()
    sys.exit(a.f(a))


if __name__ == "__main__":
    main()
