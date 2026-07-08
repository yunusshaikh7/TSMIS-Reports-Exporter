#!/usr/bin/env python3
"""Regenerate the marketing screenshots and the social/OG card.

Renders the real GUI (scripts/ui) in its built-in ``#mock`` preview mode with a
headless browser and captures it in both themes, then composes the Open Graph
card from the dark capture. Outputs land in ``docs/``:

    docs/screenshot-light.png   docs/screenshot-dark.png   docs/og-image.png

These feed the README's screenshot. The landing page (the ``gh-pages`` branch)
uses its own copies at the repo root, so after regenerating, copy the three
files onto ``gh-pages`` to refresh the site.

Usage (from the repo root):

    python tools/screenshots.py

Requires Playwright (already a project dependency) with Chromium installed:

    python -m playwright install chromium
"""
from __future__ import annotations

import base64
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
UI = (ROOT / "scripts" / "ui" / "index.html").as_uri() + "#mock"
OUT = ROOT / "docs"

# Pick four reports, hide the mock "update available" pill, and clear the log so
# the capture reads as a real, tidy export rather than the mock's demo state.
CLEAN_JS = """
() => {
  const u = document.getElementById('btnUpdate'); if (u) u.style.display = 'none';
  const boxes = document.querySelectorAll('#reportList input[type=checkbox]');
  [0,1,2,3].forEach(i => { if (boxes[i] && !boxes[i].checked) boxes[i].click(); });
  const c = document.getElementById('btnClearLog'); if (c) c.click();
}
"""


def og_html(dark_shot: Path) -> str:
    """The 1200x630 Open Graph card, embedding the dark screenshot.

    The screenshot is inlined as a data: URI — the card is rendered via
    page.set_content(), whose about:blank origin means Chromium BLOCKS file://
    subresources, so a file:// <img> silently renders as a broken-image glyph
    (the bug that shipped an empty app window in the social card until
    v0.21.0). main() additionally asserts the image decoded.
    """
    b64 = base64.b64encode(dark_shot.read_bytes()).decode("ascii")
    shot_src = f"data:image/png;base64,{b64}"
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ width: 1200px; height: 630px; overflow: hidden; display: grid;
    grid-template-columns: 1fr 1fr; align-items: center; color: #e9eef7;
    font-family: "Inter","Segoe UI",Arial,sans-serif;
    background: radial-gradient(900px 520px at 88% 8%, rgba(9,105,218,.35), transparent 60%),
                radial-gradient(700px 460px at 0% 100%, rgba(10,126,164,.28), transparent 55%), #0b0f17; }}
  .left {{ padding: 0 0 0 80px; }}
  .brand {{ display: flex; align-items: center; gap: 14px; margin-bottom: 34px; }}
  .logo {{ width: 56px; height: 56px; border-radius: 14px; display: grid; place-items: center;
    font-weight: 800; font-size: 24px; color: #fff; background: linear-gradient(135deg,#0969da,#38bec9); }}
  .brand b {{ font-size: 26px; font-weight: 600; }}
  h1 {{ font-size: 66px; font-weight: 800; letter-spacing: -2px; line-height: 1.02; }}
  .grad {{ background: linear-gradient(90deg,#4f9dff,#38bec9); -webkit-background-clip: text; background-clip: text; color: transparent; }}
  p {{ margin-top: 26px; font-size: 27px; color: #9aa6b8; max-width: 17ch; line-height: 1.35; }}
  .tags {{ margin-top: 40px; display: flex; gap: 12px; }}
  .tag {{ font-size: 18px; font-weight: 600; color: #cdd6e4; background: rgba(255,255,255,.06);
    border: 1px solid rgba(255,255,255,.12); padding: 9px 16px; border-radius: 999px; }}
  .right {{ position: relative; height: 100%; }}
  .shot {{ position: absolute; top: 50%; left: 40px; transform: translateY(-50%); width: 760px;
    border-radius: 14px; overflow: hidden; border: 1px solid #1d2636; box-shadow: 0 40px 90px rgba(0,0,0,.6); }}
  .bar {{ display: flex; gap: 8px; padding: 11px 14px; background: #111826; border-bottom: 1px solid #1d2636; }}
  .bar i {{ width: 12px; height: 12px; border-radius: 50%; }}
  .bar i:nth-child(1){{background:#ff5f57}}.bar i:nth-child(2){{background:#febc2e}}.bar i:nth-child(3){{background:#28c840}}
  .shot img {{ display: block; width: 100%; }}
</style></head><body>
  <div class="left">
    <div class="brand"><span class="logo">TS</span><b>TSMIS Exporter</b></div>
    <h1>Bulk-export every<br><span class="grad">Caltrans TSMIS route</span></h1>
    <p>All 250+ California routes, in one click.</p>
    <div class="tags"><span class="tag">Open source</span><span class="tag">Windows</span></div>
  </div>
  <div class="right"><div class="shot"><div class="bar"><i></i><i></i><i></i></div>
    <img src="{shot_src}"></div></div>
</body></html>"""


def main() -> None:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme in ("light", "dark"):
            ctx = browser.new_context(
                color_scheme=theme,
                viewport={"width": 1320, "height": 860},
                device_scale_factor=3,
            )
            page = ctx.new_page()
            page.goto(UI, wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.evaluate(CLEAN_JS)
            page.wait_for_timeout(600)
            page.screenshot(path=str(OUT / f"screenshot-{theme}.png"))
            ctx.close()
            print(f"wrote docs/screenshot-{theme}.png")

        # Open Graph card from the dark capture.
        ctx = browser.new_context(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        page = ctx.new_page()
        page.set_content(og_html(OUT / "screenshot-dark.png"), wait_until="networkidle")
        page.wait_for_timeout(800)
        # The whole point of the card is the app window — refuse to write a
        # card whose screenshot didn't decode (see og_html's docstring).
        if not page.evaluate("() => { const i = document.querySelector('.shot img');"
                             " return !!i && i.naturalWidth > 0; }"):
            raise SystemExit("og-image: the embedded screenshot failed to load")
        page.screenshot(path=str(OUT / "og-image.png"))
        ctx.close()
        print("wrote docs/og-image.png")

        browser.close()
    print("\nDone. To refresh the website, copy these onto the gh-pages branch root:")
    print("  screenshot-light.png  screenshot-dark.png  og-image.png")


if __name__ == "__main__":
    main()
