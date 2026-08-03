# Taskrunner — install & operate runbook

> For the founder's Claude Code agent. Follow this to install the taskrunner into the founder's
> Command Center and get it running on its own. Everything here is generalized — fill the config
> from the founder's setup; never hardcode a secret.

## What you're setting up
A persistent Claude Code session that loops over a kanban (`tasks.json`): it claims the top task,
does it (or delegates and orchestrates), verifies the real result, and closes it — bothering the
owner only to confirm irreversible steps or on a real blocker. It's the same model a working system
uses: a `/loop` session kept alive by a small launcher.

## Step 1 — Place the code
Copy this block's `code/` into the founder's Command Center, e.g. `command-center/taskrunner/`.
It contains: `tasks.json` (seed), `add_task.py`, `update_task.py`, `list_tasks.py`,
`start-taskrunner.sh`, `stop-taskrunner.sh`. Make the shell scripts executable:
```bash
chmod +x command-center/taskrunner/start-taskrunner.sh command-center/taskrunner/stop-taskrunner.sh
```

## Step 2 — Install the skill
The role lives in `skill/taskrunner.md`. Claude Code loads skills from `~/.claude/skills/<name>/SKILL.md`.
Install it so `/taskrunner` resolves:
```bash
mkdir -p ~/.claude/skills/taskrunner
cp blocks/taskrunner/skill/taskrunner.md ~/.claude/skills/taskrunner/SKILL.md
```
In that copied skill, set `$TR` (near the top) to the founder's install path
(`command-center/taskrunner`) so its commands resolve.

## Step 3 — Configure (no secrets)
The scripts read config from the environment. Put these in a small env file the Command Center loads
(or export them in the launching shell) — never commit real values:
- `TASKRUNNER_OWNER` — the founder's name (who confirms irreversible steps). **Required-ish** (default
  "the owner").
- `TASKRUNNER_TASKS` — path to `tasks.json` if not next to the scripts (optional).
- `TASKRUNNER_MODEL` — model for the session (default `claude-opus-5`).
- `TASKRUNNER_SESSION` — remote-control session name (default `Taskrunner`).
- `TASKRUNNER_SKILL` — installed skill name (default `taskrunner`).

## Step 4 — Start it
```bash
cd command-center/taskrunner && ./start-taskrunner.sh
```
This creates the on/off flag `.taskrunner.on`, takes a PID lock (so a second launcher can't run), and
starts a `claude --remote-control "<session>" --permission-mode auto "/loop /taskrunner"` session. If
the session dies, the launcher relaunches it after 10s — until the flag is removed. On macOS it wraps
the session in `caffeinate` so the Mac doesn't sleep. (Equivalent: open a Claude Code session named
per `TASKRUNNER_SESSION` and type `/loop /taskrunner` — the launcher just keeps it alive.)

## Step 5 — Verify before trusting it
Add a throwaway task, watch the runner pick it up, then remove it:
```bash
python3 command-center/taskrunner/add_task.py --title "Verify taskrunner works" --description "Just journal a note and close."
python3 command-center/taskrunner/list_tasks.py       # see it in "To do", then claimed, then done
```
Only once you've seen claim → work → verify → close should real work go through it.

## Operating it, day to day
- **Add work** (any agent or a human): `python3 …/add_task.py --title "…" [--priority high] [--due YYYY-MM-DD]`.
- **See the board**: `python3 …/list_tasks.py` (or the `dashboard` block, if installed).
- **Stop**: `./stop-taskrunner.sh` (removes the flag; the loop finishes its current tick, then exits).
  Restart with `./start-taskrunner.sh`.
- **Irreversible steps**: the runner never pushes/sends/deploys on its own. It posts a
  **finalization** on the task and waits (`waiting_owner`). The owner confirms, then it executes.

## Safety & platform notes
- **`--permission-mode auto` is deliberate and safe *because of* the finalization gate.** The loop
  runs without permission prompts so it doesn't stall — but the skill's reversible/irreversible
  boundary means it never does anything committing (push, send, deploy, prod write, archive) without
  the owner's explicit yes. Keep the brain's safety floor (`CLAUDE.md`) intact; it's what makes auto
  mode acceptable.
- **Platform**: the launcher is a bash script (macOS/Linux). `caffeinate` is macOS-only and degrades
  to a no-op elsewhere. On Windows, run the loop under WSL, or start the `/loop /taskrunner` session
  manually and skip the keep-alive wrapper. A periodic (cron/systemd/Task Scheduler) variant can be
  added later if the founder prefers headless runs over a persistent session.
