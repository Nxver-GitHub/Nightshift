# Terac "Zero-Human Company" Hackathon — build plan

**Team:** Surya + Anirudh + Pravin · **Event (per organizer guidebook):** doors 8:30am · keys/credits Notion doc at opening ceremony 9:15–9:45 · hacking begins 10:45 · **submissions LOCK 6:45pm (our upload target: 6:30)** · judging 7–8pm · **Base:** fork of Project Sunday

> ## 👉 START HERE: [`Agents/Release Plan/hackathon-release-plan.md`](Agents/Release%20Plan/hackathon-release-plan.md)
>
> That file is the **single source of truth**: 5 sprints, 20 user stories, every story tagged
> **[SURYA]** or **[ANIRUDH]** with hour estimates, Definition of Done, dev-process rules, the
> credential checklist, the demo script, and the risk table.
>
> **Anirudh — your Claude should read that file first and start at US-0.4.** You need no prior
> knowledge of this repo; your stories are self-contained.

## Onboarding to the codebase fast (both Claudes)

This repo ships a **knowledge graph of itself** in `graphify-out/` — 285 nodes, 484 edges, 27
communities, built from AST extraction plus semantic extraction over every doc.

**Do not read the whole repo to orient. Query the graph instead:**

```bash
graphify query "how does the taskrunner gate work?"     # BFS, broad context
graphify query "what calls add_task.py?" --dfs           # DFS, trace one path
graphify path "goal agent skill" "Finalization gate"     # shortest path between two concepts
graphify explain "The autonomy contract"                 # plain-language node explanation
```

If the `graphify` CLI isn't installed (`uv tool install graphifyy`), read `graph.json` directly with
NetworkX — nodes carry `label`, `source_file`, `source_location`, `community`; `links` carry
`relation`, `confidence`, `confidence_score`.

- **`graphify-out/GRAPH_REPORT.md`** — start here. God nodes, cross-community bridges, surprising
  connections, the 9 hyperedges, and the community map.
- **`graphify-out/graph.html`** — open in a browser for the visual map.
- **`graphify-out/graph.json`** — machine-readable, repo-relative paths, portable.

**Three findings from it that shape this hackathon** (so you don't rediscover them):
1. **`taskrunner` is the hub.** Everything funnels into `tasks.json` via `add_task.py`. It depends on
   nothing; `email-operator`, `goals`, `health`, and `prospection` all depend on it.
2. **One safety invariant repeats under five names** across five blocks (hyperedge: *"the owner's-yes
   safety floor"*) — taskrunner's finalization gate, email-operator's "never irreversible on your
   own", prospection's approve-before-send, scheduled-tasks' review mode, health's red-becomes-a-ticket.
   **That hyperedge is what this hackathon project inverts.**
3. **`goals` is the strategy layer above taskrunner, not a rival orchestrator** — `goal.md:20-21`:
   *"You steer, you don't execute."* Its autonomy contract (`goal.md:13-17`) is the one place the
   safety floor is already deliberately inverted, and it's the seed of the approver agent.

*Regenerate after big changes:* `/graphify . --update`

---

## Working agreement (both lanes)

| Rule | Detail |
|---|---|
| **Lanes** | Surya → `blocks/approver/`, `blocks/labor/`, `kit/` on `surya/autonomy`. Anirudh → `blocks/payments/`, storefront, hosting on `anirudh/payments`. Pravin → `blocks/dashboard/`, `demo-assets/`, submission package on `pravin/audit` (brief: `PRAVIN.md`). **Never edit a file outside your lane** — note it at the checkpoint and let the owner change it. |
| **Merges** | `main` only at checkpoints: end of tonight · 12:00 · 14:00 · 16:00 freeze. |
| **95% rule** | If Claude is not 95%+ confident in a decision, output, or answer affecting this project, it stops and runs `grill-me`. Never guess. |
| **Story start** | Claude runs `grill-me` at the start of every user story to pin scope before writing code. |
| **Models** | Fable 5 = PM/planning · Opus 5 = complex/long/architectural · Sonnet 5 = small/token-efficient. **Never Haiku.** |
| **Docs first** | Fetch current official docs before integrating any sponsor API. Never rely on training data for API shapes. |
| **Tests** | pytest for the Python CLI blocks · Playwright for anything with a web surface. Both are part of DoD. |
| **Security gate** | Blocking, every story: no secrets/keys in git, no crypto material exposed, no sensitive data in logs, no backdoors, no prompt-injection or phishing vectors. Must be clean for a public repo. |
| **Code quality** | Modular, small files, **commented inline** — this codebase is judged and publicly read. |
| **No doc sprawl** | Do not create extra markdown files. These two are the only planning docs. |

---

## Positioning — what the product IS (both of us pitch this, identically)

**This is not a company-files generator — files are copyable and have no moat. The product is the
authority layer: giving an agent a company credit card with rules written on it (`policy.md`), a
tamper-evident ledger of every decision (`decisions.jsonl`), and a human-judgment supply chain for
when the rules run out (Terac escalation).** Stripe won by absorbing the scary part of payments
behind seven lines of code; we absorb the scary part of agent autonomy behind one gate. The brain,
the blocks, the markdown — that's runtime state, the way Liquid templates are Shopify's state.
Demo opens with the fear ("would you give an agent your credit card?"), then the primitive
(gate → policy → ledger → escalation), then the live transaction. The founding interview is not
file generation — it is the onboarding wizard of an agent-authority platform.

## The thesis (say this in one breath)

The base kit installs an agent-run company. Its architecture has one deliberate
human dependency: **every block stops and asks the owner** — `waiting_owner`, `pending_validation`,
review mode. That is the "owner's-yes safety floor."

A zero-human company cannot wake the owner. **So we did not remove the gates — we replaced who
stands behind them.**

1. Agents act autonomously under the existing autonomy contract.
2. Ambiguous → an **approver agent** decides against the brain's *written* policy.
3. Policy genuinely can't decide → the company **hires a verified human from Terac**, pays them
   automatically on verified completion, and proceeds.

> **The company has no employees and no owner in the loop. When it needs a human, it buys one —
> and expenses it.**

And the last human dependency, the founding interview (`kit/interview/company.md`), is answered by
an agent. The company founds itself.

---

## Win condition (falsifiable, state it on stage)

> A real human who is not on our team paid real money for a product an agent chose, priced, built,
> listed, and delivered — and **no human approved any step**. An approver agent did, with an audit
> trail.

---

## Decisions locked

| # | Decision |
|---|---|
| 1 | **Keep the gates, swap the approver.** Human "yes" → policy-evaluating agent. Not a guardrail removal. |
| 2 | **Constrained autonomy.** We fix the domain ("digital product, <$25, instant delivery"); the agent picks product, copy, price. |
| 3 | **Rail (FLIPPED 8/15 per guidebook):** Stripe individual account is the PRIMARY live rail — organizers track revenue via a read-only restricted key on OUR Stripe account, and "Best Overall Agent-Run Company" eligibility requires collecting through it. Revenue on Dodo/Whop is invisible to them. MoR demoted to stretch. |
| 4 | **Product:** agent-generated digital work product for founders/builders. Terac is the *escalation path*, never the COGS (experts bill $60–220/hr; that kills unit economics and the quants in the room will notice). |
| 5 | **Customers:** live outbound to real strangers all day **and** in-room sales as the guaranteed floor. Say both out loud — transparency about the backup is what makes the primary claim believable. |
| 6 | **Split:** Surya owns the autonomy spine (needs repo knowledge). Anirudh owns the money/storefront surface (needs none — he has zero commits here). |
| 7 | **Scope:** Tier 1 + Tier 2 only. Seven working integrations beats fifteen on a slide. |

---

## Integration map

Every integration is a **block that declares credential names, never values** (repo rule:
*"No secret in git — ever"* — `blocks/connectors.md`).

### Tier 1 — thesis-critical
| Sponsor | Role | Env var (fill tomorrow) |
|---|---|---|
| **Terac** | Buys human judgment when policy can't decide. Host's product, sits exactly where the repo has a hole. **Guidebook: Terac MCP usage is REQUIRED to submit at all** — plus a "measurable before/after from real human input" criterion (expert judgment qualifies; they push General-Population studies as fastest). | `TERAC_API_KEY` |
| **Superserve** | Persistent microVMs for long-horizon agents. `start-taskrunner.sh` uses `caffeinate` + a PID lock — it is a laptop script. This makes the loop a company. | `SUPERSERVE_API_KEY` |
| **Payment (Stripe live)** | The win condition. Primary rail per guidebook eligibility: one canonical Payment Link submitted to organizers (same link for EVERY transaction — new links mid-day break their revenue tracking) + a second restricted key (Balance/Charges Read, all else None) submitted for tracking. Never submit our working rk_/sk_ keys. | `STRIPE_API_KEY` |

### Tier 2 — visible, cheap, cuttable
| Sponsor | Role | Env var |
|---|---|---|
| **Whop** | Storefront the agent creates and lists into | `WHOP_API_KEY` |
| **Lovable** | Agent-generated landing page. *Roman Yanushevskyi (judge) is an AI Engineer at Lovable* — 30 min, done well. | — (UI) |
| **Render** | Hosts dashboard + payment webhook receiver. Prize note: "Best use of Render" requires **Render Workflows** specifically — static hosting alone doesn't qualify. | `RENDER_API_KEY` |
| **Dodo/Whop (MoR)** | Demoted from primary (guidebook flip, Decision 3): second rail only, behind the same `pay.py` seam. Organizers can't see MoR revenue. | `DODO_API_KEY` / `WHOP_API_KEY` |

### Tier 3 — only after freeze is safe
**Pioneer** (Claude-compatible endpoint, one-line model swap for the tick loop — ~10 min) ·
**Linq** (iMessage/SMS customer channel; `goals` already says "multi-channel by default") ·
**BAND** (agent-to-agent bus; our 10 blocks currently coordinate through a JSON file) · **Replay**

### Not integrations
**SignalFire · 1517 · Bagel Fund · SOLO · Interview Cake** — VCs, funds, education. Do not pad.

---

## Guidebook facts (organizer Notion, read 8/15 morning — trust these over older assumptions)

**Tracks we enter** (multi-track allowed, more tracks = better odds): Best Overall Project ($2,500) ·
Best Overall Agent-Run Company ($2,500, requires Stripe rail + real revenue) · Best use of Superserve
($1,000 — must be "core part of stack"; US-1.4 qualifies) · Pioneer ($500 — US-3.3; bonus for Fastino
GLiNER models) · stretch: Linq ($1,500 — biggest sponsor pot; Agent Pay settles to our own Stripe) ·
Render ($500 credits — only if webhook moves to Render Workflows).

**Prize-eligibility mechanics (Anirudh executes, Surya's account):**
1. Stripe individual account (no business verification needed for hackathon).
2. ONE Payment Link, created once, submitted to organizers, reused for every sale.
3. A dedicated read-only restricted key: Balance=Read, Charges=Read, everything else None.
4. Submit: team name + link URL + that rk_ key. Never the working keys, never sk_.

**Credits redemption (at/after 9:15 ceremony):** Superserve = plain signup, no card ·
Lovable code `COMM-THE-4G9T` (Pro Plan 1 monthly, cancel after) · Pioneer promo `ZeroHumanHack0826` ·
Replay code `HACKATHON` · Render credits portal (link in guidebook) · Terac referral link in guidebook.
**KNOWN BLOCKER:** Terac credit redemption failing on their Twilio phone verification (8/15 morning) —
retry later or a teammate redeems; terac driver is built against docs + stub until the key works.

**Judges (corrected):** two YC S26 CTO pairs (Touchmark, Olam) — Roman Yanushevskyi is Touchmark CTO
/ Lovable AI Engineer / ex-Citadel · Shubh Mittal (MTS @ xAI) on Best Overall. **Tosh Rayadhurgam
(Head of Advanced AI @ Stripe)** and a DeepMind Group PM judge Best Agent-Run Company + Render.
The Stripe-rail story and the Lovable page each have a judge in the room.

---

## Tonight (Surya, solo — no credentials required)

Build the adapter layer. Tomorrow is `export KEY=...`.

- [ ] `blocks/approver/` — poll `waiting_owner` → evaluate vs written policy → `update_task.py --consume-question`. **The thesis. Zero external deps.**
- [ ] `blocks/payments/` — one CLI, three drivers (dodo | whop | stripe) behind `PAYMENT_PROVIDER`
- [ ] `blocks/labor/` — Terac adapter: request expert → poll → pay on verified completion
- [ ] `kit/interview/agent-founder.md` — the founding interview, answered by an agent
- [ ] `ANIRUDH.md` — his brief, so 8:30am is a 5-minute handoff not an hour
- [ ] **Sleep.** 10 hours on-site tomorrow.

### The seam (zero merge conflicts)
Anirudh touches **only** `blocks/payments/` drivers and storefront/hosting.
Surya touches **only** `blocks/approver/`, `blocks/labor/`, `kit/`.
Contract, in the repo's existing `crm.py` idiom:

```
pay.py create-link --title "…" --amount 20 --currency usd   → URL
pay.py status --link-id …                                   → paid | unpaid
pay.py sales --json                                         → closed sales
```

---

## Tomorrow

| Time | Surya | Anirudh |
|---|---|---|
| 8:30 | Check in. Keys/credits arrive via Notion doc at the 9:15–9:45 ceremony; fill env after. Redeem credits (see Guidebook facts). | Read `ANIRUDH.md` |
| 9–12 | Terac live · agent-run founding interview · start live outbound | Whop storefront · Lovable page |
| **12:00** | **PAYMENT MUST BE GREEN.** Real card, real charge, recorded in `crm.py`. | Render deploy |
| 12–2 | Wire Superserve runtime | Dashboard shows live revenue |
| **2:00** | **Full spine demoed end-to-end, once.** No stretch item starts before this. | |
| 2–4 | Tier 3 only if spine is green | |
| **4:00** | **HARD FREEZE.** No new code. | |
| 4–6:30 | Rehearse · audit trail · rehearse again. Pravin finalizes + uploads the submission by **6:30** (lock is 6:45). | |

**Freeze at 4 even if demos are at 7.** Teams lose this format by shipping at minute −5.

---

## The audit trail (this is what wins, not the product)

Have this on screen, ready:
- Every `waiting_owner` question the system raised
- The approver agent's decision + the policy line it cited
- Every Terac escalation, the expert's verdict, and what it cost
- The outbound the agent sent, unedited
- The transaction

The judges — two YC S26 CTO pairs, an xAI MTS, a Citadel quant, a Lovable engineer — will not ask
"is it cool." They will ask **"did a human write that?"** The answer must be a flat no, and the
trail must prove it.

---

## Known risks

| Risk | Mitigation |
|---|---|
| Stripe live activation held for review | MoR (Dodo/Whop) is primary. Stripe is second rail. |
| Sponsor keys arrive late / rate-limited | Every integration is behind a driver interface with a stub; demo degrades, never breaks. |
| Agent picks a product nobody buys | Domain constrained + in-room floor (track *iii*). |
| Judge asks "did a human approve this?" | Audit trail, above. Decide now the answer is no; build so it stays true. |
| Scope creep to 15 sponsors | Tier 3 is post-freeze-safe only. |
