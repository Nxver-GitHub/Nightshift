#!/usr/bin/env python3
"""
Print the kanban grouped by status (read-only). A quick board view for a human or an agent.

Usage:
  python3 list_tasks.py [--tasks PATH] [--status todo] [--json]

Config:
  --tasks PATH   Default: $TASKRUNNER_TASKS, else tasks.json next to this script.
"""
import json, os, sys, argparse

ORDER = ["todo", "in_progress", "waiting_owner", "done", "cancelled"]
LABEL = {"todo": "To do", "in_progress": "In progress", "waiting_owner": "Waiting on owner",
         "done": "Done", "cancelled": "Cancelled"}


def resolve_tasks(arg):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("TASKRUNNER_TASKS")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", default=None)
    ap.add_argument("--status", choices=ORDER, help="show only this column")
    ap.add_argument("--json", action="store_true", help="raw json for the matching tasks")
    a = ap.parse_args()

    path = resolve_tasks(a.tasks)
    try:
        tasks = json.load(open(path)).get("tasks", [])
    except (OSError, ValueError):
        print(f"(no kanban at {path})", file=sys.stderr)
        sys.exit(1)

    if a.status:
        tasks = [t for t in tasks if t.get("status") == a.status]
    if a.json:
        print(json.dumps(tasks, ensure_ascii=False, indent=2))
        return

    by = {}
    for t in tasks:
        by.setdefault(t.get("status", "todo"), []).append(t)

    for st in ORDER:
        col = by.get(st, [])
        if not col and a.status:
            continue
        print(f"\n{LABEL.get(st, st)} ({len(col)})")
        # high priority first, then nearest due date, then oldest
        col.sort(key=lambda t: (t.get("priority") != "high", t.get("due") or "9999",
                                t.get("created_at") or ""))
        for t in col:
            flags = []
            if t.get("priority") == "high":
                flags.append("!high")
            if t.get("due"):
                flags.append(f"due {t['due']}")
            if t.get("problem"):
                flags.append("PROBLEM")
            if t.get("claimed_by"):
                flags.append(f"@{t['claimed_by']}")
            tail = ("  [" + ", ".join(flags) + "]") if flags else ""
            print(f"  {t.get('id')}  {t.get('title', '')}{tail}")
    print()


if __name__ == "__main__":
    main()
