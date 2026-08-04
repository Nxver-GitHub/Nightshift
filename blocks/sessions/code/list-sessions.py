#!/usr/bin/env python3
"""
List the Claude Code conversations for a project directory, with their session id.
Use it to pick the "attributed session" of a project (record it in the brain's entity main.md,
under Links) — the one conversation that holds a project's up-to-date context, that agents resume
to delegate work.

Usage:
  python3 list-sessions.py "/path/to/DEV/some-project"
  python3 list-sessions.py            # current directory
"""
import sys, os, re, json, datetime

path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())
enc = re.sub(r"[^A-Za-z0-9]", "-", path)
proj = os.path.expanduser(f"~/.claude/projects/{enc}")

if not os.path.isdir(proj):
    print(f"No Claude Code conversation for: {path}")
    sys.exit(0)


def first_user_text(fp):
    try:
        with open(fp, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if d.get("type") != "user":
                    continue
                c = d.get("message", {}).get("content")
                txt = c if isinstance(c, str) else (
                    " ".join(x.get("text", "") for x in c
                             if isinstance(x, dict) and x.get("type") == "text")
                    if isinstance(c, list) else "")
                txt = txt.strip()
                if not txt or txt.startswith(("<local-command", "<command-name", "<system-reminder", "Caveat:")):
                    continue
                return txt[:110]
    except Exception:
        pass
    return "(unreadable)"


files = [os.path.join(proj, f) for f in os.listdir(proj) if f.endswith(".jsonl")]
files.sort(key=os.path.getmtime, reverse=True)

print(f"Conversations for {path} ({len(files)}) — most recent first:\n")
for fp in files[:15]:
    sid = os.path.basename(fp)[:-6]
    m = datetime.datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M")
    n = sum(1 for _ in open(fp, encoding="utf-8", errors="ignore"))
    print(f"* {sid}")
    print(f"   modified {m} · ~{n} events")
    print(f"   start: \"{first_user_text(fp)}\"\n")
print('To attribute: copy the session id into the project\'s entity main.md, under Links ("Session").')
