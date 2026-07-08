# Website — the `gh-pages` landing page

A single-screen marketing/landing page for TSMIS Reports Exporter, served by
**GitHub Pages** from the **`gh-pages`** branch at
`https://yunusshaikh7.github.io/TSMIS-Reports-Exporter/`.

It is deliberately **separate from `main`**: `gh-pages` is an orphan branch that
holds *only* the site, so the app code and the `docs/` knowledge library never mix
with web assets. The repo's "About → Website" and the SignPath Foundation
application both point at this URL (a real, indexable homepage was a SignPath
eligibility requirement).

## Branch contents (`gh-pages` root)

| File | Purpose |
|---|---|
| `index.html` | The whole page — self-contained HTML/CSS/JS, no build step. |
| `screenshot-light.png` / `screenshot-dark.png` | App screenshots, swapped by theme. |
| `og-image.png` | 1200×630 social/preview card (`og:image` + `twitter:card`). |
| `favicon.svg` / `apple-touch-icon.png` | Browser-tab + iOS icons (the "TS" mark). |
| `sitemap.xml` / `robots.txt` | Search-indexing hints (see *SEO* below). |
| `.nojekyll` | Disables Jekyll so the static files are served as-is. |

## Pages setup (one-time, in repo Settings)

**Settings → Pages → Build and deployment → Deploy from a branch → Branch:
`gh-pages` / `(root)`.** Project pages live under `/TSMIS-Reports-Exporter/`, which
is why the canonical URL and OG tags use that path.

## Layout & behavior

- **Single screen, no scroll.** A flex column (`nav` / `hero` / `footer`) pinned to
  `100vh`; the hero is a two-column grid (copy left, framed screenshot right).
  Verified to fit at 1366×768 and 1900×950 in both themes. Below 860px it stacks
  and scrolls normally (forcing fixed height there would crop content).
- **Download button** resolves the latest **standard `…-win64.zip`** live via the
  GitHub releases API (`/repos/:owner/:repo/releases/latest`, matches the asset
  ending `-win64.zip`, excludes `-with-browser`/`-batch-source`). The `href`
  falls back to the `/releases/latest` page, so it still works with JS off or the
  API unreachable. A "Latest release: vX.Y.Z" label is filled from the same call.
- **Theme toggle** cycles **System → Light → Dark** (nav, top-right). Preference is
  stored in `localStorage["tsmis-site-theme"]`; an inline `<head>` script applies
  the effective theme before first paint (no flash). CSS keys off
  `:root[data-theme="dark"]`, with a `prefers-color-scheme` media block as the
  no-JS fallback. Theme changes crossfade (background/text/borders + the
  screenshot, which is two stacked `<img>` with opacity transitions).

## Regenerating the screenshots / OG card

`tools/screenshots.py` (on `main`) renders the real GUI (`scripts/ui`) in its
built-in `#mock` mode, both themes at 3× device scale, and composes the OG card —
outputs to `docs/` (`screenshot-light.png`, `screenshot-dark.png`, `og-image.png`).
The README uses the `docs/` copies; the website keeps its own copies at the
`gh-pages` root. After regenerating, copy the three files onto `gh-pages` (steps in
`tools/README.md`) **and bump the `?v=` query on the two `og-image.png` meta URLs**
(`og:image` + `twitter:image`; currently `?v=2`) so social scrapers re-fetch the
card instead of serving their cached copy. Requires Playwright + Chromium
(`python -m playwright install chromium`).

The card embeds the dark screenshot as a **data: URI** and the script asserts the
image actually decoded — the v0.19.2–v0.20.x cards shipped with an EMPTY app
window because a `file://` `<img>` on a `set_content` (about:blank-origin) page is
silently blocked by Chromium (fixed v0.21.0; see `docs/lessons.md` §12).

## SEO / discoverability

- The **sitemap** can be submitted directly in **Google Search Console** (add the
  Pages URL as a URL-prefix property, verify via the HTML-tag method, then *Request
  indexing* + submit `sitemap.xml`). This is the real indexing lever.
- **Caveat:** `robots.txt` on a *project* page (`/TSMIS-Reports-Exporter/robots.txt`)
  is **not authoritative** — crawlers only honor `robots.txt` at the domain root
  (`yunusshaikh7.github.io/robots.txt`, which belongs to the user site). It's
  harmless here; the Search Console submission is what counts.

## Conventions

- Keep it **single-file and no-build** (`index.html` only) and **single-screen /
  no-scroll** on desktop — re-check both themes at a laptop and a wide size after
  changes.
- The page is **internal-tool framed**: no "Free" claims, no pricing. "Open source"
  is fine (public MIT repo).
- Never let the toggle reintroduce a flash — keep the pre-paint `<head>` script.
