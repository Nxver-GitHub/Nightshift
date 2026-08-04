# goals

> An agent that carries **one background objective** to completion — "500 prospecting emails this
> month", "get a meeting with the CEO of X". It calibrates the goal, writes a measurable plan,
> creates dated tasks for the taskrunner, and wakes on a cadence to measure and adjust, mostly on its
> own. Generalized from a working system.

## What it gives you
A goal store (`goal.py` / `goals.json`) plus the goal-agent role. The point is **autonomy**: the
owner sets a goal and steps back; the agent studies, plans, delegates the doing to the taskrunner,
measures against an honest metric, and adjusts — bothering the owner only for initial validation
(with an auto-activate delay) or a genuine exception.

## What it needs
- **Tools / accounts**: Python 3, Claude Code (one session per goal), and the `taskrunner` block (the
  goal creates tasks, it doesn't execute).
- **Config the agent must fill**: `GOALS_STORE` (goals.json path); point `$G` at goal.py and `$A` at
  the taskrunner's add_task.py.
- **Depends on blocks**: `taskrunner` (required). Reads the `crm` and the brain freely.

## What's in this block
- `code/goal.py` + `code/goals.json` — the store: `add`, `plan`, `activate`, `review`, `notify`,
  `done`, `set-session`, `show`, `list`, `due`.
- `skill/goal.md` — the role: calibrate → plan (measurable, multi-channel) → activate → watch; the
  autonomy contract; two escalation levels.
- `SETUP.md` — install & operate.

## How the agent installs it
Install `taskrunner` first. Copy `code/` into `command-center/goals/`; install the skill; run one
Claude Code session per goal (`/goal g-…`). See `SETUP.md`.

## v1 scope (honest)
Ships the store and the role. The plan file (`goals/<id>/plan.md`) is written by the agent per goal.
The periodic wake can be driven by the `scheduled-tasks` block (run `/goal` on `due` goals) or a
persistent session.

## Safety
The goal agent **only creates tasks**; the taskrunner's finalization gate still guards every
irreversible step. The high-priority escalation is reserved for real exceptions. The brain's safety
floor applies to everything it queues.
