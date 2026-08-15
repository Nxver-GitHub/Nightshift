# Messaging — install & operate

> Written for a stranger. Read-only on the policy, append-only on its own ledger, no secrets in
> any file.

## 1. Get a Linq account and a sending number

1. Sign up at linqapp.com and open the Partner API section.
2. Create an API token. It is a bearer token used as `Authorization: Bearer <token>`.
3. Provision (or confirm) a sending number. You need it in **E.164** form: `+15551234567`.

## 2. Put both values in `.env`

`.env` sits at the repo root, is gitignored, and is where every other credential in this project
already lives. Add:

```
LINQ_API_KEY=...
LINQ_FROM_NUMBER=+15551234567
MESSAGING_PROVIDER=linq
```

Then load it into the shell you are working in — once, not per key:

```bash
set -a; source .env; set +a
```

Editing `.env` does not affect a terminal that is already open, so re-run that line after any
change. Never commit `.env`, and never paste a key into a chat or an issue.

## 3. Check what the policy currently allows

```bash
python3 blocks/messaging/code/message.py quota
```

Reads the caps out of `policy.md`. If it errors saying the frontmatter is missing keys, that is the
block refusing to operate without written limits — add them to the policy, not to the code.

## 4. Dry-run before you send anything

```bash
python3 blocks/messaging/code/message.py send \
  --to +15551234567 \
  --text "I'm an autonomous agent running Nightshift. We sell a \$19 policy kit: <url>" \
  --dry-run
```

`--dry-run` runs every policy check and sends nothing. A draft without the P7 disclosure is refused
here, which is the cheapest place to find out.

## 5. Send

Drop `--dry-run`. Pick a protocol with `--service`:

| `--service` | Behaviour |
|---|---|
| `auto` (default) | iMessage → RCS → SMS fallback chain |
| `imessage` | iMessage only, no fallback |
| `rcs` | RCS, falling back to SMS, never iMessage |

Every send appends to `messages.jsonl` next to the script. That ledger is what the P6 counts are
computed from, so do not hand-edit it; if a line is unreadable the block warns and counts
conservatively.

## 6. When someone replies

A reply stops all further sends to that contact (P6). Inbound arrives by webhook, which this block
does not yet receive, so for now mark it by hand:

```bash
# set "replied": true on that contact's row in messages.jsonl
```

Until the webhook is wired, treat that as an operator responsibility, and check `log` before any
follow-up.

## Safety

- The caps and the disclosure requirement come from `policy.md`. This block never hardcodes them
  and refuses to run if they are absent.
- It cannot send to a contact who has replied, exceed the daily cap, exceed the per-contact touch
  limit, or follow up sooner than the policy's gap.
- It sends only. No deletion, no account changes, no billing.
- Testing needs no key: the suite mocks the transport.
