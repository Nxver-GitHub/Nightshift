---
name: crm
description: The Command Center's CRM discipline — how any agent records companies, contacts, and projects, and keeps every open project alive with a dated next action. Read before touching customer/pipeline data; it's a tool + a set of rules, not an autonomous agent.
---

# crm

The CRM is where the company remembers who it's talking to and what happens next. Every agent uses
the same CLI (`crm.py`). Set `$CRM` to its path and `CRM_DB` to the database.

## The rules (the tool enforces them; you honor them)
- **Nothing sleeps.** Any open project must carry a next action + a next-action date. After any real
  exchange, immediately `project-touch` to log what happened and reset the next action. A project
  with no future next action is a bug — fix it.
- **Read before you write.** Before contacting a company or citing its state, `show` it. Before
  emailing a person, read their entry in the owning entity's `people.md`.
- **Log the exchange.** Every meaningful interaction (call, meeting, reply) → `project-touch` or
  `note`. The event log is the company's memory; don't skip it.
- **Disqualify with a reason.** `set-status --status disqualified` requires `--reason`.

## Common moves
```bash
python3 "$CRM" add-company --name "Acme" --status qualified --source reference
python3 "$CRM" add-contact --company 1 --name "Jamie" --role "Ops" --email jamie@acme.example
python3 "$CRM" project-add --company 1 --title "Automate invoicing" --stage proposed --amount 8000 --next "Send quote" --next-date 2026-08-10
python3 "$CRM" project-touch --id 1 --channel call --summary "Wants a demo" --next "Book demo" --next-date 2026-08-05
python3 "$CRM" relances       # what's due or overdue — run this on every review
python3 "$CRM" show --id 1 ; python3 "$CRM" stats
```

## Money, without lying to yourself
`stats` reports **signed** (won + delivered) and **in play** (identified…negotiation) separately.
Never add them — "signed + in play" means nothing.
