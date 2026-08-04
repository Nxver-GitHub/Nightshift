# Goals — install & operate

> For the founder's Claude Code agent. Requires the `taskrunner` block.

## Install
1. Install `taskrunner` first. Note its `add_task.py` path for `$A`.
2. Copy `code/` into `command-center/goals/`.
3. Set `GOALS_STORE` (default `goals.json` next to the script).
4. Install the skill: `mkdir -p ~/.claude/skills/goal && cp blocks/goals/skill/goal.md ~/.claude/skills/goal/SKILL.md`,
   and set `$G` (goal.py) and `$A` (add_task.py) inside it.

## Create and run a goal
1. Add it: `python3 goal.py add --title "…" --objective "…"` → returns a `g-…` id.
2. Open a dedicated Claude Code session for that goal and load `/goal g-…`. One session per goal.
3. The agent calibrates, writes `goals/<id>/plan.md`, sets a measurable metric and cadence, and asks
   you to validate (or auto-activates after its delay).
4. Once active, it creates dated tasks for the taskrunner and wakes on its cadence to measure and
   adjust.

## Waking it on cadence
Drive the periodic review with the `scheduled-tasks` block: run `/goal` for goals that are `due`
(`python3 goal.py due`), or keep the session alive with the taskrunner-style launcher.

## Safety
The goal agent only queues tasks — the taskrunner still gates every irreversible step. Reserve the
high-priority escalation for real exceptions.
