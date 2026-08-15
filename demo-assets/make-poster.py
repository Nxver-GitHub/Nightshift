#!/usr/bin/env python3
"""
Build the in-room sales poster: a print-ready page with a scannable QR to the checkout link.

Everything but the URL is read from the storefront's product.json, so the poster and the website
can never disagree about the price. The QR is generated locally (qr.py) and inlined as SVG —
nothing is fetched at print time, and it prints crisply at any size.

Usage:
    python3 demo-assets/make-poster.py --url https://buy.stripe.com/xxxx
    python3 demo-assets/make-poster.py            # draft: watermarked, refuses to look printable

Then open demo-assets/poster.html and print it (portrait, no margins, 100% scale).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qr  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PRODUCT = os.path.join(REPO, "blocks", "storefront", "site", "product.json")

# A placeholder that is obviously not a real checkout link, so a draft poster can never be mistaken
# for the real thing if it ends up on a table.
PLACEHOLDER = "https://example.invalid/not-the-real-checkout-link"


def build(url: str, product: dict, draft: bool) -> str:
    # Level H (30% recovery) because this gets printed, taped to a table, and scanned at an angle
    # under bad light by people holding a drink.
    svg = qr.to_svg(qr.encode(url, "H"), box=8, quiet=4)
    price = f"${product['price_usd']}"
    watermark = ""
    if draft:
        watermark = ('<div class="draft">DRAFT — placeholder link, do not print</div>')

    return f"""<!doctype html>
<meta charset="utf-8">
<title>{product['company']} — in-room poster</title>
<style>
  @page {{ size: portrait; margin: 12mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:#fff; color:#000; text-align:center;
         font:16px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,sans-serif;
         display:flex; flex-direction:column; align-items:center; justify-content:center;
         min-height:100vh; padding:24px; }}
  .company {{ font-size:20px; letter-spacing:.22em; text-transform:uppercase; font-weight:600; }}
  h1 {{ font-size:64px; line-height:1.05; margin:14px 0 6px; font-weight:700; letter-spacing:-.02em; }}
  .tagline {{ font-size:22px; max-width:30ch; margin:0 auto 4px; }}
  .price {{ font-size:88px; font-weight:700; margin:10px 0 2px; letter-spacing:-.03em; }}
  .terms {{ font-size:18px; margin-bottom:20px; }}
  .qr {{ width:74mm; height:74mm; margin:0 auto; }}
  .qr svg {{ width:100%; height:100%; display:block; }}
  .scan {{ font-size:26px; font-weight:600; margin-top:14px; }}
  .disclosure {{ font-size:15px; max-width:44ch; margin:18px auto 0; padding:12px 16px;
                 border:2px solid #000; text-align:left; }}
  .disclosure b {{ display:block; margin-bottom:3px; }}
  .draft {{ position:fixed; top:0; left:0; right:0; background:#000; color:#fff;
            font-weight:700; letter-spacing:.1em; padding:8px; font-size:14px; }}
  @media print {{ .draft {{ position:static; }} }}
</style>
{watermark}
<div class="company">{product['company']}</div>
<h1>{product['title']}</h1>
<p class="tagline">{product['tagline']}</p>
<div class="price">{price}</div>
<div class="terms">One ZIP · instant download · no account</div>
<div class="qr">{svg}</div>
<div class="scan">Scan to buy</div>
<div class="disclosure"><b>Disclosure</b>{product['disclosure']}</div>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", help="the canonical checkout link (Stripe Payment Link)")
    ap.add_argument("--out", default=os.path.join(HERE, "poster.html"))
    a = ap.parse_args()

    with open(PRODUCT, encoding="utf-8") as f:
        product = json.load(f)

    draft = not a.url
    url = a.url or PLACEHOLDER
    if draft:
        print("WARNING: no --url given. Building a watermarked DRAFT with a placeholder link.\n"
              "         Re-run with --url once the canonical Payment Link exists.", file=sys.stderr)

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build(url, product, draft))

    print(f"wrote {a.out}")
    print(f"  product: {product['title']} at ${product['price_usd']}")
    print(f"  qr -> {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
