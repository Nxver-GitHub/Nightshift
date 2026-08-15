# Storefront — install & operate

> For Anirudh, cold. Pure static site: three HTML files + one JSON file. No server, no keys, no
> build step. Run everything below from the **repo root** unless noted.

## 1. Local preview

```bash
python3 -m http.server 8000 --directory blocks/storefront/site
```

Open `http://localhost:8000/index.html` in a browser. `product.json` is fetched with `fetch()`,
which browsers block over `file://` — always preview through a local server like this, never by
double-clicking the HTML file.

Click through the whole flow once: **index.html → Buy → stub-checkout.html → Simulate successful
payment → thanks.html** (delivery link visible, disclosure visible on both pages).

## 2. Deploy to Render (static site, no API key)

1. Push this repo (or just `blocks/storefront/site/`) to a GitHub repo Render can see.
2. In the Render dashboard: **New → Static Site**.
3. Connect the repo. Set:
   - **Root Directory**: `blocks/storefront/site`
   - **Build Command**: *(leave blank — nothing to build)*
   - **Publish Directory**: `.` (i.e., the root directory above)
4. Deploy. Render gives you a URL like `https://<name>.onrender.com`. Open
   `https://<name>.onrender.com/index.html` and click through the same flow as step 1.

No `RENDER_API_KEY` is needed for this — it's a dashboard click-through, not an API call.

## 3. Point checkout at a real payment link (tomorrow)

Once the `payments` block is wired up:

```bash
python3 blocks/payments/code/pay.py create-link --title "Policy Gate Kit" --amount 19 --currency usd
```

This prints a real checkout URL. Edit `blocks/storefront/site/product.json` and set:

```json
"checkout_url": "https://buy.stripe.com/..."
```

Redeploy (Render auto-deploys on push, or hit "Manual Deploy" in the dashboard). `stub-checkout.html`
is no longer linked from anywhere — it can stay in the repo (harmless, clearly labeled) or be
deleted; nothing else changes.

If the payment provider doesn't host its own thank-you redirect, keep `delivery_url` in
`product.json` pointed at wherever the download actually lives (e.g. a signed URL, a Gumroad link).

## 4. Generate the QR code (once the deployed URL exists)

Any of these works — pick whichever is fastest in the room:

**Online, zero install:** paste the deployed URL into any QR generator (e.g.
`qrcode.show/<url>` returns a PNG directly, or use `api.qrserver.com`:
`https://api.qrserver.com/v1/create-qr-code/?data=<url-encoded-url>`).

**One-liner, local:**
```bash
uvx --from qrcode --with pillow qr "https://<name>.onrender.com/index.html" > storefront-qr.png
```

Print it or display it on a phone/laptop for the in-room sales floor.

## 5. Playwright install + run

The test suite skips cleanly if Playwright isn't installed — it will never fail the rest of the
repo's test run for that reason. To actually run it:

```bash
uvx --with pytest-playwright playwright install chromium   # one-time, ~270MB download
uvx --with pytest-playwright pytest blocks/storefront/tests/ -q
```

Expected: `5 passed`. Without Chromium installed, expected: `5 skipped` (never a failure).

## Operate

- **The only file an agent needs to touch to relaunch this storefront is `product.json`.** New
  title, new price, new copy, new `checkout_url` — `index.html` and `thanks.html` render whatever
  is in it, unedited.
- If the product page ever shows a plain error instead of content, `product.json` is missing,
  unreachable, or not valid JSON — check that first; it is the only moving part.
- Redesign (Lovable) is a later story (US-3.2) and layers on top of this skeleton; it does not
  replace `product.json` as the content seam.

## Safety
No secrets live in this block — there is nothing to leak; it is static HTML with no server-side
code. The disclosure that Nightshift is run by an autonomous agent (policy clause P7) must stay
visible on both `index.html` and `thanks.html`, next to the primary action, whenever this block is
redeployed or redesigned.
