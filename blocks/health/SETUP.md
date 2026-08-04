# Health — install & schedule

> For the founder's Claude Code agent. Read-only except filing a taskrunner ticket on a red signal.

## Install
1. Copy `code/` into `command-center/health/`.
2. Point the checks at the other blocks (env):
   ```bash
   export TASKRUNNER_TASKS=/path/to/taskrunner/tasks.json
   export CRM_DB=/path/to/crm/crm.db
   export HEALTH_ADD_TASK=/path/to/taskrunner/add_task.py   # enables ticket creation on red
   ```
3. Try it read-only: `python3 healthcheck.py --report` — you'll get a JSON verdict. Each check is
   `unknown` if its source isn't set (that's expected, not a failure).

## Schedule it
Use the `scheduled-tasks` block to run `healthcheck.py` on a cadence (e.g. every 30 min). Without
`--report`, a red signal files a high-priority taskrunner task; the taskrunner then handles it (its
finalization gate still guards anything irreversible).

## Exemptions
To silence a check you've deliberately turned off, add its name to `healthcheck.json`:
`{ "exempt": ["crm_db"] }`. An exempted red becomes `exempt`, not `red`.

## Journal your changes
When you test or improve the system, log it so a later health drop is traceable:
```bash
python3 health-log.py add --type improvement --title "…" --detail "…" --source "…"
python3 health-log.py list --limit 20
```

## Notes
`healthcheck.py` always exits 0 — read the JSON, not the exit code. Grow it with checks for whatever
you run, keeping the "unknown-not-red" discipline so it stays trustworthy.
