# Project Sunday — Zero-Human Company Release Plan (Terac Hackathon)

> **Builds on:** Project Sunday v0 (brain + 10 built blocks, all tested)
> **Team:** 3 developers (Surya — autonomy lane · Anirudh — money lane · Pravin — evidence/audit lane, branch `pravin/audit`, brief in `PRAVIN.md`) | **Sprints:** 5, mapped to clock time (18h total)
> **Submission: LOCKS 6:45pm — our upload target 6:30pm (Pravin owns the upload).** Guidebook deltas of 8/15 are folded in below; where this file and `HACKATHON.md` "Guidebook facts" disagree, the guidebook facts win.
> **Hosting target:** Superserve (agent loop, persistent microVM) + Render (storefront + webhook receiver)
> **Release window:** Tonight → tomorrow 4:00pm code freeze → demo ~6–7pm

---

## The Thesis (the spine of every story below)

Project Sunday's architecture has ONE deliberate human dependency: every block stops and asks
the owner — `waiting_owner`, `pending_validation`, review mode. That is the "owner's-yes safety
floor" (`README.md`, Design principles). A zero-human company cannot wake the owner. So **we do
not remove the gates — we replace who stands behind them:**

1. Agents act autonomously under the existing autonomy contract (`blocks/goals/skill/goal.md`, lines 13–17).
2. Ambiguous → an **approver agent** decides against the brain's WRITTEN policy.
3. Policy genuinely can't decide → the company **hires a verified human from Terac** and pays them
   automatically on verified completion.

> **The company has no employees and no owner in the loop. When it needs a human, it buys one — and expenses it.**

The last human dependency — the founding interview (`kit/interview/company.md`) — is answered by
an agent. The company founds itself.

**Win condition (falsifiable, said on stage):** a real human not on the team paid real money for a
product an agent chose, priced, built, listed, and delivered — and no human approved any step; an
approver agent did, with an audit trail.

---

## Goals

1. **Keep the gates, swap the approver** — the taskrunner's `--question` / `--finalize` gate
   (`blocks/taskrunner/code/update_task.py`) stays untouched; an approver agent writes
   `question.answer` at the exact interface the human used. Zero modification to existing blocks.
2. **Real money, no activation blocker** — a Merchant-of-Record payment rail (Dodo/Whop) behind a
   3-command seam (`pay.py`), built tonight against Stripe test mode so tomorrow is a one-line env swap.
3. **Terac as the escalation path** — when written policy genuinely can't decide, the company buys
   verified human judgment from Terac and expenses it. Never as COGS ($60–220/hr kills a $20 product).
4. **The company founds itself** — an agent answers `kit/interview/company.md` and generates the
   brain, including the written policy the approver will enforce all day.
5. **Off the laptop** — `start-taskrunner.sh` is a `caffeinate` + PID-lock laptop script; Superserve
   persistent microVMs make the loop a company, not a demo.
6. **Auditability as the product** — every autonomous decision lands in a visible audit trail
   (task journals + CRM `events` + dashboard). The judges must be able to replay the whole day.

---

## Tech Notes

| Concern | Decision |
|---|---|
| Gate surface | `blocks/taskrunner/code/update_task.py` — `--question` sets `status=waiting_owner` + `question={text, asked_at, answer, answered_at}`; `--consume-question` clears; `--finalize TYPE=DETAIL` gates push/email/deploy/archive through the same mechanism. The approver writes `question.answer` — drop-in human replacement, **zero block modification**. |
| Payment rail | **FLIPPED 8/15 (guidebook): Stripe live is the PRIMARY rail** — "Best Overall Agent-Run Company" eligibility requires collecting through our own Stripe individual account; organizers track revenue via a read-only restricted key (Balance/Charges) and ONE submitted Payment Link reused for every sale (new links mid-day break their tracking). MoR (Dodo/Whop) demoted to stretch behind the same `pay.py` seam — organizers can't see MoR revenue. |
| The seam | `blocks/payments/code/pay.py` — 3 commands, mirrors the `crm.py` CLI idiom: `create-link --title --amount --currency` → URL · `status --link-id` → `paid|unpaid` · `sales --json`. Anirudh builds it; Surya only calls it. |
| Revenue ledger | `blocks/crm/code/crm.py` `projects` table — `amount` column, stages incl. `won`/`delivered`. Every sale recorded here so the existing dashboard shows revenue with no new UI. |
| Agent runtime | Superserve (`SUPERSERVE_API_KEY`) persistent Firecracker microVMs replace `start-taskrunner.sh`. State survives restarts. |
| Human labor | Terac (`TERAC_API_KEY`) — expert-labor MCP + REST. Sourced only via the escalation path; paid on verified completion. |
| Storefront / landing | Whop storefront (Tier 2) + Lovable agent-generated landing page (Tier 2 — judge Roman Yanushevskyi is an AI Engineer at Lovable). Render (`RENDER_API_KEY`) hosts the webhook receiver + dashboard. |
| Product domain | Fixed by humans in policy: **digital product, under $25, instant delivery, for founders/builders.** The AGENT picks product, copy, and price. |
| Models | Fable 5 = PM/planning · Opus 5 = complex/architectural · Sonnet 5 = small token-efficient tasks · **never Haiku**. |
| Testing | pytest for Python CLI blocks (most of the repo); Playwright for any web surface (storefront, landing, checkout, dashboard). |
| Secrets | Repo rule (`blocks/connectors.md`): **"No secret in git — ever."** Blocks declare credential NAMES in `block.md`, values live in git-ignored env. |
| Tier 3 (post-freeze-safe only) | Pioneer/Fastino (Claude-compatible endpoint, one-line swap for the tick loop) · Linq (iMessage/RCS/SMS outbound) · BAND (multi-agent coordination) · Replay (time-travel debugging). |
| Uncertain API surfaces | Where a sponsor's API is unverified at write-time, the story says so and mandates fetching current docs (Context7 / vendor) before coding. No invented endpoints. |

---

## Scope Rules

- **Keep the gates, swap the approver.** No story may weaken or bypass `waiting_owner` /
  `pending_validation` / review mode. This is a substitution, not a guardrail removal.
- **Constrained autonomy.** Humans fix the domain (digital product, <$25, instant delivery, for
  founders/builders — written into policy). The agent picks product, copy, and price. No human
  picks the product, ever.
- **Terac is the escalation path, never the COGS.** No story routes routine work to paid experts.
- **Customers: two channels, both stated openly on stage.** Live agent outbound to real strangers
  all day AND in-room sales as the guaranteed floor.
- **Seven working integrations beats fifteen on a slide.** Tier 3 only after the spine is green and
  only post-freeze-safe.
- **Strict lane ownership.** Surya: `blocks/approver/`, `blocks/labor/`, `kit/` (branch
  `surya/autonomy`). Anirudh: `blocks/payments/`, storefront, hosting (branch `anirudh/payments`).
  Pravin: `blocks/dashboard/`, `demo-assets/`, submission package (branch `pravin/audit`).
  Never edit a file outside your lane; note cross-lane needs at the checkpoint, the owner makes it.
- **Merge to `main` at fixed checkpoints only:** end of tonight, 12pm, 2pm, 4pm freeze.
- One user story at a time. No fake/hardcoded data — every story wires end-to-end or documents the gap.
- All secrets via environment variables; `block.md` manifests declare names, never values.

---

## Dev Process Rules

- **95% confidence rule.** If Claude is not 95%+ confident in a decision, code-quality output, or
  any response affecting the project, it STOPS and runs the `grill-me` skill to ask clarifying
  questions. Never guess.
- **grill-me at story start.** Whenever Surya or Anirudh begins a new user story, Claude runs
  `grill-me` first to pin down scope before writing code.
- **Model routing:** Fable 5 = PM/lead/planning · Opus 5 = complex, long, architectural tasks ·
  Sonnet 5 = smaller, token-efficient tasks · **NEVER route to Haiku.**
- **Latest docs.** Before integrating any sponsor tech, fetch current official documentation
  (Context7 or the vendor's own docs). Do not rely on training data for API shapes.
- **Testing contract:** Playwright for anything with a web surface (dashboard, storefront, landing
  page, checkout flow). **pytest for the Python CLI blocks** — most of this repo is Python CLI, so
  Playwright alone does not cover it. Every story's DoD includes passing tests that prove the
  story's end-to-end interaction actually works.
- **Security gate (blocking, every story):** a security-review agent verifies before any push — no
  API key or secret leaks, no credentials in git, no hashing/crypto material exposed, no sensitive
  data in logs or committed files, no backdoors, no prompt-injection or phishing vectors in
  agent-facing input paths, no known modern exploit classes. The codebase must be clean to push to
  a public GitHub repo.
- **Code quality:** modular, small files, and **commented** — document what the code is doing
  inline for readability and auditability. This is a judged, publicly-reviewed codebase.
- **No unnecessary markdown files.** They burn context and tokens.

## Definition of Done (referenced by every story as "DoD")

A user story is done only when: the end-to-end interaction works against real (or test-mode)
services · tests pass (pytest and/or Playwright as applicable) · the security-review gate passes ·
code is commented and modular · no secrets in git · merged to `main` at the next checkpoint.

---

## Sprint 0 — Tonight (both lanes in parallel, ~6h)

> **Theme:** No sponsor credentials exist yet (keys arrive 8:30am via Slack). So tonight we build
> the adapter layer that DECLARES credential names, and prove the payment flow on Stripe test mode
> so tomorrow morning is an env swap, not a build.

### US-0.1 — Approver Agent Answers a Waiting Task **[SURYA]** *(2.5h)*
When any block asks the owner a question — a task in `blocks/taskrunner/code/tasks.json` sits in
`waiting_owner` with `question.text` filled and `question.answer` null — the approver agent
(`blocks/approver/`) wakes, reads the brain's written policy, decides, and writes `question.answer`
+ `answered_at` at the exact same interface a human would have used. The taskrunner then consumes
it with `--consume-question` and continues, never knowing a human didn't answer.
- New block: `blocks/approver/` with `block.md` (manifest: declares `ANTHROPIC_API_KEY` name only),
  `code/approve.py` (CLI: `approve.py run --once` scans for `waiting_owner` tasks; `approve.py log --json`
  dumps the decision ledger), `skill/approver.md` (the agent role), `SETUP.md`.
- Decision taxonomy: `approve` (write answer) · `reject` (write answer refusing, with the policy
  clause cited) · `escalate` (leave for `blocks/labor/`, US-1.3). Every decision appends to an
  append-only `decisions.jsonl` ledger: task id, question, policy clauses cited, verdict, timestamp.
- **Selling point, stated in the demo:** this requires ZERO modification to `update_task.py` or any
  existing block — the gate stays; only who stands behind it changed.
- `--finalize` gestures (push/email/deploy/archive) route through the same path since they reuse
  the question mechanism (`update_task.py` lines 195–221).
- pytest: seed a fixtures `tasks.json` with a `waiting_owner` task; assert answer written, ledger
  appended, `--consume-question` succeeds afterward.

**Out of scope:** Terac escalation (US-1.3), Superserve hosting (US-1.4), any change to taskrunner code.

### US-0.2 — The Written Policy the Approver Enforces **[SURYA]** *(1.5h)*
When the approver faces any question, it decides against a single written policy file — so a judge
can read the policy, read the decision ledger, and verify every autonomous "yes" traces to a
written clause. Surya drafts `blocks/approver/policy/policy.md` (installed into the generated
brain at founding, US-0.3): the human-fixed domain (digital product, under $25, instant delivery,
for founders/builders), spend ceilings, allowed finalize gestures, refund rule, escalation criteria
("policy cannot decide" is itself defined), and hard NOs (no impersonation, no spam beyond rate N,
no purchases above ceiling).
- Policy is versioned in git (it contains no secrets — it IS the audit artifact).
- pytest: table-driven cases — for each canned question, the approver cites the expected clause and
  verdict (approve/reject/escalate).

**Out of scope:** policy UI; runtime policy editing.

### US-0.3 — The Company Founds Itself **[SURYA]** *(2h)*
When Surya starts the founder-agent session, an agent runs the founding interview
(`kit/interview/company.md` via `START-HERE.md`) with ANOTHER agent answering as the founder —
constrained by the locked domain — and out comes a real Company Brain (`main_brain.md`,
`company/main.md`, notes, `CLAUDE.md` routing) in a new folder, with US-0.2's policy installed as
`company/notes/policy.md`. The last human dependency in Project Sunday — the interview — is gone.
- The founder-agent's answers must satisfy the interview's phases (identity, offer, positioning),
  and pick the company name, ICP, and one-liner itself.
- The generated brain is committed (it contains no secrets — it's a synthetic company).
- Verification: the goals block can read the brain and calibrate (per `blocks/goals/skill/goal.md`
  Phase 1) without asking a single question — "zero is the normal case."

**Out of scope:** personal mode; multiple companies; re-running the interview live on stage (we show the artifact + a clip).

### US-0.4 — Payment Seam on Stripe Test Mode **[ANIRUDH]** *(3h)*
When any agent (or Anirudh at a terminal) runs `pay.py create-link --title "X" --amount 20
--currency usd`, it gets back a working checkout URL; completing that checkout with a Stripe test
card flips `pay.py status --link-id …` to `paid`, and `pay.py sales --json` lists the sale. The
whole money path is real and tested tonight, with zero sponsor dependence.
- New block: `blocks/payments/` — `block.md` declares names `STRIPE_API_KEY`, `DODO_API_KEY`,
  `WHOP_API_KEY`, `PAYMENT_PROVIDER` (values never in git); `code/pay.py` (single CLI, provider
  chosen by env — mirrors the `crm.py` idiom so it needs zero Project-Sunday knowledge to build);
  `SETUP.md` written for a stranger.
- Provider adapters behind one interface: `stripe` (test mode, Payment Links API — fetch current
  Stripe docs first), `dodo` and `whop` as stubs that declare config and raise "credentials not
  provisioned" cleanly until tomorrow.
- pytest: adapter selection, link-create against Stripe test mode, status polling, `sales --json`
  shape; Playwright: drive the hosted Stripe test checkout once with card `4242…` end-to-end.

**Out of scope:** MoR live keys (US-1.1), webhook receiver (US-1.2), CRM recording (Surya's side calls the seam later).

### US-0.5 — Storefront Skeleton, Deployed **[ANIRUDH]** *(2h)*
When a stranger opens the storefront URL on their phone, they see the product page (title, price,
copy — placeholder tonight, agent-written tomorrow) and a Buy button that opens a `pay.py`-created
checkout link; after paying (test card tonight) they land on a thank-you page with the delivery
link. Self-contained: static HTML + tiny server, hosted on Render, no Project-Sunday internals.
- Product content read from one `product.json` (title, price, copy, delivery URL) — tomorrow the
  agent overwrites this file; Anirudh's surface doesn't change.
- QR code on the thank-you/landing page for the in-room sales floor.
- Playwright: load page → click Buy → complete Stripe test checkout → thank-you page shows delivery link.

**Out of scope:** Lovable-generated design (US-3.2), Whop storefront (US-3.1), real product content.

### US-0.6 — Checkpoint 0: Merge + Credential Name Manifest **[BOTH]** *(1h)*
At the end of tonight both branches merge to `main`, and a single credential checklist exists so
that tomorrow at 8:30am key-loading is a 10-minute mechanical task, not a scramble. Each new block's
`block.md` declares every env var NAME it needs; a git-ignored `.env.example`-style template lists
them all (names only).
- Checklist (fill from sponsor Slack at 8:30am): `TERAC_API_KEY` · `SUPERSERVE_API_KEY` ·
  `DODO_API_KEY` · `WHOP_API_KEY` · `STRIPE_API_KEY` (live) · `RENDER_API_KEY` · Lovable account ·
  (Tier 3, only if reached: Pioneer/Fastino key, Linq key, BAND key, Replay account).
- Security gate runs on the full merged tree before push (public repo).

**Out of scope:** any key values; any new features.

---

## Sprint 1 — 8:30am–12pm: Credentials In, Payment Live

> **Theme:** Keys arrive at 8:30. HARD DEADLINE: a real-money payment path is green by 12:00.
> Anirudh owns the money; Surya makes the company able to buy human judgment and live off the laptop.

### US-1.1 — Real Money via Stripe Live + Prize Eligibility **[ANIRUDH]** *(2h — REWRITTEN 8/15 per guidebook)*
When a real person completes checkout on the storefront, real money is captured on OUR Stripe
individual account — the rail organizers can see — and `pay.py status` reports `paid`. The Stripe
driver already works in test mode (US-0.4); this story takes it live and does the eligibility
paperwork:
- Fix the account's public name (still "TravelAgent" → NIGHTSHIFT, Settings → Business → Public
  details) BEFORE creating the canonical link — the link carries the public name and a Stripe
  judge will see it.
- Create THE canonical Payment Link once, at the agent's chosen price ($19 — it already priced the
  product, narrative intact). **Reuse this exact link for every sale all day** — organizer revenue
  tracking follows the submitted link; minting new links breaks it. The stripe driver's
  `create-link` returns the canonical link for the listed product instead of minting fresh ones.
- Create a SECOND restricted key for organizers: Balance=Read, Charges=Read, everything else None.
  Submit team name + link URL + that rk_ key. Never our working keys, never sk_.
- Prove it: one $1–$5 live transaction from a team-external card if possible, else a live
  transaction refunded immediately.
- Stretch only (was primary): Dodo MoR driver behind the same seam as a second rail.
- pytest re-run against live-mode config (suite hard-refuses live keys for mutation tests — keep
  that guard); Playwright checkout re-run on the live storefront.

**Out of scope:** payouts/withdrawals; subscriptions; refund automation beyond the policy's refund rule.

### US-1.2 — Every Sale Lands in the CRM Ledger **[ANIRUDH → seam only; SURYA wires CRM]** *(1.5h, 1h A + 0.5h S)*
When a payment completes, the sale appears in the company's books: a small poller/webhook receiver
(Anirudh, on Render) detects `paid` links and exposes them via `pay.py sales --json`; Surya's side
consumes that JSON and records each sale in `blocks/crm/code/crm.py` as a project moved to
`delivered` with `amount` set — so the EXISTING dashboard shows revenue with no new UI. This is
the lane seam working exactly as designed: Anirudh never touches `crm.py`; Surya never touches `pay.py`.
- Anirudh: webhook receiver (MoR events if available, else polling) — self-contained, on Render.
- Surya: a scheduled task (via the existing `scheduled-tasks` block) polls `pay.py sales --json`
  and writes CRM projects; idempotent on link-id.
- pytest both sides: sales JSON shape (A); dedup + CRM insert (S).

**Out of scope:** invoicing, tax, multi-currency reporting.

### US-1.3 — When Policy Can't Decide, the Company Hires a Human **[SURYA]** *(3h)*
When the approver verdict is `escalate`, the labor block (`blocks/labor/`) posts the question to
Terac's expert-labor API, a verified human answers, payment to that human is released automatically
on verified completion, and the answer is written back into `question.answer` — the taskrunner
consumes it like any other answer. The company just bought human judgment and expensed it: the
Terac charge is recorded in the CRM ledger as a cost event, shown next to revenue.
- New block: `blocks/labor/` — `block.md` declares `TERAC_API_KEY`; `code/labor.py` CLI
  (`post`, `status`, `collect`); `skill/labor.md`; `SETUP.md`.
- **Fetch current Terac MCP/REST docs at 8:30am before coding** — the exact endpoint shapes are
  unverified from this repo; the story is blocked on docs, not guesses.
- Escalation is bounded by policy (US-0.2): max spend per question, max open escalations.
- **Guidebook (8/15): Terac MCP usage is REQUIRED to submit the project at all**, and the judged
  criterion is a measurable before/after from real human input (expert judgment qualifies). So in
  addition to the escalation path, launch ONE cheap General-Population study (their recommended
  fastest mode) — e.g., product-page copy or price-framing test — record the before, apply the
  result, record the after. That artifact goes in the submission.
- **Blocker (8/15 morning):** Terac credit redemption fails on their Twilio phone verification —
  retry later / teammate redeems. Driver is built docs-first against the stub until the key works.
- Fallback if Terac turnaround is slow live: pre-seed one real escalation during the morning so the
  demo shows a completed hire with timestamps.
- pytest: escalate → post → mock-complete → answer written back → consume; ledger shows the expense.

**Out of scope:** Terac as production/COGS labor; multi-expert workflows; disputes.

### US-1.4 — The Loop Leaves the Laptop **[SURYA]** *(2h)*
When Surya closes his laptop lid, the company keeps running: the taskrunner loop + approver tick
run in a Superserve persistent microVM, state (tasks.json, brain, CRM db) survives restarts, and
the dashboard still reflects live state. `blocks/taskrunner/code/start-taskrunner.sh` (caffeinate
+ PID lock — a laptop script) is replaced as the runtime, not modified.
- **Fetch current Superserve docs before provisioning** — API surface unverified from this repo.
- `block.md`-style manifest declares `SUPERSERVE_API_KEY`; deploy script lives in Surya's lane.
- Demo-day fallback (recorded in the risk table): if Superserve provisioning fails by 11:30, run
  the loop on the laptop with the existing script and say so on stage — honesty per Scope Rules.
- Verification: kill/restart the VM; loop resumes; a `waiting_owner` task created before the
  restart is answered after it.

**Out of scope:** autoscaling, multiple VMs, Superserve for the storefront (that's Render).

### US-1.5 — The Agent Ships Its Product **[SURYA picks/builds · ANIRUDH lists]** *(1.5h, parallel)*
When the goals-block agent (running under the autonomy contract) picks the product, writes the
copy, sets the price (all within the policy's domain: digital, <$25, instant delivery, for
founders/builders), and produces the deliverable file, the storefront updates — the agent's output
lands in `product.json` + a delivery asset URL, Anirudh's storefront re-renders it, and
`pay.py create-link` prices it. A stranger can now buy an agent-chosen, agent-priced, agent-built product.
- The product decision itself passes through the gate: the agent proposes via `--finalize deploy=…`,
  the APPROVER approves it against policy. Audit trail entry #1 for the demo.
- Delivery = instant link on the thank-you page (kept dead simple).
- Playwright: storefront shows agent content; full buy path green by 12:00.

**Out of scope:** product iteration/AB tests; more than one product live at a time.

### Checkpoint 1 — 12:00 merge. **Gate: a live-money purchase works end-to-end. If not green, Sprint 2 starts anyway on test mode and US-1.1 becomes the only Sprint 2 [ANIRUDH] item.**

---

## Sprint 2 — 12pm–2pm: The Autonomy Spine, End-to-End

> **Theme:** By 2:00pm the full loop has been demoed ONCE, on record: goal → tasks → gate →
> approver (→ Terac if escalated) → build → list → outbound → stranger pays → CRM shows revenue.
> Nothing new is added until this is on video.

### US-2.1 — One Unbroken Autonomous Run **[SURYA drives · ANIRUDH observes money side]** *(2h)*
When the goal agent is given the objective "make the first sale today," it plans and creates dated
tasks (per `blocks/goals/skill/goal.md` — it steers, taskrunner executes), the taskrunner works
them, every `--question`/`--finalize` stop is answered by the approver with a policy citation, at
least one decision escalates to a Terac human, the product is listed and sold, and the sale
appears in the CRM. Screen-recorded start to finish; this recording is the demo's backbone and the
proof for the win condition.
- No team member touches a keyboard during the run except to start it.
- Every stop in the run maps to a line in `decisions.jsonl` — count them on stage.
- If the live stranger-sale hasn't happened yet, the run ends at "listed + outbound sent" and the
  sale is captured whenever it lands (the loop keeps running on Superserve).

**Out of scope:** editing the recording beyond trims; multiple parallel goals.

### US-2.2 — The Audit Trail a Judge Can Read **[PRAVIN — reassigned 8/15, brief in `PRAVIN.md`]** *(1h)*
When a judge opens the dashboard (existing `dashboard` block, read-only), they see — alongside the
kanban and CRM revenue — the approver's decision ledger: every question asked, the policy clause
cited, the verdict, who answered (agent vs. Terac human, with the expense), and timestamps. "No
human approved any step" becomes verifiable, not claimed.
- Implementation: the dashboard reads `decisions.jsonl` + CRM events; keep it minimal, matching the
  dashboard's no-build-step ethos.
- Playwright: ledger renders; entries match the pytest-seeded fixtures.

**Out of scope:** filtering/search; write actions from the dashboard (it stays read-only).

### US-2.3 — Two Sales Channels, Both Honest **[ANIRUDH]** *(1h)*
When the agent's outbound (email via the existing `email-operator`/`prospection` path, gated
through the approver like everything else) reaches a real stranger, they can complete a purchase
from the link on their own device; and when someone in the room scans the QR, the identical flow
closes the guaranteed-floor sale. Both channels tested with Playwright against the live storefront;
both stated openly on stage per the locked decision.
- Outbound content itself passes the gate: `--finalize email=…` → approver checks policy's spam/rate clause.
- In-room QR printed/displayed by 2pm.

**Out of scope:** paid ads; bulk sending beyond the policy rate limit.

### Checkpoint 2 — 2:00 merge. **Gate: the US-2.1 recording exists. If not, Sprint 3 is cancelled and 2–4pm is spent making it exist.**

---

## Sprint 3 — 2pm–4pm: Tier 2/3 Stretch (only if the spine is green)

> **Theme:** Visible, cuttable polish. Every story here can be dropped at any minute with zero
> damage to the demo. Priority order as listed.

### US-3.1 — Whop Storefront Listing **[ANIRUDH]** *(1h)*
When a buyer browses the company's Whop store, the agent-chosen product is listed there too
(create-product + checkout-configuration API) and a purchase through Whop lands in `pay.py sales
--json` like any other — a second live shelf, same seam. Fetch current Whop API docs first.

**Out of scope:** Whop community features; migrating the primary rail.

### US-3.2 — Lovable Landing Page, Agent-Generated **[PRAVIN directs — reassigned 8/15]** *(1h)*
> Guardrail: the AGENT generates the page (brief written from the brain's positioning, gated
> through the approver); Pravin directs and judges the output, never hand-designs it — a judge
> will probe "did a human make this?". Lovable credit code is in HACKATHON.md Guidebook facts.
When a visitor hits the company's landing page, they see a page the AGENT generated via Lovable
(brief written by the agent from the brain's positioning, gated through the approver), linking to
the storefront. Judge-relevant: Roman Yanushevskyi (Lovable) is judging.

**Out of scope:** custom domain; replacing the Render storefront (landing links to it).

### US-3.3 — High-Frequency Tick on Pioneer/Fastino **[SURYA]** *(1h)*
When the approver's poll loop ticks (the highest-frequency, lowest-stakes call in the system), it
runs on Pioneer/Fastino's Claude-compatible endpoint via a one-line base-URL swap — with the
policy-decision calls themselves staying on Anthropic models. Demonstrates cost-aware routing.
Fetch current Pioneer/Fastino docs first; if the endpoint isn't drop-in as advertised, revert in
one line and cut the story.

**Out of scope:** routing any policy-deciding call off Anthropic models.

### US-3.4 — Outbound over Linq (iMessage/RCS/SMS) **[ANIRUDH]** *(1h)*
When the agent's outbound plan includes a phone-first prospect, it sends the (approver-gated)
message via Linq's messaging API and the reply lands where the agent can read it. Fetch current
Linq docs first; consent/anti-spam clause in policy applies.

**Out of scope:** voice; bulk SMS.

### Checkpoint 3 — 4:00pm **FREEZE. No new code after 4pm — only config, content, and the demo.**

---

## Sprint 4 — 4pm Freeze → Submission (upload 6:30, LOCK 6:45) → Judging 7–8pm

> **Theme:** Rehearsal and evidence. The code is done; the story is the work now.

### US-4.1 — The Demo Itself **[BOTH]** *(2h)*
When the judges watch the 3–4 minutes, they see the thesis, the live system, and the proof, in
this order — rehearsed twice, timed, with every screen pre-loaded:
1. **The hole** (30s): show `update_task.py --question` → `waiting_owner`. "Sunday's one deliberate
   human dependency. A zero-human company can't wake the owner."
2. **The swap** (45s): approver answers at the same interface — diff view proving zero changes to
   existing blocks; the policy file on screen.
3. **The escalation** (30s): a real Terac hire with timestamps and the expense in the ledger.
   "When it needs a human, it buys one — and expenses it."
4. **The run** (60s): the US-2.1 recording, compressed — founding interview answered by an agent,
   goal → tasks → gates → sale.
5. **The money** (30s): live dashboard — CRM revenue from real strangers + in-room QR sales, both
   channels named openly. State the win condition and whether it was met.
6. **Close** (15s): "No employees. No owner in the loop. The gates never came down — we changed
   who stands behind them."
- Also in this sprint: export/print the decision ledger; final security sweep of the public repo;
  in-room QR sales floor active the whole time; laptop + hotspot + backup recording redundancy.
- **Pravin owns the submission package and the upload: target 6:30, hard lock 6:45.** The
  submission must show Terac MCP usage and the before/after artifact (US-1.3) or it is ineligible.

**Out of scope:** new features, restyling, refactors — anything that is code.

---

## Delta Summary (what this plan adds to Project Sunday)

| Addition | Sprint | Lane | Purpose |
|---|---|---|---|
| `blocks/approver/` (code + skill + policy) | 0 | Surya | Policy-bound agent behind the existing gates |
| `company/notes/policy.md` (via founding) | 0 | Surya | The written law every autonomous "yes" cites |
| Self-founded Company Brain | 0 | Surya | Removes the last human dependency (the interview) |
| `blocks/payments/` (`pay.py`, 3-command seam) | 0–1 | Anirudh | MoR-first real-money rail behind a stable interface |
| Storefront + webhook receiver (Render) | 0–1 | Anirudh | Where strangers buy; where paid events land |
| `blocks/labor/` (Terac) | 1 | Surya | The company hires and pays verified humans on escalation |
| Superserve runtime | 1 | Surya | The loop becomes a company, not a laptop script |
| CRM sale-recording scheduled task | 1 | Surya | Revenue in the existing books/dashboard |
| Decision-ledger panel on the dashboard | 2 | Surya | The audit trail judges can read |
| Whop / Lovable / Pioneer / Linq | 3 | split | Visible, cuttable Tier 2/3 |

**Existing files deliberately NOT modified:** `blocks/taskrunner/code/update_task.py`,
`blocks/crm/code/crm.py`, all 10 built blocks. That restraint is the pitch.

## Risk Table

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Sponsor keys late/broken at 8:30am | Med | High | Whole flow already green on Stripe test mode (US-0.4); env swap when keys land |
| MoR (Dodo/Whop) API differs from expectations | Med | High | Docs-first rule; Stripe live is the second rail behind the same seam |
| Terac turnaround too slow for a live escalation | Med | Med | Pre-seed one real escalation in the morning (US-1.3); show completed hire with timestamps |
| Superserve provisioning fails | Med | Med | Fall back to `start-taskrunner.sh` on the laptop and say so on stage |
| No stranger buys by demo time | Med | High | In-room QR sales floor is the stated, honest guaranteed floor (locked decision #5) |
| Approver approves something it shouldn't | Low | High | Policy hard-NOs + spend ceilings + table-driven pytest cases (US-0.2); everything logged |
| 12pm payment gate missed | Low | High | Sprint 2 proceeds on test mode; US-1.1 becomes the only money-lane task until green |
| Secret leaks in the public repo | Low | Critical | Blocking security gate every story; names-only manifests; final sweep in Sprint 4 |
| Live demo network failure | Med | Med | US-2.1 recording is the backbone; hotspot backup; dashboard runs local |
| Terac credit redemption blocked (their Twilio phone-verify issue, seen 8/15 am) | High | High (Terac MCP is REQUIRED to submit) | Retry later; any teammate can redeem; driver built docs-first against stub; escalate at their booth 10:20–10:45 |
| Canonical Payment Link regenerated mid-day | Low | High (organizer revenue tracking misses it) | Link created once in US-1.1, stored in `product.json`/env, `create-link` returns it; if regeneration is forced, notify organizers immediately |

## Backlog (Out of Scope)

- Refund/dispute automation beyond the policy's single refund rule
- Multiple products / pricing experiments / A-B tests
- BAND multi-agent coordination and Replay time-travel debugging (Tier 3, not reached unless everything else is green)
- Payout/withdrawal handling; accounting, tax, invoicing
- Voice channel (Linq voice), bulk outbound beyond policy rate limits
- Sandboxo / Solari — **API surfaces unverified; explicitly not planned rather than invented**
- SignalFire, 1517 Fund, Bagel Fund, SOLO, Interview Cake — not integrations (VC/community/education); never padded in
- Multi-goal parallel autonomy; approver hierarchy (approver-of-approvers)
- Personal mode of Project Sunday; upstreaming the approver block to the kit proper (post-hackathon PR)
