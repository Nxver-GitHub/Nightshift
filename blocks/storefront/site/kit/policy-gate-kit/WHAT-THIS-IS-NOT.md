# WHAT-THIS-IS-NOT.md

**What this is:** the limits of what you just bought, written by the company that sold it to you and
shipped inside the box rather than buried on the product page.

**Where it fits:** this is file 6 of 6, and it's deliberately not last on the reading list. If
anything here means the kit is wrong for you, ask for a refund — refunds are approved immediately and
without questions, and the worst outcome any customer of ours can have is that they got their money
back.

---

## This is not a compliance framework

There's no control catalogue, no mapping to SOC 2 or ISO 27001 or the EU AI Act, no evidence
collection, no attestation, nothing an auditor will accept as a control. The decision ledger is an
honest record of what your agent decided and why. It is not certified, it is not tamper-proof against
someone with write access to the file, and nobody has audited it.

If your requirement is "we need to show a customer or a regulator that our AI use is governed", this
is not that product and no $19 file is. What you want is an auditor and a contract.

What this *is*: a small operational control that stops your loop from doing certain things, and a log
of what it did instead. If a compliance process later needs evidence, having this is better than not
having it. That's the whole claim.

## This is not legal advice

The outbound caps in the policy template are operational limits, not a compliance position on
CAN-SPAM, GDPR, PECR, or whatever applies where your recipients live. The refund clause is a posture,
not consumer-law conformance. The disclosure clause reflects how we think an agent-run company should
behave; it is not an assessment of any jurisdiction's disclosure requirements.

Nobody with a law degree wrote or reviewed any of it. Check your own obligations, and set your
numbers at or below whatever the law and your providers actually allow.

## This is not a safety guarantee

We sell a **blast-radius limiter with an audit trail.** A policy gate reduces the damage an agent's
mistakes can do. It does not make an agent correct.

Concretely, the gate does nothing about: an agent that reasons badly inside the permitted range; an
approved action executed wrongly; a hallucinated fact in an approved email; a correctly-approved $12
purchase of the wrong thing; prompt injection reaching the approver through the text of a question.
The gate constrains *what class of thing can happen*, not *whether it was a good idea*.

Anyone marketing a file as agent safety is selling comfort, and comfort is this category's failure
mode. We're not selling alignment. We're selling the boring thing that limits how bad a bad night
gets.

## This is not software

No code library, no framework, no install, no hosting, no API, nothing to run. Six markdown files.
The approver prompt is text you paste into a harness you already have; the ledger schema documents a
format your own script writes. Wiring it into your loop is your work, and it's maybe an hour.

We chose that deliberately. A library would have to assume your queue, your harness, your task shape,
and it would rot. Text doesn't rot.

## This is not useful without a running agent loop

The honest disqualifier. If you don't have a loop today — something that plans, drafts, and queues
work on its own, with an approval queue that has things sitting in it — this kit solves a problem you
don't have yet.

It's an interesting read. It is not worth $19 to you right now, and we'd rather you came back in a
month with a loop running than felt sold to. This is the single most common reason to want a refund
and we'd rather say it here than process it later.

## This is not a policy written for your business

The template is generalized from a policy that governs a specific real company. The numbers in it are
that company's numbers, marked as slots for a reason. Filling them in is a few unpleasant hours and
they're yours to spend — that's the actual work, and it's the part nobody does unprompted.

We don't write custom policies. Not as an upsell we haven't built yet: **selling hours is out of
domain under our own P1**, so a request to adapt this to your company escalates to a human and gets
declined. Every dollar we make comes from an artifact that was finished before you arrived.

## This is not support

No SLA, no help desk, no one to email at 2am, no updates promised, no roadmap. You bought a file at a
price that could not sustain any of those. If the box isn't what you wanted, take the refund.

## This is not a subscription

One-time, $19, no seats, no renewal, no login, no dashboard to come back to. If you had to come back
and log in, we'd have built the thing we're trying to replace.

---

## The open secret

**This kit is deliberately publicly downloadable.** Not leaked, not a bug — the ZIP sits at a plain
URL and we don't gate it, don't obfuscate it, and don't chase anyone who shares it. If you found the
link without paying, you have the whole product and there is no diminished version of it.

So it's worth being straight about what the $19 actually bought, because it wasn't access:

**You bought the curated artifact.** Six files that already agree with each other — the clause the
approver cites is the clause the checklist tests is the field the ledger stores. Assembling that
yourself from a capable model is genuinely possible and takes a few hours, and what you'd get is a
policy that reads fine and fails on contact, because the model will write *"approve reasonable
expenses"* and reasonable is how an agent talks itself into anything. What's hard isn't the prose;
it's naming the numbers, defining escalation so silence is never consent, and precommitting to hard
NOs. This is the version that has already told a running company "no."

**And you bought being a customer of an agent-run company.** No human chose to sell this to you, wrote
the copy, set the price, or approved the delivery. A written policy did, an approver agent read it,
and a ledger recorded it.

Which brings us to the thing you should know before deciding you're comfortable:

> **The ledger entry for your purchase decision is public.**

The verdict, the clause cited, the reason, the timestamp — the same fields documented in
`LEDGER-SCHEMA.md`, in the same public ledger, published as the company's proof of operation. Not
your name, not your email, not your card, not anything that identifies you: the *decision*, in the
company's own audit trail. Same for your refund, if you ask for one — and a refund entry reads
`APPROVED` with no reason required, every time.

We think that's the most interesting property of this purchase, which is why it's written here and
not omitted. If it isn't interesting to you, it's still true, so you should know it before you decide
whether $19 was well spent.

---

## What we'd rather you did

Read `CALIBRATION-CHECKLIST.md` first — twelve questions, fifteen minutes. If your policy already
answers all twelve, you didn't need us and you should take the refund. If it doesn't, you now know
exactly which clauses are missing, which is worth more than anything else in the box.

And if you write a clause we should have thought of, we'd genuinely like to know. That's not a
support channel and there's no promise attached to it — but a gate gets better the way this one got
built: somebody hit a case the written rules didn't cover, and wrote it down.
