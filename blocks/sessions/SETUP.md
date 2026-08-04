# Sessions — install & wire

> For the founder's Claude Code agent. Supports persistent-loop agents (macOS/Linux).

## Install
1. Copy `code/` into `command-center/sessions/`.
2. Edit `sessions.json` to list your persistent agents — each with its Remote Control session name
   (the one passed to `claude --remote-control "<name>"` in the launcher), and thresholds:
   ```json
   { "agents": { "taskrunner": { "session": "Taskrunner", "max_runs": 4, "max_hours": 24 } } }
   ```
3. No skill to install — this is a helper the other agents call.

## Wire it into a persistent agent
In the agent's tick loop (e.g. the taskrunner skill), after the run's guards:
```bash
python3 command-center/sessions/session-cycle.py tick --agent taskrunner
# ... do the run ...
# when tick/check says a reset is due, finish the turn, write the handoff, then:
python3 command-center/sessions/session-cycle.py reset --agent taskrunner --why "handoff done"
```
The launcher (`start-taskrunner.sh`) relaunches a fresh session automatically.

## Find a project's attributed session
```bash
python3 command-center/sessions/list-sessions.py "/path/to/DEV/some-project"
```
Copy the chosen session id into that project's entity `main.md`, under Links.

## Notes
- The reset uses `ps`/`pgrep` — macOS/Linux. On Windows, restart sessions manually.
- Always **handoff first, reset second** — the run counter, tasks.json, and the brain are what a fresh
  session resumes from.
