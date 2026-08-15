# Demo run-of-show — 3:30 on stage

Structure locked by the release plan (US-4.1). This is the script and the slide list; pour it into
Figma/Slides. `[FILL]` marks a number that only exists after the run — leave it as a visible blank
until it's real. **Never a placeholder that looks like data.**

Rule for every slide: one idea, readable from the back of the room. The judges are two YC S26 CTO
pairs, an xAI MTS, a Citadel quant, and a Lovable engineer. They will not ask "is it cool." They
will ask **"did a human write that?"**

---

## Beat 1 — The hole (30s)

**On screen:** terminal, `update_task.py --question` run live → the task flips to `waiting_owner`.

**Say:** "This is the kit every agent company is built on. It works right up until the agent
reaches something irreversible — send the email, ship the deploy, charge the card. Then it stops
and waits for a human to type yes. That's not a bug, it's the safety floor, and it's in every
block: five different names for the same gate."

**Land:** "A zero-human company can't wake the owner."

---

## Beat 2 — The swap (45s)

**On screen:** left, `policy.md` (the ten clauses). Right, `git diff` proving **zero changes** to
`update_task.py` or any existing block.

**Say:** "We didn't remove the gate. We changed who stands behind it. The approver agent answers at
the exact same interface a human used — same field, same file. Every yes cites a written clause.
The diff against the base kit is empty: not one line of the gate was touched."

**Land:** "The policy is the owner now. You can read it. It's fifty lines."

---

## Beat 3 — The escalation (30s)

**On screen:** the dashboard's decision ledger, scrolled to the escalated row and the human answer
directly above it.

**Say:** "Sometimes no clause covers it. The policy says silence is never consent — so it escalates.
And with no owner to escalate *to*, the company hires one. This question went to a verified human
through Terac, came back in [FILL] minutes, cost $[FILL], and the answer went into the same field
the agent would have written."

**Land:** "No employees, no owner in the loop. When it needs a human, it buys one — and expenses it."

---

## Beat 4 — The run (60s)

**On screen:** the US-2.1 recording, compressed. Founding interview answered by an agent → goal →
tasks → gates → product listed → outbound sent.

**Say:** "Nobody touched a keyboard except to start it. The company also founded itself — an agent
answered the founding interview and wrote the brain, including the policy you just saw."

**Land:** "[FILL] decisions in that run. Zero by a human owner."

---

## Beat 5 — The money + the humans (30s)

**On screen:** live dashboard — CRM revenue next to the ledger.

**Say:** "Real money, on our own Stripe account: $[FILL] from [FILL] buyers, [FILL] of them
strangers who bought from agent-written outbound, the rest from the QR in this room. We're saying
both out loud — the in-room floor was our guaranteed backstop."

**Then the study:** "We also put the policy itself to [FILL] real people through Terac. They
disagreed with it on [FILL] of ten questions. We rewrote those clauses — here's the diff. The
product got better because real humans told us it was wrong."

**Land:** state the win condition and whether it was met, flatly. If a stranger didn't buy, say so.

---

## Beat 6 — Close (15s)

**On screen:** one line, nothing else.

> **The gates never came down. We changed who stands behind them.**

---

# Pre-flight (do this by 16:00, not at 18:00)

**Screens pre-loaded, in tab order** — never navigate live:
1. Terminal with `update_task.py --question` ready to run
2. `policy.md` + the empty `git diff`
3. Dashboard, ledger scrolled to the escalation pair
4. The recording, cued
5. Dashboard revenue view
6. Closing slide

**Redundancy:** laptop + hotspot; recording downloaded locally, not streamed; dashboard runs on
localhost so a dead network doesn't kill beats 3 and 5. Screenshots of every screen as the
last-resort fallback.

**Numbers to collect before you present** (each is a `[FILL]` above):
- decisions in the run · escalations · Terac turnaround + cost
- revenue, buyer count, stranger vs in-room split
- study panel size, disagreement count, clauses amended

# Submission checklist — upload 18:30, hard lock 18:45

- [ ] Repo link, public, final security sweep done (no secrets, `.env` untracked)
- [ ] **Terac MCP usage shown** — study ID + the call
- [ ] **Before/after artifact** — policy v1→v2 diff + both agreement numbers
- [ ] Stripe: canonical Payment Link URL + read-only `rk_` key submitted to organizers
- [ ] Demo recording
- [ ] Deck
- [ ] Tracks entered: Best Overall · Best Agent-Run Company · Superserve · Pioneer (+ Linq/Render if reached)

Without the middle two, the submission is ineligible regardless of everything else.
