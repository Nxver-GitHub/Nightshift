#!/usr/bin/env python3
"""
Update ONE task in the kanban (tasks.json), atomically and concurrency-safe.

Counterpart to add_task.py: lets the taskrunner (or any agent) evolve an existing task — claim,
journal, status, delegate session, visible plan, a question to the owner, a problem banner, the
finalization gate, and the final result — without ever rewriting the other tasks (it re-reads the
file under lock just before writing).

Usage:
  python3 update_task.py --id t-20260803-153007 \
      [--status todo|in_progress|waiting_owner|done|cancelled] \
      [--claimed-by "taskrunner@2026-08-03 16:35"] [--started-now] [--done-now] \
      [--delegate-session-id <id>] [--journal "entry (auto-timestamped)"] \
      [--expect-status todo]      # guard: abort if the current status differs

Visible plan (shown on the card):
  --set-steps "Read context|Prepare the brief|Delegate|Verify|Close"
  --step "3=doing"   --step "2=done"     (repeatable; 1-indexed; pending|doing|done|skip|blocked)
      (moving a step to 'doing' auto-marks previous 'doing' steps as 'done')

Question to the owner (answered from a UI; the runner resumes when answered):
  --question "…"        --consume-question
Problem banner:
  --problem "…"         --problem-resolved
Final result (REQUIRED at close — what the owner reads when opening the card):
  --result "markdown…"            --result-file /path/report.md
Finalization (the irreversible gestures waiting for the owner's yes):
  --finalize push=... | email=... | deploy=... | archive=... | other=...   (repeatable)
  --finalize-done N     (mark gesture N as executed after confirmation)
Due date (reschedule a task blocked by a third party, without it looking overdue):
  --due 2026-08-10      --due ""    (auto journal line + increments due_reschedules)

Config:
  --tasks PATH          Default: $TASKRUNNER_TASKS, else tasks.json next to this script.
"""
import json, os, re, sys, time, fcntl, datetime, argparse

STATUSES = ["todo", "in_progress", "waiting_owner", "done", "cancelled"]


def resolve_tasks(arg):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("TASKRUNNER_TASKS")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def parse_due(v):
    """'' clears the due date; otherwise strict YYYY-MM-DD. Raises on anything else, BEFORE we open
    the kanban, so a bad input writes nothing at all."""
    s = v.strip()
    if not s:
        return ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        raise ValueError("format")
    datetime.date.fromisoformat(s)   # also rejects impossible dates (2026-02-31)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--status", choices=STATUSES)
    ap.add_argument("--claimed-by")
    ap.add_argument("--started-now", action="store_true")
    ap.add_argument("--done-now", action="store_true")
    ap.add_argument("--delegate-session-id")
    ap.add_argument("--journal")
    ap.add_argument("--expect-status", choices=STATUSES)
    ap.add_argument("--set-steps", help="full plan, steps separated by |")
    ap.add_argument("--step", action="append", default=[],
                    help="update a step: 'N=doing' / 'N=done' / 'N=skip' / 'N=blocked' (1-indexed)")
    ap.add_argument("--question", help="ask the owner (moves the task to waiting_owner)")
    ap.add_argument("--consume-question", action="store_true",
                    help="archive the Q/A into the journal, then clear it")
    ap.add_argument("--problem", help="raise the problem banner (red) on the card")
    ap.add_argument("--problem-resolved", action="store_true", help="clear the problem banner")
    ap.add_argument("--result", help="final report (markdown) shown on the card")
    ap.add_argument("--result-file", help="markdown file with the final report")
    ap.add_argument("--finalize", action="append", default=[], metavar="TYPE=DETAIL",
                    help="irreversible gesture awaiting the owner: push= | email= | deploy= | "
                         "archive= | other=. Repeatable. Posts the 'Needs you' block, moves the task "
                         "to waiting_owner, and creates the confirmation question.")
    ap.add_argument("--finalize-done", action="append", default=[], metavar="N",
                    help="mark gesture N (1-based) as executed after confirmation")
    ap.add_argument("--due", default=None, metavar="YYYY-MM-DD",
                    help="reschedule the due date ('' clears it). Writes a journal line and "
                         "increments due_reschedules.")
    ap.add_argument("--tasks", default=None)
    a = ap.parse_args()

    # Validate BEFORE the lock and BEFORE any read: a malformed due date must produce no write,
    # no trace, no held lock — just a clear message.
    if a.due is not None:
        try:
            a.due = parse_due(a.due)
        except ValueError:
            print(f"ERROR: --due '{a.due}' invalid — expected YYYY-MM-DD (e.g. 2026-08-10), "
                  f'or "" to clear. Nothing written.', file=sys.stderr)
            sys.exit(1)

    tasks_path = resolve_tasks(a.tasks)
    lock_path = tasks_path + ".lock"

    lock_fd = open(lock_path, "w")
    for _ in range(50):
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            time.sleep(0.1)
    else:
        print("ERROR: tasks.json locked too long, retry.", file=sys.stderr)
        sys.exit(1)

    try:
        d = json.load(open(tasks_path))   # re-read under lock, just before writing
        t = next((t for t in d["tasks"] if t["id"] == a.id), None)
        if t is None:
            print(f"ERROR: task {a.id} not found.", file=sys.stderr)
            sys.exit(1)
        if a.expect_status and t["status"] != a.expect_status:
            print(f"ABORT: current status '{t['status']}' != expected '{a.expect_status}' "
                  f"(the task moved; re-read the kanban).", file=sys.stderr)
            sys.exit(2)
        if a.status:
            t["status"] = a.status
        if a.claimed_by is not None:
            t["claimed_by"] = a.claimed_by
        if a.started_now:
            t["started_at"] = now()
        if a.done_now:
            t["done_at"] = now()
        if a.delegate_session_id is not None:
            t["delegate_session_id"] = a.delegate_session_id
        if a.journal:
            t["journal"].append(f"{now()} — {a.journal.strip()}")
        # Rescheduling is legitimate (task blocked by a third party) but NEVER silent: every move
        # leaves a journal line, and due_reschedules counts how often an existing due date moved.
        # Setting a first due date is not a reschedule.
        if a.due is not None:
            old = (t.get("due") or "").strip()
            if a.due != old:
                t["due"] = a.due
                if old:
                    t["due_reschedules"] = int(t.get("due_reschedules") or 0) + 1
                    what = (f"due date moved from {old} to {a.due}" if a.due
                            else f"due date cleared (was {old})")
                    t["journal"].append(f"{now()} — {what} (reschedule #{t['due_reschedules']})")
                else:
                    t["journal"].append(f"{now()} — due date set to {a.due}")
        if a.set_steps:
            t["steps"] = [{"label": s.strip(), "status": "pending", "ts": None}
                          for s in a.set_steps.split("|") if s.strip()]
        for spec in a.step:
            try:
                idx_s, st = spec.split("=", 1)
                idx, st = int(idx_s) - 1, st.strip()
                assert st in ("pending", "doing", "done", "skip", "blocked")
                steps = t.get("steps") or []
                steps[idx]  # IndexError if out of plan
            except Exception:
                print(f"ERROR: --step '{spec}' invalid (expected 'N=doing|done|skip|pending|blocked', "
                      f"N within the plan).", file=sys.stderr)
                sys.exit(1)
            if st == "doing":  # one 'doing' at a time: previous ones become 'done'
                for s2 in steps:
                    if s2["status"] == "doing":
                        s2["status"], s2["ts"] = "done", now()
            steps[idx]["status"], steps[idx]["ts"] = st, now()
        if a.question:
            if t.get("question"):
                print("ERROR: a question is already active — consume it first (--consume-question) "
                      "or wait for the answer.", file=sys.stderr)
                sys.exit(1)
            t["question"] = {"text": a.question.strip(), "asked_at": now(),
                             "answer": None, "answered_at": None}
            t["status"] = "waiting_owner"
            t["journal"].append(f"{now()} — question asked: {a.question.strip()}")
        if a.consume_question:
            q = t.get("question")
            if q:
                t["journal"].append(
                    f"{now()} — Q/A consumed — « {q.get('text','')} » -> "
                    f"« {q.get('answer') or '(no answer)'} » ({q.get('answered_at') or '—'})")
                t["question"] = None
        # Finalization: the irreversible gestures waiting for the owner. Everything reversible is
        # done; only what commits remains (push, send, deploy, archive). Reuses the question
        # mechanism so confirming it wakes the runner up.
        TYPES = {"push": "Push the code", "email": "Send the email", "deploy": "Deploy",
                 "archive": "Archive the thread", "other": "Action"}
        if a.finalize:
            actions = []
            for spec in a.finalize:
                typ, _, det = spec.partition("=")
                typ = typ.strip().lower()
                if typ not in TYPES or not det.strip():
                    print(f"ERROR: --finalize '{spec}' invalid (expected "
                          f"'{'|'.join(TYPES)}=concrete detail').", file=sys.stderr)
                    sys.exit(1)
                actions.append({"type": typ, "detail": det.strip(), "done": False})
            if t.get("question"):
                print("ERROR: a question is already active — consume it before finalizing.",
                      file=sys.stderr)
                sys.exit(1)
            t["finalization"] = {"actions": actions, "posted_at": now(), "confirmed_at": None}
            recap = "\n".join(f"- {TYPES[x['type']]}: {x['detail']}" for x in actions)
            t["question"] = {
                "text": "Everything reversible is done. May I run these irreversible steps?"
                        f"\n{recap}\n\nReply « Confirm » (or say what to change).",
                "asked_at": now(), "answer": None, "answered_at": None}
            t["status"] = "waiting_owner"
            t["journal"].append(f"{now()} — finalization proposed ({len(actions)} gesture(s)): "
                                + " | ".join(f"{x['type']}: {x['detail']}" for x in actions))
        for spec in a.finalize_done:
            fz = t.get("finalization") or {}
            acts = fz.get("actions") or []
            try:
                acts[int(spec) - 1]["done"] = True
            except Exception:
                print(f"ERROR: --finalize-done '{spec}' out of range.", file=sys.stderr)
                sys.exit(1)
            t["journal"].append(f"{now()} — executed: {acts[int(spec)-1]['detail']}")
        if a.problem:
            t["problem"] = a.problem.strip()
            t["journal"].append(f"{now()} — PROBLEM — {a.problem.strip()}")
        if a.problem_resolved:
            if t.get("problem"):
                t["journal"].append(f"{now()} — problem resolved ({t['problem']})")
            t["problem"] = None
        if a.result_file:
            try:
                t["result"] = open(a.result_file, encoding="utf-8").read().strip()
            except OSError as e:
                print(f"ERROR: cannot read --result-file: {e}", file=sys.stderr)
                sys.exit(1)
        elif a.result:
            t["result"] = a.result.strip()
        tmp = tasks_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, tasks_path)      # atomic swap
        echo = f" — status: {t['status']}"
        if a.due is not None:
            echo += f" — due: {t.get('due') or '(none)'}"
            if t.get("due_reschedules"):
                echo += f" ({t['due_reschedules']} reschedule(s))"
        print(f"OK {t['id']}{echo}")
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
