#!/usr/bin/env python3
"""
Session lifecycle for persistent agents: know when to start fresh, and do it cleanly.

WHY — an agent that runs in a persistent /loop session (the taskrunner, an operator) re-invokes its
skill in the SAME conversation each tick. After a while the context saturates, auto-compaction kicks
in, and the agent loses precision (and costs more) with nobody deciding it. An agent can't clear its
own context; the equivalent is to END the session — the launcher then relaunches a fresh one with its
init prompt. Safe because the handoff already lives on disk (tasks.json, state.json, the brain).

The RULE: dump your head into those files, THEN reset. Never the other way around.

Usage:
  python3 session-cycle.py status                       # every agent: age, reset due or not
  python3 session-cycle.py tick   --agent taskrunner    # count one REAL run (after the guards)
  python3 session-cycle.py check  --agent taskrunner    # exit 0 = reset due, 1 = not (for an `if`)
  python3 session-cycle.py reset  --agent taskrunner --why "handoff done, 14h of context"

Config: agents come from sessions.json next to this script (or $SESSIONS_CONFIG). Default: a single
`taskrunner` agent whose Remote Control session is named "Taskrunner".
"""
import json, os, sys, signal, argparse, datetime, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.environ.get("SESSIONS_RUNS") or os.path.join(BASE, "session-runs.json")
DEFAULT = {"agents": {"taskrunner": {"session": "Taskrunner", "max_runs": 4, "max_hours": 24}}}


def agents():
    cfg = os.environ.get("SESSIONS_CONFIG") or os.path.join(BASE, "sessions.json")
    try:
        return json.load(open(cfg)).get("agents", DEFAULT["agents"])
    except Exception:
        return DEFAULT["agents"]


AGENTS = agents()


def _runs_read():
    try:
        return json.load(open(RUNS, encoding="utf-8"))
    except Exception:
        return {}


def _runs_write(d):
    tmp = RUNS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, RUNS)


def _ps_started(pid):
    """Real process start time (`ps -o lstart=`). Format e.g. 'Sat Aug  3 17:27:45 2026'."""
    out = subprocess.run(["ps", "-o", "lstart=", "-p", str(pid)],
                         capture_output=True, text=True).stdout.strip()
    if not out:
        return None
    try:
        return datetime.datetime.strptime(out, "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None


def find(agent):
    """The `claude` process for this agent (not the caffeinate wrapper), or None."""
    name = AGENTS[agent]["session"]
    out = subprocess.run(["pgrep", "-fl", f"remote-control {name}"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        pid, _, cmd = line.partition(" ")
        if cmd.startswith("caffeinate"):
            continue
        started = _ps_started(pid)
        if started:
            return {"pid": int(pid), "started": started, "cmd": cmd}
    return None


def runs_of(agent, started_at):
    e = _runs_read().get(agent) or {}
    return e.get("runs", 0) if e.get("started_at") == started_at else 0


def info(agent):
    d = find(agent)
    if not d:
        return {"agent": agent, "running": False, "due": False, "reason": "no session (the launcher will start it)"}
    h = (datetime.datetime.now() - d["started"]).total_seconds() / 3600
    cfg = AGENTS[agent]
    mx_runs, mx_h = cfg.get("max_runs", 4), cfg.get("max_hours", 24)
    started = d["started"].strftime("%Y-%m-%d %H:%M")
    n = runs_of(agent, started)
    due = n >= mx_runs or h >= mx_h
    reason = (f"{n} runs on this session (threshold {mx_runs}) — start fresh" if n >= mx_runs
              else f"{h:.1f}h of context (safety net {mx_h}h) — start fresh" if h >= mx_h
              else f"{n}/{mx_runs} runs · {h:.1f}h of context")
    return {"agent": agent, "running": True, "pid": d["pid"], "started_at": started,
            "age_h": round(h, 1), "runs": n, "max_runs": mx_runs, "due": due, "reason": reason}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "check", "reset", "tick"])
    ap.add_argument("--agent", choices=list(AGENTS))
    ap.add_argument("--why", default="")
    ap.add_argument("--delay", type=int, default=25,
                    help="seconds before the actual stop (default 25) so the agent can finish its "
                         "turn and deliver its report before the session dies. 0 = immediate.")
    a = ap.parse_args()

    if a.cmd == "status":
        for ag in AGENTS:
            i = info(ag)
            mark = "reset" if i["due"] else ("ok" if i["running"] else "off")
            print(f"[{mark}] {ag}: {i['reason']}")
        return

    if not a.agent:
        sys.exit("ERROR: --agent required.")
    i = info(a.agent)

    if a.cmd == "tick":
        if not i["running"]:
            print(json.dumps({"runs": 0, "due": False, "msg": "no session"})); return
        d = _runs_read()
        e = d.get(a.agent) or {}
        n = (e.get("runs", 0) if e.get("started_at") == i["started_at"] else 0) + 1
        d[a.agent] = {"started_at": i["started_at"], "runs": n}
        _runs_write(d)
        mx = AGENTS[a.agent].get("max_runs", 4)
        print(json.dumps({"runs": n, "max_runs": mx, "due": n >= mx}))
        return

    if a.cmd == "check":
        print(json.dumps(i))
        sys.exit(0 if i["due"] else 1)

    # reset
    if not i["running"]:
        print("No session — nothing to stop."); sys.exit(1)
    if (i.get("age_h") or 0) < 0.5:
        sys.exit(f"ABORT: session started {i['age_h']}h ago — too young; resetting here would spin "
                 f"the launcher (anti-spin guard).")
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"{stamp} — reset ({a.agent}, {i.get('runs','?')} runs, {i['age_h']}h)" + (f" — {a.why}" if a.why else "")
    if a.delay > 0:
        subprocess.Popen(["bash", "-c", f"sleep {a.delay}; kill {i['pid']} 2>/dev/null"],
                         start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.kill(i["pid"], signal.SIGTERM)
    print(line)
    print(f"-> stopping in {a.delay}s, then the launcher starts a FRESH session. Finish your turn "
          f"normally; your report goes out before the stop.")


if __name__ == "__main__":
    main()
