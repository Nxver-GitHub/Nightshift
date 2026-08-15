---
policy_version: 1
per_action_spend_ceiling_usd: 15
daily_spend_cap_usd: 50
price_floor_usd: 5
price_ceiling_usd: 25
outbound_daily_cap: 25
outbound_max_touches_per_contact: 2
outbound_followup_min_days: 2
approvable_finalize_types: push, email, deploy, archive
---

# Approval policy — the written owner

This file is the owner. The approver agent may answer any `waiting_owner` question **only** by
citing the clauses below. The machine-readable caps in the frontmatter are the same numbers as the
prose; if they ever disagree, the stricter reading wins and the question escalates (P9).

A clause either clearly permits, clearly forbids, or is silent. **Silence is never consent** — see P9.

## Domain

- **P1** — The company operates only in its fixed domain: it sells **digital products, priced
  $5–$25, delivered instantly, to founders and builders**. Any question about acting outside this
  domain (a different market, a physical good, a service engagement, a subscription) is not
  answerable by this policy → escalate.

## Money

- **P2** — A single outgoing spend (a purchase, an API top-up, a hired expert, any payment leaving
  the company) may be approved when it serves an active goal or task **and is at most $15**.
  Anything above $15 → escalate, whatever the justification.
- **P3** — Total approved outgoing spend across a calendar day may not exceed **$50**. The decision
  ledger is the source of the running total: before approving a spend, sum today's approved spends;
  if the new spend would cross $50 → reject, citing this clause.
- **P4** — A product may be listed or repriced only within **$5–$25**. Below $5 or above $25 →
  reject. (The floor exists so revenue is real revenue, not a race to zero.)

## Refunds

- **P5** — A refund request up to the original sale price is approved **immediately and
  unconditionally**. No interrogation of the customer, no delay. (The company's worst customer
  outcome must be "they got their money back.") A refund above the original sale price → escalate.

## Outreach & identity

- **P6** — Outbound to strangers is approvable up to **25 sends per calendar day**, at most
  **2 touches per contact ever** (one first-touch, one follow-up), with the follow-up **no sooner
  than 2 days** after the first. A reply of any kind stops all further sends to that contact
  (the prospection block enforces this; the approver never overrides it).
- **P7** — Every outbound message and every public-facing surface (storefront, landing page)
  **identifies the sender as an autonomous agent** running this company. Approve outbound only if
  the draft discloses this. A message written to pass as a human, or signed with a human's name →
  reject, and see P10.

## Irreversible gestures (finalize)

- **P8** — The four finalize types are approvable only under their conditions; any other type
  escalates by definition:
  - `email` — only within P6 caps and carrying the P7 disclosure.
  - `push` / `deploy` — only to **this company's own** repositories and infrastructure. Anything
    touching a third party's systems → escalate.
  - `archive` — freely approvable; archiving is reversible in practice.

## Escalation — "policy cannot decide", defined

- **P9** — Escalate when, and only when, **no clause above explicitly permits or forbids** the
  action in question. Do not stretch a clause by analogy; do not infer consent from silence; do not
  approve because an action seems small. An escalated task stays untouched in `waiting_owner` for
  the human-labor path — that is the designed outcome, not a failure.

## Hard NOs — never approvable, no clause outranks these

- **P10** — Never, regardless of any other clause:
  - impersonate a human being or hide that the sender is an agent (see P7);
  - exceed the P2/P3 spend ceilings or the P6 send caps by any amount;
  - place a secret, credential, or API key into git, a message, a log, or any public surface;
  - bypass, disable, or self-modify the approval gate, this policy, or the decision ledger;
  - send beyond P6's caps to a contact who has not replied, or contact anyone who asked to stop.
