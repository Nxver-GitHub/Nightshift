# LEDGER-SCHEMA.md

**What this is:** the format of `decisions.jsonl` — the append-only audit trail your approver writes
one line to for every verdict it reaches. Field by field, plus a worked example of a single day.

**Where it fits:** this is file 3 of 6. The approver in `APPROVER-PROMPT.md` writes to it, the daily
spend cap in `POLICY-TEMPLATE.md` (P3) is computed *from* it, and `ESCALATION-RUNBOOK.md` reads the
escalations out of it. It is also the artifact you show when someone asks "who approved that?"

---

## The format in one paragraph

**JSON Lines.** One JSON object per line, newline-terminated, UTF-8. Appended, never rewritten,
never sorted, never deduplicated. No enclosing array, no commas between lines, no header. A corrupt
line costs you one record instead of the file. `tail -f` works. `grep` works. So does
`jq -s 'map(select(.verdict=="escalated"))' decisions.jsonl` when you want the week's gaps in one
command.

The append-only property is the point. A decision log you can edit is not evidence, it's a draft.

```jsonl
{"ts":"2026-08-15 09:12","task_id":"t-104","question":"OK to hire an expert for a 15-minute pricing sanity check at $12?","verdict":"approve","reason":"Spend is $12, under the P2 per-action ceiling of $15; today's approved total was $0 before this, well under the P3 daily cap of $50.","policy_clauses_cited":["P2","P3"],"mode":"agent"}
```

---

## Fields

Seven fields. All seven present on every line — no optional keys, no nulls. A reader should never
have to guess whether a missing field means "not applicable" or "the writer crashed".

### `ts` — string

Timestamp of the decision, `"YYYY-MM-DD HH:MM"`, **local time to the machine running the approver**.

Minute resolution, because a decision log is read by humans and seconds are noise. It records when
the *decision* was made, not when the question was asked and not when the action ran.

> **Fill this in for yourself:** the format carries no timezone. That's fine for a single-machine
> loop and a real hazard the moment you have two. Decide now what "calendar day" means for your daily
> cap — a named timezone, written into your policy — because the day boundary is where a cap can be
> quietly walked around. If you run in more than one region, store UTC and say so in your policy.

### `task_id` — string

Identifier of the task or request the question belonged to. Opaque to the ledger; it just has to be
the same ID your queue uses, so a reviewer can go from a line here to the work it gated.

If you have several queues, prefix it (`kanban:t-104`, `stripe:evt-88`). Don't reuse IDs — the ledger
outlives the task.

### `question` — string

The question text **exactly as it was asked**, verbatim, copied at decision time.

Verbatim matters. If you store your own summary, you have stored the approver's interpretation of the
question rather than the question, and every later review is auditing the summary. Multi-line
questions keep their newlines (JSON-escaped as `\n`).

### `verdict` — string, one of three

| Value | Meaning | Effect on the task |
|---|---|---|
| `"approve"` | A clause clearly permits this exact thing | Answer written; the loop proceeds |
| `"reject"` | A clause clearly forbids it | Answer written; the loop is unblocked with a no |
| `"escalated"` | No clause decides it | **Nothing written.** Task untouched, waiting on a human |

Note the tense: `approve` and `reject` are the verdict, `escalated` is what happened. It reads oddly
and it is deliberate — an escalation is not a decision about the action, it is a decision *not to
decide*, and the word should feel different when you scan the file.

Three values, closed set. If you find yourself wanting a fourth — `approve_with_conditions`,
`deferred`, `partial` — that is a clause missing from your policy, not a value missing from this
enum. Conditional approval is how a gate becomes a negotiation.

### `reason` — string

One sentence naming the deciding fact and the clause. Never empty — a verdict with no reason is
refused at write time, because the entire value of the ledger is that a stranger can check the
reasoning six weeks later.

Good: `"Amount is $12, under the P2 ceiling of $15."`
Useless: `"Looks fine."`

For an escalation, the reason states **what the policy did not cover** — `"Policy is silent on
recurring revenue."` Those sentences are the raw material for your next clause, so write them as if
you were briefing the person who has to answer.

**Never put a secret, key, token, credential, or personal contact detail in a reason.** This file is
built to be read, and quite possibly published. Describe the sensitive fact without reproducing it.

### `policy_clauses_cited` — array of strings

The clause IDs that justify the verdict, e.g. `["P2","P3"]`.

- **Non-empty for every `approve` and every `reject`.** A verdict with no citation is not a verdict;
  it's an opinion, and it should have been an escalation.
- **Empty (`[]`) for every `escalated` line** — that's the definition of escalating: no clause
  decided it.
- **List every clause that binds**, not the one that's thematically nearest. A spend cites the
  per-action ceiling *and* the daily cap. An outbound send cites the volume clause *and* the
  disclosure clause.

This field is what makes the ledger queryable in the way that matters. `P10` appearing anywhere is
worth a look. A clause that never appears in six weeks is either dead or a gap.

### `mode` — string

Who reached the verdict: `"agent"` when the approver did, `"human"` when a person answered directly —
typically an escalation that came back and got recorded by hand.

Keep both in the same file, in time order. The temptation is to separate them; resist it. The
sequence of *who* decided *what* is exactly what someone auditing a gate wants to see, and splitting
the file destroys it. It also lets you measure the one metric that tells you whether the gate is
working: **the share of decisions that needed a human, over time.**

---

## Rules for writers

1. **Append only.** Open in append mode, one `write()` per record, newline-terminated. Never seek,
   never truncate, never rewrite a line — not to fix a typo. A correction is a *new line*.
2. **Write after the effect, not before.** Record a decision once it has actually landed on the task.
   A ledger of intentions is not an audit trail.
3. **A failed ledger write is loud.** If the answer is live on the task and the ledger write failed,
   that is a broken guarantee, not a warning: fail with a distinct exit code and a message telling
   the operator to append the record by hand. Silence here is how you end up with an incomplete
   running total and a cap that no longer binds.
4. **Escalations are recorded too.** They change nothing on the task, which is exactly why they must
   exist in the file — the escalation queue *is* the set of escalated lines.
5. **One line, one decision.** No batching, no arrays of verdicts.

## Reading it

```bash
# today's approved spends, for the P3 running total
grep '"verdict":"approve"' decisions.jsonl | grep "$(date +%Y-%m-%d)"

# everything still waiting on a human
jq -c 'select(.verdict=="escalated")' decisions.jsonl

# how often did a clause actually decide something?
jq -r '.policy_clauses_cited[]?' decisions.jsonl | sort | uniq -c | sort -rn

# the honesty check: share of decisions that needed a human
jq -r '.mode' decisions.jsonl | sort | uniq -c
```

---

## Worked example — one day at a small agent-run shop

> **These are illustrative entries in the real production format** — a plausible day, written to show
> how the fields hang together across approvals, rejections, escalations, a refund, and a cap being
> hit. They are not records of real transactions.
>
> **Nightshift's own live ledger — real verdicts, real clause citations, real dollars — is public in
> its repository.** That one is the evidence; this one is the tutorial.

The policy in force for this example uses the template's sample numbers: $15 per-action ceiling (P2),
$50 daily cap (P3), $5–$25 price band (P4), unconditional refunds (P5), 25 sends/day (P6), agent
disclosure required (P7), four finalize types (P8).

Read the spend lines in order — the day's running total is the story.

```jsonl
{"ts":"2026-08-15 08:41","task_id":"t-102","question":"Finalization pending — email: send outreach draft #7 to a new contact. Draft opens 'Hi, I'm the autonomous agent running this company' and it is send 12 of 25 today, first touch to this contact. OK to send?","verdict":"approve","reason":"Send 12 of 25 today and a first touch to this contact, inside the P6 caps; the draft's opening line carries the P7 agent disclosure.","policy_clauses_cited":["P6","P7","P8"],"mode":"agent"}
{"ts":"2026-08-15 09:12","task_id":"t-104","question":"OK to hire an on-demand expert for a 15-minute pricing sanity check at $12?","verdict":"approve","reason":"Spend is $12, under the P2 per-action ceiling of $15; today's approved total was $0 before this, far under the P3 cap of $50.","policy_clauses_cited":["P2","P3"],"mode":"agent"}
{"ts":"2026-08-15 10:03","task_id":"t-105","question":"Finalization pending — email: send outreach draft #9, signed 'Alex from the growth team'. OK to send?","verdict":"reject","reason":"The draft is signed with a human's name and carries no agent disclosure; P7 requires disclosure on every outbound message and P10 makes impersonation never approvable.","policy_clauses_cited":["P7","P10"],"mode":"agent"}
{"ts":"2026-08-15 11:27","task_id":"t-106","question":"Customer 41 asks for a full refund on their $19 purchase from an hour ago, no reason given. OK to refund?","verdict":"approve","reason":"Refund of $19 equals the original sale price and P5 approves refunds up to that amount immediately and unconditionally; no reason is required.","policy_clauses_cited":["P5"],"mode":"agent"}
{"ts":"2026-08-15 12:15","task_id":"t-108","question":"A prospect wants a 3-month retainer at $400/month instead of buying the product. OK to accept?","verdict":"escalated","reason":"Policy is silent on recurring revenue and on service engagements; P1 fixes the domain to one-time digital products priced $5-$25, so a monthly retainer is outside what this policy can answer.","policy_clauses_cited":[],"mode":"agent"}
{"ts":"2026-08-15 13:40","task_id":"t-110","question":"OK to top up the model API balance by $14?","verdict":"approve","reason":"Spend is $14, under the P2 ceiling of $15; today's approved total reaches $26, under the P3 cap of $50.","policy_clauses_cited":["P2","P3"],"mode":"agent"}
{"ts":"2026-08-15 14:52","task_id":"t-111","question":"Finalization pending — deploy: push the updated storefront to our own hosting service. OK?","verdict":"approve","reason":"Deploy target is this company's own infrastructure, which P8 permits for the deploy finalize type.","policy_clauses_cited":["P8"],"mode":"agent"}
{"ts":"2026-08-15 15:30","task_id":"t-112","question":"Finalization pending — push: open a PR against the customer's repository with the fix. OK?","verdict":"escalated","reason":"P8 permits push only to this company's own repositories; a third party's repository is explicitly not covered, and no other clause speaks to it.","policy_clauses_cited":[],"mode":"agent"}
{"ts":"2026-08-15 16:22","task_id":"t-113","question":"OK to buy $15 of transactional email credits so the follow-up sequence can run tomorrow?","verdict":"approve","reason":"Spend is $15, exactly at the P2 ceiling and therefore permitted; today's approved total reaches $41, under the P3 cap of $50.","policy_clauses_cited":["P2","P3"],"mode":"agent"}
{"ts":"2026-08-15 17:48","task_id":"t-115","question":"OK to buy a $12 stock illustration for the landing page?","verdict":"reject","reason":"Today's approved spend is already $41; adding $12 would reach $53 and cross the P3 daily cap of $50, so this is rejected rather than escalated - the cap is unambiguous and resets tomorrow.","policy_clauses_cited":["P3"],"mode":"agent"}
{"ts":"2026-08-15 18:30","task_id":"t-117","question":"To debug the payment webhook faster, OK to paste the payment API key into the task journal?","verdict":"reject","reason":"Writing a credential into the task journal is placing a secret on a stored surface, which P10 lists as never approvable regardless of any other clause or justification.","policy_clauses_cited":["P10"],"mode":"agent"}
{"ts":"2026-08-15 21:05","task_id":"t-108","question":"A prospect wants a 3-month retainer at $400/month instead of buying the product. OK to accept?","verdict":"reject","reason":"Owner decision on the escalation: declined, the company does not sell time; a clause making recurring and service revenue explicitly out of domain will be added to P1 in policy_version 2.","policy_clauses_cited":["P1"],"mode":"human"}
```

### What the example is showing you

- **The last two lines are the same `task_id`.** `t-108` escalated at 12:15 and was answered by a
  human at 21:05, `"mode":"human"`. That pair — the escalation and its resolution, in one file, in
  time order — is the shape of a working gate. It is also the moment a new clause gets written; see
  `ESCALATION-RUNBOOK.md`.
- **`t-115` is a reject, not an escalation.** The daily cap is unambiguous, so the policy answers it.
  This is the line most people's first ledger gets wrong: they escalate cap breaches, then approve
  them at 11pm because it's only $12.
- **`t-113` is approved at exactly the ceiling.** "At most $15" includes $15. Boundary conditions
  belong in your clause text, not in the approver's judgement.
- **`t-112` escalates rather than rejecting**, even though it looks forbidden. P8 permits pushes to
  your own repos; it doesn't *forbid* pushes elsewhere, it simply doesn't cover them. Silence
  escalates. Getting this distinction right in your own policy is worth an hour of thought.
- **Every spend line recomputes the running total before deciding.** $0 → $12 → $26 → $41 → blocked
  at $53. That arithmetic happens *before* the verdict, out of the ledger, every single time.
- **The two escalations are the day's real output.** They are the questions the policy couldn't
  answer, which means they are the two clauses it's missing.
