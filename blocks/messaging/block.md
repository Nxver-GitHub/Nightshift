# messaging — iMessage / RCS / SMS, bound by the same policy (US-3.4)

> Outbound over a phone channel, refused by the written policy on exactly the terms email already
> obeys. P6 caps how many messages go out and how often a contact may be touched; P7 requires every
> message to disclose that an agent is sending it. This block reads both out of `policy.md` and
> will not send around them.

## Why it looks like this

The policy already carried outbound caps in its frontmatter — `outbound_daily_cap`,
`outbound_max_touches_per_contact`, `outbound_followup_min_days` — written for the email path.
Nothing enforced them on a phone number, because there was no phone channel. Adding one meant
either duplicating the limits in code (two sources of truth, one of which is not the policy) or
reading the written numbers at run time. This block reads them, the same way `labor.py` reads
`per_action_spend_ceiling_usd` before it agrees to hire anyone.

The consequence worth demonstrating: **edit `policy.md` and the channel obeys the new number on the
next send.** No deploy, no code change. The policy is the control surface.

If the caps are missing from the frontmatter, the block refuses to send at all rather than falling
back to a built-in default. A send channel with no written limit is what P10 forbids.

## Credentials this block DECLARES (names only — values never in this repo)

| Name | Where the value lives | Used for |
|---|---|---|
| `LINQ_API_KEY` | operator's shell | bearer token for api.linqapp.com |
| `LINQ_FROM_NUMBER` | operator's shell | the provisioned sending number, E.164 |

## Files

- `code/message.py` — CLI: `send | quota | log`
- `tests/test_message.py` — offline, transport mocked; no key needed
- `SETUP.md` — runbook

## API surface

Verified against docs.linqapp.com on 2026-08-15, not from memory:

```
POST https://api.linqapp.com/api/partner/v3/chats
Authorization: Bearer <token>
{"from": "+1...", "to": ["+1..."],
 "message": {"preferred_service": "iMessage", "parts": [{"type": "text", "value": "..."}]}}
```

`preferred_service` is `iMessage` (no fallback) or `RCS` (falls back to SMS). **Omitting the field
entirely** activates Linq's full `iMessage → RCS → SMS` chain, which is what `--service auto` does,
and why it sends no key rather than a null. Inbound messages arrive by webhook; this block sends
only, and `replied` on a ledger row is the hook for wiring that up later.

## Status

Sending works and is policy-bound. **Not wired to the prospection queue yet** — this is a CLI an
agent or an operator calls, not an automatic sender. That is deliberate: per the repo's review-mode
rule, a new outbound channel starts as prepare-then-send and is promoted only once proven.
