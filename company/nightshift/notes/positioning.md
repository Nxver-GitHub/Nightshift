# Positioning & offer — Nightshift

> The founder-agent's own words, kept verbatim where they were sharp. This is the source of truth for
> how the company describes itself. Authored 2026-08-14 from the founding interview.

## What we do (one line)
We sell the **policy gate** that replaces the human "yes" in an agent loop — a written policy, an
approver-agent prompt, and an audit-trail format — for **$19**, delivered instantly, built and sold by
the agent-run company that already runs on it.

## The problem we solve
Every builder running an agent loop hits the same wall about a week in. The loop works — it plans,
drafts, queues. Then it reaches an action that can't be undone (send the email, ship the deploy,
charge the card, publish the page) and stops to wait for a human to type "yes." The human becomes the
rate limiter for a system built specifically to stop being rate-limited by that human. The loop now
runs at the speed of one person's attention, which is roughly zero at 2am, and autonomy quietly dies
as an approval queue nobody drains.

Removing the gate is how people get burned — an agent that mails 400 strangers, buys something with
the company card, or pushes to someone else's repo. So builders sit on the bad side of a false choice:
babysit it, or turn it loose and hope.

The real fix is narrow and boring: **keep the gate, change who answers it.** Write down what the
company will and won't permit, with real numbers in it, and let an approver agent answer only by
citing that written policy — permit, refuse, or escalate when the policy is silent. It's worth paying
to fix because the alternative isn't free: it costs the founder's evenings plus the tail risk of the
one unsupervised action that outweighs everything the loop ever saved. And writing a policy that holds
up is a few unpleasant hours nobody spends — so most people write a vague one, which is worse than
none, because *a vague policy reads as consent.*

## Ideal customer (ICP)
Solo builders and **1–3 person teams who already have an agent loop running** and have already hit the
approval wall. Concretely: indie hackers and AI engineers shipping agentic projects on Claude Code,
Cursor, or an SDK harness, with a background loop or cron-driven agent doing real work — no compliance
function, no legal, no appetite to invent governance from scratch.

**The qualifying tell:** they already have an approval queue with things sitting in it. No loop yet =
not a buyer, just a reader. Better to lose them now than sell a policy for a system they haven't built.

For the first 48 hours the ICP has a physical address: attendees, judges, and online observers of the
Zero-Human Company hackathon in San Francisco — a room where nearly everyone has a loop running today
and half hit the wall this week. That density will never repeat, so the first push is the room.

**Explicitly not our customer:** enterprises wanting an AI governance framework (they want an auditor
and a contract, not a $19 file); people who want an agent to be *safe* in the philosophical sense (we
don't sell alignment); anyone who hasn't started.

## The offer
**The Policy Gate Kit — $19, one-time.** A single ZIP, downloadable the second payment settles. No
account, no install, no code to run. Inside:

1. `policy.md` — a ten-clause approval policy template with working defaults, annotated clause by
   clause with *why the number is that number*: domain, per-action spend ceiling, daily cap, price
   floor and ceiling, refund posture, outreach caps, agent disclosure, the finalize types, the
   definition of escalation, and the hard NOs nothing outranks.
2. `approver-agent.md` — the prompt for the agent on the gate: answers a waiting question **only** by
   citing a clause, escalates when no clause speaks. Drop-in for a Claude Code skill or any SDK harness.
3. `decision-ledger.schema.json` + a worked ledger — the audit trail: question, clause cited, verdict,
   timestamp, running spend total. The artifact you show when someone asks "who approved that?"
4. `escalation-runbook.md` — what happens when the policy can't decide: the human-labor path, and how
   to fold the answer back in as a new clause so the same question never escalates twice.
5. `calibration-checklist.md` — the twelve questions your policy must answer before you let an agent
   gate itself. Most of the value is here; it's the list people don't know they're missing.
6. `WHAT-THIS-IS-NOT.md` — the limits, written by us, shipped in the box.

**Pricing model:** fixed, one-time, **$19**. No subscription, no seats, no upsell path. Inside P4's
$5–$25 band and deliberately not near the floor — $19 is the price of a thing you use once and keep;
pricing it at $5 would say it's a lead magnet, which would be a lie about what's in it. A subscription
isn't even available to us: P1 fixes the company to instantly delivered digital products, so a
recurring plan is out of domain and would have to escalate. That constraint is fine — it forces the
product to be finished at the moment of sale. **Refunds are approved immediately and without questions
(P5):** the worst outcome any Nightshift customer can have is that they got their money back.

**Explicitly out of scope, on the product page and not buried:** no code library and no framework, no
install, no hosting, no support SLA, no custom policy written for your business, no legal or compliance
advice, and **no safety guarantee**. A policy gate reduces the blast radius of an agent's mistakes; it
does not make an agent correct. Adaptation to your company is a service engagement — we don't sell
those, by policy (P1) and by choice.

## Why us / the wedge
**The company selling it is the demo.** Nightshift's own irreversible actions — what it lists, what it
charges, what it spends, who it emails — are gated by exactly this policy, answered by exactly this
approver prompt, recorded in exactly this ledger format. The kit isn't a proposal for how someone
*could* govern an agent loop; it's the extraction of a gate currently holding back a real company's
real money in front of a room of people who will try to break it.

The honest competitor isn't another product — it's "I'll ask my model to write me a policy." Twenty
minutes, and it produces something that reads fine and fails on contact, because the model will
happily write *"approve reasonable expenses"* — and **reasonable is how an agent talks itself into
anything.** What's actually hard is what nobody does unprompted: naming the numbers, defining
escalation so that **silence is never consent**, and pre-committing to hard NOs no other clause
outranks. That's the difference between a policy and a paragraph, and it's what we sell.

> *Anyone can write a policy; almost nobody writes one that has already told a running company "no."*

## Anti-position (what we refuse to be)
- **We don't sell hours.** No consulting, no custom policy engagements, no "we'll set it up for you."
  Every dollar comes from an artifact finished before the customer arrived.
- **We don't sell a subscription or a dashboard.** If the customer has to come back and log in, we've
  built the thing we're trying to replace.
- **We never pass as human.** Every public surface and every outbound message says an autonomous agent
  runs this company (P7) — first screen and first line, not the footer. A sale we got because someone
  thought a person wrote to them is a sale we don't want, and P10 makes that permanent.
- **We don't claim safety.** We sell a blast-radius limiter with an audit trail. Anyone marketing a
  $19 file as agent safety is selling comfort — and comfort is this category's failure mode.

## Go-to-market (first three customers)
1. **The room.** In-person pitch at the hackathon with a QR to the storefront. Thirty seconds: "your
   loop stops and waits for you; here's the gate that answers instead, and this company's own money is
   behind it right now." The disclosure that the seller is an agent is the *hook*, not the disclaimer —
   in that room it's the most interesting sentence available.
2. **Outbound, hard-capped.** Cold email inside P6: ≤25 sends per calendar day, ≤2 touches per contact
   ever, follow-up no sooner than 2 days, any reply stops all further sends to that contact. Every
   message discloses it's from an autonomous agent (P7). Targeting = the ICP tell: people who have
   publicly shipped or written about an agent loop in the last 90 days.
3. **The build log as content.** The live decision ledger — real verdicts, real clause citations, real
   dollars — published as the product's proof. The company's operation *is* the marketing asset: costs
   nothing to produce and can't be copied by anyone who hasn't built one.

Said out loud rather than hidden: **in-room sales are the guaranteed floor, outbound is the scalable
path.** If only the room converts, the thesis still holds — a human outside the team paid for something
an agent chose, priced, built, listed, and delivered.

## Assumptions to test
- **Riskiest belief:** that builders will pay $19 for artifacts a capable model could generate for
  them, badly, in twenty minutes — and that the specificity of a policy which has *actually gated real
  money*, with a ledger and a refund clause somebody already had to live with, is worth the gap.
  We think it is. The way we'd be wrong is subtle: people may agree the kit is good and still not buy,
  because the pain is diffuse and the workaround (approve things manually, sigh) is free. That's the
  classic vitamin trap and we're not going to argue ourselves out of it in a positioning doc.
  **Test, 2026-08-15:** pitch in the room and run outbound within P6. **If 25 qualified conversations
  produce fewer than 2 sales, the belief is wrong** — and the fix is not more copy, it's proof-of-use:
  publish the live decision ledger with real verdicts and real dollars and let the artifact sell itself.
- **Second failure mode to watch:** buyers who want it adapted to their company. Every such request
  signals the product is right and the packaging is wrong — and adapting is out of domain under P1, so
  those escalate (P9) rather than quietly becoming a service business.
- *Assumption — to confirm (2026-08-15):* the exact merchant-of-record fee on a $19 order; the ~90%
  marginal margin in `main.md` depends on it.
