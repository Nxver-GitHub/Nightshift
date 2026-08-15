"""
Tests for the messaging block. Offline: the Linq transport is replaced, so no test ever reaches
api.linqapp.com and no test needs a key.

What is worth testing here is not "does an HTTP POST work" — it is that the written policy actually
binds the channel. Every refusal below traces to a clause a judge can read in policy.md.

Run:  python3 -m pytest blocks/messaging/tests/ -q
"""
import importlib.util
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
BLOCK = os.path.dirname(HERE)
MODULE = os.path.join(BLOCK, "code", "message.py")

spec = importlib.util.spec_from_file_location("message", MODULE)
message = importlib.util.module_from_spec(spec)
sys.modules["message"] = message
spec.loader.exec_module(message)

DISCLOSED = "Hi — I'm an autonomous agent running Nightshift. We sell a $19 policy kit."
UNDISCLOSED = "Hi, we sell a $19 policy kit for agent loops. Interested?"

POLICY = """---
outbound_daily_cap: 3
outbound_max_touches_per_contact: 2
outbound_followup_min_days: 2
---
# policy
"""


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """A policy with small caps and an empty ledger, wired through the env the block reads."""
    p = tmp_path / "policy.md"
    p.write_text(POLICY, encoding="utf-8")
    ledger = tmp_path / "messages.jsonl"
    monkeypatch.setenv("APPROVER_POLICY", str(p))
    monkeypatch.setenv("MESSAGING_LEDGER", str(ledger))
    monkeypatch.setenv("MESSAGING_PROVIDER", "manual")
    monkeypatch.delenv("LINQ_API_KEY", raising=False)
    return {"policy": str(p), "ledger": str(ledger)}


def run(argv):
    """Drive the real CLI, returning its exit code."""
    parser = message.build_parser()
    a = parser.parse_args(argv)
    try:
        return a.f(a)
    except message.MessageError as e:
        return ("error", str(e))


def sent_lines(ledger):
    if not os.path.exists(ledger):
        return []
    return [json.loads(x) for x in open(ledger, encoding="utf-8") if x.strip()]


# ── P7: disclosure ────────────────────────────────────────────────────────────────────────────
def test_undisclosed_message_is_refused(env):
    r = run(["send", "--to", "+15551230001", "--text", UNDISCLOSED])
    assert r[0] == "error" and "P7" in r[1]
    assert sent_lines(env["ledger"]) == []


def test_disclosed_message_sends(env):
    assert run(["send", "--to", "+15551230001", "--text", DISCLOSED]) == 0
    rows = sent_lines(env["ledger"])
    assert len(rows) == 1 and rows[0]["status"] == "sent"


# ── P6: caps ──────────────────────────────────────────────────────────────────────────────────
def test_daily_cap_refuses_the_fourth_send(env):
    for i in range(3):
        assert run(["send", "--to", f"+1555123000{i}", "--text", DISCLOSED]) == 0
    r = run(["send", "--to", "+15551230009", "--text", DISCLOSED])
    assert r[0] == "error" and "outbound_daily_cap" in r[1]


def test_second_touch_needs_the_followup_gap(env):
    assert run(["send", "--to", "+15551230001", "--text", DISCLOSED]) == 0
    r = run(["send", "--to", "+15551230001", "--text", DISCLOSED])
    assert r[0] == "error" and "follow-up needs" in r[1]


def test_touch_cap_refuses_a_third_contact_ever(env):
    """Two historical touches, both old enough to clear the gap. The third is still refused."""
    with open(env["ledger"], "w", encoding="utf-8") as f:
        for ts in ("2026-08-01 10:00", "2026-08-05 10:00"):
            f.write(json.dumps({"ts": ts, "to": "+15551230001", "text": DISCLOSED,
                                "service": "auto", "provider": "manual",
                                "status": "sent", "replied": False}) + "\n")
    r = run(["send", "--to", "+15551230001", "--text", DISCLOSED])
    assert r[0] == "error" and "touches" in r[1]


def test_a_reply_stops_all_further_sends(env):
    with open(env["ledger"], "w", encoding="utf-8") as f:
        f.write(json.dumps({"ts": "2026-08-01 10:00", "to": "+15551230001", "text": DISCLOSED,
                            "service": "auto", "provider": "manual",
                            "status": "sent", "replied": True}) + "\n")
    r = run(["send", "--to", "+15551230001", "--text", DISCLOSED])
    assert r[0] == "error" and "replied" in r[1]


# ── the policy is the source of the numbers ───────────────────────────────────────────────────
def test_missing_caps_in_policy_refuse_to_send(tmp_path, monkeypatch):
    """A send channel with no written cap is exactly what P10 forbids, so this must not fall back
    to a built-in default."""
    p = tmp_path / "policy.md"
    p.write_text("---\nunrelated: 1\n---\n", encoding="utf-8")
    monkeypatch.setenv("APPROVER_POLICY", str(p))
    monkeypatch.setenv("MESSAGING_LEDGER", str(tmp_path / "m.jsonl"))
    monkeypatch.setenv("MESSAGING_PROVIDER", "manual")
    r = run(["send", "--to", "+15551230001", "--text", DISCLOSED])
    assert r[0] == "error" and "missing" in r[1]


def test_editing_the_policy_changes_the_cap(env):
    """The caps are not hardcoded: raise the number in the file and the block obeys the new one."""
    assert run(["send", "--to", "+15551230001", "--text", DISCLOSED]) == 0
    assert run(["send", "--to", "+15551230002", "--text", DISCLOSED]) == 0
    assert run(["send", "--to", "+15551230003", "--text", DISCLOSED]) == 0
    assert run(["send", "--to", "+15551230004", "--text", DISCLOSED])[0] == "error"
    open(env["policy"], "w", encoding="utf-8").write(POLICY.replace("cap: 3", "cap: 4"))
    assert run(["send", "--to", "+15551230004", "--text", DISCLOSED]) == 0


# ── input validation and transport ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("bad", ["5551234567", "+1 555 123 4567", "", "not-a-number"])
def test_non_e164_recipients_are_refused(env, bad):
    assert run(["send", "--to", bad, "--text", DISCLOSED])[0] == "error"


def test_dry_run_checks_policy_but_sends_nothing(env):
    assert run(["send", "--to", "+15551230001", "--text", DISCLOSED, "--dry-run"]) == 0
    assert sent_lines(env["ledger"]) == []


def test_dry_run_still_refuses_an_undisclosed_draft(env):
    assert run(["send", "--to", "+15551230001", "--text", UNDISCLOSED, "--dry-run"])[0] == "error"


def test_linq_driver_sends_the_documented_payload(env, monkeypatch):
    """The wire format, pinned against docs.linqapp.com (fetched 2026-08-15). If Linq changes
    shape this test tells us, instead of a 400 in front of a customer."""
    captured = {}

    class FakeResponse:
        def read(self): return b'{"id": "chat_123"}'
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["method"] = req.get_method()
        captured["headers"] = {k.lower(): v for k, v in req.headers.items()}
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setenv("MESSAGING_PROVIDER", "linq")
    monkeypatch.setenv("LINQ_API_KEY", "test-token")
    monkeypatch.setenv("LINQ_FROM_NUMBER", "+15550000000")
    monkeypatch.setattr(message.urllib.request, "urlopen", fake_urlopen)

    assert run(["send", "--to", "+15551230001", "--text", DISCLOSED, "--service", "imessage"]) == 0
    assert captured["url"] == "https://api.linqapp.com/api/partner/v3/chats"
    assert captured["method"] == "POST"
    assert captured["headers"]["authorization"] == "Bearer test-token"
    assert captured["body"] == {
        "from": "+15550000000",
        "to": ["+15551230001"],
        "message": {"preferred_service": "iMessage",
                    "parts": [{"type": "text", "value": DISCLOSED}]},
    }


def test_auto_service_omits_preferred_service(env, monkeypatch):
    """Omitting the field is what activates Linq's iMessage -> RCS -> SMS fallback chain, so
    'auto' must send no key at all rather than a null or a string."""
    captured = {}

    class FakeResponse:
        def read(self): return b"{}"
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def fake_urlopen(req, timeout=None):
        captured["body"] = json.loads(req.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setenv("MESSAGING_PROVIDER", "linq")
    monkeypatch.setenv("LINQ_API_KEY", "t")
    monkeypatch.setenv("LINQ_FROM_NUMBER", "+15550000000")
    monkeypatch.setattr(message.urllib.request, "urlopen", fake_urlopen)

    assert run(["send", "--to", "+15551230001", "--text", DISCLOSED, "--service", "auto"]) == 0
    assert "preferred_service" not in captured["body"]["message"]


def test_missing_key_is_a_clean_refusal_not_a_traceback(env, monkeypatch):
    monkeypatch.setenv("MESSAGING_PROVIDER", "linq")
    monkeypatch.delenv("LINQ_API_KEY", raising=False)
    r = run(["send", "--to", "+15551230001", "--text", DISCLOSED])
    assert r[0] == "error" and "LINQ_API_KEY" in r[1]


def test_bad_from_number_is_refused_before_any_request(env, monkeypatch):
    monkeypatch.setenv("MESSAGING_PROVIDER", "linq")
    monkeypatch.setenv("LINQ_API_KEY", "t")
    monkeypatch.setenv("LINQ_FROM_NUMBER", "5550000000")
    r = run(["send", "--to", "+15551230001", "--text", DISCLOSED])
    assert r[0] == "error" and "E.164" in r[1]


def test_quota_reports_what_the_policy_allows(env, capsys):
    run(["send", "--to", "+15551230001", "--text", DISCLOSED])
    capsys.readouterr()                     # drop the send's own output before capturing the JSON
    run(["quota", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert out["daily_cap"] == 3 and out["sent_today"] == 1 and out["remaining_today"] == 2
    assert out["contacts"]["+15551230001"] == 1
