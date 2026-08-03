# Dashboard — install & run

> For the founder's Claude Code agent. Read-only, localhost, no dependencies.

## Install & run
1. Copy `code/` into `command-center/dashboard/`.
2. Point it at the other blocks' files (env), then start it:
   ```bash
   export TASKRUNNER_TASKS=/path/to/taskrunner/tasks.json
   export CRM_DB=/path/to/crm/crm.db
   export BRAIN_DIR=/path/to/your-company-brain
   python3 command-center/dashboard/server.py
   ```
3. Open http://localhost:8787. Each panel says what to set if its source is missing.

## Keep it running
Run it in the background (`nohup python3 server.py &`) or as a small service. It's stateless and
read-only, so restarting is harmless. Change the port with `DASH_PORT`.

## Safety
- Binds to `127.0.0.1` only. **Don't** expose the port to the network or the internet — it shows real
  business data.
- Read-only: it never writes to the kanban, CRM, or brain. To change data, use the blocks' CLIs or a
  Claude Code session.

## Growing it later
The panels read plain files/DB, not a private API, so you can swap this minimal page for a richer
dashboard (any framework) without touching the other blocks.
