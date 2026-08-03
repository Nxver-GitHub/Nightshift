#!/usr/bin/env python3
"""
Track which messages the email operator has already handled, across runs (state.json).
A run can die mid-way; this is the memory that stops it re-processing or dropping messages.

Usage:  python3 state.py mark --id <msg-id>   # remember a message as handled
        python3 state.py seen --id <msg-id>   # exit 0 if already handled, 1 if new
        python3 state.py touch                 # stamp last_run = now
        python3 state.py show | reset
Config: --state PATH or $OPERATOR_STATE (default: state.json next to this script)
"""
import os, sys, json, argparse, datetime


def path(arg):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("OPERATOR_STATE")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")


def load(p):
    try:
        d = json.load(open(p))
        d.setdefault("last_run", None)
        d.setdefault("processed_ids", [])
        return d
    except Exception:
        return {"last_run": None, "processed_ids": []}


def save(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["mark", "seen", "touch", "show", "reset"])
    ap.add_argument("--id")
    ap.add_argument("--state")
    a = ap.parse_args()
    p = path(a.state)
    d = load(p)
    if a.cmd == "mark":
        if not a.id:
            sys.exit("ERROR: --id required")
        if a.id not in d["processed_ids"]:
            d["processed_ids"].append(a.id)
            save(p, d)
        print(f"OK marked {a.id}")
    elif a.cmd == "seen":
        sys.exit(0 if a.id in d["processed_ids"] else 1)
    elif a.cmd == "touch":
        d["last_run"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        save(p, d)
        print(f"OK last_run={d['last_run']}")
    elif a.cmd == "show":
        print(json.dumps(d, indent=2, ensure_ascii=False))
    elif a.cmd == "reset":
        save(p, {"last_run": None, "processed_ids": []})
        print("OK reset")


if __name__ == "__main__":
    main()
