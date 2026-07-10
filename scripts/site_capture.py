"""Capture the TSMIS report page's source for troubleshooting (v0.26.0).

Automates the manual devtools ▸ Sources walk the maintainer does today: sign in
with the saved session, open the active site's report page, and save — into ONE
dated folder — the rendered DOM, the raw page HTML, and every SAME-ORIGIN
script/stylesheet the page references. The output is the selector/label ground
truth used to keep the app tracking site changes; it is LOCAL diagnostic data
(the TSMIS source is Caltrans-internal — the capture lands under output/ and is
never bundled, uploaded, or committed anywhere by the app).

Console-free like the rest of the core: progress via events.on_log, cancel
honored between fetches, ConsolidateResult returned. Only gui_api drives it.
"""
import logging
import re
import time
from urllib.parse import urlsplit

from events import ConsolidateResult, Events
from paths import OUTPUT_ROOT, today_str

log = logging.getLogger("tsmis.site_capture")

CAPTURE_DIRNAME = "site-capture"
_MANIFEST = "_capture_info.txt"
# The page finishes building its menus with a little post-load JS; a short fixed
# settle keeps the rendered-DOM snapshot representative without a networkidle
# wait (which long-polling keeps from ever firing).
_SETTLE_S = 2.0
_FETCH_TIMEOUT_MS = 30_000
_NAME_MAX = 120


def capture_root():
    return OUTPUT_ROOT / CAPTURE_DIRNAME


def _same_origin(url, page_url):
    a, b = urlsplit(url), urlsplit(page_url)
    return (a.scheme, a.netloc) == (b.scheme, b.netloc)


def _safe_name(url):
    """A flat, traversal-proof filename from a resource URL: the path segments
    joined with '__' (so provenance stays readable), every character outside
    [A-Za-z0-9._-] replaced, length capped. A query string keeps the name from
    colliding via a short suffix."""
    parts = urlsplit(url)
    path = parts.path.strip("/") or "index"
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", path.replace("/", "__"))
    name = name.strip("._") or "resource"
    if parts.query:
        name += "__q" + re.sub(r"[^A-Za-z0-9]+", "", parts.query)[:24]
    return name[:_NAME_MAX]


# The DOM walk that lists what the page actually loaded: external scripts +
# stylesheets (the files the maintainer downloads by hand today).
_LIST_RESOURCES_JS = """
() => {
  const out = new Set();
  for (const s of document.scripts) if (s.src) out.add(s.src);
  for (const l of document.querySelectorAll("link[rel='stylesheet'][href]"))
    out.add(l.href);
  return [...out];
}
"""


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode("utf-8", errors="replace")
    path.write_bytes(data)
    return len(data)


def capture(events=None, confirm_overwrite=None, day=None):
    """Sign in, open the active site's report page, and save its source files
    to a NEW dated folder under output/site-capture/. Returns a
    ConsolidateResult whose output_path is that folder. (`confirm_overwrite` /
    `day` are unused — the signature matches the shared ConsolidateWorker
    contract; every capture lands in its own timestamped folder.)"""
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

    saved, failed = [], []
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

            events.on_log("Saving the page (rendered DOM + raw HTML)…")
            n = _write(out_dir / "page (rendered DOM).html", page.content())
            saved.append(("page (rendered DOM).html", n))
            try:
                raw = ctx.request.get(page.url, timeout=_FETCH_TIMEOUT_MS)
                if raw.ok:
                    n = _write(out_dir / "page (raw).html", raw.body())
                    saved.append(("page (raw).html", n))
                else:
                    failed.append((page.url, f"HTTP {raw.status}"))
            except Exception as e:  # noqa: BLE001 — the rendered DOM above is the primary artifact
                log.warning("site capture: raw page fetch failed: %s: %s",
                            type(e).__name__, e)
                failed.append((page.url, type(e).__name__))

            urls = page.evaluate(_LIST_RESOURCES_JS) or []
            res = sorted(u for u in urls if isinstance(u, str)
                         and _same_origin(u, page.url))
            skipped_foreign = len(urls) - len(res)
            events.on_log(f"Fetching {len(res)} same-origin script/style file(s)"
                          + (f" ({skipped_foreign} third-party skipped)…"
                             if skipped_foreign else "…"))
            for i, u in enumerate(res, 1):
                if events.is_cancelled():
                    return ConsolidateResult(status="cancelled",
                                             message="Cancelled by user.")
                name = _safe_name(u)
                try:
                    r = ctx.request.get(u, timeout=_FETCH_TIMEOUT_MS)
                    if not r.ok:
                        failed.append((u, f"HTTP {r.status}"))
                        events.on_log(f"  [{i:>2}/{len(res)}] {name}: HTTP {r.status}")
                        continue
                    n = _write(out_dir / "files" / name, r.body())
                    saved.append((f"files/{name}", n))
                    events.on_log(f"  [{i:>2}/{len(res)}] {name} ({n:,} bytes)")
                except Exception as e:  # noqa: BLE001 — one bad file must not sink the capture
                    log.warning("site capture: %s failed: %s: %s",
                                u, type(e).__name__, e)
                    failed.append((u, type(e).__name__))
                    events.on_log(f"  [{i:>2}/{len(res)}] {name}: {type(e).__name__}")
    except Exception as e:  # noqa: BLE001 — surface one clean error; the log has the why
        log.warning("site capture failed", exc_info=True)
        if saved:
            _write_manifest(out_dir, url, src, env, saved, failed,
                            note=f"INCOMPLETE — {type(e).__name__}")
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

    if not saved:
        return ConsolidateResult(
            status="error",
            message="Nothing could be saved from the page — see the log.")
    _write_manifest(out_dir, url, src, env, saved, failed)
    events.on_log("")
    note = f" ({len(failed)} file(s) could not be fetched — see the manifest)" \
        if failed else ""
    events.on_log(f"✓ Captured {len(saved)} file(s){note}.")
    return ConsolidateResult(
        status="ok", output_path=str(out_dir),
        summary_lines=[f"Files saved: {len(saved)}{note}",
                       f"Folder: {out_dir}"],
        message=f"Website source captured — {len(saved)} file(s).")


def _write_manifest(out_dir, url, src, env, saved, failed, note=None):
    lines = [
        "TSMIS website source capture",
        f"Captured: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Site: {src}-{env}",
        f"Page: {url}",
    ]
    if note:
        lines.append(f"Note: {note}")
    lines += ["", f"Saved ({len(saved)}):"]
    lines += [f"  {name}  ({n:,} bytes)" for name, n in saved]
    if failed:
        lines += ["", f"Not fetched ({len(failed)}):"]
        lines += [f"  {u}  ({why})" for u, why in failed]
    lines += ["", "This folder is local diagnostic data (the TSMIS site source "
                  "is Caltrans-internal); the app never uploads or bundles it."]
    _write(out_dir / _MANIFEST, "\n".join(lines) + "\n")
