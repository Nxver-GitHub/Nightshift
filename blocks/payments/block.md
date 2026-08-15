# payments

> The money seam. One CLI — three verbs — that every other block calls when the company needs to
> get paid. Provider-agnostic by construction: the rail is an env variable, not a rewrite.

## What it gives you
A company that can't take money is a hobby. This block installs `pay.py`: an agent (or the founder
at a terminal) says *"sell this, for this much"* and gets back a working hosted checkout URL in one
command. Later — from a scheduled task, a storefront, or an agent mid-loop — the same tool answers
the only two questions that matter afterwards: *did this link get paid?* and *what have we sold?*
It keeps no database. The payment provider is the ledger, and everything this tool creates is
tagged `metadata[managed_by]=sunday-payments` so it can find its own work through the API alone —
which means no drift between a local file and the account that actually holds the money. The rail
itself is a driver behind one interface: Stripe today, a merchant-of-record tomorrow, by changing
one environment variable rather than one line of business logic.

## What it needs
- **Tools / accounts**: Python 3 (stdlib only — no pip installs, no vendor SDK) and one payment
  account. Stripe test mode is enough to prove the whole path end to end.
- **Config the agent must fill**: `PAYMENT_PROVIDER` (`stripe` by default, later `dodo` or `whop`),
  `STRIPE_API_KEY`, `DODO_API_KEY`, `WHOP_API_KEY`. Names only — no value ever enters this repo,
  a config file, a log line, or an error message.
- **Depends on blocks**: none. This block stands alone on purpose; it is the seam other blocks call,
  so it must never call them back.

## What's in this block
- `code/pay.py` — the whole seam in one file. `create-link` (title + amount → checkout URL),
  `status --link-id` (prints `paid` or `unpaid`, exit 0 either way), `sales [--json]` (every paid
  sale across the links this tool created). Every HTTP call goes through a single `_request`
  function, which is why the tests run offline and why a new driver is a fill-in, not a refactor.
- `tests/test_pay.py` — deterministic pytest suite: driver selection, the documented Stripe call
  sequence and form parameters, amount validation, paid/unpaid logic, `sales --json` shape, and the
  proof that a missing key exits cleanly without opening a socket or echoing a value.
- `tests/test_pay_live.py` — the same claims against real Stripe **test mode**. Skips entirely
  without an `sk_test_` key, and hard-fails the whole run if it ever sees an `sk_live_` key.
- `SETUP.md` — install, verify, and the manual test-card checkout walkthrough.

## How the agent installs it
1. Copy `code/` into the founder's `command-center/payments/`.
2. Export the config in the founder's shell or secret manager — `PAYMENT_PROVIDER` and the one key
   for that rail. Never write a key into a file in the brain, never paste one into a task card.
3. Run the mocked suite (`pytest tests/ -q`) to prove the install, then the live suite with a test
   key to prove the account.
4. Start in review mode: create one link by hand with the founder watching, complete it with a test
   card, and confirm `status` flips to `paid` and `sales` shows it — before any agent is allowed to
   call `create-link` on its own.

## Safety
- This block **creates payment links and reads payment state. That is all.** It has no refund verb,
  no capture verb, no void verb, and it never touches payout settings, bank details, or account
  configuration. There is no code path in `pay.py` that can move money *out*.
- **Refunds and live-mode operations arrive with US-1.1, behind the approver gate** — a refund is an
  irreversible gesture and will require an explicit owner's yes (or a policy clause that names the
  gesture and its cap), exactly like every other irreversible action in this brain.
- Keys are read from the environment **at call time only**. They are never cached to disk, never
  printed, never included in an error message, and never logged. When the provider rejects a call,
  the operator sees the provider's own message and nothing else.
- Amounts are validated before any API call: positive, numeric, and under a hard per-link ceiling,
  so a miscalculating agent fails locally instead of publishing an eight-figure checkout page.
- The test suites refuse live keys. A key starting `sk_live_` stops the run at collection rather
  than skipping quietly — a silent skip is how a live key ends up in a test loop.
