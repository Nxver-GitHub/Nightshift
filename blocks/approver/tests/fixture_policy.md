# Delegated approval policy — example shape

> Reference only. The tests do not parse this file; it documents the shape the `approver` skill
> expects at `$APPROVER_POLICY`. Numbered clauses, one decision each, in the founder's own words.

**P1** — Routine engineering work (local edits, commits, running tests) is pre-approved. It never
reaches this gate.

**P2** — A `git push` to a non-production branch of a repo the company owns is approved when the task
has a green test run recorded in its journal.

**P3** — A client refund up to 100 EUR is approved. Above 100 EUR: escalate.

**P4** — A reply email to an existing thread with an existing client is approved when the draft
contains no price, no date commitment, and no legal statement.

**P5** — Any write to a client's production system, any deploy to production, and any push to a
release branch are refused at this gate. Escalate; only the owner decides.

Anything not named above is not covered: escalate.
