"""
The one-command proof against the real Stripe API — TEST MODE ONLY.

    export STRIPE_API_KEY=sk_test_...        # test key, from the Stripe dashboard
    uvx pytest blocks/payments/tests/ -q

Without a test key every test here SKIPS, so the mocked suite stays the default green.
With a LIVE key (`sk_live_`) this module FAILS AT COLLECTION rather than skipping — a live key
must never be able to run a test suite, and a silent skip is exactly how that accident happens.

Completing a checkout (card 4242 4242 4242 4242) is a human/Playwright step documented in SETUP.md,
not automated here: driving a hosted third-party page is a browser test, not a unit test.
"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PAY_PATH = os.path.join(os.path.dirname(HERE), "code", "pay.py")

_spec = importlib.util.spec_from_file_location("pay_live", PAY_PATH)
pay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pay)

# Mirror _stripe_key()'s .strip() and match the prefix case-insensitively: a whitespace-padded
# or oddly-cased live key must hit the hard stop below, never fall through to a silent skip.
KEY = os.environ.get("STRIPE_API_KEY", "").strip()

# Hard stop, evaluated at import: a live key is a bug in the shell, not a reason to skip.
if KEY.lower().startswith("sk_live_"):
    raise RuntimeError(
        "STRIPE_API_KEY is a LIVE key. The live suite refuses to run against live mode — "
        "export a test key (sk_test_...) instead. No test in this repo may move real money.")

live_only = pytest.mark.skipif(
    not KEY.startswith("sk_test_"),
    reason="set STRIPE_API_KEY to a Stripe TEST key (sk_test_...) to run the live suite")


@pytest.fixture(scope="module")
def created_link():
    """One real $19 test-mode payment link, reused by the assertions below."""
    return pay.stripe_create_link("Sunday live-suite probe", 1900, "usd")


@live_only
def test_create_link_returns_a_real_hosted_url(created_link):
    assert created_link["link_id"].startswith("plink_")
    assert created_link["url"].startswith("https://")
    assert created_link["amount"] == 19.0
    assert created_link["currency"] == "usd"


@live_only
def test_new_link_is_unpaid(created_link):
    result = pay.stripe_link_status(created_link["link_id"])
    assert result["status"] == "unpaid"
    assert result["paid"] is False
    assert result["paid_sessions"] == []


@live_only
def test_unpaid_link_is_absent_from_the_sales_scan(created_link):
    """`sales` lists PAID sales only — a freshly created link must not appear until someone pays.
    After the manual 4242 checkout in SETUP.md, this link DOES appear; that is the morning step."""
    sales = pay.stripe_list_sales()
    assert created_link["link_id"] not in {s["link_id"] for s in sales}
    for sale in sales:
        assert set(sale) == {"link_id", "session_id", "title", "amount_usd", "currency", "paid_at"}


@live_only
def test_the_key_in_use_is_a_test_key():
    """Belt and braces: the objects we create must come back livemode=false."""
    product = pay._request("POST", "/v1/products", {"name": "Sunday live-suite mode check"})
    assert product["livemode"] is False
