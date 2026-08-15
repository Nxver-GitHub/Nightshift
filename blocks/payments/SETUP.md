# Payments — install & operate

> Written for someone who has never opened this repo before. You need Python 3 and a Stripe
> account. Nothing to `pip install` — `pay.py` is stdlib only, on purpose.
>
> Run every command below from the **repo root**.

## 1. Get a Stripe test key

1. Sign in at `dashboard.stripe.com`. Make sure the **Test mode** toggle (top right) is ON.
2. Developers → API keys. **Preferred: create a restricted key** (`rk_test_…`) named for this
   project with only — Products: Write · **Prices: Write** (a separate toggle, NOT covered by
   Products — without it link creation 403s) · Payment Links: Write · Checkout Sessions: Read — so the
   agent-held credential can't refund, see customers, or touch payouts. The full Secret key
   (`sk_test_`) also works.
3. Export it in your shell. It lives in your shell and nowhere else — never in a file in this repo,
   never in a commit, never pasted into a chat:

```bash
export STRIPE_API_KEY=sk_test_...        # your test key
export PAYMENT_PROVIDER=stripe           # optional; stripe is the default
```

If you accidentally paste a **live** key (`sk_live_`), the test suite will refuse to run at all.
That is deliberate. Rotate the key in the dashboard and export a test key instead.

## 2. Run the mocked tests (no key needed, no network)

```bash
uvx pytest blocks/payments/tests/ -q
```

Expected without a key: `27 passed, 4 skipped`. The 4 skips are the live suite waiting for a test
key. If the mocked 27 aren't green, stop — something is wrong with the install, not with Stripe.

## 3. Run the live tests (needs the `sk_test_` key)

```bash
export STRIPE_API_KEY=sk_test_...
uvx pytest blocks/payments/tests/ -q
```

Expected: `31 passed`. This creates a real product, price and payment link **in test mode** —
fake objects, fake money, safe to repeat. Delete them from the dashboard later if you like.

## 4. Create a link by hand

```bash
python3 blocks/payments/code/pay.py create-link --title "Nightshift Playbook" --amount 19 --currency usd
```

Prints the checkout URL and the link id (`plink_...`). Add `--json` if a script is reading it.
`--amount` is in **dollars** — `19` and `19.50` both work; the tool converts to cents for Stripe.

Check it hasn't been paid yet:

```bash
python3 blocks/payments/code/pay.py status --link-id plink_...
# -> unpaid        (exit code 0 — "unpaid" is an answer, not an error)
```

## 5. The 4242 checkout walkthrough (the morning step)

This is the part a unit test shouldn't fake: actually paying.

**By hand (2 minutes):**
1. Open the checkout URL from step 4 in a browser.
2. Email: anything, e.g. `test@example.com`.
3. Card number: `4242 4242 4242 4242` — Stripe's test card.
   Expiry: any future date (`12/34`). CVC: any 3 digits (`123`). ZIP: any (`12345`).
   Name: anything.
4. Click Pay. You land on Stripe's confirmation page.
5. Back in the terminal:

```bash
python3 blocks/payments/code/pay.py status --link-id plink_...
# -> paid

python3 blocks/payments/code/pay.py sales --json
# -> [{"link_id": "plink_...", "session_id": "cs_test_...", "title": "Nightshift Playbook",
#      "amount_usd": 19.0, "currency": "usd", "paid_at": "2026-..."}]
```

That round trip — link created, card charged, `status` flips, `sales` reports it — **is** the proof
the money path works. Nothing else in this block matters if that loop doesn't close.

**With Playwright**, if you're automating the demo: navigate to the checkout URL, fill the email
field, then fill the card fields (they sit inside Stripe's iframes — use Playwright's
`frame_locator` on the payment element), submit, and wait for the confirmation page. Then assert on
`pay.py status` from the same script. Keep this as a browser test, separate from
`blocks/payments/tests/` — the pytest suites there must stay runnable with no browser installed.

Other useful test cards (all with any future expiry / any CVC):
`4000 0000 0000 0002` declines, `4000 0025 0000 3155` requires 3D Secure.

## 6. Calling it from another block or agent

The seam is these three commands and nothing else — treat the output as the contract:

| Command | Prints | Exit |
|---|---|---|
| `pay.py create-link --title X --amount 19 --currency usd [--json]` | checkout URL + link id | 0 on success, 1 on any error |
| `pay.py status --link-id plink_...` | `paid` or `unpaid` | **0 for both**; 1 only on a real failure |
| `pay.py sales [--json]` | paid sales across links this tool created | 0 |

Errors always go to stderr with exit 1, and never contain a key or any part of one.

## 7. Tomorrow: swapping the rail (US-1.1)

The provider is a driver behind one interface, so moving to a merchant of record is an env swap,
not a rewrite:

```bash
export PAYMENT_PROVIDER=dodo     # or whop
export DODO_API_KEY=...          # or WHOP_API_KEY=...
```

Today those drivers are honest stubs — they exit 1 with:

> `provider 'dodo' declared but credentials/implementation not provisioned yet — set PAYMENT_PROVIDER=stripe or complete this driver (US-1.1)`

To complete one, fill in the three functions in `DRIVERS["dodo"]` inside `code/pay.py`
(`create_link`, `link_status`, `list_sales`) so they return the same shapes the Stripe driver
returns. **Fetch the current Dodo/Whop API docs first** — their surfaces are not verified anywhere
in this repo, and coding a payment rail from memory is how a demo dies on stage. Nothing outside
that dict should need to change; if it does, the seam has been broken and should be fixed rather
than worked around.

## 8. Recording sales into the CRM (US-1.2)

`record_sales.py` closes the lane seam from payments to the CRM: it reads `pay.py sales --json`
and, for every paid sale not already recorded, creates a `won` project under a "Direct sales"
company in `blocks/crm/code/crm.py` — via crm.py's own CLI, never by importing or editing it. It
is idempotent: run it as often as you like, and only genuinely new sales get recorded.

```bash
python3 blocks/payments/code/record_sales.py run
```

Add `--json` for machine-readable output (`{"recorded": [...], "already_recorded": [...],
"failed": [...]}`). Exit code is 1 if any individual sale failed to record — everything else in
that run still succeeded, and the failed sale is retried automatically on the next run.

Config:
- `PAYMENTS_RECORDED` — this tool's own idempotency journal (default: `recorded.jsonl` next to
  `record_sales.py`). Never a second source of truth about revenue — the CRM database is that;
  this file is only a seen-list of session_ids, same role as `labor.py`'s `hires.jsonl`.
- `CRM_DB` — honoured by `crm.py` itself (this tool inherits it); pass `--crm-db PATH` here to set
  it per-invocation without exporting the env var.

To dump what's been recorded so far:

```bash
python3 blocks/payments/code/record_sales.py log --json
```

**Cron / scheduled-tasks note:** this is designed to be called on a recurring interval from the
`scheduled-tasks` block (or plain cron) — e.g. every 5–15 minutes — so a sale lands in the CRM
without anyone remembering to run it by hand. It is safe to run this concurrently with `pay.py`
create-link/status calls; it never writes to Stripe, only reads `sales`.

## Safety

`pay.py` only ever **creates payment links and reads payment state**. It cannot refund, capture,
void, or touch payout settings — there is no such code path. Refunds and live-mode operations land
in US-1.1 and will sit behind the approver gate, because a refund is irreversible and irreversible
gestures need an owner's yes. Keys are read from the environment at call time, never written to
disk, never printed, never logged.

`record_sales.py` only ever **reads `pay.py sales` and creates CRM companies/projects**. It never
calls Stripe directly and has no refund, capture, or delete access to anything.
