# Pravin — your brief (read this first, ~5 minutes)

Welcome. You need zero prior knowledge of this repo. This file is everything.

## What this is

This repo IS a company — **Nightshift**, founded by an agent (see `company/founding-interview.md`),
competing in the Terac "Zero-Human Company" hackathon. The product we pitch is the **authority
layer**: an approver agent behind every safety gate (`blocks/approver/`), a written policy it
cites (`blocks/approver/policy/policy.md`), a tamper-evident decision ledger
(`decisions.jsonl`), and a human-hire escalation path (`blocks/labor/`). Never pitch it as a
file generator.

**Win condition:** a stranger pays real money for an agent-chosen product with zero human
approvals — and the audit trail proves it. **The audit trail is what wins, not the product.**
Your lane makes that trail visible.

## Your lane (branch `pravin/audit` — never edit outside it)

- `blocks/dashboard/` — the read-only dashboard
- Demo/submission assets (deck, QR poster, recording) — keep them in `demo-assets/` (new folder, yours)

Surya owns approver/labor/kit. Anirudh owns payments/storefront/hosting. **Never edit their
files** — if you need a change there, ask the owner at a checkpoint. Merge to `main` at
12:00, 14:00, 16:00 (hard freeze). **Submission upload: 6:30 PM sharp.**

## Task 1 — US-2.2: the audit trail a judge can read (do this first)

The dashboard (`blocks/dashboard/code/server.py`, 102 lines, stdlib-only Python) already serves
`index.html` plus JSON at `/api/tasks`, `/api/crm`, `/api/brain`. Paths come from env vars.

Add a **decision-ledger panel**:
1. `server.py`: new `/api/decisions` endpoint reading the approver's append-only ledger at
   `blocks/approver/code/decisions.jsonl` (path via env var `APPROVER_LEDGER`, same optional
   pattern as the others). Each line is JSON: task id, question, verdict, policy clauses cited,
   mode (`agent` or `human`), cost, timestamps.
2. `index.html`: render every decision — question asked, policy clause cited, verdict, **who
   answered (agent vs. hired human, with the expense shown)**, timestamp. The money shot is a
   `mode:"agent"` entry next to a `mode:"human"` entry: the company bought human judgment and
   expensed it.
3. This is where your UI/UX judgment matters: judges (YC CTOs, a Citadel quant, an xAI MTS)
   must *read* this in seconds. Design for skimmability, not decoration.

**Constraints:** no build step, no npm, no frameworks, no pip installs — static HTML + stdlib
Python only (repo-wide rule). Dashboard stays read-only. Playwright test proving the panel
renders seeded fixture entries is part of done.

## Task 2 — the submission package (yours end-to-end)

- Screen-record the full autonomous run when Surya drives it (~14:00) — this recording is the
  demo backbone.
- Build the submission deck + any brand assets. Your ChatGPT-image-gen + Figma workflow is
  welcome **here** — pitch materials are human-facing and don't touch the "no human built the
  product" claim.
- Print/display the QR poster for the in-room sales floor by 14:00.
- Own the submission upload: target 6:30 PM, hard lock 6:45 PM. Freeze is 16:00; 16:00–18:30 is
  your finalization window. The submission must show Terac MCP usage + the before/after artifact
  (organizer requirement — see HACKATHON.md "Guidebook facts") or the project is ineligible.

## Task 3 (stretch, only if 1–2 are green) — US-3.2 Lovable landing page

One judge (Roman) is an AI Engineer at Lovable. **Guardrail: the AGENT generates this page**
(agent writes the brief from the brain's positioning, the approver gates it) — you *direct* the
agent and judge the output; you do not hand-design it. A hand-made page destroys the narrative
that a judge will specifically probe.

## Process rules (non-negotiable, from HACKATHON.md)

- Run the `grill-me` skill at the start of each task to pin scope; also any time <95% confident.
- Tests before commit (pytest for Python, Playwright for web). Commit messages explain WHY.
- Security gate: no secrets/keys ever in git; `.env` files are Surya's alone — never create or
  commit one.
- No new markdown files beyond this brief and your assets.
- Orient via the knowledge graph, not by reading the repo: `graphify query "how does the
  dashboard work?"` (or read `graphify-out/GRAPH_REPORT.md`).
