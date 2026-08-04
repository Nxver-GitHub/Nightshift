# Email operator — install & operate

> For the founder's Claude Code agent. Requires the `taskrunner` block and a connected email tool.

## Install
1. Install `taskrunner` first (multi-step work is delegated to it). Note its path for `$TR`.
2. Copy `code/` into `command-center/email-operator/`.
3. Connect the founder's email tool. **Recommended: Composio** (`blocks/connectors.md`) — it handles
   the OAuth and exposes email tools to the agent; a native MCP or CLI works too. The skill uses
   whatever is available — no hardcoded provider. Confirm the agent can list today's messages and
   create a draft.
4. Install the skill: `mkdir -p ~/.claude/skills/email-operator && cp blocks/email-operator/skill/email-operator.md ~/.claude/skills/email-operator/SKILL.md`,
   then set `$STATE` (state.py) and `$TR` (taskrunner) inside it.
5. Configure: `OPERATOR_STATE` (default `state.json` next to the script), `OPERATOR_MODEL`.

## Operate
- **By hand**: `./run-operator.sh` — one pass, drafts + report only.
- **Periodically**: schedule `run-operator.sh` with the `scheduled-tasks` block (e.g. every 30 min
  during working hours). Keep it review-mode: drafts only, the owner sends.
- Each run marks handled messages (`state.py mark`) so the next run skips them; it stamps `last_run`.

## Safety
- The operator **never sends**. It drafts and delegates; the owner reviews and sends.
- It only discloses client data to a **known** sender (checked against the brain's `people.md`).
- Anything committing or sensitive is flagged to the owner, not actioned.
