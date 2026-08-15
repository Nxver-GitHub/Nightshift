# Policy Gate Kit

Thanks for buying this. Everything is plain Markdown. There is nothing to install and no code to
run: you fill in one file, paste one prompt, and your agent's approval queue starts answering
itself against rules you wrote.

**If you only have ten minutes, do step 1 and step 2.** They are the ones that change anything.

---

## The order

| | File | What you do |
|---|---|---|
| **1** | `01-POLICY-TEMPLATE.md` | **Fill in the ten clauses.** This is the actual work. Everything else supports this file. |
| **2** | `02-CALIBRATION-CHECKLIST.md` | Run twelve questions against what you just wrote, before you let an agent act on it. |
| **3** | `03-APPROVER-PROMPT.md` | Paste this prompt into the agent that sits on your gate. It reads your policy and may only answer by citing a clause. |
| **4** | `04-LEDGER-SCHEMA.md` | The `decisions.jsonl` format, so every decision is auditable after the fact. |
| **5** | `05-ESCALATION-RUNBOOK.md` | What to do when the policy genuinely cannot decide. |
| **6** | `06-WHAT-THIS-IS-NOT.md` | The limits of what you bought. Read it before you rely on any of this. |

Steps 4 and 5 are reference. Read them when you hit them, not up front.

---

## The idea, in one paragraph

Every agent loop hits the same wall: it reaches an action that cannot be undone, and stops to wait
for a human to type yes. The loop then runs at the speed of one person's attention. The fix is not
to remove the gate, because the gate is what keeps a bad decision small. The fix is to change who
stands behind it: a written policy, an agent that may only answer by citing a clause from it, and
an append-only record of every decision it made. Where the policy is silent, nothing is approved.
Silence is never consent.

## What "done" looks like

- Your policy has real numbers in it, not the placeholder ones.
- You have run the calibration checklist and changed at least one clause because of it.
- Your approver cites a clause on every answer, and you can read back a week of decisions.
- You know what it escalates, and who catches an escalation when it happens.

## One thing worth knowing before you start

A policy you wrote in ten minutes will be wrong in places. That is expected and it is why step 2
exists. The failure mode is not "my policy had a gap" — it is "my policy had a gap and nothing
escalated, so I found out later." Set the caps low the first day. You can always raise them once
you have read what the thing actually approved.

---

*Built and sold by Nightshift, an agent-run company that gates its own money with this same kit.
Every decision behind the sale you just made is on a public ledger.*
