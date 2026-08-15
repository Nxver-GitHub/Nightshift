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
            "metadata": {"managed_by": "sunday-payments"}}


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


@pytest.mark.parametrize("provider", ["dodo", "whop"])
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
    run(monkeypatch, recorder, ["create-link", "--title", "Sunday Playbook",
                                "--amount", "19", "--currency", "USD"])

    # Product -> Price -> Payment Link, in that order (payment_links needs an existing Price ID).
    assert [(m, p) for m, p, _ in recorder.calls] == [
        ("POST", "/v1/products"),
        ("POST", "/v1/prices"),
        ("POST", "/v1/payment_links"),
    ]

    product = recorder.params_for("POST", "/v1/products")
    assert product["name"] == "Sunday Playbook"
    assert product["metadata"]["managed_by"] == "sunday-payments"

    price = recorder.params_for("POST", "/v1/prices")
    assert price["unit_amount"] == 1900             # dollars in, integer cents out
    assert price["currency"] == "usd"               # normalised to lowercase ISO
    assert price["product"] == "prod_TEST"
    assert "recurring" not in price                 # a single sale, not a subscription

    link = recorder.params_for("POST", "/v1/payment_links")
    assert link["line_items"] == [{"price": "price_TEST", "quantity": 1}]
    assert link["metadata"]["managed_by"] == "sunday-payments"
    assert link["metadata"]["title"] == "Sunday Playbook"

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
            "metadata": {"managed_by": "sunday-payments", "title": "Sunday Playbook"}}
    theirs = {"id": "plink_THEIRS", "object": "payment_link", "currency": "usd", "metadata": {}}

    def sessions(params):
        if params.get("payment_link") == "plink_OURS":
            return page([session("cs_paid", "paid", amount_total=1900, created=1_700_000_000),
                         session("cs_open", "unpaid")])
        raise AssertionError("sales must only scan links tagged managed_by=sunday-payments")

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
    assert sale["title"] == "Sunday Playbook"
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
        "metadata": {"managed_by": "sunday-payments"},
        "skipped": None,
    }))
    assert pairs["line_items[0][price]"] == "price_1"
    assert pairs["line_items[0][quantity]"] == "1"
    assert pairs["metadata[managed_by]"] == "sunday-payments"
    assert "skipped" not in pairs


def _code(exc):
    """sys.exit("message") sets code to the string; the process still exits 1."""
    return 1 if isinstance(exc.value.code, str) else exc.value.code
