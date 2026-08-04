# sessions

> Keeps persistent agents sharp. A persistent `/loop` session accumulates context until it saturates
> and degrades; this block counts each real run and starts the session fresh at a threshold (the
> launcher relaunches it clean). Plus a helper to find a project's "attributed session". Generalized
> from a working system.

## What it gives you
- `session-cycle.py` — for each persistent agent: count runs (`tick`), check whether a reset is due
  (`check`), and reset cleanly (`reset`) — ending the session so the launcher starts a fresh one. The
  reset is safe because the handoff already lives on disk (tasks.json, state.json, the brain).
- `list-sessions.py` — list the Claude Code conversations for a directory, to pick the one
  conversation that holds a project's up-to-date context (record it in the brain).

## What it needs
- **Tools / accounts**: Python 3, and a Unix shell with `ps`/`pgrep` (macOS/Linux) for the reset
  logic. `list-sessions.py` just reads `~/.claude/projects/`.
- **Config the agent must fill**: `sessions.json` (which persistent agents exist, their Remote Control
  session name, max runs/hours). Default: a single `taskrunner`.
- **Depends on blocks**: pairs with `taskrunner` (and any persistent-loop agent); no hard dependency.

## What's in this block
- `code/session-cycle.py` + `code/sessions.json` — the run counter + reset.
- `code/list-sessions.py` — find a project's attributed session.
- `SETUP.md` — install & wire.

## How agents use it
A persistent agent calls `session-cycle.py tick --agent <name>` **once per real run** (after the
guards, so an empty/skipped run doesn't count). When `tick`/`check` says a reset is due, the agent
finishes its turn, writes its handoff, then `session-cycle.py reset --agent <name>` — the launcher
relaunches a fresh session. The taskrunner skill's tick loop is the natural caller.

## v1 scope (honest)
The reset relies on `ps`/`pgrep` and the Remote Control session name — macOS/Linux. `ps -o lstart`
formats vary slightly by OS; if the age can't be parsed, the run counter is the primary signal (age
is only a backstop). On Windows, skip the auto-reset and restart sessions manually.

## Safety
Read/introspection only, plus killing a **session it owns** (matched by Remote Control name) after a
delay so the agent finishes cleanly. It never touches other processes or data.
