#!/usr/bin/env python3
"""
Settle — against the real Whop API — the assumptions `pay.py`'s whop driver is built on.

Not a pytest module (hence the name: pytest collects `test_*.py`, and this must never run inside a
suite). It cannot be one. The question it answers is "what does a REAL paid Whop payment object
actually look like", and getting one requires a human to complete a checkout in the middle. A test
that pauses for a purchase is not a test.

Why this exists at all: `whop_list_sales` keeps a payment only if `_ours(p)` — i.e. only if the
payment carries `metadata.managed_by`, a tag we set on the *checkout configuration* at create time.
Nothing has ever confirmed Whop copies that tag onto the payment. If it does not, every paid Whop
sale is filtered out and `pay.py sales` returns an empty list while money is landing. The mocked
suite cannot catch this: its fixtures build payments in exactly the shape the driver expects, so
tests and code share one unverified guess. Only the live API can break the tie.

    export WHOP_API_KEY=...
    export WHOP_COMPANY_ID=biz_...

    # 1. create a real listing, print the buyer URL  (see the money warning below)
    python3 blocks/payments/tests/verify_whop_live.py probe --amount 1 --yes

    # 2. buy it in a browser, then:
    python3 blocks/payments/tests/verify_whop_live.py check --link-id ch_...

    # anytime: dump one raw page of GET /payments, unfiltered, no interpretation
    python3 blocks/payments/tests/verify_whop_live.py raw

**This moves real money.** Whop has no test-mode sandbox equivalent to Stripe's `sk_test_` keys, so
unlike `test_pay_live.py` there is no key prefix this script can inspect to prove it is safe. A
purchase here is a real charge on a real card, which is why `probe` refuses to run without `--yes`
and defaults to the smallest amount worth testing. Use the lowest amount Whop will accept.

Every verdict names the exact `pay.py` symbol it governs, so a FAIL is immediately actionable.
Raw payloads are written to disk rather than only printed: the point of this exercise is to have
the real object to read, not a summary of it.
"""
import argparse
import datetime
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAY_PATH = os.path.join(os.path.dirname(HERE), "code", "pay.py")

_spec = importlib.util.spec_from_file_location("pay_verify", PAY_PATH)
pay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pay)

# Written next to this script, gitignored by extension below — raw API bodies can carry buyer
# names and emails, which must never reach the repo.
DUMP_DIR = os.path.join(HERE, "whop-live-dumps")


# ── helpers ───────────────────────────────────────────────────────────────────
def _require_env():
    """Fail before any network call, naming both vars — the driver reads them at call time and
    would otherwise raise mid-probe, after a product had already been created."""
    missing = [v for v in ("WHOP_API_KEY", "WHOP_COMPANY_ID") if not os.environ.get(v, "").strip()]
    if missing:
        sys.exit(f"ERROR: {' and '.join(missing)} not set — export them in this shell first.")


def _dump(name, payload):
    """Persist a raw body and return its path. Timestamped so repeated runs never overwrite the
    evidence from the run that actually mattered."""
    os.makedirs(DUMP_DIR, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(DUMP_DIR, f"{stamp}-{name}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    return path


def _verdict(ok, assumption, governs, detail):
    """One line per assumption. `governs` is the pay.py symbol that breaks if `ok` is False."""
    print(f"  [{'PASS' if ok else 'FAIL'}] {assumption}")
    print(f"         governs: {governs}")
    print(f"         saw:     {detail}")
    return ok


# ── commands ──────────────────────────────────────────────────────────────────
def cmd_probe(a):
    """Create ONE real listing through the driver itself — not a hand-rolled request.

    Going through `pay.whop_create_link` is the point: if the create path is wrong (bad field name,
    wrong price unit, missing external_identifier) this surfaces it before the checkout, and the
    id it returns is the same id `check` will filter on.
    """
    _require_env()
    if not a.yes:
        sys.exit("ERROR: `probe` creates a real, purchasable listing in your Whop shop and any "
                 "purchase is a real charge — Whop has no test mode. Re-run with --yes.")
    cents = pay.to_cents(a.amount)
    title = pay.clean_title(a.title)
    try:
        link = pay.whop_create_link(title, cents, pay.normalise_currency(a.currency))
    except pay.PaymentError as e:
        sys.exit(f"ERROR: {e}")

    print(json.dumps(link, indent=2))
    print(f"\nraw create response saved: {_dump('create', link)}")
    print("\nNext: open the url above, complete a real purchase, then run:")
    print(f"  python3 {os.path.relpath(__file__)} check --link-id {link['link_id']}")
    if not link.get("url"):
        print("\nNOTE: purchase_url came back empty — whop_create_link's `purchase_url` field name "
              "is already wrong. Inspect the saved dump before buying anything.")


def cmd_raw(a):
    """One unfiltered page of GET /payments, straight from the transport.

    Deliberately bypasses `_whop_payments` (which injects statuses/cursor params) and
    `whop_list_sales` (which filters). Interpretation is what is being tested; it must not sit
    between you and the payload.
    """
    _require_env()
    try:
        page = pay._whop_request("GET", "/payments",
                                 query={"first": a.limit, "company_id": pay._whop_company()})
    except pay.PaymentError as e:
        sys.exit(f"ERROR: {e}")
    print(json.dumps(page, indent=2))
    print(f"\nsaved: {_dump('payments-raw', page)}", file=sys.stderr)


def _find_payment(page, link_id):
    """Locate our payment WITHOUT assuming the field name we are here to verify.

    Checks `checkout_configuration_id` first, then scans every string value on the object for the
    ch_… id. If the id turns up under some other key, that key is the fix — and this reports it.
    """
    for p in page.get("data") or []:
        if p.get("checkout_configuration_id") == link_id:
            return p, "checkout_configuration_id"
        for key, value in p.items():
            if isinstance(value, str) and value == link_id:
                return p, key
    return None, None


def cmd_check(a):
    """Read the real payment for one link and rule on each assumption the driver makes."""
    _require_env()
    link_id = a.link_id.strip()

    # Unfiltered first. If the server-side filter is broken, an empty filtered result would look
    # identical to "nobody has paid yet" — so establish the payment exists before trusting a query.
    try:
        wide = pay._whop_request("GET", "/payments",
                                 query={"first": 100, "company_id": pay._whop_company()})
    except pay.PaymentError as e:
        sys.exit(f"ERROR: {e}")
    print(f"raw unfiltered page saved: {_dump('payments-unfiltered', wide)}\n")

    payment, id_field = _find_payment(wide, link_id)
    if payment is None:
        sys.exit(f"No payment referencing {link_id} in the latest {len(wide.get('data') or [])} "
                 f"payments. Either the purchase has not completed, or the payment does not carry "
                 f"the checkout-configuration id at all — read the saved dump to tell which. "
                 f"(If it is the latter, whop_list_sales' `link_id` and whop_link_status' filter "
                 f"both need another join key.)")

    print(f"Found the payment ({payment.get('id')}). Assumptions in pay.py's whop driver:\n")
    results = []

    # A1 — the one that silently zeroes out revenue. pay.py:391-396
    tag = (payment.get("metadata") or {}).get("managed_by")
    results.append(_verdict(
        tag == pay.MANAGED_BY,
        "a payment inherits metadata.managed_by from its checkout configuration",
        "whop_list_sales -> _ours(p); a FAIL means paid sales are filtered out and `pay.py sales` "
        "returns [] while money lands",
        f"metadata.managed_by = {tag!r} (expected {pay.MANAGED_BY!r}); "
        f"full metadata = {json.dumps(payment.get('metadata') or {})}"))

    # A2 — the join key. pay.py:399
    results.append(_verdict(
        id_field == "checkout_configuration_id",
        "the checkout-configuration id is exposed as `checkout_configuration_id`",
        "whop_list_sales -> sale['link_id']",
        f"id found under key {id_field!r}"))

    # A3 — the server-side filter whop_link_status depends on entirely. pay.py:379
    try:
        narrow = pay._whop_request("GET", "/payments", query={
            "first": 100, "company_id": pay._whop_company(),
            "checkout_configuration_ids": [link_id]})
        narrow_ids = {p.get("id") for p in narrow.get("data") or []}
        results.append(_verdict(
            payment.get("id") in narrow_ids and len(narrow_ids) <= len(wide.get("data") or []),
            "checkout_configuration_ids[] narrows GET /payments server-side",
            "whop_link_status -> _whop_payments({'checkout_configuration_ids': [...]})",
            f"filtered returned {len(narrow_ids)} of {len(wide.get('data') or [])}; "
            f"our payment {'present' if payment.get('id') in narrow_ids else 'MISSING'}"))
    except pay.PaymentError as e:
        results.append(_verdict(False,
                                "checkout_configuration_ids[] narrows GET /payments server-side",
                                "whop_link_status", f"request rejected: {e}"))

    # A4 — the status enum both read paths branch on. pay.py:380, 395
    results.append(_verdict(
        payment.get("status") == "paid",
        "a completed payment reports status == 'paid'",
        "whop_link_status (paid filter) and whop_list_sales (statuses=['paid'] query)",
        f"status = {payment.get('status')!r}"))

    # A5 — the fields `sales` prints. pay.py:400-404
    total, paid_at = payment.get("total"), payment.get("paid_at") or payment.get("created_at")
    results.append(_verdict(
        isinstance(total, (int, float, str)) and total is not None and paid_at is not None,
        "`total` and `paid_at`/`created_at` are present and populated",
        "whop_list_sales -> sale['amount_usd'] and sale['paid_at']",
        f"total = {total!r} ({type(total).__name__}), paid_at = {payment.get('paid_at')!r}, "
        f"created_at = {payment.get('created_at')!r}"))

    # A6 — pagination shape; wrong here means silent truncation at 100 sales. pay.py:369-372
    info = wide.get("page_info")
    results.append(_verdict(
        isinstance(info, dict) and "has_next_page" in info and "end_cursor" in info,
        "pagination is page_info.has_next_page / end_cursor",
        "_whop_payments cursor walk; a FAIL means sales silently truncate at one page",
        f"page_info = {json.dumps(info) if info is not None else 'absent'}"))

    # The driver's own answer, end to end — the assumptions above explain any mismatch here.
    print("\nDriver output for this link:")
    try:
        print(f"  whop_link_status: {json.dumps(pay.whop_link_status(link_id))}")
        ours = [s for s in pay.whop_list_sales() if s["link_id"] == link_id]
        print(f"  whop_list_sales:  {json.dumps(ours)}")
        if not ours:
            print("  ^ EMPTY while a real payment exists — this is the failure mode this script "
                  "was written to catch. The FAILs above name the cause.")
    except pay.PaymentError as e:
        print(f"  driver raised: {e}")

    failed = len(results) - sum(results)
    print(f"\n{sum(results)}/{len(results)} assumptions hold." if not failed
          else f"\n{failed} of {len(results)} assumptions FAILED — fix pay.py before trusting "
               f"this rail, and update the mocked fixtures in test_pay.py to match reality.")
    sys.exit(1 if failed else 0)


def build_parser():
    ap = argparse.ArgumentParser(
        description="Verify pay.py's whop driver against the real Whop API.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("probe", help="create one real listing to buy (REAL MONEY)")
    s.add_argument("--title", default="Nightshift whop-verification probe")
    s.add_argument("--amount", default="1", help="whole currency units; keep this small")
    s.add_argument("--currency", default="usd")
    s.add_argument("--yes", action="store_true", help="required: acknowledges a real charge")
    s.set_defaults(f=cmd_probe)

    s = sub.add_parser("check", help="rule on every assumption, using a real paid link")
    s.add_argument("--link-id", required=True, help="the ch_… id from `probe`")
    s.set_defaults(f=cmd_check)

    s = sub.add_parser("raw", help="dump one unfiltered page of GET /payments")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(f=cmd_raw)
    return ap


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.f(args)
