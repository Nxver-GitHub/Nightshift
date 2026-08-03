#!/usr/bin/env python3
"""
Add a task to the taskrunner kanban (tasks.json), atomically and concurrency-safe.

Any agent (an operator, a delegate, the taskrunner itself, or a human via a UI) can queue work
"for later": it appears in the "To do" column and gets picked up on its own.

Usage:
  python3 add_task.py --title "…" [--description "…"] [--project "clients/x"] \
                      [--due 2026-08-10] [--priority normal|high] [--source "operator"]

Config:
  --tasks PATH            kanban file. Default: $TASKRUNNER_TASKS, else tasks.json next to this script.
  TASKRUNNER_OWNER (env)  the human who confirms irreversible steps. Default: "the owner".

Message-triggered task (an email, a chat…): pass --email-from/--email-subject/--email-id/
--email-thread. The message becomes the task's reference (shown on the card) and an EXECUTION
CONTRACT is appended to the description: do everything reversible, stop before push/send/deploy,
and ask the owner to confirm. The same contract is added to any task created with --contract.
"""
import json, os, sys, time, fcntl, datetime, argparse

OWNER = os.environ.get("TASKRUNNER_OWNER", "the owner")


def resolve_tasks(arg):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("TASKRUNNER_TASKS")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


CONTRACT = f"""

## Execution contract — DO NOT CROSS THE IRREVERSIBLE LINE
Go as far as you can, then stop before any irreversible action and ask {OWNER} to confirm via the
"Needs you" block (update_task.py --finalize).

**Allowed, without asking**: analyze, edit code locally, **commit** (never push), prepare the draft
reply in the original thread, prepare infra commands/manifests without running them, update the
brain and the CRM.

**Forbidden without explicit confirmation**: `git push`, any deploy (cloud, hosting, DB…), sending
an email, writing to a client's production system, archiving a thread.

When everything reversible is done: `--finalize` with the exact list of pending gestures, then wait.
After confirmation: execute in order push -> send -> archive, verify, then close with the final
result."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--project", default="")
    ap.add_argument("--due", default="")
    ap.add_argument("--priority", default="normal", choices=["normal", "high"])
    ap.add_argument("--source", default="agent", help="who created it (traceability)")
    ap.add_argument("--email-from", default="")
    ap.add_argument("--email-subject", default="")
    ap.add_argument("--email-id", default="", help="message id, to reply in the same thread")
    ap.add_argument("--email-thread", default="", help="thread/conversation id, for archiving")
    ap.add_argument("--email-date", default="")
    ap.add_argument("--contract", action="store_true",
                    help="force-append the execution contract (automatic when --email-* is set)")
    ap.add_argument("--tasks", default=None, help="target kanban (default: see --tasks in the header)")
    a = ap.parse_args()

    tasks_path = resolve_tasks(a.tasks)
    lock_path = tasks_path + ".lock"

    # Execution contract is written INTO the task, not only into the skill: an instruction that
    # lives in the brief cannot be forgotten by whichever agent later picks the task up.
    email = {k: v for k, v in (("from", a.email_from), ("subject", a.email_subject),
                               ("message_id", a.email_id), ("thread_id", a.email_thread),
                               ("received", a.email_date)) if v}
    desc = a.description.strip()
    if email or a.contract:
        desc += CONTRACT
    if email:
        ref = " · ".join(filter(None, [email.get("from"), email.get("subject"),
                                       email.get("received", "")[:16]]))
        desc = f"**Source message**: {ref}\n\n" + desc

    # Inter-process lock: two simultaneous writers (a UI, the runner, another agent) must not clobber
    # each other. Held across the read-modify-write.
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
        try:
            d = json.load(open(tasks_path))
            assert isinstance(d.get("tasks"), list)
        except Exception:
            d = {"tasks": []}
        # Unique id even if several creations land in the same second: suffix -1, -2… until free.
        base = "t-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        existing = {x.get("id") for x in d["tasks"]}
        tid, n = base, 0
        while tid in existing:
            n += 1
            tid = f"{base}-{n}"
        t = {
            "id": tid,
            "title": a.title.strip(),
            "description": desc.strip(),
            "project": a.project.strip(),
            "due": a.due.strip(),
            "priority": a.priority,
            "status": "todo",
            "claimed_by": None,
            "delegate_session_id": None,
            "email": email or None,
            "finalization": None,
            "journal": [f"{now()} — created by {a.source}"
                        + (f" (email from {email.get('from')})" if email else "")],
            "created_at": now(),
            "started_at": None,
            "done_at": None,
        }
        d["tasks"].append(t)
        tmp = tasks_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, tasks_path)   # atomic swap
        print(f"OK task created: {t['id']} — {t['title']}  (status: todo)")
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


if __name__ == "__main__":
    main()
