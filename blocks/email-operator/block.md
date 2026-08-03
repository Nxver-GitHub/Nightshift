# email-operator

> Keeps the inbox under control. One run triages the day's messages: a simple reply becomes a draft
> now; anything multi-step becomes one task on the taskrunner (with the message reference) and the
> operator never touches it again. It never sends or does anything irreversible without the owner's yes.

## What it gives you
An inbox triage role (the skill) plus a tiny state tracker (`state.py`) so it never re-processes or
drops a message across runs, and a headless run script. **Connector-agnostic**: it uses whatever
email tool the founder has connected — an email MCP, a CLI — the skill is about the *decisions*, not
a provider.

## What it needs
- **Tools / accounts**: Python 3, an email tool the founder has connected, and the `taskrunner` block
  (for multi-step delegation). Reads the brain (for `people.md` identity checks) and the `crm` block
  if present.
- **Config the agent must fill**: `OPERATOR_STATE` (state.json path), `OPERATOR_MODEL` (default
  `claude-opus-5`). Point `$TR` at the taskrunner install.
- **Depends on blocks**: `taskrunner`. Pairs with `crm`, `scheduled-tasks` (to run it every N min).

## What's in this block
- `code/state.py` + `code/state.json` — the already-handled tracker (`mark`, `seen`, `touch`, `show`).
- `code/run-operator.sh` — one headless run (drafts + report only; never sends).
- `skill/email-operator.md` — the role: triage, draft simple replies, delegate multi-step to the
  taskrunner, verify sender identity before disclosing data, never send without the owner's yes.
- `SETUP.md` — install & operate.

## How the agent installs it
Install `taskrunner` first. Copy `code/` into `command-center/email-operator/`; install the skill;
connect the founder's email tool; run `run-operator.sh` by hand once, or schedule it with the
`scheduled-tasks` block. See `SETUP.md`.

## Safety
Hard line: **never send or do anything irreversible on its own.** It prepares drafts and tasks; the
owner sends. Identity check before disclosing any client data. This is the brain's safety floor,
enforced by the role.
