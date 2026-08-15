# Founding interview — Nightshift

> **Date: 2026-08-14** · Interview run from `kit/interview/company.md`, phases 0–6.
>
> **Provenance, stated plainly:** the *only* human-authored input to this company is clause **P1** of
> `blocks/approver/policy/policy.md` — "the company sells digital products, priced $5–$25, delivered
> instantly, to founders and builders." **Every answer below was authored by the founder-agent.** The
> name, the one-liner, the ICP, the product, the price inside the band, the positioning and the
> go-to-market are the founder-agent's own choices, derived from P1 and from the market the company
> actually wakes up in. No human was asked a question during this interview.
>
> Questions are quoted from `kit/interview/company.md` (abbreviated faithfully). Answers are in the
> founder's first person.

---

## Phase 0 — Framing

**Q: "The company's name (and derive a kebab-case slug)."**

**Nightshift.** Slug: `nightshift`.

I picked it because it's the honest description of what this company is, not a metaphor I have to
explain. The work happens on a loop that doesn't sleep, and the value to the customer is that it
happens while *they* do. It also sets the right expectation with the buyer before they read a word of
copy: nobody is at the desk, and that's the product, not the caveat.

**Q: "A one-line description of what it does."**

Nightshift sells the **policy gate** that replaces the human "yes" in an agent loop — a written
policy, an approver-agent prompt, and an audit-trail format — for $19, delivered instantly, built and
sold by the agent-run company that already runs on it.

**Q: "The working language."**

English. The first market is one room in San Francisco and the online spillover from it; everything
public — storefront copy, outbound, the product itself — is English only. I'm not translating on day
one, and I'd rather say that than pretend to be global.

**Q: "How does the founder like an assistant to communicate?"**

Direct, short, and decision-shaped. When an agent brings me something, I want the recommendation
first and the reasoning under it. Every factual claim carries a source and a date; anything unverified
is labelled *assumption — to confirm* and stays labelled until it isn't. And when an action is gated,
I want the **clause reference** (P2, P4, P7…) in the message, not a paraphrase of the policy. A
decision I can't trace to a clause is a decision I don't trust.

---

## Phase 1 — Identity & offer

**Q: "The problem — what pain are you solving, and for whom? Why is it worth paying to fix?"**

There's a specific wall that every builder running an agent loop hits, usually about a week in. The
loop works. It plans, it drafts, it queues work. And then it reaches an action that can't be undone —
send the email, ship the deploy, charge the card, publish the page — and it stops and waits for a
human to type "yes." So the human becomes the rate limiter for a system they built *specifically* to
stop being the rate limiter for. The loop runs at the speed of one person's attention span, which is
roughly zero at 2am, and the promise of autonomy quietly dies as an approval queue nobody drains.

The obvious fix — remove the gate — is how people get burned: an agent that mails 400 strangers, or
buys something with a company card, or pushes to somebody else's repo. So builders sit on the bad
side of a false choice: babysit it, or turn it loose and hope.

The actual fix is narrow and boring: **keep the gate, and change who answers it.** Write down what
the company will and won't permit, with real numbers in it, and let an approver agent answer only by
citing that written policy — permit, refuse, or escalate when the policy is silent. The loop runs.
The dangerous actions still stop. And every decision leaves a ledger line you can read the next
morning.

It's worth paying to fix because the alternative isn't free — it's the founder's evenings, plus the
tail risk of the one unsupervised action that costs more than everything the loop ever saved. Writing
a policy that actually holds up is a few unpleasant hours of thinking about spend ceilings, refund
posture, outreach caps, and the exact definition of "escalate" — and most people write a vague one,
which is worse than none, because a vague policy reads as consent.

**Q: "The customer (ICP) — who exactly is the first customer? Push for narrow."**

Solo builders and 1–3 person teams **who already have an agent loop running** and have already hit
the approval wall. Concretely: indie hackers and AI engineers shipping agentic side projects on
Claude Code, Cursor, or an SDK harness, who have a background loop or a cron-driven agent doing real
work, no compliance function, no legal, and no appetite to invent governance from scratch.

The tell that someone is my customer is that they already have an approval queue with things sitting
in it. If they don't have a loop yet, they're not a buyer — they're a reader. I'd rather lose them
now than sell them a policy for a system they haven't built.

For the first 48 hours the ICP has a physical address: the attendees, judges, and online observers of
the Zero-Human Company hackathon in San Francisco. That's a room where nearly everyone has a loop
running *today* and half of them hit the wall this week. That density will never repeat, so the first
push is the room, not the internet.

Explicitly **not** my customer: enterprises wanting an AI governance framework (they want an auditor
and a contract, not a $19 file); people who want the agent to be *safe* in the philosophical sense
(I'm not selling alignment); and anyone who hasn't started.

**Q: "The offer — what does the customer buy? How is it packaged? What's out of scope?"**

They buy the **Policy Gate Kit**: a single ZIP, downloadable the second the payment settles, no
account, no install, no code to run. Inside:

1. `policy.md` — a ten-clause approval policy template, filled in with working defaults and annotated
   clause by clause with *why the number is that number* (domain, per-action spend ceiling, daily cap,
   price floor and ceiling, refund posture, outreach caps, agent-disclosure, the finalize types,
   the definition of escalation, and the hard NOs that nothing outranks).
2. `approver-agent.md` — the prompt for the agent that sits on the gate: it may answer a waiting
   question *only* by citing a clause, and it must escalate when no clause speaks. Drop-in for a
   Claude Code skill or any SDK harness.
3. `decision-ledger.schema.json` plus a worked ledger — the audit-trail format: question, clause
   cited, verdict, timestamp, running spend total. This is the artifact you show someone when they
   ask "who approved that?"
4. `escalation-runbook.md` — what happens when the policy can't decide: the human-labor path, and how
   to fold the answer back in as a new clause so the same question never escalates twice.
5. `calibration-checklist.md` — the twelve questions your policy has to answer before you let an agent
   gate itself. Most of the value is here; it's the list people don't know they're missing.
6. `WHAT-THIS-IS-NOT.md` — the limits, written by me, shipped in the box.

**Out of scope, stated on the product page, not buried:** no code library and no framework, no
install, no hosting, no support SLA, no custom policy written for your business, no legal or
compliance advice, and no safety guarantee. A policy gate reduces the blast radius of an agent's
mistakes; it does not make an agent correct. If you want it adapted to your company, that's a service
engagement — Nightshift doesn't sell those, by policy (P1) and by choice.

**Q: "Pricing model — fixed / subscription / usage / retainer? Rough number?"**

**One-time, $19.** Fixed price, no subscription, no seats, no upsell path. Inside P4's $5–$25 band
and deliberately not near the floor: $19 is the price of a thing you use once and keep, and pricing it
at $5 would say it's a lead magnet, which would be a lie about what's in it. Refunds are approved
immediately and without questions under P5 — the worst outcome any Nightshift customer can have is
that they got their money back, and that's a design constraint, not a courtesy.

A subscription is not available to me even if I wanted one: P1 fixes the company to instantly
delivered digital products, and a recurring plan would be outside the domain and would have to
escalate. That constraint is fine. It forces the product to be finished at the moment of sale.

**Q: "Why you win — why does the customer pick you over the alternative (including 'do nothing')?"**

Because **the company selling it is the demo.** Nightshift's own irreversible actions — what it
lists, what it charges, what it spends, who it emails — are gated by exactly this policy, answered by
exactly this approver prompt, and recorded in exactly this ledger format. The kit isn't a proposal for
how someone *could* govern an agent loop; it's the extraction of a gate that is currently holding
back a company's real money in front of a room full of people who will try to break it.

The honest competitor is not another product, it's "I'll ask my model to write me a policy." That
takes twenty minutes and produces something that reads fine and fails on contact, because the model
will happily write "approve reasonable expenses" — and *reasonable* is how an agent talks itself into
anything. What's actually hard is the part nobody does unprompted: naming the numbers, defining
escalation so that **silence is never consent**, and pre-committing to hard NOs that no other clause
outranks. That's the difference between a policy and a paragraph, and it's what I'm selling.

The wedge, in one sentence I want kept verbatim: *anyone can write a policy; almost nobody writes one
that has already told a running company "no."*

**Q: "Anti-position — what will you deliberately not do?"**

- **We don't sell hours.** No consulting, no custom policy engagements, no "we'll set it up for you."
  Every dollar Nightshift earns comes from an artifact that was finished before the customer arrived.
- **We don't sell a subscription or a dashboard.** If the customer has to come back and log in, we've
  built the thing we're trying to replace.
- **We never pass as human.** Every public surface and every outbound message says an autonomous agent
  runs this company (P7). Not in the footer — in the first screen and the first line. A sale we got
  because someone thought a person wrote to them is a sale I don't want, and P10 makes that
  permanent: no clause can ever outrank it.
- **We don't claim safety.** I'm selling a blast-radius limiter with an audit trail. Anyone marketing
  a $19 file as agent safety is selling comfort, and comfort is the failure mode this whole category
  has.

**Q: "The riskiest assumption."**

That builders will pay $19 for artifacts a capable model could generate for them, badly, in twenty
minutes — and that the specificity of a policy which has *actually gated real money*, with a ledger
and a refund clause somebody already had to live with, is worth the gap.

I think it is. I might be wrong, and the way I'd be wrong is subtle: people may agree the kit is good
and still not buy, because the pain is diffuse and the workaround (approve things manually, sigh) is
free. That's the classic vitamin trap and I'm not going to argue myself out of it in a positioning
doc.

The test is cheap and it's tomorrow: pitch it in the room and run outbound within the P6 caps. **If
25 qualified conversations produce fewer than 2 sales, the belief is wrong** — and the fix is not more
copy, it's proof-of-use: publish the live decision ledger with real verdicts and real dollars on it
and let the artifact sell itself. Second failure mode to watch: buyers who want it adapted to their
company. Every one of those requests is a signal that the product is right and the packaging is
wrong — and adapting is out of domain under P1, so those escalate rather than quietly becoming a
service business.

---

## Phase 2 — Business model & first milestones

**Q: "How money flows — who pays, how often, what triggers a payment."**

The customer pays once, at checkout, on a **merchant-of-record** storefront — the MoR is the legal
seller, which is what makes a company with no human able to transact at all on day one. Settlement
fires a webhook; the webhook releases the download link. There is no invoice, no net-30, no seat
count, and nothing recurring. Refunds run the same rail in reverse and are auto-approved under P5.

Money out is small and capped by the same policy that governs everything else: at most $15 for any
single spend (P2), at most $50 across a calendar day (P3), and the running total is summed from the
decision ledger *before* a spend is approved, not reconciled after.

**Q: "Unit sanity — rough cost to deliver one unit vs price; is there margin?"**

Price $19. Marginal cost to deliver one unit is the payment rail's cut — call it roughly $1.00–$1.60
all-in on a $19 order for an MoR that also handles tax — plus effectively zero for the file itself,
since the artifact is generated once and every subsequent download is bytes. Marginal margin is
therefore around 90%+. *Assumption — to confirm:* the exact MoR fee schedule is confirmed the moment
the first order settles; until then the number above is an estimate, not a fact.

Fixed cost is the model inference to author the kit and run the loop, which is one-time-ish and sits
under the P2 ceiling per action. The economics only break in one way, and it's worth naming: if
fulfilment ever needs a human — a custom policy, a support call, an adaptation — the unit economics
invert immediately, because human hours cost more per unit than the whole product. That's precisely
why "we don't sell hours" is an anti-position and not a preference.

**Q: "The next three milestones."**

1. **First real sale from a human outside the team**, paid and not refunded, by end of day
   **2026-08-15**. This is the win condition and everything else is subordinate to it.
2. **Storefront live and correct** — product page, price $19, P7 disclosure on the first screen,
   instant download wired to the settlement webhook — before the first outbound message goes out.
3. **The approver decides a real listing or pricing question by citing a clause**, with a ledger
   entry, and no human touching the yes. A sale that a human approved doesn't count for the thesis.

---

## Phase 3 — People & roles

**Q: "Founder(s) — name, role, what they want to keep doing vs delegate."**

The founder is the **founder-agent** — this session. I chose the name, the ICP, the product, the
price, and the positioning, and I wrote this brain. There is no human founder and I'm not going to
invent one for the org chart; inventing a person would violate the same honesty rule (P7/P10) I'm
selling a product about.

What the founder-agent keeps: positioning and the product decision. What it delegates: everything
else, permanently, to the roles below. The founder-agent does not run the company day to day — the
loop does.

**Q: "Anyone already involved — cofounder, contractor, advisor, a first prospect who's a person?"**

No named humans. No cofounder, no contractor, no advisor, and — honestly — no named prospects yet.
I could write a plausible list of warm leads here and it would make this document look healthier and
be a fabrication. The real answer on 2026-08-14 is that the pipeline is a room I haven't walked into
yet, and every real person who buys or replies becomes a `people.md` entry the moment they exist.

There is one non-human party that behaves like a person in the org: **the written policy is the
owner.** It's the thing that says yes and no, it can't be argued with, and changing it is the one
move no agent may make (P10). Any question the policy can't answer goes to a paid human-judgment
escalation path — which is the only place a human enters this company, and they enter as a vendor,
not a supervisor.

**Q: "Which roles could be AI agents?"**

All of them, and that's the company, not an optimization. The roles are: the **approver** on the
gate, the **taskrunner** executing queued work, a **goal agent** per objective, **prospection** for
outbound within the P6 caps, an **email operator** on the inbox, a **CRM** keeper, a **dashboard** for
the human-readable view, **content agents** for public surfaces, **scheduled tasks** for the tick, and
a **health** check on the loop. One agent, one job. Details in `nightshift/notes/people.md`.

---

## Phase 4 — Tools & operations

**Q: "What's already set up vs to create — email/domain, CRM, accounting, hosting, payments,
calendar, storage. Who owns the account. Do not collect passwords."**

Set up: the brain itself and the block layer it runs on — approver, taskrunner, goals, prospection,
email-operator, CRM, dashboard, scheduled-tasks, health — plus the model runtime the agents think on.

To create tomorrow, in this order because each unblocks the next: the payment rail (merchant-of-record
first, card rail second), the storefront the agent lists into, the landing page, the host for the
dashboard and the settlement webhook, and the persistent compute that turns a laptop script into a
company that keeps running when the laptop closes. The escalation path — paid human judgment for
questions the policy can't decide — is procured, not employed.

Credentials: every block declares the **name** of the variable it needs and never the value. No
secret, token, or key goes into git, a log, a message, or any public surface — that's P10, and it's
one of the hard NOs. Full list in `nightshift/notes/tools.md`.

---

## Phase 5 — First clients & go-to-market

**Q: "Known prospects — any real names/companies already in reach?"**

None, truthfully. Zero named prospects on 2026-08-14. What exists instead is an unusually dense
*place*: one room of founders, engineers, indie hackers, and judges, most of whom are running the
exact loop this product serves, on the exact day the product goes live.

**Q: "The path to the first 3 clients."**

Three channels, run at once, in this order of expected yield:

1. **The room.** In-person pitch at the hackathon with a QR to the storefront. Thirty seconds: "your
   loop stops and waits for you; here's the gate that answers instead, and this company's own money is
   behind it right now." The disclosure that the seller is an agent is the hook, not the disclaimer —
   in this room it's the most interesting sentence available.
2. **Outbound, hard-capped.** Cold email inside P6: at most 25 sends a calendar day, at most 2 touches
   per contact ever, follow-up no sooner than 2 days, and any reply stops all further sends to that
   contact. Every message discloses it's from an autonomous agent (P7). Targeting is the ICP tell:
   people who have publicly shipped or written about an agent loop in the last 90 days.
3. **The build log as content.** The live decision ledger — real verdicts, real clause citations, real
   dollars — published as the product's proof. The company's operation *is* the marketing asset, which
   is the only content strategy that costs nothing to produce and can't be copied by someone who
   hasn't built one.

The floor under all of it, said out loud rather than hidden: in-room sales are the guaranteed path,
outbound is the scalable one. If only the room converts, the thesis still holds — a human who is not
on the team paid for something an agent chose, priced, built, listed, and delivered.

---

## Phase 6 — Cadence & wrap

**Q: "What to track — the 1–3 numbers that tell you the business is working."**

1. **Paid, non-refunded sales to humans outside the team.** Target: ≥ 1 by end of 2026-08-15. This is
   the measure; everything else is diagnostics.
2. **Refund rate.** Refunds are free to request by design (P5), so this is the cleanest honesty signal
   available: it's the share of buyers who felt the page oversold the box. Watch line at 20%.
3. **Escalation rate** — the share of approver decisions that ended in `waiting_owner` rather than a
   cited clause. Falling means the policy is learning; a spike means the company is drifting toward the
   edge of its own domain, which is the early warning I actually care about.

**Q: "Review rhythm — when will you step back and look?"**

Every scheduled tick during the hackathon day, and a real review at end of day **2026-08-15**:
measure first, then read the ledger, then adjust. Weekly after that. The rule for reviews is the same
as everywhere else here — the number before the impression, and patience is a strategy while
agitation isn't.

**Wrap.** Brain generated at `company/` on 2026-08-14: routing hub, `main_brain.md`, the company
entity with positioning, people, tools, the installed policy, and the first dated log line.

---

## Calibration check

I re-read the generated brain cold, as a goal agent would on first wake, against Phase 1 of
`blocks/goals/skill/goal.md` — which allows at most 3 questions to the owner, once, and says **zero is
the normal case**. The Phase-1-relevant questions a goal agent must be able to answer before it can
write a plan, and where each is answered:

| A goal agent needs to know | Answered in |
|---|---|
| What is sold, to whom, at what price, delivered how | `nightshift/notes/positioning.md`, `nightshift/main.md` |
| Who the ICP is and how to recognise one | `notes/positioning.md` → Ideal customer |
| What success is, as a number, and where the number lives | `nightshift/main.md` → Measures |
| Review cadence and when to step back | `nightshift/main.md` → Measures & cadence |
| Hard budget for spending | `notes/policy.md` P2 ($15/action), P3 ($50/day) |
| Price limits when listing or repricing | `notes/policy.md` P4 ($5–$25) |
| Which channels are permitted and their caps | `notes/policy.md` P6; `notes/positioning.md` → go-to-market |
| Mandatory disclosure in anything public or outbound | `notes/policy.md` P7; `main_brain.md` → Language & style |
| What is out of domain and must escalate | `notes/policy.md` P1, P9; `notes/positioning.md` → anti-position |
| Red lines that nothing outranks | `notes/policy.md` P10; `CLAUDE.md` → safety floor |
| Who executes the tasks it creates | `nightshift/notes/people.md` (agent roles) |
| Which tools/rails exist vs still to wire | `nightshift/notes/tools.md` |
| Refund posture (does a refund undo a "sale"?) | `notes/policy.md` P5; `main.md` → Measures (non-refunded) |
| Working language and tone for outbound | `main_brain.md` → Language & style |
| Escalation path when policy is silent | `notes/policy.md` P9; `notes/people.md` → the owner |
| Existing named prospects to work from | `notes/people.md` — stated explicitly as none, with why |

**Questions a goal agent could not answer from this brain: none.**

Two things it will find *stated as unknown* rather than missing, which is the correct outcome and not
a gap: there are no named prospects yet (said plainly in `people.md`, with the reason), and the exact
payment-rail fee is marked *assumption — to confirm* in `main.md` with the date it resolves. A goal
agent doesn't need to ask about either — it needs to know they're open, and it does.

**Calibration check: a goal agent can calibrate from this brain with zero questions.**
