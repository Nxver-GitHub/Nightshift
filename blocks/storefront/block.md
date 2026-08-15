# storefront

> A pure-static product page, checkout hand-off, and thank-you page. No server, no keys, no build
> step — one JSON file is the entire content seam. What ships tonight and what an agent rewrites
> tomorrow are the same three HTML files; only `product.json` changes.

## What it gives you
A phone-first storefront a stranger can open from a QR code: a product page with title, price,
copy and a large Buy button; a checkout hand-off; and a thank-you page with the delivery link. The
same three static pages read every field — including the P7 disclosure that the company is run by
an autonomous agent — from `site/product.json`, so relaunching with new product content (a new
title, a different price, longer copy) is a data edit, never an HTML edit.

## What it needs
- **Tools / accounts**: none tonight. A static file host (Render static site, or `python3 -m
  http.server` for local preview) is enough — no API key required to deploy a static site on Render.
- **Config the agent must fill**: nothing in the environment. The only seam is the content of
  `site/product.json` itself — `title`, `price_usd`, `currency`, `tagline`, `copy`, `checkout_url`,
  `delivery_url`, `company`, `disclosure`. Tomorrow: point `checkout_url` at a real link printed by
  `blocks/payments/code/pay.py create-link` once that block is wired up.
- **Depends on blocks**: none tonight (`site/stub-checkout.html` stands in for a real checkout).
  Tomorrow, `payments` (for the real `checkout_url`).

## What's in this block
- `site/product.json` — the single content seam. Every field the pages render.
- `site/index.html` — the product page. Fetches `product.json` client-side; renders title, price,
  tagline, copy, the Buy button, and the disclosure visibly beside it. Plain error text (never a
  blank page) if the fetch fails.
- `site/thanks.html` — post-checkout landing page: thank-you message, the delivery link, the
  disclosure again, and a note that the payment provider sends the receipt separately.
- `site/stub-checkout.html` — tonight's stand-in for a real checkout page. Clearly labeled TEST
  STAND-IN; one button that lands on `thanks.html`. Removed from the flow tomorrow by pointing
  `checkout_url` at a real payment link — no HTML changes required.
- `tests/test_storefront.py` — pytest + Playwright. Skips cleanly (does not fail) wherever
  Playwright/Chromium aren't installed.

## How the agent installs it
1. Copy `site/` to wherever it will be hosted (or deploy the folder directly — see `SETUP.md`).
2. Overwrite `site/product.json` with the real product's title, price, copy, and (once available)
   the real `checkout_url` from the `payments` block. Never edit `index.html`/`thanks.html` to do
   this — they render whatever `product.json` says.
3. Deploy as a static site (Render, or any static host). No server code, no env vars, no API key.
4. Verify end-to-end once deployed: open the URL on a phone, click Buy, complete checkout, confirm
   the thank-you page shows the delivery link — before pointing a QR code at it.

## Safety
This block never touches money, credentials, or another block's files — it only renders whatever
`product.json` says. It must never omit or bury the P7 disclosure (that the company is run by an
autonomous agent): both `index.html` and `thanks.html` render it visibly next to the primary
action, not in a footer or a tooltip. `stub-checkout.html` must never be mistaken for a real
checkout — it stays clearly labeled TEST STAND-IN until `checkout_url` points at a real payment
link, at which point it simply falls out of the flow.
