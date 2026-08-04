# Connectors — wiring blocks to your apps

Sunday blocks are **connector-agnostic**: the kit imposes no specific integration. Where a block
needs an external app, it uses whatever tool you've connected. This page says what actually needs a
connector, and what we recommend.

## What actually needs a connector (it's little)
Most blocks are fully **local** — no connector, no account:
`taskrunner` · `crm` · `prospection` (the queue) · `content-agents` (the pipeline) · `dashboard` ·
`scheduled-tasks` · `sessions` · `health` · `goals`.

Only two surfaces reach outside:
- **Email** — read/draft for `email-operator`, and the *send* step of `prospection`. Needs an email tool.
- **Stats** — `content-agents` reads each network's analytics. Usually just the browser.

## Recommended: Composio
For email — and later a CRM, calendar, LinkedIn, Slack, and 250+ other apps — we recommend
**[Composio](https://composio.dev)**: a connector platform that links your apps to your agent through
one interface and handles the OAuth for you, so you don't wire each API by hand. It covers the most
apps for the least setup, which is why it's our default.

Setup (once):
1. Install the Composio CLI (or its MCP) for your Claude Code.
2. Connect your accounts (e.g. Outlook or Gmail) — Composio walks you through the sign-in in your browser.
3. `email-operator` then uses the available email tools automatically — nothing to hardcode.

## Alternatives (equally fine — the kit stays agnostic)
- A **native MCP connector** in your Claude Code (an Outlook/Gmail MCP).
- A **CLI** for your mail provider.

Pick one; `email-operator` and `prospection` adapt to what's available.

## The one rule
**No secret in git — ever.** Whatever connector you use, credentials live in the connector's own
store (Composio's vault, your OS keychain, a git-ignored env file), never in a file in your brain or
this kit.
