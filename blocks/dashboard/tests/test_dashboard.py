"""
Tests for the dashboard's decision-ledger panel (US-2.2).

Two layers, deliberately:

  * **API layer** — pure stdlib, always runs. `/api/decisions` parses the approver's append-only
    JSONL, summarises it, separates agent decisions from bought human judgment, and survives a
    malformed line without blanking the panel.
  * **Browser layer** — Playwright, skips cleanly when it isn't installed (same discipline as
    `blocks/storefront/tests/`: nothing in this repo's suite should fail because a browser wasn't
    provisioned). Proves the panel a judge reads actually renders the seeded entries.

The server reads its config from the environment at import time, so every test launches the real
`server.py` as a subprocess — the entry point a judge will actually run, not an imported copy.

Run:  python3 -m pytest blocks/dashboard/tests/ -q
      uvx --with pytest-playwright pytest blocks/dashboard/tests/ -q      # includes the browser layer
"""
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.dirname(HERE)
SERVER = os.path.join(BLOCK, "code", "server.py")

# A ledger that tells the demo's story in four lines: the policy priced the product, the policy
# refused a spend that would have crossed the daily cap, the policy admitted it could not decide,
# and a bought human answered that one for $8. Plus one corrupt line, because real append-only
# files acquire them.
AGENT_APPROVE = {
    "ts": "2026-08-15T10:04:11Z", "task_id": "t-101",
    "question": "List the Policy Gate Kit at $19?",
    "verdict": "approve", "reason": "Inside the $5-25 band the policy fixes.",
    "policy_clauses_cited": ["P1", "P4"], "mode": "agent",
}
AGENT_REJECT = {
    "ts": "2026-08-15T11:20:02Z", "task_id": "t-102",
    "question": "Buy a $40 ad credit pack to push the storefront?",
    "verdict": "reject", "reason": "Single spend over the $15 per-action ceiling.",
    "policy_clauses_cited": ["P2"], "mode": "agent",
}
AGENT_ESCALATE = {
    "ts": "2026-08-15T12:41:37Z", "task_id": "t-103",
    "question": "A buyer asks for an invoice addressed to their employer. Issue it?",
    "verdict": "escalated", "reason": "No clause covers issuing documents to a third party.",
    "policy_clauses_cited": [], "mode": "agent",
}
HUMAN_ANSWER = {
    "ts": "2026-08-15T13:02:55Z", "task_id": "t-103",
    "question": "A buyer asks for an invoice addressed to their employer. Issue it?",
    "verdict": "approve", "reason": "Standard B2B practice; the sale is unchanged.",
    "policy_clauses_cited": [], "mode": "human", "cost_usd": 8.0, "provider": "terac",
}
SEEDED = [AGENT_APPROVE, AGENT_REJECT, AGENT_ESCALATE, HUMAN_ANSWER]


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _write_ledger(path: str, entries=SEEDED, with_garbage=True) -> str:
    with open(path, "w", encoding="utf-8") as f:
        for i, e in enumerate(entries):
            f.write(json.dumps(e) + "\n")
            if with_garbage and i == 1:
                f.write("{not json at all\n")   # the corrupt line
        f.write("\n")                            # a blank line: ignored, not counted as malformed
    return path


class _Dashboard:
    """The real server.py in a subprocess, on an ephemeral port, pointed at a seeded ledger."""

    def __init__(self, ledger_path: str = None, bind: str = None):
        self.port = _free_port()
        env = dict(os.environ, DASH_PORT=str(self.port))
        env.pop("APPROVER_LEDGER", None)          # never inherit a real ledger from the operator
        if ledger_path:
            env["APPROVER_LEDGER"] = ledger_path
        if bind:
            env["DASH_BIND"] = bind
        self.proc = subprocess.Popen([sys.executable, SERVER], env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self._wait_ready()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _wait_ready(self, timeout=10.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                raise RuntimeError(f"server exited early:\n{self.proc.stdout.read()}")
            try:
                urllib.request.urlopen(self.base_url + "/api/decisions", timeout=0.5).read()
                return
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.05)
        raise RuntimeError("dashboard did not come up in time")

    def get(self, path: str) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))

    def stop(self):
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()


@pytest.fixture(scope="module")
def ledger_file(tmp_path_factory) -> str:
    return _write_ledger(str(tmp_path_factory.mktemp("ledger") / "decisions.jsonl"))


@pytest.fixture(scope="module")
def dash(ledger_file):
    d = _Dashboard(ledger_file)
    yield d
    d.stop()


# ── API layer (stdlib only) ───────────────────────────────────────────────────────────────────
def test_decisions_endpoint_returns_every_seeded_entry(dash):
    """(a) the endpoint exists and returns the ledger, chronological order preserved."""
    d = dash.get("/api/decisions")
    assert d["available"] is True
    assert [e["task_id"] for e in d["decisions"]] == ["t-101", "t-102", "t-103", "t-103"]


def test_summary_separates_policy_decisions_from_bought_judgment(dash):
    """(b) the headline numbers: what the policy decided vs what the company paid a human for."""
    s = dash.get("/api/decisions")["summary"]
    assert s["total"] == 4
    assert s["by_mode"] == {"agent": 3, "human": 1}
    assert s["by_verdict"] == {"approve": 2, "reject": 1, "escalated": 1}
    assert s["human_cost_usd"] == 8.0


def test_malformed_line_is_skipped_not_fatal(dash):
    """(c) one corrupt line must never blank the audit panel — it is counted and stepped over."""
    d = dash.get("/api/decisions")
    assert d["summary"]["malformed_lines"] == 1
    assert len(d["decisions"]) == 4


def test_human_entry_carries_its_cost_and_provider(dash):
    """(d) the money shot: the hired-human decision arrives with what it cost and who supplied it."""
    human = [e for e in dash.get("/api/decisions")["decisions"] if e.get("mode") == "human"]
    assert len(human) == 1
    assert human[0]["cost_usd"] == 8.0
    assert human[0]["provider"] == "terac"


def test_unset_ledger_degrades_quietly():
    """(e) no APPROVER_LEDGER set → available:false, and the rest of the dashboard still serves."""
    d = _Dashboard(ledger_path=None)
    try:
        assert d.get("/api/decisions") == {"available": False, "decisions": []}
        assert "available" in d.get("/api/tasks")        # other endpoints unaffected
    finally:
        d.stop()


def test_missing_ledger_file_degrades_quietly(tmp_path):
    """(f) a configured-but-absent ledger is the pre-first-decision state, not an error."""
    d = _Dashboard(ledger_path=str(tmp_path / "not-created-yet.jsonl"))
    try:
        assert d.get("/api/decisions")["available"] is False
    finally:
        d.stop()


def test_dash_bind_is_configurable(ledger_file):
    """(g) DASH_BIND overrides the loopback default — Superserve's preview router needs this.
    Default behaviour is asserted by every other test in this file, which reaches 127.0.0.1."""
    d = _Dashboard(ledger_file, bind="0.0.0.0")
    try:
        assert d.get("/api/decisions")["available"] is True
    finally:
        d.stop()


# ── Browser layer (skips cleanly without Playwright) ──────────────────────────────────────────
@pytest.fixture()
def page():
    pw = pytest.importorskip(
        "playwright.sync_api",
        reason="pip install pytest-playwright && playwright install chromium")
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        yield pg
        browser.close()


def test_panel_renders_seeded_entries(page, dash):
    """(h) every seeded decision is on the page, with its question and verdict."""
    page.goto(dash.base_url + "/")
    page.wait_for_selector(".dec")
    assert page.locator(".dec").count() == 4
    body = page.locator("#ledger").inner_text()
    for e in SEEDED:
        assert e["question"] in body
    assert "Inside the $5-25 band" in body


def test_panel_shows_policy_clauses_cited(page, dash):
    """(i) a verdict without the clause it cites is not an audit trail."""
    page.goto(dash.base_url + "/")
    page.wait_for_selector(".clause")
    clauses = page.locator("#ledger .clause").all_inner_texts()
    assert "P1, P4" in clauses
    assert "P2" in clauses


def test_panel_marks_who_answered_and_what_it_cost(page, dash):
    """(j) the money shot: an agent-answered row next to a human-answered row carrying its expense."""
    page.goto(dash.base_url + "/")
    page.wait_for_selector(".who.human")
    human = page.locator("#ledger .who.human")
    assert human.count() == 1
    text = human.first.inner_text()
    assert "hired human" in text and "terac" in text and "$8.00" in text
    assert page.locator("#ledger .who").count() == 4      # every row says who answered it


def test_panel_headline_numbers_are_visible(page, dash):
    """(k) the strip a judge reads in two seconds."""
    page.goto(dash.base_url + "/")
    page.wait_for_selector(".strip")
    strip = page.locator(".strip").inner_text()
    for expected in ("4", "3", "1", "$8.00"):
        assert expected in strip


def test_panel_without_ledger_explains_itself(page):
    """(l) unconfigured renders one honest line, not a broken panel or a silent blank."""
    d = _Dashboard(ledger_path=None)
    try:
        page.goto(d.base_url + "/")
        page.wait_for_selector("#ledger .empty")
        assert "APPROVER_LEDGER" in page.locator("#ledger").inner_text()
    finally:
        d.stop()
