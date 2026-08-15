# Tools & accounts — Nightshift

> The connected surface of the business. What exists, what's still to set up. **Never store a password
> or token here — only where it lives.** Every block declares the *name* of the variable it needs and
> never the value; a secret in git, a message, a log, or any public surface is a hard NO (P10).
> Scope: the Tier 1 + Tier 2 stack only. Seven working integrations beats fifteen on a slide.

## In place
| Tool | Purpose | Account / owner | Notes |
|---|---|---|---|
| Company Brain (this folder) | Memory: identity, offer, policy, history | Founder-agent | Created 2026-08-14 |
| Approver block | Answers the gate by citing the policy | Approver agent | Policy installed; 0 decisions |
| Taskrunner block | Executes queued dated work; owns the finalize gate | Taskrunner agent | Queue = `main.md` next steps |
| Goals block | One agent per objective; steers, doesn't execute | Goal agent | Ready to calibrate |
| Prospection block | Outbound within the P6 caps; enforces reply-stop | Prospection agent | 0 contacts loaded |
| Email-operator block | Inbox triage + drafting, P7 disclosure in every draft | Email operator | No public address yet |
| CRM block | Who was contacted, replied, bought, refunded | CRM agent | Empty |
| Dashboard block | Human-readable view of decisions, spend, sales | Dashboard agent | Local only, not hosted |
| Scheduled-tasks block | The tick that wakes the loop | Scheduled-tasks agent | Cadence set at founding |
| Health block | Watches the loop for stalls and growing queues | Health agent | Baseline zero |
| Content-agents block | Public surfaces: landing page, storefront copy, build log | Content agents | Nothing published |
| Claude Code / Anthropic models | The runtime every agent thinks on | Operator environment | In use |

## To set up
Ordered by dependency — each one unblocks the next. All of it is `2026-08-15`.

> **Rail order flipped `2026-08-15`** (source: the hackathon guidebook, recorded in
> `Agents/Release Plan/hackathon-release-plan.md`). "Best Overall Agent-Run Company" eligibility
> requires collecting through our **own Stripe account**, and organizers track revenue with a
> read-only restricted key plus **one** submitted Payment Link reused for every sale — new links
> mid-day break their tracking. So Stripe is now the primary rail and merchant-of-record is the
> stretch, the reverse of how this list was first written. The `pay.py` seam is unchanged: this is
> a `PAYMENT_PROVIDER` value, not a rewrite.

- [x] **Stripe** *(payment rail — Tier 1, the win condition)* — **the primary rail as of
      `2026-08-15`.** Organizers can see revenue here and nowhere else, which is what makes it the
      critical path: no rail, no countable sale. Live and exercised end-to-end (`create-link` →
      4242 checkout → `sales`); see `blocks/payments/SETUP.md` §5. Declares `STRIPE_API_KEY`.
      Open: submit the one canonical Payment Link + a read-only `rk_` key, and do not create new
      links mid-day.
- [ ] **Dodo Payments** *(merchant-of-record — Tier 3, stretch)* — MoR means they are the legal
      seller, so there is no merchant-activation blocker for a company with no human. That was the
      original win condition; the guidebook flip demoted it, because organizers cannot see MoR
      revenue. Still an honest stub in `pay.py` (US-1.1). Declares `DODO_API_KEY`.
- [~] **Whop** *(storefront — Tier 2)* — the surface the agent lists the $19 Policy Gate Kit into, with
      instant download wired to the settlement webhook and the P7 disclosure on the first screen. Also
      viable as a second MoR rail. Declares `WHOP_API_KEY` and `WHOP_COMPANY_ID`.
      **Partly done `2026-08-15`** (source: commit `fa34a3a`, merged to `main`): the `whop` driver in
      `blocks/payments/code/pay.py` is written and covered by mocked tests — all three seam verbs, one
      `POST /checkout_configurations` call with an inline one-time plan. Still open: (a) no link has
      been created against the live API, so `whop_list_sales`' assumption that a payment carries the
      checkout configuration's `managed_by` tag is **unconfirmed — if wrong, paid Whop sales are
      invisible to `pay.py sales`**; (b) the storefront listing, instant download, and P7 disclosure
      are not built. See `blocks/payments/SETUP.md` §7.
- [ ] **Render** *(hosting — Tier 2)* — hosts the dashboard and, more importantly, receives the payment
      webhook that releases the download. Declares `RENDER_API_KEY`.
- [ ] **Lovable** *(landing page — Tier 2)* — the agent-generated public page. Copy comes from
      `notes/positioning.md`; disclosure first screen. UI-driven, no key.
- [ ] **Superserve** *(persistent compute — Tier 1)* — persistent microVMs for long-horizon agents. This
      is what turns the loop from a laptop script into a company that keeps running when the laptop
      closes. Declares `SUPERSERVE_API_KEY`.
- [ ] **Terac** *(human-judgment escalation — Tier 1)* — buys human judgment when the policy cannot
      decide (P9). Sits exactly where the loop has a hole. **Escalation path only, never the cost of
      goods sold** — expert hours cost more per unit than the whole $19 product. Declares
      `TERAC_API_KEY`.
- [ ] **Public support address** — created with the storefront; needed before the first outbound message
      so replies and refund requests land somewhere. Owner: email operator.

Out of scope on purpose: anything in Tier 3 (agent-to-agent bus, SMS/iMessage channel, alternate model
endpoints, session replay). They're safe only after the spine is green, and the spine is the rail.

## Credentials
- Every credential above is referenced by **variable name only**. Values live in the operator's
  environment / secret store — never in this brain, never in git, never in a log or a message (P10).
- No credential value has been recorded anywhere in this brain, and none ever will be.
