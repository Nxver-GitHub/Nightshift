#!/usr/bin/env python3
"""
Content pipeline — track content items per network, from idea to posted, with stats for iteration.
The agent never publishes: the owner posts manually and returns the URL (mark-posted).

Statuses: idea -> draft -> ready -> posted.

Usage:  python3 content.py add --network linkedin --title "…"
        python3 content.py set --id 3 --status draft --body-file draft.md
        python3 content.py mark-posted --id 3 --url https://…
        python3 content.py stats --id 3 --impressions 1200 --reactions 40
        python3 content.py list [--network linkedin] [--status ready]
        python3 content.py show --id 3
Config: --store PATH or $CONTENT_STORE (default: content.json next to this script)
"""
import os, sys, json, argparse, datetime

NETWORKS = ["linkedin", "x", "shorts", "blog"]
STATUS = ["idea", "draft", "ready", "posted"]


def store_path(arg):
    if arg:
        return os.path.abspath(arg)
    env = os.environ.get("CONTENT_STORE")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "content.json")


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def load(p):
    try:
        d = json.load(open(p))
        d.setdefault("items", [])
        return d
    except Exception:
        return {"items": []}


def save(p, d):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def find(d, i):
    return next((x for x in d["items"] if x["id"] == i), None)


def cmd_add(d, a):
    nid = (max([x["id"] for x in d["items"]], default=0)) + 1
    d["items"].append({"id": nid, "network": a.network, "status": "idea", "title": a.title,
                       "body": "", "url": None, "stats": {}, "created_at": now(), "posted_at": None})
    return f"OK content #{nid} — [{a.network}] {a.title} (idea)"


def cmd_set(d, a):
    it = find(d, a.id)
    if not it:
        sys.exit(f"ERROR: item #{a.id} not found.")
    if a.status:
        it["status"] = a.status
    if a.body_file:
        it["body"] = open(a.body_file, encoding="utf-8").read()
    elif a.body is not None:
        it["body"] = a.body
    return f"OK item #{a.id} -> {it['status']}"


def cmd_mark_posted(d, a):
    it = find(d, a.id)
    if not it:
        sys.exit(f"ERROR: item #{a.id} not found.")
    it["status"] = "posted"
    it["url"] = a.url
    it["posted_at"] = now()
    return f"OK item #{a.id} posted — {a.url}"


def cmd_stats(d, a):
    it = find(d, a.id)
    if not it:
        sys.exit(f"ERROR: item #{a.id} not found.")
    for k in ("impressions", "reactions", "comments", "shares", "clicks"):
        v = getattr(a, k)
        if v is not None:
            it["stats"][k] = v
    return f"OK stats updated for #{a.id}: {it['stats']}"


def cmd_list(d, a):
    items = d["items"]
    if a.network:
        items = [x for x in items if x["network"] == a.network]
    if a.status:
        items = [x for x in items if x["status"] == a.status]
    for x in items:
        u = f"  {x['url']}" if x.get("url") else ""
        print(f"  #{x['id']:>3} [{x['network']}] [{x['status']}] {x['title']}{u}")
    return None


def cmd_show(d, a):
    it = find(d, a.id)
    if not it:
        sys.exit(f"ERROR: item #{a.id} not found.")
    print(f"# [{it['network']}] {it['title']}  (#{it['id']}, {it['status']})")
    if it.get("url"):
        print(f"  url: {it['url']}  posted: {it['posted_at']}")
    if it.get("stats"):
        print(f"  stats: {it['stats']}")
    print("  ---")
    print(it.get("body") or "(no body yet)")
    return None


def build_parser():
    ap = argparse.ArgumentParser(description="Content pipeline per network")
    ap.add_argument("--store")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("add"); s.add_argument("--network", required=True, choices=NETWORKS)
    s.add_argument("--title", required=True); s.set_defaults(f=cmd_add)
    s = sub.add_parser("set"); s.add_argument("--id", type=int, required=True)
    s.add_argument("--status", choices=STATUS); s.add_argument("--body"); s.add_argument("--body-file")
    s.set_defaults(f=cmd_set)
    s = sub.add_parser("mark-posted"); s.add_argument("--id", type=int, required=True)
    s.add_argument("--url", required=True); s.set_defaults(f=cmd_mark_posted)
    s = sub.add_parser("stats"); s.add_argument("--id", type=int, required=True)
    for k in ("impressions", "reactions", "comments", "shares", "clicks"):
        s.add_argument(f"--{k}", type=int)
    s.set_defaults(f=cmd_stats)
    s = sub.add_parser("list"); s.add_argument("--network", choices=NETWORKS)
    s.add_argument("--status", choices=STATUS); s.set_defaults(f=cmd_list)
    s = sub.add_parser("show"); s.add_argument("--id", type=int, required=True); s.set_defaults(f=cmd_show)
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
