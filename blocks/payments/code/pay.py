#!/usr/bin/env python3
"""
payments — the money seam. One CLI every agent (and every human at a terminal) calls to take money.

Three verbs, and only three, because a seam that grows verbs stops being a seam:

    pay.py create-link --title "X" --amount 19 --currency usd [--json]
    pay.py status --link-id plink_...                         [--json]
    pay.py sales                                              [--json]

Design notes (this file is read by other agents, so the WHY is written down):

- **Stateless.** There is no local database. The provider is the ledger. Everything this tool
  creates is tagged `metadata[managed_by]=nightshift-payments`, so `sales` can find OUR links — and
  only ours — from the API alone. A local DB would be a second source of truth about money, and
  two sources of truth about money is how a company loses count.
- **Dollars in, cents out.** `--amount` is in whole currency units (19, 19.50) because that is what
  a founder types. Stripe wants an integer in the smallest unit; the conversion happens once, here,
  through `Decimal` so 19.99 never becomes 1998.
- **One provider interface, three drivers.** `PAYMENT_PROVIDER` (default `stripe`) picks a driver:
  a dict of three functions. `stripe` and `whop` are live; `dodo` remains an honest stub so that
  swapping rails is filling in a driver, not a refactor.
- **One network function per provider.** Stripe calls go through `_request`, Whop calls through
  `_whop_request` (JSON, not form-encoded). Tests monkeypatch those two symbols and the whole
  suite runs offline. Nothing else in this file opens a socket.
- **Stdlib only.** This repo has zero pip dependencies by design — no `stripe` SDK, no `requests`.

Config (names only — values live in the environment, never in this repo):
    PAYMENT_PROVIDER   stripe (default) | dodo | whop
    STRIPE_API_KEY     read at call time, never logged, never printed
    DODO_API_KEY       reserved for the Dodo driver (US-1.1)
    WHOP_API_KEY       read at call time by the Whop driver (US-3.1), never logged, never printed
    WHOP_COMPANY_ID    the biz_… id the Whop driver lists into (not a secret, still env-only)
"""
import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation

# ── constants ─────────────────────────────────────────────────────────────────
STRIPE_API_BASE = "https://api.stripe.com"
MANAGED_BY = "nightshift-payments"      # the tag that makes `sales` possible without a local DB
HTTP_TIMEOUT = 30                       # seconds; an agent loop must never hang on the money seam
PAGE_LIMIT = 100                        # Stripe's max page size — fewer round trips per scan
MAX_PAGES = 50                          # hard stop so a runaway account can't spin us forever
MAX_AMOUNT_CENTS = 99_999_999           # Stripe's per-charge ceiling; also a runaway-agent guard
DEFAULT_PROVIDER = "stripe"


class PaymentError(Exception):
    """Anything the operator needs to read on stderr. Never carries a key or a key fragment."""


# ── HTTP transport — the ONLY place this file touches the network ─────────────
def _flatten(params, prefix=""):
    """Stripe speaks form-encoded bodies with bracket notation, not JSON.

    {"line_items": [{"price": "price_1"}]} -> line_items[0][price]=price_1
    Nested dicts/lists are expanded the same way, which is how `metadata[managed_by]` is sent.
    """
    out = []
    for key, value in params.items():
        name = f"{prefix}[{key}]" if prefix else str(key)
        if value is None:
            continue                                  # omit rather than send an empty string
        if isinstance(value, dict):
            out.extend(_flatten(value, name))
        elif isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    out.extend(_flatten(item, f"{name}[{i}]"))
                else:
                    out.append((f"{name}[{i}]", str(item)))
        elif isinstance(value, bool):
            out.append((name, "true" if value else "false"))
        else:
            out.append((name, str(value)))
    return out


def _stripe_key():
    """Read the key at call time. Never cached at import, never logged, never echoed."""
    key = os.environ.get("STRIPE_API_KEY", "").strip()
    if not key:
        raise PaymentError(
            "STRIPE_API_KEY is not set. Export your Stripe secret key in this shell "
            "(test keys start with sk_test_). The value is never written to this repo.")
    return key


def _request(method, path, params=None):
    """Single chokepoint for every Stripe HTTP call. Tests monkeypatch exactly this symbol.

    method: "GET" or "POST". path: e.g. "/v1/payment_links". params: nested dict, form-encoded.
    Returns the parsed JSON body. Raises PaymentError with Stripe's own error.message on failure.
    """
    key = _stripe_key()
    pairs = _flatten(params or {})
    url = STRIPE_API_BASE + path
    body = None
    if method == "GET":
        if pairs:
            url += "?" + urllib.parse.urlencode(pairs)
    else:
        body = urllib.parse.urlencode(pairs).encode("utf-8")

    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {key}")   # docs.stripe.com/api/authentication
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # Stripe returns {"error": {"message": ..., "type": ...}} — surface its words, not ours.
        detail = ""
        try:
            detail = (json.loads(e.read().decode("utf-8")).get("error") or {}).get("message", "")
        except Exception:
            pass
        raise PaymentError(f"Stripe API error ({e.code}): {detail or 'no message returned'}")
    except urllib.error.URLError as e:
        raise PaymentError(f"could not reach the Stripe API: {e.reason}")


def _list_all(path, params):
    """Walk a Stripe list endpoint. docs.stripe.com/api/pagination — cursor is `starting_after`."""
    items, cursor = [], None
    for _ in range(MAX_PAGES):
        page_params = dict(params, limit=PAGE_LIMIT)
        if cursor:
            page_params["starting_after"] = cursor
        page = _request("GET", path, page_params)
        data = page.get("data") or []
        items.extend(data)
        if not page.get("has_more") or not data:
            break
        cursor = data[-1]["id"]
    return items


# ── stripe driver ─────────────────────────────────────────────────────────────
def _ours(obj):
    """True if this object carries our tag. Payment Link metadata is copied onto the checkout
    sessions the link creates (docs.stripe.com/api/payment-link/create — `metadata`), so the same
    predicate works for links and sessions."""
    return (obj.get("metadata") or {}).get("managed_by") == MANAGED_BY


def _sessions_for(link_id):
    """GET /v1/checkout/sessions?payment_link=... — docs.stripe.com/api/checkout/sessions/list
    (`payment_link` is a documented filter on that endpoint)."""
    return _list_all("/v1/checkout/sessions", {"payment_link": link_id})


def _iso(epoch):
    """Stripe timestamps are UNIX seconds; the seam publishes ISO-8601 UTC so callers can sort."""
    if not epoch:
        return None
    return datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc).isoformat()


def stripe_create_link(title, amount_cents, currency):
    """Product -> Price -> Payment Link. Three calls, in that order, because the Payment Links API
    accepts only an EXISTING Price ID in `line_items[0][price]` — there is no inline `price_data`
    on this endpoint (docs.stripe.com/payment-links/api: "create a payment link by passing in
    line_items ... Each line item contains a price and quantity")."""
    # 1) POST /v1/products — docs.stripe.com/api/products/create (`name` required)
    product = _request("POST", "/v1/products", {
        "name": title,
        "metadata": {"managed_by": MANAGED_BY},
    })
    # 2) POST /v1/prices — docs.stripe.com/api/prices/create
    #    `currency` required, `product` required unless product_data, `unit_amount` in cents.
    #    No `recurring` -> a one-off price, which is what a single sale needs.
    price = _request("POST", "/v1/prices", {
        "currency": currency,
        "unit_amount": amount_cents,
        "product": product["id"],
        "metadata": {"managed_by": MANAGED_BY},
    })
    # 3) POST /v1/payment_links — docs.stripe.com/api/payment-link/create
    #    `line_items` required; metadata here is copied onto every checkout session this link
    #    creates, which is what makes `sales` possible with no local database.
    link = _request("POST", "/v1/payment_links", {
        "line_items": [{"price": price["id"], "quantity": 1}],
        "metadata": {"managed_by": MANAGED_BY, "title": title},
    })
    return {
        "link_id": link["id"],
        "url": link["url"],
        "title": title,
        "amount": round(amount_cents / 100, 2),
        "currency": currency,
        "product_id": product["id"],
        "price_id": price["id"],
    }


def stripe_link_status(link_id):
    """A link is paid the moment ANY of its checkout sessions reaches payment_status=paid.
    `payment_status` is one of paid | unpaid | no_payment_required
    (docs.stripe.com/api/checkout/sessions/object)."""
    sessions = _sessions_for(link_id)
    paid = [s for s in sessions if s.get("payment_status") == "paid"]
    return {
        "link_id": link_id,
        "status": "paid" if paid else "unpaid",
        "paid": bool(paid),
        "sessions": len(sessions),
        "paid_sessions": [s["id"] for s in paid],
    }


def stripe_list_sales():
    """Every PAID session across the links this tool created.

    Links first, then their sessions: neither /v1/payment_links nor /v1/checkout/sessions supports
    a server-side metadata filter, so we list OUR links (tag on the link), then ask each link for
    its sessions via the documented `payment_link` filter. That also keeps the scan bounded to
    links we made, instead of every session in the account.
    """
    links = [l for l in _list_all("/v1/payment_links", {}) if _ours(l)]
    sales = []
    for link in links:
        title = (link.get("metadata") or {}).get("title") or ""
        for s in _sessions_for(link["id"]):
            if s.get("payment_status") != "paid":
                continue
            cents = s.get("amount_total") or 0
            sales.append({
                "link_id": link["id"],
                "session_id": s["id"],
                "title": title,
                "amount_usd": round(cents / 100, 2),   # major units of `currency`, not always USD
                "currency": s.get("currency") or link.get("currency") or "",
                "paid_at": _iso(s.get("created")),
            })
    sales.sort(key=lambda x: (x["paid_at"] or "", x["session_id"]))
    return sales


# ── whop driver ───────────────────────────────────────────────────────────────
WHOP_API_BASE = "https://api.whop.com/api/v1"
WHOP_CHECKOUT_BASE = "https://whop.com"      # purchase_url comes back relative; buyers need absolute


def _whop_key():
    """Read at call time, same discipline as the Stripe key: never cached, logged, or echoed."""
    key = os.environ.get("WHOP_API_KEY", "").strip()
    if not key:
        raise PaymentError(
            "WHOP_API_KEY is not set. Export your Whop company API key in this shell. "
            "The value is never written to this repo.")
    return key


def _whop_request(method, path, params=None, query=None):
    """Single chokepoint for every Whop HTTP call — tests monkeypatch exactly this symbol.

    Whop speaks JSON bodies (docs.whop.com/developer/api/getting-started), unlike Stripe's
    form encoding, so this transport is separate from `_request` rather than a flag on it.
    Array query params use Rails bracket style: statuses[]=paid&statuses[]=open.
    """
    key = _whop_key()
    url = WHOP_API_BASE + path
    if query:
        pairs = []
        for k, v in query.items():
            if v is None:
                continue
            if isinstance(v, (list, tuple)):
                pairs.extend((f"{k}[]", str(item)) for item in v)
            else:
                pairs.append((k, str(v)))
        if pairs:
            url += "?" + urllib.parse.urlencode(pairs)
    body = json.dumps(params).encode("utf-8") if params is not None else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            payload = json.loads(e.read().decode("utf-8"))
            detail = payload.get("message") or (payload.get("error") or {}).get("message", "")
        except Exception:
            pass
        raise PaymentError(f"Whop API error ({e.code}): {detail or 'no message returned'}")
    except urllib.error.URLError as e:
        raise PaymentError(f"could not reach the Whop API: {e.reason}")


def _whop_company():
    """The biz_… id this driver lists into. The live API requires it both on every inline plan
    (400 without) and as a filter on GET /payments (a company key still 400s bare)."""
    company_id = os.environ.get("WHOP_COMPANY_ID", "").strip()
    if not company_id:
        raise PaymentError(
            "WHOP_COMPANY_ID is not set — the biz_… id from the Whop dashboard URL. "
            "Not a secret, but it lives in the environment like every other config value.")
    return company_id


def _whop_external_id(title):
    """Deterministic product key for Whop's find-or-create: lowercase title, non-alphanumerics
    collapsed to hyphens, under our namespace so `sales` provenance stays obvious in their UI."""
    slug = "".join(ch if ch.isalnum() else "-" for ch in title.lower())
    slug = "-".join(filter(None, slug.split("-")))
    return f"{MANAGED_BY}-{slug}"


def whop_create_link(title, amount_cents, currency):
    """One call: POST /checkout_configurations with an inline one-time plan.

    docs.whop.com/api-reference/checkout-configurations/create-checkout-configuration —
    mode "payment" plus a `plan` object creates the plan (and its product) on the fly, which is
    why the release plan names this endpoint over create-plan: no separate product step.
    `initial_price` is in major currency units, so the seam's cents convert back once, here.
    """
    config = _whop_request("POST", "/checkout_configurations", params={
        "mode": "payment",
        "plan": {
            "company_id": _whop_company(),
            "plan_type": "one_time",
            "initial_price": float(Decimal(amount_cents) / 100),
            "renewal_price": 0,
            "billing_period": None,
            "currency": currency,
            # external_identifier is required by the live API (400 without it) and acts as a
            # find-or-create key: a stable slug means re-listing the same title reuses the
            # product instead of piling up duplicates in the shop.
            "product": {"title": title, "external_identifier": _whop_external_id(title)},
        },
        "metadata": {"managed_by": MANAGED_BY, "title": title},
    })
    url = config.get("purchase_url") or ""
    if url.startswith("/"):
        url = WHOP_CHECKOUT_BASE + url
    return {
        "link_id": config["id"],                       # ch_… — payments filter on this id
        "url": url,
        "title": title,
        "amount": round(amount_cents / 100, 2),
        "currency": currency,
        "product_id": ((config.get("plan") or {}).get("product") or {}).get("id"),
        "price_id": (config.get("plan") or {}).get("id"),
    }


def _whop_payments(query):
    """Walk GET /payments (docs.whop.com/api-reference/payments/list-payments).
    Cursor pagination: page_info.has_next_page / end_cursor, forwarded as `after`."""
    items, cursor = [], None
    for _ in range(MAX_PAGES):
        q = dict(query, first=PAGE_LIMIT, company_id=_whop_company())
        if cursor:
            q["after"] = cursor
        page = _whop_request("GET", "/payments", query=q)
        data = page.get("data") or []
        items.extend(data)
        info = page.get("page_info") or {}
        if not info.get("has_next_page") or not data:
            break
        cursor = info.get("end_cursor")
    return items


def whop_link_status(link_id):
    """Paid the moment any payment on this checkout configuration reports status "paid"
    (status enum: draft | open | paid | pending | uncollectible | unresolved | void)."""
    payments = _whop_payments({"checkout_configuration_ids": [link_id]})
    paid = [p for p in payments if p.get("status") == "paid"]
    return {
        "link_id": link_id,
        "status": "paid" if paid else "unpaid",
        "paid": bool(paid),
        "sessions": len(payments),
        "paid_sessions": [p["id"] for p in paid],
    }


def whop_list_sales():
    """Every paid payment carrying our tag. The tag is set as checkout-configuration metadata at
    create time; payments expose a `metadata` object, so the same `_ours` predicate applies.
    Server-side we narrow to status=paid; ownership is filtered here, like the Stripe driver."""
    sales = []
    for p in _whop_payments({"statuses": ["paid"]}):
        if not _ours(p):
            continue
        sales.append({
            "link_id": p.get("checkout_configuration_id") or "",
            "session_id": p["id"],
            "title": (p.get("metadata") or {}).get("title") or "",
            "amount_usd": float(p.get("total") or 0),
            "currency": p.get("currency") or "",
            "paid_at": p.get("paid_at") or p.get("created_at"),
        })
    sales.sort(key=lambda x: (x["paid_at"] or "", x["session_id"]))
    return sales


# ── stub drivers (US-1.1 fills these in; they exist so tomorrow is not a refactor) ────────────
def _stub(provider):
    def _unavailable(*_args, **_kwargs):
        raise PaymentError(
            f"provider '{provider}' declared but credentials/implementation not provisioned yet "
            f"— set PAYMENT_PROVIDER=stripe or complete this driver (US-1.1)")
    return _unavailable


def _stub_driver(provider):
    fn = _stub(provider)
    return {"create_link": fn, "link_status": fn, "list_sales": fn}


DRIVERS = {
    "stripe": {
        "create_link": stripe_create_link,
        "link_status": stripe_link_status,
        "list_sales": stripe_list_sales,
    },
    # Money-on-record rails. Config names are declared in block.md.
    "dodo": _stub_driver("dodo"),
    "whop": {
        "create_link": whop_create_link,
        "link_status": whop_link_status,
        "list_sales": whop_list_sales,
    },
}


def get_driver():
    """PAYMENT_PROVIDER selects the rail. Unset means stripe, so the seam works out of the box."""
    name = (os.environ.get("PAYMENT_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if name not in DRIVERS:
        raise PaymentError(
            f"unknown PAYMENT_PROVIDER '{name}' — expected one of: {', '.join(sorted(DRIVERS))}")
    return name, DRIVERS[name]


# ── validation ────────────────────────────────────────────────────────────────
MAX_TITLE_LEN = 250   # defense-in-depth, like the amount ceiling: a runaway agent can't spam huge names


def clean_title(raw) -> str:
    """Validate a buyer-visible title. Strips whitespace, rejects empties and oversize, and
    removes control characters (incl. ANSI escapes): titles round-trip through Stripe metadata
    back onto an operator's terminal in `sales`, so they must never carry escape sequences."""
    title = "".join(ch for ch in (raw or "") if ch.isprintable()).strip()
    if not title:
        raise PaymentError("--title must not be empty — it is what the buyer sees at checkout.")
    if len(title) > MAX_TITLE_LEN:
        raise PaymentError(f"--title too long ({len(title)} chars; max {MAX_TITLE_LEN}).")
    return title


def to_cents(amount):
    """Dollars (the founder's unit) -> integer cents (Stripe's unit). Decimal, not float, so
    19.99 is 1999 and not 1998. Rejects anything that isn't a positive number."""
    try:
        value = Decimal(str(amount).strip())
    except (InvalidOperation, AttributeError):
        raise PaymentError(f"--amount must be a number in whole currency units (got '{amount}')")
    if not value.is_finite() or value <= 0:
        raise PaymentError(f"--amount must be greater than 0 (got '{amount}')")
    cents = int((value * 100).to_integral_value(rounding="ROUND_HALF_UP"))
    if cents <= 0:
        raise PaymentError(f"--amount is below the smallest chargeable unit (got '{amount}')")
    if cents > MAX_AMOUNT_CENTS:
        # Fail here, not at Stripe: a runaway agent computing a price should never get as far as
        # posting an eight-figure charge, and Decimal happily accepts '1e400'.
        raise PaymentError(
            f"--amount exceeds the maximum this seam will create "
            f"({MAX_AMOUNT_CENTS // 100:,} per link) — got '{amount}'")
    return cents


def normalise_currency(currency):
    code = (currency or "").strip().lower()
    if len(code) != 3 or not code.isalpha():
        raise PaymentError(f"--currency must be a 3-letter ISO code, e.g. usd (got '{currency}')")
    return code


# ── commands ──────────────────────────────────────────────────────────────────
def cmd_create_link(a):
    _, driver = get_driver()
    cents = to_cents(a.amount)
    currency = normalise_currency(a.currency)
    title = clean_title(a.title)
    result = driver["create_link"](title, cents, currency)
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["url"])
        print(f"link id: {result['link_id']}")


def cmd_status(a):
    _, driver = get_driver()
    result = driver["link_status"](a.link_id)
    # Exit 0 either way: "unpaid" is a fact, not a failure. Callers branch on the word.
    print(json.dumps(result, indent=2) if a.json else result["status"])


def cmd_sales(a):
    _, driver = get_driver()
    sales = driver["list_sales"]()
    if a.json:
        print(json.dumps(sales, indent=2))
        return
    if not sales:
        print("No paid sales yet.")
        return
    for s in sales:
        print(f"  {s['paid_at'] or '?':<25} {s['amount_usd']:>10.2f} {s['currency'].upper()}  "
              f"{s['title'] or '(untitled)'}  [{s['link_id']}]")


def build_parser():
    ap = argparse.ArgumentParser(description="Payment seam — create links, read payment state.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("create-link", help="create a hosted checkout link")
    s.add_argument("--title", required=True, help="what the buyer sees")
    # Deliberately a string, not type=float: we validate it ourselves so a bad amount exits 1
    # (argparse's own type errors exit 2, and the seam contract says 1).
    s.add_argument("--amount", required=True, help="price in whole currency units, e.g. 19 or 19.50")
    s.add_argument("--currency", default="usd", help="3-letter ISO code (default: usd)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_create_link)

    s = sub.add_parser("status", help="'paid' or 'unpaid' for one link")
    s.add_argument("--link-id", required=True)
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_status)

    s = sub.add_parser("sales", help="paid sales across links this tool created")
    s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_sales)
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        a.f(a)
    except PaymentError as e:
        # Written, then exit 1. (`sys.exit("msg")` would only print at interpreter shutdown, which
        # is invisible to an in-process caller — an agent embedding this seam would see nothing.)
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)                 # the message never carries a key or a key fragment


if __name__ == "__main__":
    main()
