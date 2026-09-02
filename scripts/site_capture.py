"""Capture the TSMIS report page's source for troubleshooting (v0.26.0; made
exhaustive 2026-09-02).

Automates the manual devtools ▸ Sources walk the maintainer does today: sign in
with the saved session, open the active site's report page, and save — into ONE
dated folder — the raw page HTML (as `index.html`), the rendered DOM, and EVERY
same-origin file the page uses: the scripts and stylesheets the DOM loaded, plus
every relative file name found in the page and inside the fetched files
themselves (the report modules the page inserts with `document.write`,
`config.js`, `debug.js`, images, the notes a comment points at, …). Discovery
repeats over each newly fetched text file until nothing new turns up, so a
module that references another module is followed. Files keep their site names
(`shared.js`, not a flattened URL) and the manifest records the site's
BUILD_DATE, its CONFIG env/src and a SHA-256 per file, so the folder can be
handed over as-is.

The output is the selector/label ground truth used to keep the app tracking site
changes; it is LOCAL diagnostic data (the TSMIS source is Caltrans-internal —
the capture lands under output/ and is never bundled, uploaded, or committed
anywhere by the app; it deliberately writes no archive — `evidence.py` is the
one module that builds a zip, by design). Third-party URLs (CDNs, monitoring
agents) are listed in the manifest but never fetched.

Console-free like the rest of the core: progress via events.on_log, cancel
honored between fetches, ConsolidateResult returned. Only gui_api drives it.
"""
import hashlib
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from events import ConsolidateResult, Events
from paths import OUTPUT_ROOT, today_str

log = logging.getLogger("tsmis.site_capture")

CAPTURE_DIRNAME = "site-capture"
_MANIFEST = "_capture_info.txt"
_PAGE_RAW = "index.html"                 # the manual captures' name for the page
_PAGE_DOM = "page (rendered DOM).html"
# The page finishes building its menus with a little post-load JS; a short fixed
# settle keeps the rendered-DOM snapshot representative without a networkidle
# wait (which long-polling keeps from ever firing).
_SETTLE_S = 2.0
_FETCH_TIMEOUT_MS = 30_000
_NAME_MAX = 120
# A runaway reference scan (a script that names hundreds of files) can't turn
# the capture into a crawl.
_MAX_FILES = 400

# The file kinds worth following when the page or a fetched file names one — the
# site's real vocabulary (HTML / JS / CSS, the markdown notes its modules point
# at, JSON, images, fonts, source maps). A reference must stand at a token
# boundary and be RELATIVE (a name preceded by `/`, `.`, `:` or a word character
# is the tail of a longer path or of an absolute URL, so a CDN URL's own
# `xlsx.full.min.js` never reads as a site file), and must not be a METHOD CALL
# (`rows.map(`, `resp.json(` — JS that merely looks like `x.map` / `x.json`).
_REF_EXTS = r"js|css|html?|json|md|txt|png|jpe?g|gif|svg|ico|webp|woff2?|ttf|map"
_REF_RE = re.compile(
    r"(?<![\w/.:@-])(/?(?:[\w-]+/)*[\w-][\w.-]*\.(?:" + _REF_EXTS + r"))"
    r"(?![\w.-]|\s*\(|\s*://)",
    re.I)
# The fetched files whose TEXT is scanned for further references.
_TEXT_EXTS = {".js", ".css", ".html", ".htm", ".md", ".txt", ".json", ".map"}
_BUILD_DATE_RE = re.compile(r"BUILD_DATE\s*=\s*['\"]([^'\"]+)['\"]")


def capture_root():
    return OUTPUT_ROOT / CAPTURE_DIRNAME


def _same_origin(url, page_url):
    a, b = urlsplit(url), urlsplit(page_url)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def _safe_name(url):
    """A flat, traversal-proof filename from a resource URL: the path segments
    joined with '__' (so provenance stays readable), every character outside
    [A-Za-z0-9._-] replaced, length capped. A query string keeps the name from
    colliding via a short suffix. The fallback spelling when two different URLs
    would share a clean name."""
    parts = urlsplit(url)
    path = parts.path.strip("/") or "index"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", path.replace("/", "__"))
    name = name.strip("._") or "resource"
    if parts.query:
        name += "__q" + re.sub(r"[^A-Za-z0-9]+", "", parts.query)[:24]
    return name[:_NAME_MAX]


def _clean_name(url, taken):
    """The file's own name on the site (`shared.js`), the way a manual devtools
    capture names it: the URL path's last segment with the `?v=` cache-buster
    dropped, sanitized to [A-Za-z0-9._-] and length-capped, never traversal-
    capable. `taken` maps names already assigned to their URL; when a DIFFERENT
    url would reuse a name, the flattened `_safe_name` (path + query) is used
    instead so nothing is overwritten."""
    base = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")[:_NAME_MAX] or "resource"
    if taken.get(name) not in (None, url):
        name = _safe_name(url)
    return name


def _canonical(url):
    """The identity a site file is deduplicated by: scheme + host + path, with
    the query (`?v=<build>`) and fragment dropped — `shared.js?v=2026-08-19`
    from the DOM and `shared.js` from a `document.write` string are one file."""
    p = urlsplit(url)
    return f"{p.scheme}://{p.netloc}{p.path}"


def _find_refs(text, base_url):
    """Every relative file name mentioned in `text` (HTML or a fetched script /
    stylesheet), resolved against `base_url` — the `document.write` module
    list, a `fetch('DEBUG.md')`, an `<img src>`, a CSS `url(...)`. Absolute
    URLs are left to the DOM walk (and the same-origin filter). Ordered by
    first mention, de-duplicated by canonical identity."""
    out, seen = [], set()
    for m in _REF_RE.finditer(text or ""):
        ref = m.group(1)
        if ref.lower().startswith(("http:", "https:", "data:")):
            continue
        url = urljoin(base_url, ref)
        key = _canonical(url)
        if key in seen:
            continue
        seen.add(key)
        out.append(url)
    return out


def _build_date(html):
    """The page's BUILD_DATE stamp (`const BUILD_DATE = '2026-08-19 09:35'`),
    or None when the page doesn't carry one."""
    m = _BUILD_DATE_RE.search(html or "")
    return m.group(1).strip() if m else None


def _is_text_name(name):
    return Path(name).suffix.lower() in _TEXT_EXTS


# The DOM walk that lists what the page actually loaded: external scripts,
# stylesheets (+ icons/preloads), images, frames and embedded objects — the
# files the maintainer downloads by hand today, whatever tag loaded them.
_LIST_RESOURCES_JS = """
() => {
  const out = new Set();
  for (const s of document.scripts) if (s.src) out.add(s.src);
  for (const l of document.querySelectorAll("link[href]")) out.add(l.href);
  for (const el of document.querySelectorAll("img[src], iframe[src], source[src], video[src], audio[src]"))
    out.add(el.src);
  for (const o of document.querySelectorAll("object[data]")) out.add(o.data);
  return [...out];
}
"""

# The site's own idea of which environment / data source it is serving.
_CONFIG_JS = """
() => {
  try {
    return { env: String(CONFIG.env), src: String(CONFIG.src),
             service: String(CONFIG.mapServiceUrl || '') };
  } catch (e) { return null; }
}
"""


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8", errors="replace")
    path.write_bytes(data)
    return len(data)


def _sha256(data):
    if isinstance(data, str):
        data = data.encode("utf-8", errors="replace")
    return hashlib.sha256(data).hexdigest()


class _Walk:
    """What one capture walk produced (mutable while the walk runs, so an
    exception mid-walk still leaves the partial record for the manifest)."""

    def __init__(self):
        self.saved = []        # (name, bytes, sha256)
        self.failed = []       # (url, why)
        self.foreign = []      # third-party URLs seen, never fetched
        self.build_date = None
        self.config = None
        self.cancelled = False


def _snapshot_and_walk(ctx, page, out_dir, events, walk=None):
    """Everything after sign-in: save the page (raw `index.html` + rendered
    DOM), read its BUILD_DATE + CONFIG, then fetch every same-origin file the
    page uses — the DOM's own scripts/styles/images plus every relative file
    name mentioned in the page or in any fetched text file, followed until
    nothing new turns up (bounded by `_MAX_FILES`). Returns the `_Walk`
    record; `walk.cancelled` is set when the user cancelled between fetches.
    Kept free of sign-in so it can be exercised against a served copy of the
    site source."""
    walk = walk or _Walk()
    page_url = page.url
    page_key = _canonical(page_url)

    events.on_log("Saving the page (raw HTML + rendered DOM)…")
    dom = page.content()
    n = _write(out_dir / _PAGE_DOM, dom)
    walk.saved.append((_PAGE_DOM, n, _sha256(dom)))
    raw_text = ""
    try:
        raw = ctx.request.get(page_url, timeout=_FETCH_TIMEOUT_MS)
        if raw.ok:
            body = raw.body()
            n = _write(out_dir / _PAGE_RAW, body)
            walk.saved.append((_PAGE_RAW, n, _sha256(body)))
            raw_text = body.decode("utf-8", errors="replace")
        else:
            walk.failed.append((page_url, f"HTTP {raw.status}"))
    except Exception as e:  # noqa: BLE001 — the rendered DOM above is the primary artifact
        log.warning("site capture: raw page fetch failed: %s: %s",
                    type(e).__name__, e)
        walk.failed.append((page_url, type(e).__name__))
    walk.build_date = _build_date(raw_text) or _build_date(dom)
    try:
        walk.config = page.evaluate(_CONFIG_JS)
    except Exception as e:  # noqa: BLE001 — a diagnostic extra; the files are the capture
        log.info("site capture: CONFIG not readable (%s)", type(e).__name__)
        walk.config = None
    if walk.build_date:
        events.on_log(f"Site build: {walk.build_date}")
    if walk.config:
        events.on_log(f"Site CONFIG: env={walk.config.get('env')} "
                      f"src={walk.config.get('src')}")

    # Seed the worklist: what the DOM loaded + every relative name the page
    # text mentions (the document.write'd modules included).
    try:
        dom_urls = [u for u in (page.evaluate(_LIST_RESOURCES_JS) or [])
                    if isinstance(u, str)]
    except Exception as e:  # noqa: BLE001 — the text scan below still finds the files
        log.warning("site capture: DOM resource walk failed (%s)", type(e).__name__)
        dom_urls = []
    queue, seen = [], {page_key}

    def _offer(u):
        key = _canonical(u)
        if key in seen:
            return
        seen.add(key)
        if _same_origin(u, page_url):
            queue.append(u)
        else:
            walk.foreign.append(u)

    for u in dom_urls + _find_refs(raw_text, page_url) + _find_refs(dom, page_url):
        _offer(u)
    events.on_log("Fetching every same-origin file the page uses"
                  + (f" ({len(walk.foreign)} third-party skipped)…"
                     if walk.foreign else "…"))
    taken = {_PAGE_RAW: page_url, _PAGE_DOM: "", _MANIFEST: ""}
    i = 0
    while queue and i < _MAX_FILES:
        if events.is_cancelled():
            walk.cancelled = True
            return walk
        u = queue.pop(0)
        i += 1
        name = _clean_name(u, taken)
        taken[name] = u
        try:
            r = ctx.request.get(u, timeout=_FETCH_TIMEOUT_MS)
            if not r.ok:
                walk.failed.append((u, f"HTTP {r.status}"))
                events.on_log(f"  [{i:>2}] {name}: HTTP {r.status}")
                continue
            body = r.body()
            n = _write(out_dir / name, body)
            walk.saved.append((name, n, _sha256(body)))
            events.on_log(f"  [{i:>2}] {name} ({n:,} bytes)")
            if _is_text_name(name):
                for ref in _find_refs(body.decode("utf-8", errors="replace"), u):
                    _offer(ref)
        except Exception as e:  # noqa: BLE001 — one bad file must not sink the capture
            log.warning("site capture: %s failed: %s: %s", u, type(e).__name__, e)
            walk.failed.append((u, type(e).__name__))
            events.on_log(f"  [{i:>2}] {name}: {type(e).__name__}")
    if queue:
        events.on_log(f"  (stopped at {_MAX_FILES} files; {len(queue)} more "
                      "referenced — see the manifest)")
        walk.failed.extend((u, "not fetched (file cap)") for u in queue)
    return walk


def capture(events=None, confirm_overwrite=None, day=None):
    """Sign in, open the active site's report page, and save its source files
    to a NEW dated folder under output/site-capture/. Returns a
    ConsolidateResult whose output_path is that folder.
    (`confirm_overwrite` / `day` are unused — the signature matches the shared
    ConsolidateWorker contract; every capture lands in its own timestamped
    folder.)"""
    del confirm_overwrite, day
    events = events or Events()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return ConsolidateResult(
            status="error",
            message="Required components are missing (playwright).")
    from common import get_site, get_url
    from session import new_authed_browser

    src, env = get_site()
    stamp = time.strftime("%H%M%S")
    out_dir = capture_root() / f"{today_str()} {src}-{env} {stamp}"
    url = get_url()

    events.on_log("=" * 60)
    events.on_log(f"Website source capture — {src.upper()}-{env.upper()}")
    events.on_log("=" * 60)
    events.on_log(f"Page: {url}")
    events.on_log(f"Saving to: {out_dir}")
    events.on_log("")

    walk = _Walk()
    browser = None
    try:
        with sync_playwright() as p:
            browser, ctx, page = new_authed_browser(p)
            events.on_log("Signing in and opening the report page…")
            from common import navigate_with_auth
            navigate_with_auth(page, should_cancel=events.is_cancelled)
            if events.is_cancelled():
                return ConsolidateResult(status="cancelled",
                                         message="Cancelled by user.")
            page.wait_for_timeout(int(_SETTLE_S * 1000))
            _snapshot_and_walk(ctx, page, out_dir, events, walk)
            if walk.cancelled:
                return ConsolidateResult(status="cancelled",
                                         message="Cancelled by user.")
    except Exception as e:  # noqa: BLE001 — surface one clean error; the log has the why
        log.warning("site capture failed", exc_info=True)
        if walk.saved:
            _write_manifest(out_dir, url, src, env, walk.saved, walk.failed,
                            note=f"INCOMPLETE — {type(e).__name__}",
                            build_date=walk.build_date, config=walk.config,
                            foreign=walk.foreign)
        return ConsolidateResult(
            status="error",
            message=("Could not capture the website source "
                     f"({type(e).__name__}). Check the connection/sign-in and "
                     "try again — details are in the log."))
    finally:
        try:
            if browser is not None:
                browser.close()
        except Exception:  # silent-ok: teardown after the capture already concluded
            pass

    saved, failed = walk.saved, walk.failed
    build_date = walk.build_date
    if not saved:
        return ConsolidateResult(
            status="error",
            message="Nothing could be saved from the page — see the log.")
    _write_manifest(out_dir, url, src, env, saved, failed,
                    build_date=build_date, config=walk.config, foreign=walk.foreign)
    events.on_log("")
    note = f" ({len(failed)} file(s) could not be fetched — see the manifest)" \
        if failed else ""
    events.on_log(f"✓ Captured {len(saved)} file(s){note}.")
    events.on_log(f"  Folder: {out_dir}")
    return ConsolidateResult(
        status="ok", output_path=str(out_dir),
        summary_lines=[f"Files saved: {len(saved)}{note}",
                       f"Folder: {out_dir}"]
        + ([f"Site build: {build_date}"] if build_date else []),
        message=f"Website source captured — {len(saved)} file(s).")


def _write_manifest(out_dir, url, src, env, saved, failed, note=None,
                    build_date=None, config=None, foreign=()):
    lines = [
        "TSMIS website source capture",
        f"Captured: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Site: {src}-{env}",
        f"Page: {url}",
        f"Site build (BUILD_DATE): {build_date or 'not found'}",
    ]
    if config:
        lines.append(f"Site CONFIG: env={config.get('env')} src={config.get('src')}"
                     + (f" service={config.get('service')}" if config.get("service") else ""))
    if note:
        lines.append(f"Note: {note}")
    lines += ["", f"Saved ({len(saved)}):"]
    for entry in saved:
        name, n = entry[0], entry[1]
        sha = entry[2] if len(entry) > 2 else None
        lines.append(f"  {name}  ({n:,} bytes)" + (f"  sha256={sha}" if sha else ""))
    if failed:
        lines += ["", f"Not fetched ({len(failed)}):"]
        lines += [f"  {u}  ({why})" for u, why in failed]
    if foreign:
        lines += ["", f"Third-party references, never fetched ({len(foreign)}):"]
        lines += [f"  {u}" for u in foreign]
    lines += ["", "This folder is local diagnostic data (the TSMIS site source "
                  "is Caltrans-internal); the app never uploads or bundles it."]
    _write(out_dir / _MANIFEST, "\n".join(lines) + "\n")
