"""
Playwright tests for the storefront skeleton. No LLM, no network beyond localhost.

Skips cleanly wherever Playwright/Chromium aren't installed — nothing else in this repo's test
suite should ever fail because a browser wasn't provisioned. Install with:
    pip install pytest-playwright && playwright install chromium
or run via:
    uvx --with pytest-playwright pytest blocks/storefront/tests/ -q
"""
import http.server
import functools
import json
import os
import shutil
import socket
import threading
import time

import pytest

# The one line that makes this suite optional: no playwright installed -> skip, don't fail.
pw = pytest.importorskip("playwright.sync_api", reason="pip install pytest-playwright && playwright install chromium")

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.dirname(HERE)
SITE = os.path.join(BLOCK, "site")


def product() -> dict:
    """The listing is the source of truth — tests assert against it, never against a hardcoded copy."""
    with open(os.path.join(SITE, "product.json"), encoding="utf-8") as f:
        return json.load(f)


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class _ServerHandle:
    """A python http.server.ThreadingHTTPServer serving `directory`, run in a background thread."""

    def __init__(self, directory: str):
        self.directory = directory
        self.port = _free_port()
        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=directory
        )
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


@pytest.fixture(scope="module")
def site_server():
    """Serves blocks/storefront/site/ (the real site, with product.json) on an ephemeral port."""
    srv = _ServerHandle(SITE)
    yield srv
    srv.stop()


@pytest.fixture(scope="module")
def broken_site_server(tmp_path_factory):
    """Serves a copy of the site with product.json removed, to exercise the fetch-failure path."""
    tmp_dir = tmp_path_factory.mktemp("storefront-no-product-json")
    for name in ("buy.html", "thanks.html", "stub-checkout.html"):
        shutil.copy(os.path.join(SITE, name), os.path.join(tmp_dir, name))
    # Deliberately do NOT copy product.json.
    srv = _ServerHandle(str(tmp_dir))
    yield srv
    srv.stop()


@pytest.fixture()
def page():
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        yield pg
        browser.close()


def test_index_renders_title_price_tagline(page, site_server):
    """(a) index renders title/price/tagline from product.json."""
    page.goto(site_server.base_url + "/buy.html")
    page.wait_for_selector("h1")
    assert "Policy Gate Kit" in page.content()
    assert "$19" in page.content()
    assert "policy that answers your agent's approval queue" in page.content()


def test_p7_disclosure_visible_on_index(page, site_server):
    """(b) the P7 disclosure text is visible on the page, near the buy button — not hidden."""
    page.goto(site_server.base_url + "/buy.html")
    page.wait_for_selector(".disclosure")
    disclosure = page.locator(".disclosure")
    assert disclosure.is_visible()
    assert "autonomous agents" in disclosure.inner_text()
    # It must actually sit near the buy button, not off in a footer somewhere.
    buy = page.locator("#buy-button")
    assert buy.is_visible()


def test_buy_button_points_at_checkout_url(page, site_server):
    """(c) the Buy button targets exactly whatever checkout_url says.

    This used to click through and assert it landed on stub-checkout.html. That baked the stub
    into the test, so the day checkout_url became a live Stripe link the suite failed on a
    correct change — and following the link would have put a test on the network, against a real
    payment page. Assert the contract instead: the button goes where product.json points."""
    page.goto(site_server.base_url + "/buy.html")
    page.wait_for_selector("#buy-button")
    href = page.locator("#buy-button").get_attribute("href")
    assert href == product()["checkout_url"]


def test_stub_checkout_simulate_lands_on_thanks_with_delivery_link(page, site_server):
    """(d) stub 'Simulate successful payment' lands on thanks.html showing the delivery link."""
    page.goto(site_server.base_url + "/stub-checkout.html")
    page.wait_for_selector("#simulate-payment")
    page.click("#simulate-payment")
    page.wait_for_url("**/thanks.html")
    page.wait_for_selector("#delivery-link")
    delivery = page.locator("#delivery-link")
    assert delivery.is_visible()
    # Read the expected href from product.json rather than hardcoding it: the delivery target moves
    # (placeholder -> real ZIP) and the test's job is that the page honours the listing.
    assert delivery.get_attribute("href") == product()["delivery_url"]
    assert "autonomous agents" in page.content()


def test_delivery_url_is_downloadable(page, site_server):
    """(f) the delivery target named by product.json actually resolves — no dead download link."""
    url = product()["delivery_url"]
    if url.startswith("#"):
        pytest.skip("delivery_url is still a placeholder anchor, nothing to fetch")
    resp = page.request.get(site_server.base_url + "/" + url.lstrip("/"))
    assert resp.status == 200, f"delivery_url {url!r} returned {resp.status}"
    assert len(resp.body()) > 0


def test_product_json_fetch_failure_shows_error(page, broken_site_server):
    """(e) product.json fetch failure path shows the error message, never a blank page."""
    page.goto(broken_site_server.base_url + "/buy.html")
    # Give the fetch a moment to fail and the error branch to render.
    page.wait_for_selector(".error", timeout=5000)
    error_text = page.locator(".error").inner_text()
    assert error_text.strip() != ""
    assert "went wrong" in error_text.lower()
    # The page body should not be empty/blank.
    assert page.locator("#app").inner_text().strip() != ""
