# Dashboard — install & run

> For the founder's Claude Code agent. Read-only, localhost, no dependencies.

## Install & run
1. Copy `code/` into `command-center/dashboard/`.
2. Point it at the other blocks' files (env), then start it:
   ```bash
   export TASKRUNNER_TASKS=/path/to/taskrunner/tasks.json
   export CRM_DB=/path/to/crm/crm.db
   export BRAIN_DIR=/path/to/your-company-brain
   export APPROVER_LEDGER=/path/to/approver/decisions.jsonl
   python3 command-center/dashboard/server.py
   ```
3. Open http://localhost:8787. Each panel says what to set if its source is missing.

## Keep it running
Run it in the background (`nohup python3 server.py &`) or as a small service. It's stateless and
read-only, so restarting is harmless. Change the port with `DASH_PORT`.

## Running it somewhere other than your laptop
`DASH_BIND` sets the listening interface; it defaults to `127.0.0.1`. Inside a VM published through
a preview URL (the `runtime` block), the router can't reach a loopback-only socket, so set
`DASH_BIND=0.0.0.0` there — and only there, where the platform controls who reaches the port.

## Tests
```bash
python3 -m pytest blocks/dashboard/tests/ -q                        # API layer (stdlib only)
uvx --with pytest-playwright pytest blocks/dashboard/tests/ -q      # + the browser layer
```
The Playwright tests skip cleanly when Chromium isn't installed — no test in this repo should fail
because a browser wasn't provisioned.

## Safety
- Binds to `127.0.0.1` by default. **Don't** widen `DASH_BIND` or expose the port to the internet
  without something in front of it — the page shows real business data.
- Read-only: it never writes to the kanban, CRM, brain, or the decision ledger. To change data, use
  the blocks' CLIs or a Claude Code session.

## Growing it later
The panels read plain files/DB, not a private API, so you can swap this minimal page for a richer
dashboard (any framework) without touching the other blocks.
