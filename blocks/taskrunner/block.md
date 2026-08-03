# taskrunner

> The engine that makes a Command Center *act*. A kanban of tasks that agents work through, one at a
> time, self-paced — and a task is only closed when the runner has **verified** it's actually done,
> not just when a delegate claims it is. Generalized from a working system; no secrets, config-driven.

## What it gives you
A durable to-do queue (`tasks.json`) that any agent or human can add work to, and a **taskrunner
role** that picks the highest-priority task, does it (or delegates substantial coding work to another
agent and orchestrates it), verifies the real artifact, and closes it — updating your brain as it
goes. It bothers you (the owner) at exactly two moments: to confirm an irreversible step
(finalization), or when it hits a real blocker. Everything else, it decides on its own.

## What it needs
- **Tools / accounts**: none external. Python 3, Claude Code (for the `/loop` session and the
  installed skill), and a bash shell (macOS/Linux) for the launcher. Optional: whatever connectors
  your tasks touch (email, hosting…) — those belong to *other* blocks, not this one.
- **Config the agent must fill**:
  - `TASKRUNNER_OWNER` (env) — the human who confirms irreversible steps. Default: `the owner`.
  - `TASKRUNNER_TASKS` (env) or `--tasks PATH` — where `tasks.json` lives. Default: next to the scripts.
- **Depends on blocks**: none. Pairs well with `dashboard` (to see and edit the board) and
  `email-operator` (which files message-triggered tasks here), but runs fine alone.

## What's in this block
- `code/tasks.json` — an empty kanban to seed (`{"tasks": []}`).
- `code/add_task.py` — queue a task, atomically and concurrency-safe. Any agent can call it.
- `code/update_task.py` — evolve one task: claim, journal, visible plan (steps), ask the owner a
  question, raise a problem banner, propose finalization of irreversible gestures, record the result.
- `code/list_tasks.py` — print the board grouped by status (read-only).
- `code/start-taskrunner.sh` — the **launcher**: starts the persistent `/loop` session, auto-relaunches
  it if it dies, guards against a second instance (PID lock), keeps the machine awake. This is the
  "trigger" layer.
- `code/stop-taskrunner.sh` — clean stop (removes the on/off flag; the loop finishes its tick, then exits).
- `skill/taskrunner.md` — the role: the tick loop, claim-before-work, "the runner judges
  completion", the reversible/irreversible boundary, and how it closes a task.
- `SETUP.md` — the install & operate runbook the founder's Claude Code follows to set it all up and run it.

## How the agent installs it
Follow `SETUP.md` — the full install & operate runbook. In short: place `code/` in the founder's
`command-center/taskrunner/`; install `skill/taskrunner.md` into `~/.claude/skills/taskrunner/SKILL.md`
so `/taskrunner` resolves; set `TASKRUNNER_OWNER` (and optional paths/model) via an env file, never a
secret in git; start the persistent session with `./start-taskrunner.sh`; verify with a throwaway task
before real work goes through it.

## Safety
Inherits the brain's safety floor (`CLAUDE.md`). The runner does everything **reversible** on its own
(analyze, edit code locally, commit, prepare drafts, write infra commands without running them,
update the brain). It never does anything **irreversible** without the owner's explicit yes: `git
push`, any deploy, sending an email, writing to a client's production system, archiving a thread.
Those wait behind the finalization gate.
