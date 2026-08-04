#!/usr/bin/env python3
"""
Goals — the store behind the goal agent. A goal is ONE background objective ("500 prospecting emails
in August", "get a meeting with the CEO of X"). The agent calibrates it, writes a measurable plan,
creates dated tasks for the taskrunner, then wakes on a cadence to measure and adjust.

State lives here (goals.json) + a plan file per goal. If the agent's session is ever recreated, it
resumes from goals.json + the plan.

Usage:  python3 goal.py <command> [options]
Config: --store PATH or $GOALS_STORE (default: goals.json next to this script)
"""
import os, sys, json, argparse, datetime

STATUS = ["calibrating", "active", "done", "abandoned"]


def store_path(arg):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("GOALS_STORE")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "goals.json")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def today():
    return datetime.date.today()


def load(p):
    try:
        d = json.load(open(p)); d.setdefault("goals", []); return d
    except Exception:
        return {"goals": []}


def save(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def find(d, gid):
    return next((g for g in d["goals"] if g["id"] == gid), None)


def next_review(cadence):
    return (today() + datetime.timedelta(days=max(1, cadence))).isoformat()


def cmd_add(d, a):
    base = "g-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    used = {g["id"] for g in d["goals"]}
    gid, n = base, 0
    while gid in used:
        n += 1; gid = f"{base}-{n}"
    d["goals"].append({
        "id": gid, "title": a.title.strip(), "objective": a.objective.strip(),
        "status": "calibrating", "measure": {}, "cadence_days": None, "next_review": None,
        "session_id": a.session_id, "plan_file": f"goals/{gid}/plan.md",
        "notifications": [], "reviews": [], "created_at": now()})
    return f"OK goal {gid} — {a.title} (calibrating)"


def cmd_plan(d, a):
    g = find(d, a.goal)
    if not g:
        sys.exit(f"ERROR: goal {a.goal} not found.")
    if not (a.measure_cmd or a.measure_criterion):
        sys.exit("ERROR: a plan needs a measure — --measure-cmd (+ --measure-target/--unit) OR "
                 "--measure-criterion (a verifiable binary criterion).")
    g["measure"] = {"cmd": a.measure_cmd, "target": a.measure_target, "current": None,
                    "unit": a.measure_unit, "criterion": a.measure_criterion, "reached": False}
    g["cadence_days"] = a.cadence
    g["next_review"] = next_review(a.cadence)
    return f"OK plan set for {a.goal} — cadence {a.cadence}d, next review {g['next_review']}"


def cmd_activate(d, a):
    g = find(d, a.goal)
    if not g:
        sys.exit(f"ERROR: goal {a.goal} not found.")
    if not g.get("measure"):
        sys.exit("ERROR: no plan yet — run `plan` first.")
    g["status"] = "active"
    g["next_review"] = next_review(g.get("cadence_days") or 1)
    how = "auto (no explicit validation)" if a.auto else "validated"
    g["notifications"].append({"ts": now(), "text": f"Plan activated ({how}).",
                               "priority": "normal", "read": False})
    return f"OK goal {a.goal} active ({how}) — next review {g['next_review']}"


def cmd_review(d, a):
    g = find(d, a.goal)
    if not g:
        sys.exit(f"ERROR: goal {a.goal} not found.")
    if a.measure_current is not None:
        g["measure"]["current"] = a.measure_current
        tgt = g["measure"].get("target")
        if tgt is not None:
            g["measure"]["reached"] = a.measure_current >= tgt
    g["reviews"].append({"ts": now(), "note": a.note,
                         "measure_current": a.measure_current})
    g["next_review"] = next_review(g.get("cadence_days") or 1)
    return f"OK review logged for {a.goal} — next review {g['next_review']}"


def cmd_notify(d, a):
    g = find(d, a.goal)
    if not g:
        sys.exit(f"ERROR: goal {a.goal} not found.")
    g["notifications"].append({"ts": now(), "text": a.text.strip(),
                               "priority": a.priority, "read": False})
    return f"OK notification ({a.priority}) added to {a.goal}"


def cmd_done(d, a):
    g = find(d, a.goal)
    if not g:
        sys.exit(f"ERROR: goal {a.goal} not found.")
    g["status"] = a.status
    g["summary"] = a.summary
    g["closed_at"] = now()
    return f"OK goal {a.goal} closed — {a.status}"


def cmd_set_session(d, a):
    g = find(d, a.goal)
    if not g:
        sys.exit(f"ERROR: goal {a.goal} not found.")
    g["session_id"] = a.session_id
    return f"OK goal {a.goal} session set"


def cmd_show(d, a):
    g = find(d, a.goal)
    if not g:
        sys.exit(f"ERROR: goal {a.goal} not found.")
    if a.json:
        print(json.dumps(g, ensure_ascii=False, indent=2)); return None
    print(f"# {g['title']}  ({g['id']}, {g['status']})")
    print(f"  objective: {g['objective']}")
    m = g.get("measure") or {}
    if m:
        if m.get("criterion"):
            print(f"  measure: {m['criterion']}  reached={m.get('reached')}")
        else:
            print(f"  measure: {m.get('current')}/{m.get('target')} {m.get('unit') or ''}  "
                  f"reached={m.get('reached')}")
    print(f"  cadence: {g.get('cadence_days')}d · next review: {g.get('next_review')}")
    for r in (g.get("reviews") or [])[-3:]:
        print(f"    review {r['ts']}: {r.get('note','')}")
    return None


def cmd_list(d, a):
    for g in d["goals"]:
        if a.status and g["status"] != a.status:
            continue
        print(f"  {g['id']}  [{g['status']}]  next:{g.get('next_review') or '—'}  {g['title']}")
    return None


def cmd_due(d, a):
    t = today().isoformat()
    due = [g for g in d["goals"] if g["status"] == "active"
           and (not g.get("next_review") or g["next_review"] <= t)]
    if not due:
        print("No goal due for review.")
    for g in due:
        print(f"  {g['id']}  next:{g.get('next_review')}  {g['title']}")
    return None


def build_parser():
    ap = argparse.ArgumentParser(description="Goals store")
    ap.add_argument("--store")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("--title", required=True)
    s.add_argument("--objective", required=True); s.add_argument("--session-id")
    s.set_defaults(f=cmd_add)
    s = sub.add_parser("plan"); s.add_argument("--goal", required=True)
    s.add_argument("--cadence", type=int, default=2); s.add_argument("--measure-cmd")
    s.add_argument("--measure-target", type=float); s.add_argument("--measure-unit")
    s.add_argument("--measure-criterion"); s.set_defaults(f=cmd_plan)
    s = sub.add_parser("activate"); s.add_argument("--goal", required=True)
    s.add_argument("--auto", action="store_true"); s.set_defaults(f=cmd_activate)
    s = sub.add_parser("review"); s.add_argument("--goal", required=True)
    s.add_argument("--note", required=True); s.add_argument("--measure-current", type=float)
    s.set_defaults(f=cmd_review)
    s = sub.add_parser("notify"); s.add_argument("--goal", required=True)
    s.add_argument("--text", required=True); s.add_argument("--priority", default="normal",
                                                            choices=["normal", "high"])
    s.set_defaults(f=cmd_notify)
    s = sub.add_parser("done"); s.add_argument("--goal", required=True)
    s.add_argument("--status", required=True, choices=["done", "abandoned"])
    s.add_argument("--summary", default=""); s.set_defaults(f=cmd_done)
    s = sub.add_parser("set-session"); s.add_argument("--goal", required=True)
    s.add_argument("--session-id", required=True); s.set_defaults(f=cmd_set_session)
    s = sub.add_parser("show"); s.add_argument("--goal", required=True)
    s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_show)
    s = sub.add_parser("list"); s.add_argument("--status", choices=STATUS); s.set_defaults(f=cmd_list)
    sub.add_parser("due", help="goals due for review today").set_defaults(f=cmd_due)
    return ap


def main():
    a = build_parser().parse_args()
    p = store_path(a.store)
    d = load(p)
    out = a.f(d, a)
    save(p, d)
    if out:
        print(out)


if __name__ == "__main__":
    main()
