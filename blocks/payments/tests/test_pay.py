"""
Deterministic tests for the payment seam. No network, no key, no clock assumptions.

Every test replaces `pay._request` — the single transport function — with a recorder, so the whole
suite proves the *documented call sequence and form parameters* without touching Stripe. The one
test that must not be mocked (missing key) blows up `urlopen` instead, to prove no socket is opened.
"""
import importlib.util
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PAY_PATH = os.path.join(os.path.dirname(HERE), "code", "pay.py")

_spec = importlib.util.spec_from_file_location("pay", PAY_PATH)
pay = importlib.util.module_from_spec(_spec)
sys.modules["pay"] = pay
_spec.loader.exec_module(pay)


# ── helpers ───────────────────────────────────────────────────────────────────
class Recorder:
    """Stands in for pay._request. Records (method, path, params) and replays canned responses."""

    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def __call__(self, method, path, params=None):
        self.calls.append((method, path, params or {}))
        key = (method, path)
        value = self.responses.get(key)
        if callable(value):
            return value(params or {})
        if value is None:
            raise AssertionError(f"no canned response for {method} {path}")
        return value

    def params_for(self, method, path):
        for m, p, params in self.calls:
            if (m, p) == (method, path):
                return params
        raise AssertionError(f"{method} {path} was never called")


def session(sid, payment_status, amount_total=1900, created=1_700_000_000, currency="usd"):
    return {"id": sid, "object": "checkout.session", "payment_status": payment_status,
            "amount_total": amount_total, "currency": currency, "created": created,
            "metadata": {"managed_by": "nightshift-payments"}}


def page(items):
    return {"object": "list", "data": items, "has_more": False}


def create_link_responses():
    return {
        ("POST", "/v1/products"): {"id": "prod_TEST", "object": "product"},
        ("POST", "/v1/prices"): {"id": "price_TEST", "object": "price"},
        ("POST", "/v1/payment_links"): {
            "id": "plink_TEST", "object": "payment_link",
            "url": "https://buy.stripe.com/test_TEST", "active": True},
    }


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """No provider and no key leak in from the developer's shell into any test."""
    monkeypatch.delenv("PAYMENT_PROVIDER", raising=False)
    monkeypatch.delenv("STRIPE_API_KEY", raising=False)
    monkeypatch.delenv("WHOP_API_KEY", raising=False)
    monkeypatch.delenv("WHOP_COMPANY_ID", raising=False)


def run(monkeypatch, recorder, argv):
    monkeypatch.setattr(pay, "_request", recorder)
    return pay.main(argv)


# ── driver selection ──────────────────────────────────────────────────────────
def test_default_provider_is_stripe():
    name, driver = pay.get_driver()
    assert name == "stripe"
    assert driver["create_link"] is pay.stripe_create_link


def test_explicit_stripe_provider(monkeypatch):
    monkeypatch.setenv("PAYMENT_PROVIDER", "STRIPE")   # case-insensitive on purpose
    assert pay.get_driver()[0] == "stripe"


@pytest.mark.parametrize("provider", ["dodo"])
def test_stub_drivers_exit_1_with_the_handover_message(monkeypatch, capsys, provider):
    monkeypatch.setenv("PAYMENT_PROVIDER", provider)
    recorder = Recorder()
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, recorder, ["create-link", "--title", "X", "--amount", "19"])
    assert _code(exc) == 1
    err = capsys.readouterr().err
    assert f"provider '{provider}' declared but credentials/implementation not provisioned yet" in err
    assert "set PAYMENT_PROVIDER=stripe or complete this driver (US-1.1)" in err
    assert recorder.calls == []                        # a stub must never reach the network


def test_unknown_provider_exits_1(monkeypatch, capsys):
    monkeypatch.setenv("PAYMENT_PROVIDER", "paypal")
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, Recorder(), ["sales"])
    assert _code(exc) == 1
    assert "unknown PAYMENT_PROVIDER 'paypal'" in capsys.readouterr().err


# ── create-link ───────────────────────────────────────────────────────────────
def test_create_link_issues_the_documented_call_sequence(monkeypatch, capsys):
    recorder = Recorder(create_link_responses())
    run(monkeypatch, recorder, ["create-link", "--title", "Nightshift Playbook",
                                "--amount", "19", "--currency", "USD"])

    # Product -> Price -> Payment Link, in that order (payment_links needs an existing Price ID).
    assert [(m, p) for m, p, _ in recorder.calls] == [
        ("POST", "/v1/products"),
        ("POST", "/v1/prices"),
        ("POST", "/v1/payment_links"),
    ]

    product = recorder.params_for("POST", "/v1/products")
    assert product["name"] == "Nightshift Playbook"
    assert product["metadata"]["managed_by"] == "nightshift-payments"

    price = recorder.params_for("POST", "/v1/prices")
    assert price["unit_amount"] == 1900             # dollars in, integer cents out
    assert price["currency"] == "usd"               # normalised to lowercase ISO
    assert price["product"] == "prod_TEST"
    assert "recurring" not in price                 # a single sale, not a subscription

    link = recorder.params_for("POST", "/v1/payment_links")
    assert link["line_items"] == [{"price": "price_TEST", "quantity": 1}]
    assert link["metadata"]["managed_by"] == "nightshift-payments"
    assert link["metadata"]["title"] == "Nightshift Playbook"

    out = capsys.readouterr().out
    assert "https://buy.stripe.com/test_TEST" in out
    assert "plink_TEST" in out


def test_create_link_json_shape(monkeypatch, capsys):
    run(monkeypatch, Recorder(create_link_responses()),
        ["create-link", "--title", "X", "--amount", "19.50", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["link_id"] == "plink_TEST"
    assert payload["url"] == "https://buy.stripe.com/test_TEST"
    assert payload["amount"] == 19.5
    assert payload["currency"] == "usd"


def test_cents_conversion_uses_decimal_not_float():
    assert pay.to_cents("19") == 1900
    assert pay.to_cents("19.50") == 1950
    assert pay.to_cents("19.99") == 1999          # the classic float trap: 19.99*100 == 1998.999…
    assert pay.to_cents("0.01") == 1


# ── amount validation: reject before any API call ─────────────────────────────
@pytest.mark.parametrize("amount", ["0", "0.00", "-5", "-0.01", "abc", "", "nan", "1e400"])
def test_bad_amount_exits_1_without_calling_the_api(monkeypatch, capsys, amount):
    recorder = Recorder(create_link_responses())
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, recorder, ["create-link", "--title", "X", "--amount", amount])
    assert _code(exc) == 1
    assert recorder.calls == []
    assert "--amount" in capsys.readouterr().err


# ── title validation: control chars stripped, bounds enforced, no API call on bad input ───────
def test_title_strips_ansi_and_control_chars(monkeypatch, recorder_calls=None):
    # A malicious/buggy agent title with ANSI escapes must never round-trip to an operator's
    # terminal via `sales` — clean_title drops every non-printable character.
    assert pay.clean_title("\x1b[31mEVIL\x1b[0m Playbook\x07") == "[31mEVIL[0m Playbook"
    assert pay.clean_title("  plain title  ") == "plain title"


@pytest.mark.parametrize("title", ["", "   ", "\x1b\x07\x00", "x" * 251])
def test_bad_title_exits_1_without_calling_the_api(monkeypatch, capsys, title):
    recorder = Recorder(create_link_responses())
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, recorder, ["create-link", "--title", title, "--amount", "19"])
    assert _code(exc) == 1
    assert recorder.calls == []
    assert "--title" in capsys.readouterr().err


def test_bad_currency_exits_1_without_calling_the_api(monkeypatch, capsys):
    recorder = Recorder(create_link_responses())
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, recorder, ["create-link", "--title", "X", "--amount", "19",
                                    "--currency", "dollars"])
    assert _code(exc) == 1
    assert recorder.calls == []
    assert "--currency" in capsys.readouterr().err


# ── status ────────────────────────────────────────────────────────────────────
def test_status_unpaid_when_no_session_is_paid(monkeypatch, capsys):
    recorder = Recorder({("GET", "/v1/checkout/sessions"): page([
        session("cs_1", "unpaid"), session("cs_2", "no_payment_required")])})
    run(monkeypatch, recorder, ["status", "--link-id", "plink_TEST"])
    assert capsys.readouterr().out.strip() == "unpaid"
    assert recorder.params_for("GET", "/v1/checkout/sessions")["payment_link"] == "plink_TEST"


def test_status_paid_when_any_session_is_paid(monkeypatch, capsys):
    recorder = Recorder({("GET", "/v1/checkout/sessions"): page([
        session("cs_1", "unpaid"), session("cs_2", "paid")])})
    run(monkeypatch, recorder, ["status", "--link-id", "plink_TEST"])
    assert capsys.readouterr().out.strip() == "paid"


def test_status_exits_0_for_unpaid_and_paid(monkeypatch):
    for status in ("unpaid", "paid"):
        recorder = Recorder({("GET", "/v1/checkout/sessions"): page([session("cs_1", status)])})
        assert run(monkeypatch, recorder, ["status", "--link-id", "plink_TEST"]) is None


def test_status_json_carries_the_detail(monkeypatch, capsys):
    recorder = Recorder({("GET", "/v1/checkout/sessions"): page([
        session("cs_1", "unpaid"), session("cs_2", "paid")])})
    run(monkeypatch, recorder, ["status", "--link-id", "plink_TEST", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"link_id": "plink_TEST", "status": "paid", "paid": True,
                       "sessions": 2, "paid_sessions": ["cs_2"]}


# ── sales ─────────────────────────────────────────────────────────────────────
def sales_recorder():
    ours = {"id": "plink_OURS", "object": "payment_link", "currency": "usd",
            "metadata": {"managed_by": "nightshift-payments", "title": "Nightshift Playbook"}}
    theirs = {"id": "plink_THEIRS", "object": "payment_link", "currency": "usd", "metadata": {}}

    def sessions(params):
        if params.get("payment_link") == "plink_OURS":
            return page([session("cs_paid", "paid", amount_total=1900, created=1_700_000_000),
                         session("cs_open", "unpaid")])
        raise AssertionError("sales must only scan links tagged managed_by=nightshift-payments")

    return Recorder({
        ("GET", "/v1/payment_links"): page([ours, theirs]),
        ("GET", "/v1/checkout/sessions"): sessions,
    })


def test_sales_json_shape(monkeypatch, capsys):
    run(monkeypatch, sales_recorder(), ["sales", "--json"])
    sales = json.loads(capsys.readouterr().out)
    assert len(sales) == 1
    sale = sales[0]
    assert set(sale) == {"link_id", "session_id", "title", "amount_usd", "currency", "paid_at"}
    assert sale["link_id"] == "plink_OURS"
    assert sale["session_id"] == "cs_paid"
    assert sale["title"] == "Nightshift Playbook"
    assert sale["amount_usd"] == 19.0
    assert sale["currency"] == "usd"
    assert sale["paid_at"].startswith("2023-11-14T")     # ISO-8601 UTC, sortable


def test_sales_ignores_links_we_did_not_create(monkeypatch, capsys):
    recorder = sales_recorder()
    run(monkeypatch, recorder, ["sales", "--json"])
    scanned = [p.get("payment_link") for m, path, p in recorder.calls
               if path == "/v1/checkout/sessions"]
    assert scanned == ["plink_OURS"]


def test_sales_human_output_when_empty(monkeypatch, capsys):
    recorder = Recorder({("GET", "/v1/payment_links"): page([])})
    run(monkeypatch, recorder, ["sales"])
    assert "No paid sales yet." in capsys.readouterr().out


# ── secrets ───────────────────────────────────────────────────────────────────
def test_missing_key_exits_1_names_the_var_and_opens_no_socket(monkeypatch, capsys):
    def boom(*_a, **_k):
        raise AssertionError("no HTTP request may be attempted without STRIPE_API_KEY")
    monkeypatch.setattr(pay.urllib.request, "urlopen", boom)

    with pytest.raises(SystemExit) as exc:
        pay.main(["create-link", "--title", "X", "--amount", "19"])
    assert _code(exc) == 1
    err = capsys.readouterr().err
    assert "STRIPE_API_KEY" in err
    assert "sk_" not in err.replace("sk_test_", "")     # the hint may name the prefix, never a key


def test_key_value_never_appears_in_an_error(monkeypatch, capsys):
    secret = "sk_test_NEVER_PRINT_ME"
    monkeypatch.setenv("STRIPE_API_KEY", secret)

    class FakeHTTPError(pay.urllib.error.HTTPError):
        def __init__(self):
            super().__init__("https://api.stripe.com/v1/products", 402, "Payment Required", {}, None)

        def read(self):
            return json.dumps({"error": {"message": "Your card was declined."}}).encode()

    monkeypatch.setattr(pay.urllib.request, "urlopen",
                        lambda *_a, **_k: (_ for _ in ()).throw(FakeHTTPError()))
    with pytest.raises(SystemExit) as exc:
        pay.main(["create-link", "--title", "X", "--amount", "19"])
    assert _code(exc) == 1
    err = capsys.readouterr().err
    assert "Your card was declined." in err             # Stripe's own words reach the operator
    assert secret not in err


# ── transport encoding ────────────────────────────────────────────────────────
def test_flatten_uses_stripe_bracket_notation():
    pairs = dict(pay._flatten({
        "line_items": [{"price": "price_1", "quantity": 1}],
        "metadata": {"managed_by": "nightshift-payments"},
        "skipped": None,
    }))
    assert pairs["line_items[0][price]"] == "price_1"
    assert pairs["line_items[0][quantity]"] == "1"
    assert pairs["metadata[managed_by]"] == "nightshift-payments"
    assert "skipped" not in pairs


def _code(exc):
    """sys.exit("message") sets code to the string; the process still exits 1."""
    return 1 if isinstance(exc.value.code, str) else exc.value.code


# ── whop driver (US-3.1) — same offline discipline, monkeypatching pay._whop_request ──────────
class WhopRecorder:
    """Stands in for pay._whop_request. Records (method, path, params, query), replays canned."""

    def __init__(self, responses=None):
        self.calls = []
        self.responses = responses or {}

    def __call__(self, method, path, params=None, query=None):
        self.calls.append((method, path, params or {}, query or {}))
        value = self.responses.get((method, path))
        if callable(value):
            return value(params or {}, query or {})
        if value is None:
            raise AssertionError(f"no canned response for {method} {path}")
        return value


def whop_payment(pid, status, total=19.0, config="ch_TEST", paid_at="2026-08-15T20:00:00Z",
                 managed=True):
    meta = {"managed_by": "nightshift-payments", "title": "Nightshift Playbook"} if managed else {}
    return {"id": pid, "status": status, "total": total, "currency": "usd",
            "checkout_configuration_id": config, "paid_at": paid_at,
            "created_at": "2026-08-15T19:59:00Z", "metadata": meta}


def whop_page(items, has_next=False, end_cursor=None):
    return {"data": items, "page_info": {"has_next_page": has_next, "end_cursor": end_cursor}}


def run_whop(monkeypatch, recorder, argv):
    monkeypatch.setenv("PAYMENT_PROVIDER", "whop")
    monkeypatch.setenv("WHOP_COMPANY_ID", "biz_TEST")
    monkeypatch.setattr(pay, "_whop_request", recorder)
    return pay.main(argv)


def whop_config_response(purchase_url="/checkout/plan_TEST?session=ch_TEST"):
    return {("POST", "/checkout_configurations"): {
        "id": "ch_TEST", "mode": "payment", "currency": "usd",
        "plan": {"id": "plan_TEST", "plan_type": "one_time",
                 "product": {"id": "prod_TEST", "title": "Nightshift Playbook"}},
        "purchase_url": purchase_url, "metadata": {}}}


def test_whop_create_link_one_call_inline_plan(monkeypatch, capsys):
    recorder = WhopRecorder(whop_config_response())
    run_whop(monkeypatch, recorder, ["create-link", "--title", "Nightshift Playbook",
                                     "--amount", "19", "--currency", "USD"])
    # One call — the checkout-configuration endpoint creates plan and product on the fly.
    assert [(m, p) for m, p, _, _ in recorder.calls] == [("POST", "/checkout_configurations")]
    body = recorder.calls[0][2]
    assert body["mode"] == "payment"
    assert body["plan"]["company_id"] == "biz_TEST"        # live API 400s without it
    assert body["plan"]["plan_type"] == "one_time"
    # required by the live API; stable slug = find-or-create, so re-listing never duplicates
    assert body["plan"]["product"]["external_identifier"] == "nightshift-payments-nightshift-playbook"
    assert body["plan"]["initial_price"] == 19.0        # cents back to major units, once
    assert body["plan"]["renewal_price"] == 0
    assert body["plan"]["billing_period"] is None
    assert body["plan"]["currency"] == "usd"            # normalised to lowercase ISO
    assert body["plan"]["product"]["title"] == "Nightshift Playbook"
    assert body["metadata"]["managed_by"] == "nightshift-payments"

    out = capsys.readouterr().out
    # purchase_url comes back relative; buyers must receive an absolute URL.
    assert "https://whop.com/checkout/plan_TEST?session=ch_TEST" in out
    assert "ch_TEST" in out


def test_whop_product_carries_the_p7_disclosure(monkeypatch, capsys):
    """P7: every public-facing surface identifies the seller as an autonomous agent. A Whop product
    page IS such a surface, and it is created from this body — so the disclosure has to travel with
    it. The storefront block renders its own; this driver is the only author of the Whop one.
    P10 makes a listing that reads as human-run unapprovable by anyone, so this is not cosmetic."""
    recorder = WhopRecorder(whop_config_response())
    run_whop(monkeypatch, recorder, ["create-link", "--title", "Policy Gate Kit", "--amount", "19"])
    description = recorder.calls[0][2]["plan"]["product"]["description"]
    assert pay.P7_DISCLOSURE in description
    assert "autonomous agent" in description.lower()


def test_p7_disclosure_constant_cannot_be_blanked(monkeypatch, capsys):
    """Guard the constant itself: an empty or agent-free disclosure would ship a silently
    non-compliant listing, and the assertion above would still pass against ''."""
    assert pay.P7_DISCLOSURE.strip()
    assert "autonomous agent" in pay.P7_DISCLOSURE.lower()


def test_whop_create_link_json_shape(monkeypatch, capsys):
    run_whop(monkeypatch, WhopRecorder(whop_config_response()),
             ["create-link", "--title", "X", "--amount", "19.50", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["link_id"] == "ch_TEST"
    assert payload["url"] == "https://whop.com/checkout/plan_TEST?session=ch_TEST"
    assert payload["amount"] == 19.5
    assert payload["price_id"] == "plan_TEST"
    assert payload["product_id"] == "prod_TEST"


def test_whop_status_filters_on_the_configuration_id(monkeypatch, capsys):
    recorder = WhopRecorder({("GET", "/payments"): whop_page([
        whop_payment("pay_1", "open"), whop_payment("pay_2", "paid")])})
    run_whop(monkeypatch, recorder, ["status", "--link-id", "ch_TEST", "--json"])
    assert recorder.calls[0][3]["checkout_configuration_ids"] == ["ch_TEST"]
    assert recorder.calls[0][3]["company_id"] == "biz_TEST"  # bare GET /payments is refused live
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"link_id": "ch_TEST", "status": "paid", "paid": True,
                       "sessions": 2, "paid_sessions": ["pay_2"]}


def test_whop_status_unpaid_when_nothing_is_paid(monkeypatch, capsys):
    recorder = WhopRecorder({("GET", "/payments"): whop_page([whop_payment("pay_1", "open")])})
    run_whop(monkeypatch, recorder, ["status", "--link-id", "ch_TEST"])
    assert capsys.readouterr().out.strip() == "unpaid"


def test_whop_sales_keeps_only_our_tagged_payments(monkeypatch, capsys):
    recorder = WhopRecorder({("GET", "/payments"): whop_page([
        whop_payment("pay_ours", "paid"),
        whop_payment("pay_theirs", "paid", managed=False)])})
    run_whop(monkeypatch, recorder, ["sales", "--json"])
    assert recorder.calls[0][3]["statuses"] == ["paid"]  # server narrows, we own-filter
    sales = json.loads(capsys.readouterr().out)
    assert [s["session_id"] for s in sales] == ["pay_ours"]
    sale = sales[0]
    assert set(sale) == {"link_id", "session_id", "title", "amount_usd", "currency", "paid_at"}
    assert sale["link_id"] == "ch_TEST"
    assert sale["amount_usd"] == 19.0
    assert sale["paid_at"] == "2026-08-15T20:00:00Z"


def test_whop_sales_walks_the_cursor(monkeypatch, capsys):
    pages = [whop_page([whop_payment("pay_1", "paid")], has_next=True, end_cursor="cur_1"),
             whop_page([whop_payment("pay_2", "paid")])]

    def payments(_params, query):
        assert query.get("after") == (None if not pages_served else "cur_1")
        pages_served.append(1)
        return pages[len(pages_served) - 1]

    pages_served = []
    recorder = WhopRecorder({("GET", "/payments"): payments})
    run_whop(monkeypatch, recorder, ["sales", "--json"])
    assert len(json.loads(capsys.readouterr().out)) == 2


def test_whop_missing_key_exits_1_names_the_var_and_opens_no_socket(monkeypatch, capsys):
    def boom(*_a, **_k):
        raise AssertionError("no HTTP request may be attempted without WHOP_API_KEY")
    monkeypatch.setattr(pay.urllib.request, "urlopen", boom)
    monkeypatch.setenv("PAYMENT_PROVIDER", "whop")
    monkeypatch.setenv("WHOP_COMPANY_ID", "biz_TEST")   # so the KEY check is what trips
    with pytest.raises(SystemExit) as exc:
        pay.main(["create-link", "--title", "X", "--amount", "19"])
    assert _code(exc) == 1
    assert "WHOP_API_KEY" in capsys.readouterr().err
