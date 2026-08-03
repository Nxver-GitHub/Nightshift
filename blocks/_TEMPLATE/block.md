# {{BLOCK_NAME}}

> One capability, self-contained and generalized. No secrets, no wiring to anyone's specific
> accounts — everything company-specific is config the consolidating agent fills from the founder's
> answers.

## What it gives you
{{One paragraph: the outcome for the founder, in plain terms.}}

## What it needs
- **Tools / accounts**: {{e.g. an email account, a Supabase project, a domain}}
- **Config the agent must fill**: {{list the names it needs — never the values}}
- **Depends on blocks**: {{e.g. `dashboard`, `crm` — or "none"}}

## What's in this block
- `code/` — {{what the scaffold is; how it's parameterized}}
- `skill/` — {{the agent-role(s) this installs, and their one job}}

## How the agent installs it
1. {{copy `code/` into the founder's `command-center/…`}}
2. {{wire config to the founder's tools — never hardcode, never store a secret in a file}}
3. {{install the skill(s) into the founder's setup}}
4. {{start in review mode; verify it works end-to-end before promoting to automatic}}

## Safety
{{What this block must never do without an explicit human yes — it inherits the brain's safety
floor. Be specific: sends, payments, publishing, production writes.}}
