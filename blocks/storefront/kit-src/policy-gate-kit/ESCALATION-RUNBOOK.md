# ESCALATION-RUNBOOK.md

**What this is:** what to do when the policy can't decide. The escalate verdict, why an escalated task
must be left completely untouched, how to get a human answer fast (including buying one), and how
every escalation turns into a clause so the same question never escalates twice.

**Where it fits:** this is file 4 of 6. It picks up where P9 of `POLICY-TEMPLATE.md` leaves off and
where the `escalated` lines in `LEDGER-SCHEMA.md` accumulate. If you only wire up files 1–3, you have
a gate that stops correctly and a queue that never drains. This file is the drain.

---

## Escalation is the feature, not the failure

The instinct on seeing an escalation is that the gate underperformed — it had a question and didn't
answer it. That instinct will, over a few weeks, quietly destroy your policy: you'll widen clauses to
reduce escalations, and the widened clauses will approve the thing you built the gate to stop.

An escalation is the gate **working as designed**. It means the loop reached something your written
rules genuinely do not cover, and rather than improvising, it stopped and asked. That is the entire
value proposition. A gate that never escalates is either running a trivial loop or approving things
it shouldn't.

The number to watch isn't escalations. It's **escalations that never got answered.** That's the one
that means you rebuilt the approval queue you were trying to replace.

---

## When the approver escalates

Exactly one condition, from P9: **no clause explicitly permits or forbids the action.**

Three cases, all the same verdict:

| Case | Example |
|---|---|
| **Silence** — the policy simply doesn't speak to it | A prospect offers a monthly retainer; the policy only covers one-time sales |
| **Conflict** — two clauses point opposite ways | A spend is under the per-action ceiling but the domain clause makes the purpose out of scope |
| **Out of domain** — the question is about being a different business | "Should we take on a support contract?" |

And a fourth that isn't in the clause text but should be in your head: **hesitation.** When the
approver is choosing between approve and escalate, it escalates. An escalation costs a human a
minute. A wrong approve costs something you can't take back.

### The thing it must not do: half-act

An escalation writes **nothing**. Not the answer field, not the status, not a note on the task, and
absolutely not a partial version of the action ("I drafted it but didn't send"). The task stays byte
for byte where the loop left it.

This matters more than it sounds. A half-acted escalation is the worst state in the system: the human
arrives at a task that has already moved, can't tell what was done, and has to reconstruct state
before deciding. Meanwhile the loop may treat the partial write as progress. Leave it alone.

The only thing an escalation produces is **a line in the ledger** — verdict `escalated`, empty
citation list, and a reason that says what the policy did not cover. That line is the work item.

---

## Routing: getting a human answer

Three routes. Pick one as your default before you turn the gate on, not the first time something
escalates at 2am.

### Route 1 — You, batched

The default for a solo builder, and it's fine, as long as it's **batched and scheduled** rather than
interrupt-driven. Once or twice a day, run the escalation query, answer everything in the list, record
each answer in the ledger with `"mode":"human"`.

```bash
jq -c 'select(.verdict=="escalated")' decisions.jsonl | tail -20
```

The trap is that this route silently becomes the approval queue you were trying to eliminate. Two
rules keep it honest:

- **A service level, written down.** "Escalations answered within 12 hours." If you can't hold it,
  your policy is too narrow — fix the policy, don't lower the bar.
- **Every answer becomes a clause** (see below). If you're answering the same shape of question a
  third time, you skipped that step and you're now doing manual labour on a solved problem.

### Route 2 — A named human who isn't you

A cofounder, a contractor, whoever owns that domain. Worth it for classes of escalation that
genuinely need someone else's authority — spend above your comfort, anything legal-adjacent, anything
touching a customer relationship.

Two things to get right: **route by class, not by volume** (write in your policy which kinds of
question go to whom), and **give them the ledger line, not the task** — question, what the policy
didn't cover, what you'd do. They should be able to answer in a sentence.

### Route 3 — Buy the judgement

The one people don't consider: for a specific, bounded question, you can **hire an expert on demand**
and pay for the answer. On-demand expert marketplaces will get you a real person with the relevant
background within minutes to hours, for a small bounded fee. Pricing sanity checks, "is this copy
misleading", "does this contract shape look normal", "is this refund wording going to bite me" — all
answerable in fifteen minutes by someone who has seen a hundred of them.

This is the route that makes an unsupervised loop actually work overnight, and it has three
non-obvious properties:

- **It is a spend, so it goes through the gate.** A $12 fifteen-minute consult sits under a typical
  per-action ceiling and gets approved by the same policy, citing the same clauses, as any other
  purchase. A $200 legal review does not — it escalates, and now you have an escalation about how to
  resolve an escalation, which is the correct outcome and worth noticing.
- **Bound the question before you buy.** "Is $19 a defensible price for X, given Y?" gets a useful
  answer. "What should we do?" gets a conversation you're paying for by the hour.
- **It is the escalation path, never the cost of goods.** If bought judgement ends up inside every
  unit you deliver, you haven't built an automated company, you've built an agency with a scheduler —
  and at expert hourly rates the unit economics stop working immediately. Escalations are exceptions.
  If they're routine, that's a clause you haven't written.

### What you tell the customer while it's pending

If an escalation is holding up someone outside your company, say so plainly and without inventing a
reason. "This needs a human decision and one is being asked; you'll hear back by X." Do not let the
loop improvise a holding message that implies the decision has been made, and do not let it imply a
person is already looking at it if nobody is.

---

## Closing the loop: every escalation becomes a clause

This is the part that compounds, and the part almost everyone skips.

An escalation is a **question your policy couldn't answer.** Answering it once as a human resolves
the task. Writing the clause resolves the *class*. Do only the first and your escalation queue grows
with your loop's capability, forever.

### The five-minute procedure

**1. Answer the actual task first.** Unblock the work, record it in the ledger with `"mode":"human"`,
naming the clause you'd have cited if it had existed. Then do the rest.

**2. Ask what class this was.** Not "should we accept this retainer" but "what does this company do
about recurring revenue?" The clause has to answer the next instance too, and the next instance will
have different numbers.

**3. Write the clause with a number in it.** The failure mode is a clause as vague as the silence it
replaced. *"Evaluate retainers case by case"* escalates every time and you've gained nothing. Either
a rule with a threshold, or an explicit refusal:

> *P1 (amended) — …recurring revenue of any kind, and any engagement that bills for time rather than
> delivering a finished artifact, is outside the domain: reject, do not escalate.*

Note that this one **rejects** rather than escalating. That's the strongest kind of new clause: you've
converted a recurring interruption into a permanent, instant no. Not every answer can be one, but
check whether yours can before you write something softer.

**4. Decide where it goes.** Amend an existing clause when it's the same subject; add a new numbered
clause when it's genuinely new. **Never renumber existing clauses** — your ledger cites them by ID and
renumbering silently invalidates every past decision. New clauses get new numbers, `P11`, `P12`, and
the list grows. Bump `policy_version` and keep the old file.

**5. Test it against the ledger you already have.** Re-read the last few escalations of that shape
and ask whether the new clause would have answered them cleanly. Then check it does not accidentally
permit something you'd have rejected — new clauses are where over-permission enters a policy, because
you write them while annoyed about an interruption.

**6. Only after all of that: relax the constraint if you want to.** If the review shows a whole class
of escalations was boringly fine, that's evidence to widen a ceiling. Widening from ledger evidence
is a good decision. Widening because the queue is long is how policies die.

### What good looks like after a month

Your escalation rate falls, then plateaus at a low number of genuinely novel questions. Your policy is
a couple of clauses longer than it started and every added clause traces back to a real event in the
ledger. You can point at any decision from the past six weeks and name the clause, the number, and
the person or agent who decided it.

That's the whole game. The gate doesn't stay in place because it was well designed on day one — it
stays in place because every time it stopped you, you wrote down the answer.

---

## Anti-patterns, in the order people hit them

1. **Approving the escalation instead of writing the clause.** Works once. Never scales. Six weeks
   later you're the approval queue again.
2. **Widening a clause to make an escalation go away.** You didn't answer the question, you deleted
   it — along with the protection that surfaced it.
3. **Letting the approver amend the policy itself.** The single fastest way to end up with no gate.
   An agent that can edit its own constraints doesn't have constraints (P10).
4. **An escalation queue with no owner and no SLA.** Escalations that nobody answers are just tasks
   that never happen, and eventually you'll disable the gate rather than drain the queue.
5. **Bought judgement as the default answer.** Cheap for exceptions, ruinous as a habit — see Route 3.
6. **Escalating something the policy actually forbids.** If a clause says no, the verdict is reject.
   Sending a clear "no" upstairs for a second opinion is how caps get exceeded at 11pm.
