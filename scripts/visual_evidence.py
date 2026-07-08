"""Visual evidence for vs-TSN comparisons: highlighted PDF snippets per diff.

For each shared column the comparison flags somewhere, sample random example
rows (random routes — not just the first), find that exact cell in BOTH source
PDFs (the TSMIS per-route "(PDF)" export and the TSN district print), render
the region and box the cell on each side, and compose captioned evidence
images — the manual screenshot-and-circle workflow, automated.

Trust contract: an example is only used when the value parsed back OUT of each
PDF, normalized with the comparator's own projections, equals the value the
comparison actually compared — so an image can never illustrate something other
than what was diffed, and every rendered pair doubles as an end-to-end check of
the comparison at that cell. Candidates that fail (the TSMIS PDF/Excel editions
disagreeing at that cell, a TSN reference-date skew, a duplicated key) are
skipped with a recorded reason, never shown.

Outputs, next to the comparison workbook (the "(formulas).xlsx" sibling
convention): `<comparison> (evidence).xlsx` — a Summary sheet + every stacked
image embedded — and `<comparison> (evidence images)/` holding each example in
BOTH layouts (stacked for reading, side-by-side for pasting into docs). Both
writes are keep-last-good: a failed/cancelled run leaves the previous set
untouched; files locked open in Excel divert to a ".new" sibling with a note.

Report-agnostic: everything report-specific comes from an adapter module (see
evidence_highway_detail — currently Highway Detail Excel + PDF rows). Engine is
console-free (Events sink, cancellation honored between steps) and never
affects the comparison result it decorates.
"""
import logging
import os
import random
import re
import shutil
from pathlib import Path

try:
    import pdfplumber
    from PIL import Image, ImageDraw, ImageFont
    from openpyxl import Workbook
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.styles import Font
    _DEPS_OK = True
except ImportError:
    _DEPS_OK = False

import paths

log = logging.getLogger("tsmis.evidence")

DEPS_MSG = "Required components are missing (pdfplumber/Pillow/openpyxl)."

# row_key -> adapter module name (lazy import; both Highway Detail rows share
# one adapter — the Excel row's images render from the PDF-edition export, the
# PDF row's from the same files it was compared from).
_ADAPTER_MODULES = {
    "highway_detail": "evidence_highway_detail",
    "highway_detail_pdf": "evidence_highway_detail",
}
# Where each row's TSMIS-side PDFs live (the per-route export subdir) and which
# TSN library report's pdf/ folder holds the district prints.
TSMIS_PDF_SUBDIR = {"highway_detail": "highway_detail_pdf",
                    "highway_detail_pdf": "highway_detail_pdf"}
TSN_PDF_REPORT = {"highway_detail": "highway_detail",
                  "highway_detail_pdf": "highway_detail"}

MIN_EXAMPLES, MAX_EXAMPLES, DEFAULT_EXAMPLES = 1, 10, 2
_RES = 180                     # render DPI (points * _RES/72 = pixels)
_SC = _RES / 72.0
_STACK_W = 1900                # stacked strip width (px)
_PAIR_SIDE_W = 1300            # side-by-side per-side width (px)
_CTX_PT = 27                   # vertical context around the record (points)
_PAGE_CACHE_MAX = 16
_EMBED_W = 1500                # embedded image display width in the workbook
_PX_PER_ROW = 20               # Excel's default row height in pixels


def capable(row_key):
    return row_key in _ADAPTER_MODULES


def rows():
    return sorted(_ADAPTER_MODULES)


def adapter_for(row_key):
    import importlib
    return importlib.import_module(_ADAPTER_MODULES[row_key])


def pdf_subdir_for(row_key):
    """The TSMIS export subdir whose per-route PDFs illustrate this row."""
    return TSMIS_PDF_SUBDIR[row_key]


def tsn_pdf_dir(row_key):
    return paths.tsn_library_pdf_dir(TSN_PDF_REPORT[row_key])


def clamp_examples(n):
    try:
        return max(MIN_EXAMPLES, min(MAX_EXAMPLES, int(n)))
    except (TypeError, ValueError):
        return DEFAULT_EXAMPLES


def availability():
    """Cheap probe for the GUI toggle: which rows support evidence and whether
    the TSN district prints are in place (the TSMIS side varies per run/day and
    is reported per cell instead)."""
    d = tsn_pdf_dir("highway_detail")
    try:
        n = sum(1 for _ in Path(d).glob("*.pdf"))
    except OSError:              # silent-ok: a pure probe; unreadable = not ready
        n = 0
    return {"rows": rows(), "tsn_pdfs": n, "ready": _DEPS_OK and n > 0,
            "dir": str(d), "deps_ok": _DEPS_OK}


def sibling_paths(comparison_path):
    """(workbook, image folder) next to a comparison workbook — the same
    naming family as its '(formulas).xlsx' sibling."""
    p = Path(comparison_path)
    return (p.with_name(f"{p.stem} (evidence){p.suffix}"),
            p.with_name(f"{p.stem} (evidence images)"))


# --------------------------------------------------------------------------- #
# generation
# --------------------------------------------------------------------------- #
def generate(row_key, consolidated, tsn_path, comparison_path, tsmis_pdf_dir,
             events, examples=DEFAULT_EXAMPLES):
    """Generate the evidence set for one finished vs-TSN comparison. Returns a
    result dict {note, rendered, fields_ok, fields_with_diffs, misses,
    workbook, folder} — `note` is the one summary line for the run log. Raises
    ValueError for a not-runnable setup (missing deps/PDFs); the caller treats
    any failure as a skipped decoration, never a failed comparison."""
    if not _DEPS_OK:
        raise ValueError(DEPS_MSG)
    if not capable(row_key):
        raise ValueError(f"no visual-evidence support for {row_key}")
    adapter = adapter_for(row_key)
    examples = clamp_examples(examples)
    tsmis_pdf_dir = Path(tsmis_pdf_dir)
    tsn_dir = tsn_pdf_dir(row_key)
    n_tsmis = sum(1 for _ in tsmis_pdf_dir.glob("*.pdf")) if tsmis_pdf_dir.is_dir() else 0
    if not n_tsmis:
        raise ValueError(f"no {adapter.REPORT_LABEL} (PDF) export found in "
                         f"{tsmis_pdf_dir} — run that export first")
    n_tsn = sum(1 for _ in Path(tsn_dir).glob("*.pdf")) if Path(tsn_dir).is_dir() else 0
    if not n_tsn:
        raise ValueError(f"no TSN district PDFs in {tsn_dir}")

    seed = int.from_bytes(os.urandom(4), "big")
    rng = random.Random(seed)
    log.info("evidence: %s seed=%08x examples=%d tsmis=%s tsn=%s",
             row_key, seed, examples, tsmis_pdf_dir, tsn_dir)
    events.on_log(f"  evidence: sampling up to {examples} example(s) per column "
                  f"(seed {seed:08x})…")

    tsmis_rows, tsn_rows, sidecar, note = adapter.load_sides(consolidated, tsn_path)
    if sidecar is None:
        raise ValueError(note or "the TSN workbook carries no district info")
    if events.is_cancelled():
        return _cancelled()
    diffs = adapter.enumerate_diffs(tsmis_rows, tsn_rows, sidecar)
    fields_with_diffs = [f for f in adapter.FIELDS if diffs.get(f)]
    if not fields_with_diffs:
        return {"note": "evidence: the comparison has no differing columns to "
                        "illustrate", "rendered": 0, "fields_ok": 0,
                "fields_with_diffs": 0, "misses": {}, "workbook": None,
                "folder": None}

    # pick candidates, then group the lookups by source file so each PDF is
    # parsed exactly once
    cand = {f: rng.sample(diffs[f], min(len(diffs[f]), max(examples * 4, examples + 6)))
            for f in fields_with_diffs}
    need_tsmis = {}
    need_tsn_routes, need_tsn_keys = {}, {}
    for f in fields_with_diffs:
        for ex in cand[f]:
            need_tsmis.setdefault(ex["route"], set()).add(ex["key"])
            need_tsn_routes.setdefault(ex["dist"], set()).add(ex["route"])
            need_tsn_keys.setdefault(ex["dist"], set()).add(
                (ex["cnty"], ex["route"], ex["key"]))

    events.on_log(f"  evidence: locating candidates in {len(need_tsmis)} TSMIS "
                  f"PDF(s) and {len(need_tsn_keys)} TSN district print(s)…")
    tsmis_loc, missing_routes = {}, set()
    for ri, (route, keys) in enumerate(sorted(need_tsmis.items()), 1):
        if events.is_cancelled():
            return _cancelled()
        if ri % 10 == 0:
            events.on_log(f"    …TSMIS PDFs {ri}/{len(need_tsmis)}")
        p = adapter.tsmis_pdf_path(tsmis_pdf_dir, route)
        if not p.is_file():
            missing_routes.add(route)
            continue
        try:
            tsmis_loc[route] = adapter.locate_tsmis(p, keys)
        except Exception as e:                            # a corrupt route PDF
            log.warning("evidence: %s unparseable: %s: %s",
                        p.name, type(e).__name__, e)
            missing_routes.add(route)
    if missing_routes:
        events.on_log(f"    note: no readable TSMIS PDF for route(s) "
                      f"{', '.join(sorted(missing_routes))} — sampling around them")
    dist_index = adapter.district_index(tsn_dir, events)
    tsn_loc = {}
    # The district prints are the slow half (word extraction on every page), so
    # narrate each one — a stalled run must name where it stalled.
    for di, dist in enumerate(sorted(need_tsn_keys), 1):
        if events.is_cancelled():
            return _cancelled()
        p = dist_index.get(dist)
        if p is None:
            continue
        try:
            tsn_loc[dist] = adapter.locate_tsn(p, need_tsn_routes[dist],
                                               need_tsn_keys[dist])
            events.on_log(f"    …TSN district {dist}: "
                          f"{sum(len(v) for v in tsn_loc[dist].values())} "
                          f"candidate row(s) ({di}/{len(need_tsn_keys)})")
        except Exception as e:
            log.warning("evidence: %s unparseable: %s: %s",
                        p.name, type(e).__name__, e)

    # render into a temp folder; swap in only on success (keep-last-good)
    wb_path, img_dir = sibling_paths(comparison_path)
    tmp_dir = img_dir.with_name(img_dir.name + ".tmp")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    page_cache = {}
    entries, misses = [], {}
    rendered = 0
    try:
        for fi, f in enumerate(fields_with_diffs, 1):
            if events.is_cancelled():
                return _cancelled()
            got, reasons = 0, []
            for ex in cand[f]:
                if got >= examples:
                    break
                ok, reason = _try_example(adapter, ex, f, tsmis_loc, tsn_loc,
                                          dist_index, tsmis_pdf_dir, tmp_dir,
                                          got + 1, page_cache)
                if ok:
                    got += 1
                    rendered += 1
                    entries.append(ok)
                else:
                    reasons.append(reason)
            if not got:
                misses[f] = _summarize_reasons(reasons)
                log.info("evidence: %s — no verifiable example (%s)",
                         f, misses[f])
            if fi % 8 == 0:
                events.on_log(f"  evidence: {fi}/{len(fields_with_diffs)} "
                              "columns done…")
        if events.is_cancelled():
            return _cancelled()
        if not rendered:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return {"note": "evidence: no verifiable examples could be rendered "
                            "(see the log)", "rendered": 0, "fields_ok": 0,
                    "fields_with_diffs": len(fields_with_diffs),
                    "misses": misses, "workbook": None, "folder": None}
        wb_note = _write_workbook(wb_path, tmp_dir, entries, misses, dict(
            comparison=Path(comparison_path).name, report=adapter.REPORT_LABEL,
            seed=f"{seed:08x}", examples=examples,
            tsmis_dir=str(tsmis_pdf_dir), tsn_dir=str(tsn_dir)))
        dir_note = _swap_dir(tmp_dir, img_dir)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    fields_ok = len({e["field"] for e in entries})
    note = (f"evidence: {rendered} example(s) across {fields_ok}/"
            f"{len(fields_with_diffs)} differing column(s) → {wb_path.name}")
    if misses:
        note += (f" — {len(misses)} column(s) had no verifiable example "
                 "(reasons in the workbook)")
    for extra in (wb_note, dir_note):
        if extra:
            note += f"; {extra}"
    events.on_log("  " + note)
    return {"note": note, "rendered": rendered, "fields_ok": fields_ok,
            "fields_with_diffs": len(fields_with_diffs), "misses": misses,
            "workbook": str(wb_path), "folder": str(img_dir)}


def _cancelled():
    return {"note": "evidence: cancelled — previous evidence files left as-is",
            "rendered": 0, "fields_ok": 0, "fields_with_diffs": 0,
            "misses": {}, "workbook": None, "folder": None}


def _summarize_reasons(reasons):
    if not reasons:
        return "no candidates"
    uniq = []
    for r in reasons:
        if r not in uniq:
            uniq.append(r)
    return "; ".join(uniq[:3])


def _try_example(adapter, ex, field, tsmis_loc, tsn_loc, dist_index,
                 tsmis_pdf_dir, out_dir, k, page_cache):
    """Verify one candidate end-to-end and render both layouts. Returns
    (entry_dict, None) on success, (None, reason) otherwise."""
    trecs = tsmis_loc.get(ex["route"], {}).get(ex["key"], [])
    if len(trecs) != 1:
        return None, ("no readable TSMIS PDF for the route" if
                      ex["route"] not in tsmis_loc
                      else "row not found uniquely in the TSMIS PDF")
    nrecs = tsn_loc.get(ex["dist"], {}).get(
        (ex["cnty"], ex["route"], ex["key"]), [])
    if len(nrecs) != 1:
        return None, "row not found uniquely in the TSN district print"
    trec, nrec = trecs[0], nrecs[0]
    tb = adapter.tsmis_box(trec, field)
    if tb is None:
        return None, "record on an approximate-geometry page"
    tv = adapter.tsmis_value(trec, field)
    if tv != ex["va"]:
        return None, "the TSMIS PDF prints a different value than the compared export"
    nv = adapter.tsn_value(nrec, field)
    if nv != ex["vb"]:
        return None, "the TSN print differs from the TSN workbook at this cell"
    npage, nbox, nyspan, nxspan = adapter.tsn_box(nrec, field)
    tpage, tbox, tyspan, txspan = tb

    t_pdf = adapter.tsmis_pdf_path(tsmis_pdf_dir, ex["route"])
    n_pdf = dist_index[ex["dist"]]
    t_img = _strip(t_pdf, tpage, tbox, tyspan, txspan, page_cache)
    n_img = _strip(n_pdf, npage, nbox, nyspan, nxspan, page_cache)
    title = (f"{field} — TSMIS '{ex['va'] or '(blank)'}'  vs  "
             f"TSN '{ex['vb'] or '(blank)'}'")
    sub = (f"Route {ex['route']} @ {ex['key']} — both PDFs re-parsed and "
           f"verified against the compared values — TSN district "
           f"D{ex['dist']} ({ex['cnty']})")
    t_label = f"TSMIS (PDF)  —  {t_pdf.name} · page {tpage}"
    n_label = (f"TSN  —  {n_pdf.name} · page {npage} · "
               f"{ex['cnty']}-{ex['route']}")
    safe = re.sub(r"[^A-Za-z0-9]+", "_", field).strip("_")
    stacked = out_dir / f"{safe}_{k}_stacked.png"
    pair = out_dir / f"{safe}_{k}_pair.png"
    _compose_stacked(title, sub, t_label, t_img, n_label, n_img, stacked)
    _compose_pair(title, sub, t_label, t_img, n_label, n_img, pair)
    return {"field": field, "route": ex["route"], "key": ex["key"],
            "va": ex["va"], "vb": ex["vb"], "stacked": stacked.name,
            "pair": pair.name}, None


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def _render_page(path, page_no, cache):
    key = (str(path), page_no)
    if key not in cache:
        if len(cache) >= _PAGE_CACHE_MAX:
            cache.pop(next(iter(cache)))
        with pdfplumber.open(path) as pdf:
            cache[key] = pdf.pages[page_no - 1].to_image(
                resolution=_RES).original.convert("RGB")
    return cache[key]


def _strip(path, page_no, cell_box, record_yspan, xspan, cache):
    """A context crop around the record: gray box = the record's printed
    line(s), red box = the compared cell."""
    img = _render_page(path, page_no, cache).copy()
    d = ImageDraw.Draw(img)
    rx0, rx1 = xspan
    ry0, ry1 = record_yspan
    d.rectangle([rx0 * _SC, (ry0 - 1.5) * _SC, rx1 * _SC, (ry1 + 1.5) * _SC],
                outline=(150, 150, 150), width=2)
    x0, y0, x1, y1 = cell_box
    d.rectangle([x0 * _SC, y0 * _SC, x1 * _SC, y1 * _SC],
                outline=(220, 20, 20), width=4)
    return img.crop((int(max(0, (rx0 - 8) * _SC)),
                     int(max(0, (ry0 - _CTX_PT) * _SC)),
                     int(min(img.width, (rx1 + 8) * _SC)),
                     int(min(img.height, (ry1 + _CTX_PT + 2) * _SC))))


_FONT_WARNED = False


def _font(size, bold=False):
    global _FONT_WARNED
    name = "arialbd.ttf" if bold else "arial.ttf"
    windir = os.environ.get("WINDIR", r"C:\Windows")
    try:
        return ImageFont.truetype(str(Path(windir) / "Fonts" / name), size)
    except OSError:
        if not _FONT_WARNED:
            _FONT_WARNED = True
            log.info("evidence: Arial not found; using the built-in font")
        return ImageFont.load_default()


def _scaled(im, width):
    if im.width <= width:
        return im
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def _header(canvas, w, title, sub):
    d = ImageDraw.Draw(canvas)
    d.text((16, 12), title, font=_font(26, True), fill=(20, 20, 20))
    d.text((16, 50), sub, font=_font(17), fill=(90, 90, 90))
    return 84


def _compose_stacked(title, sub, top_label, top_img, bot_label, bot_img, out):
    top_img, bot_img = _scaled(top_img, _STACK_W), _scaled(bot_img, _STACK_W)
    w = max(top_img.width, bot_img.width) + 32
    lab = 30
    h = 84 + lab + top_img.height + 14 + lab + bot_img.height + 16
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    y = _header(canvas, w, title, sub)
    d = ImageDraw.Draw(canvas)
    for label, im in ((top_label, top_img), (bot_label, bot_img)):
        d.text((16, y + 4), label, font=_font(16, True), fill=(31, 56, 100))
        y += lab
        canvas.paste(im, (16, y))
        d.rectangle([15, y - 1, 16 + im.width, y + im.height],
                    outline=(200, 200, 200), width=1)
        y += im.height + 14
    canvas.save(out)


def _compose_pair(title, sub, l_label, l_img, r_label, r_img, out):
    l_img, r_img = _scaled(l_img, _PAIR_SIDE_W), _scaled(r_img, _PAIR_SIDE_W)
    lab = 30
    col_h = max(l_img.height, r_img.height)
    w = l_img.width + r_img.width + 48
    h = 84 + lab + col_h + 16
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    y0 = _header(canvas, w, title, sub)
    d = ImageDraw.Draw(canvas)
    x = 16
    for label, im in ((l_label, l_img), (r_label, r_img)):
        d.text((x, y0 + 4), label, font=_font(16, True), fill=(31, 56, 100))
        canvas.paste(im, (x, y0 + lab))
        d.rectangle([x - 1, y0 + lab - 1, x + im.width, y0 + lab + im.height],
                    outline=(200, 200, 200), width=1)
        x += im.width + 16
    canvas.save(out)


# --------------------------------------------------------------------------- #
# outputs (keep-last-good)
# --------------------------------------------------------------------------- #
def _write_workbook(wb_path, img_dir, entries, misses, info):
    """Write '<comparison> (evidence).xlsx' — Summary sheet + every stacked
    image embedded — via a temp file + os.replace. Returns a short note when
    the previous workbook was locked open and the new one diverted to .new."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    title = Font(name="Arial", size=14, bold=True)
    bold = Font(name="Arial", size=10, bold=True)
    body = Font(name="Arial", size=10)
    small = Font(name="Arial", size=9, color="666666")
    ws.append([f"{info['report']} — visual evidence"])
    ws["A1"].font = title
    ws.append([f"Comparison: {info['comparison']}   ·   examples per column: "
               f"{info['examples']}   ·   sample seed: {info['seed']}"])
    ws["A2"].font = small
    ws.append([f"TSMIS PDFs: {info['tsmis_dir']}   ·   TSN PDFs: {info['tsn_dir']}"])
    ws["A3"].font = small
    ws.append([])
    ws.append(["Column", "Route @ Post Mile", "TSMIS", "TSN", "Images"])
    for c in "ABCDE":
        ws[f"{c}5"].font = bold
    r = 6
    for e in entries:
        ws.cell(row=r, column=1, value=e["field"]).font = body
        ws.cell(row=r, column=2, value=f"{e['route']} @ {e['key']}").font = body
        ws.cell(row=r, column=3, value=e["va"]).font = body
        ws.cell(row=r, column=4, value=e["vb"]).font = body
        ws.cell(row=r, column=5, value=f"{e['stacked']}  /  {e['pair']}").font = body
        r += 1
    for f, why in misses.items():
        ws.cell(row=r, column=1, value=f).font = body
        ws.cell(row=r, column=2, value=f"no verifiable example — {why}").font = small
        r += 1
    for col, width in (("A", 14), ("B", 24), ("C", 26), ("D", 26), ("E", 46)):
        ws.column_dimensions[col].width = width

    ev = wb.create_sheet("Evidence")
    ev.sheet_properties.tabColor = "C00000"
    ev.append(["Red box = the compared cell in each source PDF; gray box = the "
               "record (its printed lines). Values shown are the compared "
               "(normalized) forms."])
    ev["A1"].font = small
    r = 3
    for e in entries:
        ev.cell(row=r, column=1, value=(
            f"{e['field']}   —   route {e['route']} @ {e['key']}   —   "
            f"TSMIS '{e['va']}' vs TSN '{e['vb']}'")).font = bold
        img = XLImage(str(img_dir / e["stacked"]))
        scale = min(1.0, _EMBED_W / img.width)
        img.width, img.height = int(img.width * scale), int(img.height * scale)
        ev.add_image(img, f"A{r + 1}")
        r += 1 + max(1, round(img.height / _PX_PER_ROW)) + 2

    tmp = wb_path.with_name(wb_path.name + ".tmp")
    wb.save(tmp)
    try:
        os.replace(tmp, wb_path)
        return None
    except OSError as e:                       # workbook open in Excel, etc.
        log.warning("evidence: workbook swap failed: %s: %s",
                    type(e).__name__, e)
        alt = wb_path.with_name(wb_path.stem + ".new" + wb_path.suffix)
        try:
            os.replace(tmp, alt)
            return f"previous evidence workbook is locked open — new set saved as {alt.name}"
        except OSError:
            Path(tmp).unlink(missing_ok=True)
            return "previous evidence workbook is locked open — new workbook not saved"


def _swap_dir(tmp_dir, target):
    """Swap the freshly-rendered image folder into place; the previous set
    survives any failure. Returns a note when the swap had to divert."""
    old = target.with_name(target.name + ".old")
    shutil.rmtree(old, ignore_errors=True)
    try:
        if target.exists():
            os.replace(target, old)
        os.replace(tmp_dir, target)
        shutil.rmtree(old, ignore_errors=True)
        return None
    except OSError as e:                       # a file inside is locked open
        log.warning("evidence: image-folder swap failed: %s: %s",
                    type(e).__name__, e)
        alt = target.with_name(target.name + ".new")
        shutil.rmtree(alt, ignore_errors=True)
        try:
            os.replace(tmp_dir, alt)
            if old.exists() and not target.exists():
                os.replace(old, target)        # restore the previous set
            return f"previous images are locked open — new set saved to {alt.name}"
        except OSError:
            if old.exists() and not target.exists():
                os.replace(old, target)
            return "previous images are locked open — new image set not saved"
