#!/usr/bin/env python3
"""
message — outbound iMessage / RCS / SMS, bound by the same written policy as everything else.

The company already has a policy that caps outreach: P6 sets a daily send cap, a maximum number of
touches per contact, and a minimum gap before a follow-up; P7 requires every outbound message to
disclose that an agent is sending it. Email honours those clauses. Phone numbers did not, because
there was no phone channel. This block adds one and enforces the same clauses on it.

It follows labor.py's pattern exactly: read the numbers out of the policy's frontmatter, refuse
anything the clause does not permit, and append every send to a ledger. The caps are never
hardcoded here — edit the policy and this block obeys the new numbers on the next run.

Commands
    send   --to +15551234567 --text "..." [--service imessage|rcs|auto] [--dry-run]
    quota  [--json]                     what P6 still allows today
    log    [--json] [--limit N]         the send ledger

Config (env)
    LINQ_API_KEY        bearer token for api.linqapp.com          (value never in this repo)
    LINQ_FROM_NUMBER    the provisioned sending number, E.164
    MESSAGING_PROVIDER  linq (default) | manual
    APPROVER_POLICY     policy.md whose frontmatter carries the P6 caps
    MESSAGING_LEDGER    messages.jsonl (default: next to this script)

API surface verified against docs.linqapp.com on 2026-08-15:
    POST https://api.linqapp.com/api/partner/v3/chats
    Authorization: Bearer <token>
    {"from": "+1...", "to": ["+1..."], "message": {"preferred_service": "iMessage",
                                                   "parts": [{"type": "text", "value": "..."}]}}
"""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API_BASE = "https://api.linqapp.com/api/partner/v3"
DEFAULT_PROVIDER = "linq"

# Frontmatter keys this block reads out of the policy. Names match the policy file exactly; if a
# key is missing the block refuses to send rather than inventing a limit.
CAP_DAILY = "outbound_daily_cap"
CAP_TOUCHES = "outbound_max_touches_per_contact"
CAP_GAP_DAYS = "outbound_followup_min_days"

# P7: an outbound message must say an agent is sending it. We look for evidence of that rather than
# an exact string, so the agent can write naturally — but "agent" alone is too weak, so require it
# alongside a word that makes the sentence a disclosure.
DISCLOSURE_HINTS = ("autonomous agent", "ai agent", "an agent", "agent-run", "run by agents",
                    "automated agent", "i am an agent", "this is an agent")

E164 = re.compile(r"^\+[1-9]\d{7,14}$")

SERVICES = {"imessage": "iMessage", "rcs": "RCS", "auto": None}


class MessageError(Exception):
    """Anything that should stop a send with a readable reason and a non-zero exit."""


# ── small helpers ─────────────────────────────────────────────────────────────────────────────
def now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def today() -> str:
    return datetime.date.today().isoformat()


def parse_ts(raw: str):
    """Ledger timestamps are 'YYYY-MM-DD HH:MM'. Anything unreadable is treated as absent rather
    than crashing a send on one malformed historical line."""
    try:
        return datetime.datetime.strptime(raw, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


def resolve_policy(arg=None) -> str:
    if arg:
        return arg
    env = os.environ.get("APPROVER_POLICY")
    if env:
        return env
    # Same default the approver block uses, so both read one file.
    return os.path.abspath(os.path.join(HERE, "..", "..", "approver", "policy", "policy.md"))


def resolve_ledger(arg=None) -> str:
    return arg or os.environ.get("MESSAGING_LEDGER") or os.path.join(HERE, "messages.jsonl")


def read_caps(policy_path: str) -> dict:
    """Pull the P6 numbers out of the policy's flat 'key: value' frontmatter.

    Missing key or unparseable value is fatal on purpose: a send block with no cap is exactly the
    thing P10 forbids, and defaulting to some built-in number would silently replace the written
    policy with this file's opinion."""
    try:
        with open(policy_path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise MessageError(f"cannot read the policy at {policy_path}: {e}. Refusing to send.")

    if not text.startswith("---"):
        raise MessageError(f"{policy_path} has no '---' frontmatter block. Refusing to send.")
    block = text.split("---", 2)[1]

    caps = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        if key in (CAP_DAILY, CAP_TOUCHES, CAP_GAP_DAYS):
            try:
                caps[key] = int(raw.strip())
            except ValueError:
                raise MessageError(f"{key} in the policy is not a whole number ('{raw.strip()}').")

    missing = [k for k in (CAP_DAILY, CAP_TOUCHES, CAP_GAP_DAYS) if k not in caps]
    if missing:
        raise MessageError(
            f"the policy frontmatter is missing {', '.join(missing)}. This block will not send "
            f"without written caps to obey.")
    return caps


def read_ledger(path: str) -> list:
    """Append-only send log. A corrupt line is skipped, never fatal: one bad append must not brick
    the channel, and the counts stay conservative because a skipped line only ever means we
    under-count our own sends... which is why cmd_send warns loudly when it happens."""
    entries, malformed = [], 0
    if not os.path.exists(path):
        return entries
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                malformed += 1
    if malformed:
        print(f"WARNING: {malformed} unreadable line(s) in {path}. Send counts may be low.",
              file=sys.stderr)
    return entries


def ledger_append(entry: dict, path: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── policy checks (P6 and P7) ─────────────────────────────────────────────────────────────────
def check_disclosure(text: str) -> None:
    """P7. A message written to pass as a human is a hard NO under P10, so this is a refusal and
    not a warning."""
    low = text.lower()
    if not any(hint in low for hint in DISCLOSURE_HINTS):
        raise MessageError(
            "P7: every outbound message must disclose that an autonomous agent is sending it, and "
            "this draft does not. Add a sentence saying so (for example: 'I'm an autonomous agent "
            "running Nightshift.') and re-run.")


def check_caps(to: str, caps: dict, entries: list) -> None:
    """P6. Three separate limits, each refused with the number it violated so the reason lands in
    the operator's terminal and not just in a log."""
    sent = [e for e in entries if e.get("status") == "sent"]

    today_count = sum(1 for e in sent if str(e.get("ts", "")).startswith(today()))
    if today_count >= caps[CAP_DAILY]:
        raise MessageError(
            f"P6: {today_count} messages already sent today and the policy's {CAP_DAILY} is "
            f"{caps[CAP_DAILY]}. Refusing.")

    to_contact = [e for e in sent if e.get("to") == to]
    if len(to_contact) >= caps[CAP_TOUCHES]:
        raise MessageError(
            f"P6: {to} has already had {len(to_contact)} touches and the policy allows "
            f"{caps[CAP_TOUCHES]} ever. Refusing.")

    if to_contact:
        last = max((parse_ts(e.get("ts", "")) for e in to_contact
                    if parse_ts(e.get("ts", ""))), default=None)
        if last is not None:
            gap = (datetime.datetime.now() - last).days
            if gap < caps[CAP_GAP_DAYS]:
                raise MessageError(
                    f"P6: last touch to {to} was {gap} day(s) ago and a follow-up needs "
                    f"{caps[CAP_GAP_DAYS]}. Refusing.")

    if any(e.get("to") == to and e.get("replied") for e in entries):
        raise MessageError(
            f"P6: {to} has replied. A reply stops all further sends to that contact. Refusing.")


# ── drivers ───────────────────────────────────────────────────────────────────────────────────
def linq_send(to: str, text: str, service: str) -> dict:
    """POST /chats. One request, stdlib only, same zero-pip idiom as pay.py."""
    token = (os.environ.get("LINQ_API_KEY") or "").strip()
    if not token:
        raise MessageError("LINQ_API_KEY is not set. Export it in this shell; never put it in a file.")
    sender = (os.environ.get("LINQ_FROM_NUMBER") or "").strip()
    if not E164.match(sender):
        raise MessageError(
            f"LINQ_FROM_NUMBER must be an E.164 number like +15551234567 (got '{sender}').")

    message = {"parts": [{"type": "text", "value": text}]}
    wire_service = SERVICES[service]
    if wire_service:                      # omitted entirely means iMessage -> RCS -> SMS fallback
        message["preferred_service"] = wire_service

    body = json.dumps({"from": sender, "to": [to], "message": message}).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/chats", data=body, method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise MessageError(f"Linq returned {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise MessageError(f"could not reach Linq: {e.reason}")


def manual_send(to: str, text: str, service: str) -> dict:
    """No credentials needed. Prints what would go out so the channel is demonstrable, and the
    policy checks above still run — which is the part worth showing."""
    print(f"\n--- manual provider: nothing sent ---\n  to:      {to}\n"
          f"  service: {service}\n  text:    {text}\n")
    return {"manual": True}


DRIVERS = {"linq": linq_send, "manual": manual_send}


def get_driver():
    name = (os.environ.get("MESSAGING_PROVIDER") or DEFAULT_PROVIDER).strip().lower()
    if name not in DRIVERS:
        raise MessageError(
            f"unknown MESSAGING_PROVIDER '{name}' — expected one of: {', '.join(sorted(DRIVERS))}")
    return name, DRIVERS[name]


# ── commands ──────────────────────────────────────────────────────────────────────────────────
def cmd_send(a) -> int:
    to = a.to.strip()
    if not E164.match(to):
        raise MessageError(f"--to must be E.164, like +15551234567 (got '{to}').")
    text = a.text.strip()
    if not text:
        raise MessageError("--text is empty.")
    if a.service not in SERVICES:
        raise MessageError(f"--service must be one of: {', '.join(sorted(SERVICES))}")

    caps = read_caps(resolve_policy(a.policy))
    ledger = resolve_ledger(a.ledger)
    entries = read_ledger(ledger)

    check_disclosure(text)                 # P7 first: cheapest refusal, clearest message
    check_caps(to, caps, entries)          # then P6

    provider, driver = get_driver()
    if a.dry_run:
        print(f"OK dry-run — passes P6 and P7. Would send via {provider} ({a.service}) to {to}.")
        return 0

    response = driver(to, text, a.service)
    ledger_append({"ts": now(), "to": to, "text": text, "service": a.service,
                   "provider": provider, "status": "sent", "replied": False,
                   "response_id": (response or {}).get("id")}, ledger)
    remaining = caps[CAP_DAILY] - sum(1 for e in read_ledger(ledger)
                                      if e.get("status") == "sent" and str(e.get("ts", "")).startswith(today()))
    print(f"OK sent to {to} via {provider} ({a.service}). {remaining} of today's "
          f"{caps[CAP_DAILY]} remaining under P6.")
    return 0


def cmd_quota(a) -> int:
    caps = read_caps(resolve_policy(a.policy))
    entries = [e for e in read_ledger(resolve_ledger(a.ledger)) if e.get("status") == "sent"]
    used = sum(1 for e in entries if str(e.get("ts", "")).startswith(today()))
    contacts = {}
    for e in entries:
        contacts[e.get("to")] = contacts.get(e.get("to"), 0) + 1
    out = {"daily_cap": caps[CAP_DAILY], "sent_today": used,
           "remaining_today": max(0, caps[CAP_DAILY] - used),
           "max_touches_per_contact": caps[CAP_TOUCHES],
           "followup_min_days": caps[CAP_GAP_DAYS],
           "contacts": contacts}
    if a.json:
        print(json.dumps(out, indent=2))
    else:
        print(f"  today: {used}/{caps[CAP_DAILY]} sent, {out['remaining_today']} remaining (P6)")
        print(f"  per contact: max {caps[CAP_TOUCHES]} touches, {caps[CAP_GAP_DAYS]}-day gap")
        for c, n in sorted(contacts.items()):
            print(f"    {c}  {n} touch(es)")
    return 0


def cmd_log(a) -> int:
    entries = read_ledger(resolve_ledger(a.ledger))
    if a.limit:
        entries = entries[-a.limit:]
    if a.json:
        print(json.dumps(entries, indent=2, ensure_ascii=False))
        return 0
    if not entries:
        print("(no messages yet)")
        return 0
    for e in entries:
        print(f"  {e.get('ts')}  {e.get('to')}  [{e.get('service')}/{e.get('provider')}]  "
              f"{str(e.get('text'))[:60]}")
    return 0


def build_parser():
    ap = argparse.ArgumentParser(prog="message.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send", help="send one message, subject to P6 and P7")
    s.add_argument("--to", required=True, help="recipient, E.164 (+15551234567)")
    s.add_argument("--text", required=True, help="message body; must carry the P7 disclosure")
    s.add_argument("--service", default="auto", choices=sorted(SERVICES),
                   help="imessage (no fallback) | rcs (falls back to SMS) | auto (default chain)")
    s.add_argument("--dry-run", action="store_true", help="run the policy checks, send nothing")
    s.add_argument("--policy", default=None, help="policy.md path (beats $APPROVER_POLICY)")
    s.add_argument("--ledger", default=None, help="messages.jsonl (beats $MESSAGING_LEDGER)")
    s.set_defaults(f=cmd_send)

    s = sub.add_parser("quota", help="what P6 still allows today")
    s.add_argument("--json", action="store_true")
    s.add_argument("--policy", default=None)
    s.add_argument("--ledger", default=None)
    s.set_defaults(f=cmd_quota)

    s = sub.add_parser("log", help="the send ledger")
    s.add_argument("--json", action="store_true")
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--ledger", default=None)
    s.set_defaults(f=cmd_log)
    return ap


def main() -> int:
    a = build_parser().parse_args()
    try:
        return a.f(a)
    except MessageError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
