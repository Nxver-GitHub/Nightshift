#!/usr/bin/env python3
"""
Journal of the system's TESTS and IMPROVEMENTS — health/journal.jsonl.

healthcheck.py says whether the system is ALIVE; this journal is the dated trace of what you CHANGED
between two measurements. Without it, a drop in health is a mystery: you see the symptom, never the
change that caused it.

Format: JSON Lines (one entry per line, append-only) — two concurrent writes can't corrupt each
other, and one bad line doesn't take the rest down.

Usage:
  python3 health-log.py add --type improvement --title "…" [--detail "…"] [--source "…"] [--date 2026-08-03]
  python3 health-log.py list [--limit 20] [--type test]
"""
import json, os, sys, time, fcntl, datetime, argparse

BASE = os.path.dirname(os.path.abspath(__file__))
HEALTH_DIR = os.path.join(BASE, "health")
FILE = os.path.join(HEALTH_DIR, "journal.jsonl")
TYPES = ["test", "improvement", "incident"]


def today():
    return datetime.date.today().strftime("%Y-%m-%d")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def _read(path):
    out, bad = [], 0
    if not os.path.exists(path):
        return out, bad
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
                out.append(e) if isinstance(e, dict) else out
                if not isinstance(e, dict):
                    bad += 1
            except Exception:
                bad += 1
    return out, bad


def _append(path, entry):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines, _ = _read(path)
    lines.append(entry)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for e in lines:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description="Journal of tests & improvements.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--type", required=True, choices=TYPES)
    a.add_argument("--title", required=True)
    a.add_argument("--detail", default="")
    a.add_argument("--source", default="", help="where it came from: healthcheck, skills, dev:<x>…")
    a.add_argument("--date", default="")
    a.add_argument("--file", default=FILE)
    l = sub.add_parser("list")
    l.add_argument("--limit", type=int, default=20)
    l.add_argument("--type", default="", choices=[""] + TYPES)
    l.add_argument("--file", default=FILE)
    args = ap.parse_args()
    path = os.path.abspath(args.file)

    lock = open(path + ".lock", "w")
    for _ in range(50):
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            time.sleep(0.1)
    try:
        if args.cmd == "add":
            d = (args.date or today()).strip()
            try:
                datetime.datetime.strptime(d, "%Y-%m-%d")
            except ValueError:
                sys.exit(f"invalid date: {d!r} — expected YYYY-MM-DD")
            if not args.title.strip():
                sys.exit("empty title.")
            existing, _ = _read(path)
            used = {e.get("id") for e in existing}
            base_id = "h-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            new_id, n = base_id, 1
            while new_id in used:
                new_id = f"{base_id}-{n}"; n += 1
            entry = {"id": new_id, "date": d, "type": args.type, "title": args.title.strip(),
                     "detail": args.detail.strip(), "source": args.source.strip(), "created_at": now()}
            _append(path, entry)
            print(f"OK {entry['id']} [{entry['date']}] {entry['type']} — {entry['title']}")
        else:
            entries, bad = _read(path)
            if args.type:
                entries = [e for e in entries if e.get("type") == args.type]
            entries = list(enumerate(entries))
            entries.sort(key=lambda p: (str(p[1].get("date") or ""), p[0]), reverse=True)
            entries = [e for _, e in entries][: max(1, args.limit)]
            if not entries:
                print("empty journal."); return
            print(f"{len(entries)} entry(ies)" + (f" · {bad} bad line(s) ignored" if bad else "") + ":")
            for e in entries:
                src = f"  ({e.get('source')})" if e.get("source") else ""
                print(f"  [{e.get('date','?')}] {e.get('type','?'):12s} {e.get('title','')}{src}")
                if e.get("detail"):
                    print(f"        {e['detail']}")
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


if __name__ == "__main__":
    main()
