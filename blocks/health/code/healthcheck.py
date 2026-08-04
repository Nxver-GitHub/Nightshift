#!/usr/bin/env python3
"""
Health check — it CONSTATES, it doesn't fix. Verifies the Command Center is healthy and, when a
signal is RED, optionally files a taskrunner task so a silent failure becomes a ticket the system
picks up on its own.

THE RULE THAT GOVERNS EVERYTHING: every signal must be allowed to be false without crying. A check
that alarms wrongly gets ignored within a week, and you've rebuilt the same silence. So: verdict
`unknown` when a source is unreadable (never `red` by default), explicit margins, and an exemptions
file. This script ALWAYS exits 0 (except an internal crash) — the result is in the JSON, not the exit
code, so a scheduler doesn't loop on the checker's own "non-zero" status.

Usage:
  python3 healthcheck.py                 # constate + create a task for each RED signal (if enabled)
  python3 healthcheck.py --report        # read-only, writes nothing
Config (env):
  TASKRUNNER_TASKS   the kanban to inspect (stale claims)
  CRM_DB             the crm database to probe
  HEALTH_ADD_TASK    path to the taskrunner's add_task.py (enables task creation on RED)
  healthcheck.json   next to this script: {"exempt": ["signal_name", …]} to silence a check
"""
import os, sys, json, sqlite3, datetime, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
STALE_HOURS = 24


def cfg():
    try:
        return json.load(open(os.path.join(BASE, "healthcheck.json")))
    except Exception:
        return {"exempt": []}


def parse_ts(s):
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(s, fmt)
        except (ValueError, TypeError):
            continue
    return None


def check_tasks_json():
    path = os.environ.get("TASKRUNNER_TASKS")
    if not path or not os.path.exists(path):
        return {"name": "tasks_json", "verdict": "unknown", "detail": "TASKRUNNER_TASKS unset/missing"}
    try:
        d = json.load(open(path))
        assert isinstance(d.get("tasks"), list)
        return {"name": "tasks_json", "verdict": "green", "detail": f"{len(d['tasks'])} tasks, valid"}
    except Exception as e:
        return {"name": "tasks_json", "verdict": "red", "detail": f"tasks.json invalid: {e}"}


def check_stale_claims():
    path = os.environ.get("TASKRUNNER_TASKS")
    if not path or not os.path.exists(path):
        return {"name": "stale_claims", "verdict": "unknown", "detail": "no kanban"}
    try:
        tasks = json.load(open(path)).get("tasks", [])
    except Exception:
        return {"name": "stale_claims", "verdict": "unknown", "detail": "kanban unreadable"}
    now = datetime.datetime.now()
    stale = []
    for t in tasks:
        if t.get("status") != "in_progress":
            continue
        ts = parse_ts(t.get("started_at"))
        if ts and (now - ts).total_seconds() / 3600 >= STALE_HOURS:
            stale.append(t.get("id"))
    if stale:
        return {"name": "stale_claims", "verdict": "red",
                "detail": f"claimed >{STALE_HOURS}h with no progress: {', '.join(stale)}"}
    return {"name": "stale_claims", "verdict": "green", "detail": "no stale claim"}


def check_crm():
    path = os.environ.get("CRM_DB")
    if not path or not os.path.exists(path):
        return {"name": "crm_db", "verdict": "unknown", "detail": "CRM_DB unset/missing"}
    try:
        c = sqlite3.connect(path)
        c.execute("SELECT 1 FROM companies LIMIT 1")
        c.close()
        return {"name": "crm_db", "verdict": "green", "detail": "reachable"}
    except Exception as e:
        return {"name": "crm_db", "verdict": "red", "detail": f"crm.db not reachable: {e}"}


def main():
    report_only = "--report" in sys.argv
    exempt = set(cfg().get("exempt", []))
    signals = [check_tasks_json(), check_stale_claims(), check_crm()]
    for s in signals:
        if s["name"] in exempt and s["verdict"] == "red":
            s["verdict"], s["detail"] = "exempt", s["detail"] + " (exempted)"

    reds = [s for s in signals if s["verdict"] == "red"]
    created = []
    add_task = os.environ.get("HEALTH_ADD_TASK")
    if reds and not report_only and add_task and os.path.exists(add_task):
        for s in reds:
            try:
                subprocess.run([sys.executable, add_task, "--title",
                                f"Health: {s['name']} is red", "--priority", "high",
                                "--source", "healthcheck", "--description", s["detail"]],
                               check=True, capture_output=True, text=True)
                created.append(s["name"])
            except Exception:
                pass

    out = {"at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "overall": "red" if reds else "green",
           "signals": signals, "tasks_created": created}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0)   # ALWAYS 0 — the verdict is in the JSON


if __name__ == "__main__":
    main()
