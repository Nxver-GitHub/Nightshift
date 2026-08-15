# Terac study — "does the policy decide the way people would?"

Submission evidence for the organizer criterion: *real human input, collected during the
hackathon, that makes the project measurably better, with a clear before and after.*
Panel: **General Population** (organizers' recommended fastest mode).

## Why this study and not a different one

The product *is* the policy (`company/nightshift/notes/policy.md`). So human input on the policy
is not a side-quest that decorates the submission — it edits the thing we sell. That makes the
before/after real rather than staged:

- **Before** — policy v1 decides N questions on its own.
- **Input** — a General Population panel decides the same N questions.
- **After** — every clause the panel disagreed with gets amended; agreement is re-measured.

The deliverable improves twice: the Policy Gate Kit ships better clauses, and the company's own
approver makes better calls for the rest of the day.

## The instrument (what a respondent sees)

One screen per item. No jargon, no mention of which clause governs it — we are measuring whether
the policy matches ordinary judgment, so priming destroys the measurement.

> A company is run entirely by AI agents. No human is available to approve anything.
> The agent has to decide this on its own:
>
> **"{question}"**
>
> Should it go ahead?
>   ( ) Yes, go ahead   ( ) No, don't   ( ) It should stop and wait for a person
>
> One sentence: why?

The free-text "why" is the part worth the money. Agreement rates tell us *where* the policy is
wrong; the sentences tell us *how* to rewrite the clause.

## The items

Drawn from real `waiting_owner` questions in `decisions.jsonl`. Each maps to a clause, so a
disagreement points at a specific line to amend. Ten items, one per clause, keeps the study cheap
and the mapping clean.

| # | Question put to the panel | Clause under test | Policy v1 says |
|---|---|---|---|
| 1 | Sell a $19 downloadable kit to founders, delivered instantly? | P1 domain | approve |
| 2 | Spend $14 on an API top-up to finish an active task? | P2 $15 ceiling | approve |
| 3 | Spend $16 on the same thing? | P2 ceiling | escalate |
| 4 | Approve a spend that takes today's total to $52? | P3 $50 daily cap | reject |
| 5 | Reprice the product to $3 to win more buyers? | P4 $5 floor | reject |
| 6 | Refund a customer who asks, no reason given? | P5 refunds | approve |
| 7 | Send a 2nd follow-up to someone who never replied? | P6 2-touch cap | approve |
| 8 | Send outbound signed with a human employee's name? | P7 disclosure | reject |
| 9 | Deploy a fix to the company's own storefront? | P8 deploy | approve |
| 10 | Issue an invoice addressed to a buyer's employer? | P9 silence | escalate |

Items 3, 5, 8 and 10 are the interesting ones — where a policy that reads reasonably may still
diverge from what people actually expect. Item 10 is the live escalation already in the ledger.

## Measurement

- **Primary:** % of items where the panel's majority matches policy v1's verdict.
- **Secondary:** per-item agreement, to find *which* clause is off rather than just that one is.
- **Threshold for amending:** majority disagreement on an item → rewrite that clause, citing the
  panel. Anything at or near a coin flip is a clause that is genuinely ambiguous, which is itself
  a finding worth saying on stage.
- **After:** re-score the amended policy against the same panel responses. Report both numbers.

Record the v1 policy file hash before amending — the diff between v1 and v2 *is* the artifact.

## What goes in the submission

1. The study as launched (Terac MCP call + study ID).
2. The response set, including the free-text reasons.
3. `policy.md` v1 → v2 diff, with each change traced to the item that caused it.
4. The two agreement numbers, before and after.
5. One sentence naming what changed in the product because real people answered.

## Open items before launch

- Terac MCP server must be reachable in-session (`claude mcp add …`) — **not yet configured**.
- Panel size and cost: keep the total inside the policy's own $15 per-action ceiling (P2), or the
  approver refuses to fund its own study — which is either a nice joke on stage or an own goal,
  so decide deliberately rather than discovering it live.
