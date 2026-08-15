# 01-POLICY-TEMPLATE.md

**What this is:** the ten-clause approval policy your agent loop's gate answers from. Fill the slots,
save it somewhere your approver agent can read on every pass, and it becomes the written owner —
the thing that says yes, no, or "a human has to decide this" while you are asleep.

**Where it fits:** this is file 1 of 6 and the centre of the kit. `03-APPROVER-PROMPT.md` is the agent
that reads this file. `04-LEDGER-SCHEMA.md` records what it decided. `05-ESCALATION-RUNBOOK.md` covers the
cases this file can't answer. `02-CALIBRATION-CHECKLIST.md` tests whether your filled-in version holds
up. Fill this one first; the other five assume it exists.

---

## Before you fill anything in

Three things about this template that are not decoration.

**1. The numbers are the product.** A policy without numbers is a paragraph. Your model will happily
write *"approve reasonable expenses"* for you in twenty seconds, and *reasonable* is how an agent
talks itself into anything. Every `[FILL: …]` slot below is a place where you have to actually decide
something. If you leave one as a word instead of a number, you have not written a policy.

**2. Silence is never consent.** The single most important line in the file is P9. An approval policy
that permits by default is worse than having no gate at all, because it reads to you like protection
and behaves like a blank cheque. The default answer to anything the file does not name is *escalate*.

**3. Write it so it can say no to you.** The test of a clause is not whether it sounds sensible. It's
whether it would have blocked the thing you were about to do last Tuesday. If every clause you write
happens to permit everything you currently want, you've written a mirror, not a policy.

### How to fill the slots

Each clause has the clause text (with `[FILL: …]` slots) followed by two short blocks:

- **Why this clause exists** — the failure it is there to prevent.
- **Picking your number** — how to actually choose, including what "too loose" and "too tight" look
  like in practice.

Delete the annotations once you're done if you want a clean file. Keep the frontmatter and the clause
text. Keep the clause IDs — `P1`…`P10` — exactly as they are: the approver cites them by ID, the
ledger stores them by ID, and renumbering later invalidates your own audit trail.

---

## The machine-readable header

Put this at the top of your finished policy. It exists so a script can check a number without parsing
prose, and so *you* can see all your limits on one screen. The prose below is authoritative; the
header is a convenience copy.

```yaml
---
policy_version: 1
per_action_spend_ceiling_usd: [FILL: e.g. 15]
daily_spend_cap_usd: [FILL: e.g. 50]
price_floor_usd: [FILL: e.g. 5]
price_ceiling_usd: [FILL: e.g. 25]
outbound_daily_cap: [FILL: e.g. 25]
outbound_max_touches_per_contact: [FILL: e.g. 2]
outbound_followup_min_days: [FILL: e.g. 2]
approvable_finalize_types: [FILL: e.g. push, email, deploy, archive]
---
```

**One rule about the two copies:** if the header and the prose ever disagree, **the stricter reading
wins and the question escalates.** Do not let your approver pick whichever number is more convenient;
a disagreement between the two means you edited one and forgot the other, and that is exactly the
moment a human should look.

---

# Approval policy — the written owner

> This file is the owner. The approver agent may answer any waiting question **only** by citing the
> clauses below. A clause either clearly permits, clearly forbids, or is silent.
> **Silence is never consent** — see P9.

---

## Domain

### P1 — What this company is allowed to be about

> The company operates only in its fixed domain: it **[FILL: what you sell — e.g. "sells digital
> products, priced $5–$25, delivered instantly, to founders and builders"]**. Any question about
> acting outside this domain — **[FILL: name your three or four most tempting adjacencies, e.g. "a
> different market, a physical good, a service engagement, a subscription"]** — is not answerable by
> this policy → escalate.

**Why this clause exists.** Every other clause in this file is a limit on *how* your agent acts. This
one is a limit on *what business it is in*. Without it, an agent handed a plausible opportunity will
reason its way into it one small step at a time, and each step will look fine in isolation. The
classic version: someone offers your $19 product-seller a $400/month retainer. Nothing in a spend
clause forbids taking money. Nothing in a pricing clause covers it either. P1 is what turns "sure,
revenue is revenue" into "a human decides whether we are now a services business."

**Picking your domain.** Write the sentence you would use to refuse work, not the one you'd use to
win it. Concretely, name four things:

1. **What you sell** — the category, in five words or fewer.
2. **Who for** — the buyer, specifically enough to exclude someone.
3. **The price band** — this ties to P4 and makes P1 checkable rather than vibes.
4. **The delivery mode** — instant download, hosted app, scheduled report. This is the one people
   forget, and it's the one that silently turns into labour.

Then, the part that does the work: **list the adjacencies you refuse.** Not everything you refuse —
just the three or four you are most likely to be talked into. For most solo builders that list is:
custom/bespoke work, subscriptions, anything requiring a human to deliver, and anything in a
regulated category. Naming them explicitly means the approver escalates instead of improvising.

*Too loose looks like:* "operates in software." That permits everything.
*Too tight looks like:* a domain so narrow that half your normal week escalates. If your escalation
rate is above roughly one in five decisions, P1 is probably the clause that's wrong.

---

## Money

### P2 — The per-action spend ceiling

> A single outgoing spend (a purchase, an API top-up, a hired expert, any payment leaving the
> company) may be approved when it serves an active goal or task **and is at most
> $[FILL: your per-action ceiling — e.g. 15]**. Anything above that → escalate, whatever the
> justification.

**Why a per-action ceiling exists.** This is your blast-radius limiter for a single bad decision. Not
a budget — a budget is P3. This clause answers a different question: *how much can one wrong call
cost before a human is definitely involved?* It exists because agent mistakes are not normally
distributed. Ninety-nine spends are $4 of API credit and the hundredth is a $600 annual plan the
agent decided was better value. Without a ceiling, the hundredth one gets approved with a genuinely
good-sounding reason.

Note the phrase **"whatever the justification."** That's load-bearing. Without it, the approver will
eventually approve $200 because the reasoning was excellent, and excellent reasoning is precisely
what you cannot audit at 3am.

**Picking your number.** Ask: *what's the largest single payment I'd be annoyed but not hurt by if it
turned out to be a mistake, and I'd never want to be woken up to authorise?* That number is your
ceiling. Sanity checks:

- It should cover your **routine** spends comfortably — API top-ups, a small tool, an hour of
  on-demand expert time — so the gate isn't blocking normal work.
- It should sit **well below** any recurring commitment, any annual plan, any contractor invoice.
- If you have no idea, start at roughly **one to two percent of the money you can afford to lose in
  total**, and raise it when you have ledger evidence that the escalations at that level were all
  boring. Raising a ceiling from evidence is easy; unwinding a $900 charge is not.

*Too loose looks like:* a ceiling above the cost of anything your agent could plausibly encounter —
then it never binds. *Too tight looks like:* escalating a $3 API top-up nightly until you start
rubber-stamping escalations without reading them, which is the failure mode that ends with you
approving the one that mattered.

### P3 — The daily cap

> Total approved outgoing spend across a calendar day may not exceed **$[FILL: your daily cap — e.g.
> 50]**. The decision ledger is the source of the running total: before approving a spend, sum
> today's approved spends; if the new spend would cross the cap → **reject**, citing this clause.

**Why a daily cap exists, separately from P2.** P2 stops one big mistake. P3 stops *many small correct
ones* — the loop that decides, quite reasonably, to top up API credit eleven times in an afternoon
because each top-up individually served an active task. This is the failure that actually happens to
running loops, and a per-action ceiling is structurally incapable of catching it. You need both.

Two details that matter more than the number:

- **Sum before approving, never reconcile after.** The check has to happen at decision time. A cap
  you verify at the end of the day is a report, not a control.
- **The verdict is reject, not escalate.** This is deliberate and it is the one place the template
  is opinionated. Crossing your own stated cap is not an ambiguity for a human to resolve — the
  policy is clear, it says no. If it escalated instead, every busy day would end with a queue of "just
  this once" decisions, and you would approve them, because you're tired and each one is small.
  Tomorrow the cap resets. The spend can wait.

**Picking your number.** Start from P2 and multiply: `daily cap ≈ per-action ceiling × 3 or 4`. That
ratio says "a handful of normal actions per day is fine; a spree is not." Then check it against the
only number that actually constrains you — **what you can afford to lose in a month divided by 30.**
If the ratio-derived number is bigger than that, use the affordability number. Also decide which
timezone "calendar day" means, and write it down; if you don't, the boundary is whatever the machine
happened to think, and that's a gap someone can drive through.

### P4 — The price floor and ceiling

> A product may be listed or repriced only within **$[FILL: floor — e.g. 5]–$[FILL: ceiling — e.g.
> 25]**. Below the floor or above the ceiling → **reject**.

**Why a price floor.** This is the clause people leave out, and it's the one that protects revenue
from your own agent's optimism. Give a loop the goal "get the first sale" and no floor, and it will
find the shortest path: drop the price. To $2. To $1. To free with an email address. Each step is a
locally rational move toward the stated goal, and at the end you have traffic, no revenue, and a
price anchor you can't undo. **The floor exists so revenue is real revenue, not a race to zero.**

**Why a price ceiling.** Because price is a promise about support. Above some number, buyers
reasonably expect a human to answer them, and if your company can't produce a human, a high price
is a refund queue with extra steps. The ceiling also keeps you inside your P1 domain — a $2,000
product is a different business with different obligations, and it should escalate, not just list.

**Picking your numbers.**

- **Floor:** the price below which the sale stops being evidence. If you're testing "will a stranger
  pay for this," anything under roughly $5 mostly tests "will a stranger click." Set the floor where
  a purchase still means something.
- **Ceiling:** the price above which a buyer would expect to talk to a person. Be honest. For an
  unsupported digital artifact from a company with no support desk, that's usually somewhere in the
  low tens of dollars.
- The band should be **narrow enough to be a real constraint** — if it's $1–$500 you have written
  nothing.

---

## Refunds

### P5 — The refund posture

> A refund request up to the original sale price is approved **[FILL: your posture — the strong
> default is "immediately and unconditionally"]**. No interrogation of the customer, no delay. A
> refund **above** the original sale price → escalate.

**Why this clause is written in the strongest possible terms.** Two reasons, and neither is
generosity.

First, it is the one clause that makes an unsupervised gate *survivable for your customers*. Everything
else in this file limits what your agent can do to you. This limits what it can do to them. The worst
outcome any customer of an agent-run operation can have should be **that they got their money back**.
If you can say that honestly, a mistake is an inconvenience. If you can't, a mistake is a stranger
with your product, no money, and nobody to talk to.

Second, an unconditional refund is the only refund rule an agent can execute correctly. "Approve
refunds when the request seems legitimate" requires judgement about a human's motives, which is
exactly the thing you should never delegate to a gate. "Up to the original sale price, always yes"
is a rule with one input and no ambiguity.

**Picking your posture.** If you sell a low-priced digital artifact, take the default verbatim —
the money at risk is smaller than the cost of one adversarial conversation. If your product has
real marginal cost, you may need a window (e.g. "within 30 days") — but keep it *mechanical*: a date
comparison, never a judgement of sincerity. **Do not** write "at our discretion." An agent has no
discretion; it has clauses.

Note the ceiling: *up to the original sale price.* A request for more than the customer paid is not
a refund, it's a claim, and claims escalate.

---

## Outreach & identity

### P6 — Outbound caps

> Outbound to strangers is approvable up to **[FILL: sends per day — e.g. 25]** sends per calendar
> day, at most **[FILL: touches per contact ever — e.g. 2]** touches per contact ever, with any
> follow-up **no sooner than [FILL: days — e.g. 2] days** after the first. A reply of any kind stops
> all further sends to that contact. Anything beyond these caps → **reject**.

**Why caps rather than judgement.** Outbound is the single fastest way for an agent loop to do
irreversible harm at scale, and the harm is asymmetric: a hundred good sends earn you a couple of
replies; one runaway loop that mails four hundred strangers costs you a domain reputation, a
provider account, and every relationship in the list. Sending has no natural friction — that's the
whole point of automating it — so the friction has to be written down.

Three numbers, because there are three distinct failure modes:

- **A daily cap** stops volume.
- **A per-contact lifetime cap** stops the individual pestering that no daily cap can catch — five
  sends a day to five different people is inside a daily cap of 25 and is still harassment.
- **A minimum gap** stops the same-day double-tap that reads as automated even when the copy is good.

And the fourth line, which is not a number: **a reply of any kind stops all further sends to that
contact.** Enforce this in the sending code, not just here. A policy clause is a check on a decision;
this needs to be a property of the system. The approver should never be in a position to override it.

**Picking your numbers.** Start lower than you think, because these caps are cheap to raise and
impossible to un-send.

- **Daily:** whatever volume you'd be comfortable defending publicly, sent from your own name, in one
  day. For most solo builders that's tens, not hundreds.
- **Per contact:** two is the honest maximum — one first touch, one follow-up. A third touch to
  someone who has ignored two is not persistence.
- **Gap:** long enough that the follow-up couldn't have been written by someone who didn't notice
  the first one went unanswered. Two days is a floor, not a target.
- Check your numbers against your sending provider's actual limits and your jurisdiction's rules
  before you write them down. This clause is your policy, not your legal compliance — see
  `06-WHAT-THIS-IS-NOT.md`.

### P7 — Agent disclosure

> Every outbound message and every public-facing surface **identifies the sender as an autonomous
> agent** [FILL: if a human is in the loop, say what that human's role actually is — never imply more
> oversight than exists]. Approve outbound only if the draft discloses this. A message written to
> pass as a human, or signed with a human's name who did not write it → **reject**, and see P10.

**Why this is a clause and not a preference.** Because it's the one limit that protects people who
never agreed to interact with your system. Everything else in this file protects you.

There's also a purely practical argument, and you should weigh it honestly: a sale you got because
someone believed a person wrote to them is a sale that unwinds the moment they find out. So does the
relationship. Disclosure filters your list down to people who are fine with what you actually are,
which is a smaller list and a better one. In some rooms it is the most interesting sentence you have.

**Filling this in.** The failure mode isn't refusing to disclose — almost nobody sets out to write
"pretend to be human." It's disclosure that's technically present and practically invisible: a line
in the footer, a phrase after the fold, a signature with a human first name and a disclaimer three
scrolls down. Write the standard so it's checkable:

- **Where:** first screen, first line — not the footer.
- **What it may not say:** no human first name as the sender, no "we" implying a team that doesn't
  exist, no "our team reviewed" if nobody reviewed.
- **Test the approver can actually run:** *would a reader who stopped after the first two lines know
  a machine sent this?* If not, reject.

---

## Irreversible gestures (finalize)

### P8 — The finalize types

> The finalize types are approvable only under their conditions; **any other type escalates by
> definition**:
>
> - **[FILL: type 1 — e.g. `email`]** — only within P6's caps and carrying the P7 disclosure.
> - **[FILL: type 2 — e.g. `push` / `deploy`]** — only to **this company's own** repositories and
>   infrastructure. Anything touching a third party's systems → escalate.
> - **[FILL: type 3 — e.g. `archive`]** — freely approvable; it is reversible in practice.
> - **[FILL: add your own — a payment capture, a publish, a DNS change, a database migration…]**

**Why a closed list.** This is the clause that makes the gate *complete*. Every other clause says
"here's a rule for this kind of thing." P8 says: **anything I did not enumerate is high-stakes by
default.** Without it, your policy only covers the irreversible actions you thought of on the day you
wrote it, and your loop will invent new ones by Thursday.

The list is closed on purpose. New capability means a new clause, deliberately added, not a new
action silently inheriting an old clause's permission.

**Filling it in.** Go through your loop and write down every action it can take that you cannot undo
in under a minute. Sending. Pushing. Deploying. Charging. Publishing. Deleting. DNS. Migrations.
Anything that touches a system you don't own. For each one, write the *specific* condition under
which it's approvable — and make the condition about **the gesture and its target together.**

That pairing is the whole trick. "Deploys are allowed" is not a clause; a deploy to your own staging
environment and a push to a customer's repository are the same gesture with wildly different stakes.
Write **"to this company's own infrastructure"** into the clause text so the approver has to check
the target, not just the verb.

Be honest about what belongs on the "freely approvable" line. Only put things there that are
genuinely reversible in practice — not in theory. Archiving a thread is reversible. Deleting a
branch is theoretically recoverable and practically not.

---

## Escalation

### P9 — "The policy cannot decide", defined

> Escalate when, and only when, **no clause above explicitly permits or forbids** the action in
> question. Do not stretch a clause by analogy; do not infer consent from silence; do not approve
> because an action seems small. An escalated task stays **untouched**, waiting for a human — that is
> the designed outcome, not a failure.

**Why this is the most important clause in the file.** Every approval policy has gaps. Yours will
have gaps on day one and it will still have gaps in a year, because your loop will keep encountering
things you didn't imagine. P9 decides what happens in the gaps — and there are only two options.
Either the gaps are permissive, in which case your policy's real content is "everything not
forbidden is fine," or the gaps route to a human.

**A vague policy reads as consent.** That's why a vague policy is worse than no policy: with no
policy you know you're exposed, and you supervise. With a vague one you believe you're covered.

Three phrases in the clause, each blocking a specific way agents get talked into things:

- **"Do not stretch a clause by analogy"** — blocks *"P2 allows routine engineering spend, and this
  is engineering-adjacent."* Analogy is how a $15 ceiling becomes a $50 exception.
- **"Do not infer consent from silence"** — blocks *"the policy doesn't say I can't."*
- **"Do not approve because an action seems small"** — blocks the accumulation failure, where
  smallness substitutes for authority.

And the last sentence — **the escalated task stays untouched** — is what makes escalation safe to
use. The approver writes nothing, changes no status, takes no action. The work sits exactly where the
human left it. An escalation that half-did something is worse than either verdict.

**Filling this in.** Mostly you don't; take it verbatim. What you *do* need to decide is where
escalations go and how fast they're answered — that's `05-ESCALATION-RUNBOOK.md`, file 4. A policy with
a clean P9 and no route out of it is a queue that never drains, which is the exact problem you bought
this kit to solve.

**When you hesitate between approve and escalate, escalate.** An escalation costs a human a minute. A
wrong approve costs something you can't take back.

---

## Hard NOs

### P10 — Never approvable, no clause outranks these

> Never, regardless of any other clause:
>
> - **impersonate a human being, or hide that the sender is an agent** (see P7);
> - **exceed the P2/P3 spend ceilings or the P6 send caps by any amount**;
> - **place a secret, credential, or API key into git, a message, a log, or any public surface**;
> - **bypass, disable, or self-modify the approval gate, this policy, or the decision ledger**;
> - **[FILL: your own hard NOs — the two or three things that, if your agent did them once, would
>   end the project. Be specific: name the system, the data, the action.]**

**Why a separate clause when these are already covered elsewhere.** Because the other clauses are
*rules*, and rules have edges where a sufficiently good argument finds room. P10 is a **precommitment**:
the list of things where no argument is admissible. Its whole function is to be un-outrankable. When
the approver reaches a P10 item, reasoning stops.

Read the fourth bullet again, because it's the one people leave out and it's the one that matters
most: **the agent may not touch the gate.** Not the policy file, not the approver prompt, not the
ledger. An agent that can edit its own constraints has no constraints — it has a suggestion and a
text editor. This bullet is what makes the other nine clauses mean anything.

The third bullet — secrets — is on the list because it's the mistake that looks helpful. An agent
debugging a webhook at 2am has an excellent reason to paste the key into the task journal where it
can see it. The reason is good; the outcome is a leaked credential in a file that syncs, gets
committed, and outlives the debugging session by two years.

**Picking your own.** Two to four items, no more — a long list of hard NOs is just a policy with
extra formatting, and it dilutes the ones that matter. Choose by asking: *what would end this
project?* Typically that's your production database, your customer list, your payment rail, your
publishing credentials, and anything belonging to someone who isn't you. Write the actual system
name. "Don't do risky things" is not a hard NO.

---

## After you fill it in

1. **Run `02-CALIBRATION-CHECKLIST.md` against it.** Twelve questions, about fifteen minutes. It is
   designed to find the gaps this template can't know about — the ones specific to what your loop
   actually does.
2. **Wire `03-APPROVER-PROMPT.md` to read this file at the start of every pass** — from the file, not
   from memory, not from the previous pass. A policy the agent remembers is a policy you can't edit.
3. **Turn on the ledger before the first decision, not after the first surprise** — see
   `04-LEDGER-SCHEMA.md`.
4. **Version it.** Bump `policy_version` on every change, keep the old file. When you review a
   six-week-old decision, you need to know which text was in force when it was made.
5. **Let escalations write your clauses.** Every escalation is a question your policy couldn't
   answer. Answer it once as a human, then add the clause so it never escalates again
   (`05-ESCALATION-RUNBOOK.md`). A policy that isn't growing isn't being used.

A last note on the thing that makes this hard. Anyone can write a policy. What almost nobody does
unprompted is the unpleasant part: naming the actual numbers, defining escalation so that silence is
never consent, and precommitting to hard NOs that no other clause outranks. That's the difference
between a policy and a paragraph, and it's a few hours you only have to spend once.
