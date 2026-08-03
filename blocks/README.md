# Blocks — build your Command Center

The **brain** (see `START-HERE.md`) gives your company its memory. **Blocks** give it hands: a
dashboard, agents that actually work, connectors. Each block is self-contained and **generalized** —
no wiring to anyone else's accounts, no secrets. Your Claude Code agent reads this catalog, *you*
pick what you want, and the agent **consolidates** the chosen blocks into your **own** Command
Center — private, yours, wired to your tools.

That's the model: Sunday ships the parts; your agent assembles the machine for you.

## How consolidation works
1. Your brain exists (the founding interview is done).
2. You run `/sunday-assemble` (or just say "build my command center").
3. The agent shows you the menu below; you pick the blocks you want.
4. For each block, the agent installs its code + role-skill into a private `command-center/`, wires
   it to **your** tools (never hardcoded, never a secret in a file), and starts it in **review mode**
   (it prepares, you approve) until it's proven.
5. Nothing runs on your real data without your explicit yes. Add or drop blocks anytime.

## The catalog
| Block | What it gives you | Status |
|---|---|---|
| `dashboard` | A read-only local view over your brain, kanban, and CRM (minimal, no build step) | **built** |
| `taskrunner` | A kanban the agents work through, self-paced, only closed when verified done | **built** |
| `email-operator` | Inbox triage → drafts + queued tasks; never sends without your yes | **built** |
| `crm` | Companies / contacts / projects / interactions, each with a dated next action | **built** |
| `prospection` | Outbound engine on top of the CRM ("nothing sleeps") | **built** |
| `content-agents` | One persistent agent per network (LinkedIn / X / shorts / blog) | **built** |
| `scheduled-tasks` | Cron-style automation, review-mode first, promoted to auto once proven | **built** |

*(Status is `planned` until a block is generalized and dropped in. Blocks are built one at a time,
each proven before the next.)*

## Anatomy of a block
Each block is a folder holding:
- `block.md` — the manifest: what it does, what it needs, how the agent installs it. See
  `_TEMPLATE/block.md`.
- `code/` — the generalized, parameterized scaffold (UI, script, function). Optional for
  skill-only blocks.
- `skill/` — the agent-role skill(s) this block installs. Optional for code-only blocks.

## The one rule for every block
Generalized and config-driven. Everything company-specific (accounts, endpoints, addresses) is
**config the agent fills from the founder's answers** — never hardcoded, never a secret in a file.
A block a stranger clones must work for *their* company, not leak yours.
