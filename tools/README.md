# tools/

Developer utilities (not shipped with the app).

## screenshots.py

Regenerates the marketing screenshots and the social/OG card by rendering the
real GUI (`scripts/ui`) in its built-in `#mock` preview mode with a headless
browser, in both light and dark themes.

```bash
python -m playwright install chromium   # once, if not already present
python tools/screenshots.py
```

Outputs (overwritten in place):

- `docs/screenshot-light.png`, `docs/screenshot-dark.png` — used by the README.
- `docs/og-image.png` — the 1200×630 social preview card.

The landing page lives on the **`gh-pages`** branch and keeps its own copies at
the branch root. After regenerating, copy the three files onto `gh-pages` to
refresh the site:

```bash
git checkout gh-pages
git checkout main -- docs/screenshot-light.png docs/screenshot-dark.png docs/og-image.png
git mv -f docs/screenshot-light.png screenshot-light.png
git mv -f docs/screenshot-dark.png  screenshot-dark.png
git mv -f docs/og-image.png         og-image.png
git commit -m "Refresh site screenshots" && git push
```
