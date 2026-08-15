# labor

> The last hole in the autonomy spine, filled. The approver answers what the policy covers and
> escalates what it doesn't — and an escalation used to mean *stop and wait for a human*. This block
> makes it mean *buy one*. Zero modification to `taskrunner` or `approver`.

## What it gives you
When a question reaches the approver and no clause covers it, the company doesn't go to sleep until
you wake up — it **hires one verified human for one decision** and carries on. The hired expert is a
substitute approver, never a worker: they read the exact question the taskrunner asked, return a
verdict and one paragraph of reasoning, and touch nothing else. Their answer lands in the two fields
a human owner would have typed (`question.answer`, `question.answered_at`), under the same lock, so
the taskrunner consumes it like any other answer — and it lands in the **same `decisions.jsonl`
ledger** as every agent decision, marked `mode: "human"` with what it cost. One ledger, two kinds of
entries: reading it shows exactly where the written policy decided and where the policy ran out and
the company paid for judgment. Every hire is capped by the policy's own per-action spend ceiling, so
the human-judgment supply chain obeys the same money clause as everything else the company buys.

## What it needs
- **Tools / accounts**: Python 3, the `taskrunner` and `approver` blocks already running. A human
  reachable by any channel (the `manual` driver), or a Terac account (the `terac` driver).
- **Config the agent must fill**: `LABOR_PROVIDER` (which rail supplies the human), `TERAC_API_KEY`
  (reserved for the terac driver), `APPROVER_LEDGER` (the approver's ledger — escalations are read
  from it, human decisions are appended to it), `APPROVER_POLICY` (its frontmatter carries the spend
  ceiling that gates every hire), `TASKRUNNER_TASKS` (the shared kanban), `LABOR_HIRES` (this
  block's own hire log). Names only; no values, no secrets.
- **Depends on blocks**: `taskrunner` (required), `approver` (required — this block has no queue of
  its own; it reads the approver's escalations).

## What's in this block
- `code/labor.py` — the interface: `pending`, `submit`, `collect`, `log`. It gates on money, opens
  one bounded hire, and writes the expert's verdict back at the same interface the approver uses.
- `tests/` — deterministic pytest suite, including a real `update_task.py --consume-question`
  round-trip proving the hired answer is drop-in.
- `SETUP.md` — install, the manual-driver drill end to end, and the terac fill-in.

## How the agent installs it
1. Install `taskrunner` and `approver` first; note the kanban, ledger and policy paths.
2. Copy `code/` into `command-center/labor/`.
3. Wire the config to the founder's environment — `LABOR_PROVIDER`, `APPROVER_LEDGER`,
   `APPROVER_POLICY`, `TASKRUNNER_TASKS`, `LABOR_HIRES`. Never hardcode a path or a secret into the
   scripts; `TERAC_API_KEY` lives in the environment only.
4. Agree the hire price with the founder **before** the first escalation, and check it against the
   policy's `per_action_spend_ceiling_usd`. If the founder wants to spend more per judgment, the fix
   is to change the clause with them — never to bypass the gate.
5. Start on `LABOR_PROVIDER=manual`: run one hire by hand, end to end, and read the ledger with the
   founder so they see the agent entry and the human entry side by side. See `SETUP.md`.

## Safety
- A hire buys **one bounded judgment, never task labor**. The expert answers a question; the
  taskrunner still performs every gesture, through the unchanged finalization gate. There is no path
  in this block that makes an outsider do the company's work.
- **The spend ceiling is not negotiable here.** A hire is an outgoing spend and is refused above the
  policy's `per_action_spend_ceiling_usd` (P2), whatever the justification — an autonomy layer that
  exempts its own supply chain from its own money gate has no money gate. No policy, no ceiling, no
  hire: this block refuses rather than inventing a default.
- **A rejection is a decision, not a retry.** An escalation the hired human rejects stays rejected —
  the block will not re-hire around an answer it dislikes, and it refuses to open a second hire on a
  question that already has one open, or to overwrite an answer the owner gave by hand.
- **No PII of the expert is stored anywhere** — not in the hire log, not in the ledger, not on the
  card. What is recorded is the verdict, the reasoning, the provider and the cost. The company is
  buying a judgment, not building a file on a person.
- **No secret ever goes into `--context`, a card, or the ledger.** The context is read by an
  outsider; treat it as public. Credentials, keys and customer data never leave through this block.
- Every hire is on the record: the decision in the approver's append-only ledger with `mode:
  "human"` and its cost, the answer labelled `[via hired expert]` on the card itself.
