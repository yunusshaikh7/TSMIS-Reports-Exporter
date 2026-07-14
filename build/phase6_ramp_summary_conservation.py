#!/usr/bin/env python3
"""Independent Stage-6 Ramp Summary PDF-to-r7 conservation oracle.

The authoritative input is the exact TSN PDF, not a production parser's output.
This audit captures that PDF into private immutable bytes, parses it independently
with two PDF libraries, binds every text/layout role, and compares the 31 semantic
summary rows to the accepted r7 normalized XLSX.  It imports no application
normalizer, projector, comparator, report schema, or evidence adapter.

Three outcomes are intentionally separate:

* ``stage6_family_audit_complete`` means every source role and normalized row has
  an explicit, mutation-tested disposition and there is no unexplained residue.
* ``projection_exact`` means the current Category/Count projection is exact.
* ``normalized_full_conservation`` means the normalized bytes preserve every
  comparison-semantic source fact, including printed report provenance.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Sequence
import zipfile

import pdfplumber
import pypdf
from pypdf import PdfReader

from phase3_xlsx_stream import (ColumnSpec, FileIdentity, SheetSpec,
                                capture_file_bytes, capture_file_identity,
                                read_sheet)


RAW_PDF = Path(
    r"C:\Users\Yunus\Downloads\TSMIS\tsn_library\ramp_summary\raw"
    r"\Ramp Summary Statewide_TSN.pdf")
R7_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
    r"\raw-2026-07-12-r7")
NORMALIZED_XLSX = (
    R7_ROOT / "ramp_summary" / "consolidated" /
    "tsn_ramp_summary_normalized.xlsx")
NORMALIZED_SIDECAR = Path(str(NORMALIZED_XLSX) + ".outcome.json")
R7_WITNESS = R7_ROOT / "result.json"

RAW_BINDING = {
    "bytes": 11_758,
    "sha256": "e09842e939af4bc0da82014cfd0de1f6670e7fed5e4c5f6441628bda818a118b",
    "pages": 3,
    "page_size_points": [792, 612],
}
NORMALIZED_BINDING = {
    "bytes": 5_758,
    "sha256": "15e5b9260b79618371d0378afa40f051a8912c7056c8fbf43cdbbde47b143356",
    "sheet": "Ramp Summary (TSN)",
    "rows": 31,
    "columns": 2,
    "normalization_version": 2,
}
SIDECAR_BINDING = {
    "bytes": 892,
    "sha256": "e5b3b115c674d58b52711a3745d82f7b5cf80a4c3874de0c66a602f41f4bc2b4",
}
R7_WITNESS_BINDING = {
    "bytes": 173_124,
    "sha256": "b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa",
}
RAW_MANIFEST_BINDING = {
    "member_count": 1,
    "byte_length": 11_758,
    "sha256": "9bd11b3057a8d626744e64f56256ac138c031efb76e31986042ea384745cdc7b",
    "relative_path": "Ramp Summary Statewide_TSN.pdf",
}
IDENTITY_TOKEN = (
    "tsn-normalized-v1:7fd9bdf19e58addc3c77bb4e33818e463af12ecfe45a60c02fd053e65ef61eb4")

GENERATOR_PATH = Path(__file__).resolve()
READER_PATH = GENERATOR_PATH.with_name("phase3_xlsx_stream.py")
READER_GATE_PATH = GENERATOR_PATH.with_name("check_phase3_xlsx_stream.py")
SELF_GATE_PATH = GENERATOR_PATH.with_name("check_phase6_ramp_summary_conservation.py")
GENERATOR_START = capture_file_identity(GENERATOR_PATH)
READER_START = capture_file_identity(READER_PATH)
READER_GATE_START = capture_file_identity(READER_GATE_PATH)

EXPECTED_PDF_METADATA = {
    "/Author": "Oracle Reports",
    "/CreationDate": "D:20250915171107",
    "/Creator": "Oracle12c AS Reports Services",
    "/ModDate": "D:20250915171107",
    "/Producer": "Oracle PDF driver",
    "/Title": "otm22270.pdf",
}
EXPECTED_CHAR_COUNTS = (980, 256, 960)
EXPECTED_WORD_COUNTS = (145, 39, 193)
EXPECTED_SECTION_CODES = {
    "highway_groups": ("R", "D", "U", "X", "L", "Others"),
    "on_off": ("ON", "OFF", "OTH"),
    "population_groups": (
        "R-RURAL -I INSIDE CITY",
        "R-RURAL -O OUTSIDE CITY",
        "U-URBAN -I INSIDE CITY",
        "U-URBAN -O OUTSIDE CITY",
        "-INVALID DATA",
    ),
    "ramp_types": tuple("ABCDEFGHJKLMPRVZ"),
}
SECTION_ORDER = ("highway_groups", "on_off", "population_groups", "ramp_types")
NORMALIZED_HEADERS = ("Category", "Count")

VISUAL_REVIEW = {
    "workflow": "PDF skill: Poppler 150-dpi render plus original-resolution visual inspection",
    "reviewed_utc_date": "2026-07-12",
    "page_pngs": [
        {"page": 1, "bytes": 118_863,
         "sha256": "ec480efd1725cab789076a0da5e4561af18c712e774ac598aba176831bd83d76"},
        {"page": 2, "bytes": 61_636,
         "sha256": "11c6c322e8a057248337a04a29ae47282a7221d20302ccab299a8e402b7bc502"},
        {"page": 3, "bytes": 140_749,
         "sha256": "052ae2fc34d619bbe56ed4f534bff1013d9f19de874163f0784e645df0377dd6"},
    ],
    "observations": (
        "All three landscape-letter pages were legible and unclipped: page 1 is the policy "
        "cover, page 2 is report provenance/criteria, and page 3 is the four-axis summary. "
        "The renderer emitted missing-display-font warnings but substituted legible glyphs; "
        "semantic acceptance is therefore bound to PDF chars/words/content streams, not to "
        "font substitution in the PNGs."),
}


class ConservationError(ValueError):
    """The bound corpus did not satisfy the independent conservation contract."""


@dataclass(frozen=True)
class CategoryRecord:
    section: str
    ordinal: int
    code: str
    label: str
    count: int
    page: int
    top: str
    x0: str


def _identity(identity: FileIdentity) -> dict[str, object]:
    return asdict(identity)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _coord(value: object) -> str:
    return str(float(value))


def _typed(value: object) -> list[object]:
    if value is None:
        return ["null", None]
    if type(value) is bool:
        return ["bool", value]
    if type(value) is int:
        return ["int", str(value)]
    if isinstance(value, Decimal):
        return ["decimal", str(value)]
    if isinstance(value, str):
        return ["str", value]
    return [type(value).__name__, repr(value)]


def _wire(row: Sequence[object]) -> bytes:
    return (json.dumps([_typed(value) for value in row], ensure_ascii=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _ordered_digest(rows: Iterable[Sequence[object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_wire(row))
    return digest.hexdigest()


def _multiset_digest(rows: Iterable[Sequence[object]]) -> tuple[str, Counter[str]]:
    counter = Counter(_wire(row).decode("utf-8").rstrip("\n") for row in rows)
    digest = hashlib.sha256()
    for item, count in sorted(counter.items()):
        digest.update(f"{count}\t{item}\n".encode("utf-8"))
    return digest.hexdigest(), counter


def _field_digest(values: Sequence[object]) -> dict[str, object]:
    ordered = _ordered_digest((value,) for value in values)
    multiset, counter = _multiset_digest((value,) for value in values)
    types = Counter(_typed(value)[0] for value in values)
    return {
        "count": len(values),
        "ordered_typed_sha256": ordered,
        "multiset_typed_sha256": multiset,
        "distinct_typed_values": len(counter),
        "type_counts": dict(sorted(types.items())),
    }


def _capture_bound(path: Path, binding: dict[str, object], label: str,
                   *, max_bytes: int) -> Any:
    captured = capture_file_bytes(path, max_bytes=max_bytes)
    expected = (int(binding["bytes"]), str(binding["sha256"]).lower())
    actual = (captured.identity.size, captured.identity.sha256)
    if actual != expected:
        raise ConservationError(
            f"{label} identity mismatch: expected {expected}, observed {actual}")
    return captured


def _strict_json(payload: bytes, label: str) -> object:
    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ConservationError(f"{label} contains duplicate JSON key {key!r}")
            result[key] = value
        return result

    def bad_constant(value: str) -> object:
        raise ConservationError(f"{label} contains non-finite JSON constant {value}")

    try:
        return json.loads(payload.decode("utf-8"), object_pairs_hook=pairs_hook,
                          parse_constant=bad_constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConservationError(f"{label} is not strict UTF-8 JSON") from exc


def _word_manifest(page: Any) -> list[dict[str, object]]:
    return [
        {
            "text": str(word["text"]),
            "x0": _coord(word["x0"]),
            "top": _coord(word["top"]),
            "x1": _coord(word["x1"]),
            "bottom": _coord(word["bottom"]),
        }
        for word in page.extract_words(
            x_tolerance=1, y_tolerance=1, keep_blank_chars=False)
    ]


def _char_manifest(page: Any) -> list[dict[str, object]]:
    return [
        {
            "text": str(char.get("text", "")),
            "fontname": str(char.get("fontname", "")),
            "size": _coord(char.get("size", 0)),
            "x0": _coord(char["x0"]),
            "top": _coord(char["top"]),
            "x1": _coord(char["x1"]),
            "bottom": _coord(char["bottom"]),
            "upright": bool(char.get("upright", False)),
        }
        for char in page.chars
    ]


def _graphic_manifest(page: Any) -> list[dict[str, object]]:
    graphics: list[dict[str, object]] = []
    for kind in ("rect", "line", "curve", "image"):
        for item in page.objects.get(kind, []):
            graphics.append({
                "kind": kind,
                "x0": _coord(item.get("x0", 0)),
                "top": _coord(item.get("top", 0)),
                "x1": _coord(item.get("x1", 0)),
                "bottom": _coord(item.get("bottom", 0)),
                "width": _coord(item.get("width", 0)),
                "height": _coord(item.get("height", 0)),
            })
    return graphics


def _role_for_word(page_number: int, word: dict[str, object]) -> str | None:
    x0 = float(word["x0"])
    top = float(word["top"])
    if page_number == 1:
        if top < 180:
            return "cover_title"
        if 180 <= top < 340:
            return "policy_notice"
        return None
    if page_number == 2:
        if top < 200:
            return "cover_title"
        if 200 <= top < 315:
            return "report_parameters"
        if 315 <= top < 350:
            return "location_criteria"
        if 350 <= top < 390:
            return "selection_criteria"
        return None
    if page_number == 3:
        if top < 50:
            return "report_header"
        if 85 <= top < 118:
            return "section_headers"
        if x0 < 300 and 118 <= top < 225:
            return "highway_groups"
        if x0 < 300 and 250 <= top < 340:
            return "on_off"
        if x0 < 300 and 350 <= top < 485:
            return "population_groups"
        if x0 >= 300 and 118 <= top < 430:
            return "ramp_types"
        if x0 >= 300 and 445 <= top < 485:
            return "total"
    return None


def _role_manifest(page_number: int, words: list[dict[str, object]]) -> dict[str, object]:
    roles: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    residue: list[dict[str, object]] = []
    for word in words:
        role = _role_for_word(page_number, word)
        if role is None:
            residue.append(word)
        else:
            roles[role].append(word)
    return {
        "role_counts": {role: len(items) for role, items in sorted(roles.items())},
        "role_word_layout_sha256": {
            role: _sha(json.dumps(items, ensure_ascii=False, separators=(",", ":"))
                       .encode("utf-8"))
            for role, items in sorted(roles.items())
        },
        "classified_words": sum(len(items) for items in roles.values()),
        "unclassified_words": residue,
    }


def _observed_role_universe(page_audits: Sequence[dict[str, object]]) -> list[str]:
    return sorted(
        f"page_{page['page']}.{role}"
        for page in page_audits
        for role in page["roles"]["role_counts"]
    )


def _role_disposition_coverage(
        observed_roles: Sequence[str],
        dispositions: Sequence[dict[str, object]]) -> dict[str, object]:
    observed = list(observed_roles)
    declared = [str(item.get("role_id", "")) for item in dispositions]
    counts = Counter(declared)
    duplicates = sorted(role for role, count in counts.items() if count > 1)
    missing = sorted(set(observed) - set(declared))
    extra = sorted(set(declared) - set(observed))
    exact = (
        len(observed) == len(set(observed))
        and not duplicates and not missing and not extra
        and len(declared) == len(observed)
    )
    return {
        "observed_role_count": len(observed),
        "declared_disposition_count": len(declared),
        "observed_roles": observed,
        "declared_roles": declared,
        "missing_roles": missing,
        "duplicate_roles": duplicates,
        "extra_roles": extra,
        "exact_one_to_one_coverage": exact,
    }


def _line_words(words: list[dict[str, object]], anchor: dict[str, object],
                x_min: float, x_max: float, tolerance: float) -> list[dict[str, object]]:
    selected = [
        word for word in words
        if x_min <= float(word["x0"]) < x_max
        and abs(float(word["top"]) - float(anchor["top"])) <= tolerance
    ]
    return sorted(selected, key=lambda item: float(item["x0"]))


def _joined(words: Sequence[dict[str, object]]) -> str:
    return " ".join(str(word["text"]) for word in words)


def _parse_highway(words: list[dict[str, object]]) -> list[CategoryRecord]:
    counts = sorted(
        (word for word in words
         if 70 <= float(word["x0"]) < 120
         and 118 <= float(word["top"]) < 225
         and str(word["text"]).isdigit()),
        key=lambda item: float(item["top"]))
    records: list[CategoryRecord] = []
    for ordinal, count_word in enumerate(counts, 1):
        label = _joined(_line_words(words, count_word, 145, 290, 1.5))
        code = "Others" if label == "Others" else label.split(" - ", 1)[0]
        records.append(CategoryRecord(
            "highway_groups", ordinal, code, label, int(str(count_word["text"])),
            3, _coord(count_word["top"]), _coord(count_word["x0"])))
    return records


def _parse_on_off(words: list[dict[str, object]]) -> list[CategoryRecord]:
    counts = sorted(
        (word for word in words
         if 70 <= float(word["x0"]) < 120
         and 280 <= float(word["top"]) < 340
         and str(word["text"]).isdigit()),
        key=lambda item: float(item["top"]))
    records: list[CategoryRecord] = []
    for ordinal, count_word in enumerate(counts, 1):
        label = _joined(_line_words(words, count_word, 145, 260, 1.5))
        code = label.split()[0] if label else ""
        records.append(CategoryRecord(
            "on_off", ordinal, code, label, int(str(count_word["text"])),
            3, _coord(count_word["top"]), _coord(count_word["x0"])))
    return records


def _parse_population(words: list[dict[str, object]]) -> list[CategoryRecord]:
    counts = sorted(
        (word for word in words
         if 70 <= float(word["x0"]) < 120
         and 380 <= float(word["top"]) < 485
         and str(word["text"]).isdigit()),
        key=lambda item: float(item["top"]))
    records: list[CategoryRecord] = []
    group = ""
    for ordinal, count_word in enumerate(counts, 1):
        fragment = _joined(_line_words(words, count_word, 135, 300, 6.0))
        if fragment.startswith("R-RURAL"):
            group = "R-RURAL"
            label = fragment
        elif fragment.startswith("U-URBAN"):
            group = "U-URBAN"
            label = fragment
        elif fragment.startswith("-O") and group:
            label = f"{group} {fragment}"
        else:
            label = fragment
        records.append(CategoryRecord(
            "population_groups", ordinal, label, label,
            int(str(count_word["text"])), 3, _coord(count_word["top"]),
            _coord(count_word["x0"])))
    return records


def _parse_ramp_types(words: list[dict[str, object]]) -> list[CategoryRecord]:
    counts = sorted(
        (word for word in words
         if 370 <= float(word["x0"]) < 410
         and 118 <= float(word["top"]) < 430
         and str(word["text"]).isdigit()),
        key=lambda item: float(item["top"]))
    records: list[CategoryRecord] = []
    for ordinal, count_word in enumerate(counts, 1):
        label = _joined(_line_words(words, count_word, 475, 760, 1.5))
        code = label.split(" - ", 1)[0]
        records.append(CategoryRecord(
            "ramp_types", ordinal, code, label, int(str(count_word["text"])),
            3, _coord(count_word["top"]), _coord(count_word["x0"])))
    return records


def _extract_one(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        raise ConservationError(f"PDF is missing {label}")
    return match.group(1).strip()


def _validate_source_categories(
        sections: dict[str, list[CategoryRecord]], total: int) -> dict[str, object]:
    anomalies: list[dict[str, object]] = []
    section_totals: dict[str, int] = {}
    section_contiguity: dict[str, bool] = {}
    for section in SECTION_ORDER:
        records = sections[section]
        actual = tuple(record.code for record in records)
        expected = EXPECTED_SECTION_CODES[section]
        if actual != expected:
            anomalies.append({
                "kind": "category_shape_or_order", "section": section,
                "expected": list(expected), "actual": list(actual),
            })
        if len(actual) != len(set(actual)):
            anomalies.append({"kind": "duplicate_category", "section": section})
        if any(type(record.count) is not int or record.count < 0 for record in records):
            anomalies.append({"kind": "invalid_count_domain", "section": section})
        tops = [float(record.top) for record in records]
        contiguous = (
            [record.ordinal for record in records] == list(range(1, len(records) + 1))
            and all(left < right for left, right in zip(tops, tops[1:])))
        section_contiguity[section] = contiguous
        if not contiguous:
            anomalies.append({"kind": "physical_order", "section": section})
        section_totals[section] = sum(record.count for record in records)
        if section_totals[section] != total:
            anomalies.append({
                "kind": "axis_total_mismatch", "section": section,
                "actual": section_totals[section], "expected": total,
            })
    return {
        "anomalies": anomalies,
        "section_totals": section_totals,
        "all_four_axes_equal_total": all(value == total for value in section_totals.values()),
        "section_physical_order_contiguous": section_contiguity,
    }


def _parse_pdf(payload: bytes) -> dict[str, object]:
    strict = PdfReader(io.BytesIO(payload), strict=True)
    if strict.is_encrypted:
        raise ConservationError("authoritative PDF unexpectedly requires decryption")
    if len(strict.pages) != RAW_BINDING["pages"]:
        raise ConservationError("authoritative PDF page count changed")
    metadata = {str(key): str(value) for key, value in (strict.metadata or {}).items()}
    if metadata != EXPECTED_PDF_METADATA:
        raise ConservationError(
            f"authoritative PDF metadata changed: {metadata!r}")
    strict_pages: list[dict[str, object]] = []
    for number, page in enumerate(strict.pages, 1):
        media = [float(value) for value in page.mediabox]
        crop = [float(value) for value in page.cropbox]
        if media != [0.0, 0.0, 792.0, 612.0] or crop != media or page.rotation != 0:
            raise ConservationError(f"PDF page {number} geometry/rotation changed")
        content = page.get_contents().get_data()
        strict_pages.append({
            "page": number,
            "media_box": media,
            "crop_box": crop,
            "rotation": page.rotation,
            "decoded_content_bytes": len(content),
            "decoded_content_sha256": _sha(content),
        })

    page_audits: list[dict[str, object]] = []
    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        if len(pdf.pages) != RAW_BINDING["pages"]:
            raise ConservationError("pdfplumber disagrees with strict page topology")
        texts: list[str] = []
        manifests: list[list[dict[str, object]]] = []
        for number, page in enumerate(pdf.pages, 1):
            if (float(page.width), float(page.height)) != (792.0, 612.0):
                raise ConservationError(f"pdfplumber page {number} geometry changed")
            text = page.extract_text(x_tolerance=1, y_tolerance=2) or ""
            words = _word_manifest(page)
            chars = _char_manifest(page)
            graphics = _graphic_manifest(page)
            if len(chars) != EXPECTED_CHAR_COUNTS[number - 1]:
                raise ConservationError(f"PDF page {number} character topology changed")
            if len(words) != EXPECTED_WORD_COUNTS[number - 1]:
                raise ConservationError(f"PDF page {number} word topology changed")
            roles = _role_manifest(number, words)
            if roles["unclassified_words"]:
                raise ConservationError(
                    f"PDF page {number} has unexplained word-layout residue")
            page_audits.append({
                "page": number,
                "width": float(page.width),
                "height": float(page.height),
                "text_characters": len(text),
                "text_sha256": _sha(text.encode("utf-8")),
                "character_count": len(chars),
                "character_layout_sha256": _sha(json.dumps(
                    chars, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
                "word_count": len(words),
                "word_layout_sha256": _sha(json.dumps(
                    words, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
                "graphic_object_count": len(graphics),
                "graphic_layout_sha256": _sha(json.dumps(
                    graphics, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
                "roles": roles,
            })
            texts.append(text)
            manifests.append(words)

    cover, parameters_text, report_text = texts
    if "OTM22270" not in cover or "TSAR - RAMPS SUMMARY" not in cover:
        raise ConservationError("cover report identity is missing")
    if "Policy controlling the use" not in cover or "4. The contents" not in cover:
        raise ConservationError("cover policy role is incomplete")

    parameters = {
        "report_date": _extract_one(
            r"REPORT DATE\s*:\s*(\d{2}/\d{2}/\d{4})", parameters_text, "report date"),
        "reference_date": _extract_one(
            r"REFERENCE DATE\s*:\s*(\d{2}/\d{2}/\d{4})", parameters_text,
            "reference date"),
        "submittor": _extract_one(
            r"SUBMITTOR\s*:\s*([A-Z0-9]+)", parameters_text, "submittor"),
        "report_title": _extract_one(
            r"REPORT TITLE\s*:\s*'\s*([^']+?)\s*'", parameters_text, "report title"),
        "event_id": _extract_one(
            r"EVENT ID\s*:\s*(\d+)", parameters_text, "event id"),
        "location_criteria": _extract_one(
            r"LOCATION CRITERIA:\s*([A-Z]+)", parameters_text, "location criteria"),
        "selection_criteria": "",
    }
    if not parameters_text.rstrip().endswith("SELECTION CRITERIA:"):
        raise ConservationError("selection-criteria blank-state topology changed")

    header = {
        "report_identifier": _extract_one(r"^(OTM\d+)", report_text, "report identifier"),
        "report_date": _extract_one(
            r"^OTM\d+.*?\n(\d{2}/\d{2}/\d{4})", report_text, "page-3 date"),
        "report_time": _extract_one(
            r"^\d{2}/\d{2}/\d{4}.*?\n(\d{2}:\d{2}\s+[AP]M)", report_text,
            "page-3 report time"),
        "page_number": _extract_one(r"Page#\s+(\d+)", report_text, "report page number"),
        "event_id": _extract_one(r"Event ID\s+(\d+)", report_text, "page-3 event id"),
        "report_title": _extract_one(
            r"'\s*([^']+?)\s*'", report_text, "page-3 report title"),
    }
    if (parameters["report_date"] != header["report_date"]
            or parameters["event_id"] != header["event_id"]
            or parameters["report_title"] != header["report_title"]
            or header["report_identifier"] != "OTM22270"
            or header["page_number"] != "1"):
        raise ConservationError("cross-page printed provenance is internally inconsistent")

    data_words = manifests[2]
    sections = {
        "highway_groups": _parse_highway(data_words),
        "on_off": _parse_on_off(data_words),
        "population_groups": _parse_population(data_words),
        "ramp_types": _parse_ramp_types(data_words),
    }
    total_words = [
        word for word in data_words
        if 500 <= float(word["x0"]) < 550
        and 445 <= float(word["top"]) < 485
        and str(word["text"]).isdigit()
    ]
    if len(total_words) != 1:
        raise ConservationError("PDF total row is absent or ambiguous")
    total = int(str(total_words[0]["text"]))
    validation = _validate_source_categories(sections, total)
    if validation["anomalies"]:
        raise ConservationError(
            f"PDF category contract failed: {validation['anomalies']!r}")
    records = [record for section in SECTION_ORDER for record in sections[section]]
    if len(records) + 1 != NORMALIZED_BINDING["rows"]:
        raise ConservationError("source semantic row universe is not 31 rows")
    return {
        "strict_topology": strict_pages,
        "metadata": metadata,
        "page_layout_audits": page_audits,
        "parameters": parameters,
        "report_header": header,
        "sections": sections,
        "records": records,
        "total": total,
        "validation": validation,
    }


def _normalized_archive_topology(payload: bytes) -> dict[str, object]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise ConservationError("normalized XLSX has duplicate archive members")
            forbidden = [
                name for name in names
                if name.casefold().endswith("vbaProject.bin".casefold())
                or "externallink" in name.casefold()
            ]
            if forbidden:
                raise ConservationError(
                    f"normalized XLSX contains forbidden active/external members: {forbidden}")
            members = []
            for info in infos:
                data = archive.read(info.filename)
                members.append({
                    "name": info.filename,
                    "compressed_bytes": info.compress_size,
                    "uncompressed_bytes": info.file_size,
                    "crc32": f"{info.CRC:08x}",
                    "uncompressed_sha256": _sha(data),
                })
            return {
                "member_count": len(members),
                "members_ordered_sha256": _sha(json.dumps(
                    members, ensure_ascii=False, separators=(",", ":")).encode("utf-8")),
                "members": members,
                "forbidden_members": forbidden,
            }
    except zipfile.BadZipFile as exc:
        raise ConservationError("normalized source is not a readable XLSX") from exc


def _load_normalized() -> tuple[list[tuple[int, str, Decimal]], dict[str, object]]:
    spec = SheetSpec(
        sheet_name=str(NORMALIZED_BINDING["sheet"]),
        columns=tuple(ColumnSpec(header) for header in NORMALIZED_HEADERS),
        exact_schema=True,
    )
    sheet = read_sheet(NORMALIZED_XLSX, spec)
    expected_identity = (NORMALIZED_BINDING["bytes"], NORMALIZED_BINDING["sha256"])
    actual_identity = (sheet.pre_identity.size, sheet.pre_identity.sha256)
    if actual_identity != expected_identity or sheet.pre_identity != sheet.post_identity:
        raise ConservationError("normalized XLSX reader identity is not the accepted r7 member")
    if len(sheet.rows) != NORMALIZED_BINDING["rows"]:
        raise ConservationError("normalized XLSX row count changed")
    rows: list[tuple[int, str, Decimal]] = []
    for streamed in sheet.rows:
        category, count = streamed.values
        if not isinstance(category, str) or not category:
            raise ConservationError(
                f"normalized row {streamed.source_row} has an invalid Category")
        if not isinstance(count, Decimal) or count != count.to_integral_value() or count < 0:
            raise ConservationError(
                f"normalized row {streamed.source_row} has a non-integral Count")
        rows.append((streamed.source_row, category, count))
    source_rows = [row[0] for row in rows]
    if source_rows != list(range(2, 33)):
        raise ConservationError("normalized physical rows are not contiguous 2..32")
    return rows, {
        "sheet_name": sheet.sheet_name,
        "headers": list(sheet.headers),
        "date_system": sheet.date_system,
        "pre_identity": _identity(sheet.pre_identity),
        "post_identity": _identity(sheet.post_identity),
        "physical_source_rows": source_rows,
        "physical_rows_contiguous": True,
    }


def _project_source(pdf: dict[str, object]) -> list[tuple[str, Decimal]]:
    prefixes = {
        "highway_groups": "Highway Group: ",
        "on_off": "On/Off: ",
        "population_groups": "Population: ",
        "ramp_types": "Ramp Type: ",
    }
    rows: list[tuple[str, Decimal]] = []
    for section in SECTION_ORDER:
        for record in pdf["sections"][section]:
            rows.append((prefixes[section] + record.label, Decimal(record.count)))
    rows.append(("Total Number of Ramps", Decimal(pdf["total"])))
    return rows


def _projection_comparison(expected: Sequence[tuple[str, Decimal]],
                           observed_rows: Sequence[tuple[int, str, Decimal]]) -> dict[str, object]:
    observed = [(category, count) for _source_row, category, count in observed_rows]
    differences: list[dict[str, object]] = []
    for index in range(max(len(expected), len(observed))):
        left = expected[index] if index < len(expected) else None
        right = observed[index] if index < len(observed) else None
        if left != right:
            differences.append({
                "ordinal": index + 1,
                "expected": None if left is None else [left[0], str(left[1]), type(left[1]).__name__],
                "observed": None if right is None else [right[0], str(right[1]), type(right[1]).__name__],
            })
    expected_multi, expected_counter = _multiset_digest(expected)
    observed_multi, observed_counter = _multiset_digest(observed)
    expected_ordered = _ordered_digest(expected)
    observed_ordered = _ordered_digest(observed)
    return {
        "expected_rows": len(expected),
        "observed_rows": len(observed),
        "paired_rows": min(len(expected), len(observed)),
        "ordered_typed_sha256": {
            "source_projection": expected_ordered,
            "normalized": observed_ordered,
        },
        "multiset_typed_sha256": {
            "source_projection": expected_multi,
            "normalized": observed_multi,
        },
        "ordered_exact": expected_ordered == observed_ordered and not differences,
        "multiset_exact": expected_counter == observed_counter,
        "differences": differences,
        "unexplained_residue_count": len(differences),
    }


def _validate_r7(witness: dict[str, object], sidecar: dict[str, object]) -> dict[str, object]:
    if witness.get("source_root") != str(RAW_PDF.parents[2]):
        raise ConservationError("r7 witness source_root is not the authoritative tsn_library")
    if witness.get("output_root") != str(R7_ROOT):
        raise ConservationError("r7 witness output_root changed")
    if witness.get("source_universe_stable") is not True:
        raise ConservationError("r7 witness did not certify stable source universe")
    families = [item for item in witness.get("families", [])
                if isinstance(item, dict) and item.get("report") == "ramp_summary"]
    if len(families) != 1:
        raise ConservationError("r7 witness does not contain exactly one ramp_summary family")
    family = families[0]
    raw = family.get("raw_manifest", {})
    members = raw.get("members", [])
    output = family.get("output", {})
    result = family.get("result", {})
    reuse = family.get("reuse", {})
    status = family.get("status_after_build", {})
    expected_raw_member = {
        "relative_path": "ramp_summary/raw/Ramp Summary Statewide_TSN.pdf",
        "bytes": RAW_BINDING["bytes"],
        "sha256": RAW_BINDING["sha256"],
    }
    checks = {
        "raw_manifest_exact": (
            raw.get("member_count") == 1
            and raw.get("bytes") == RAW_BINDING["bytes"]
            and raw.get("sha256") == "1983ae8865cd235b7a77ccc6fc8abe7f6f8f788d06bdf032aa4abdb807c6d408"
            and members == [expected_raw_member]),
        "output_identity_exact": (
            output.get("bytes") == NORMALIZED_BINDING["bytes"]
            and output.get("sha256") == NORMALIZED_BINDING["sha256"]
            and output.get("sidecar_sha256") == SIDECAR_BINDING["sha256"]),
        "producer_complete": (
            result.get("completion") == "complete"
            and result.get("failed_inputs") == 0
            and result.get("skipped_inputs") == 0),
        "reuse_certified_unchanged": (
            reuse.get("certified") is True
            and reuse.get("output_unchanged") is True
            and reuse.get("sidecar_unchanged") is True),
        "status_current_complete": (
            status.get("current") is True
            and status.get("producer_complete") is True
            and status.get("raw_admissible") is True
            and status.get("coherent_snapshot_current") is True
            and status.get("identity_token") == IDENTITY_TOKEN),
    }
    sidecar_manifest = sidecar.get("tsn_raw_manifest", {})
    sidecar_members = sidecar_manifest.get("members", [])
    checks.update({
        "sidecar_complete": (
            sidecar.get("completion") == "complete"
            and sidecar.get("failed_inputs") == 0
            and sidecar.get("skipped_inputs") == 0
            and sidecar.get("tsn_normalization_version") == NORMALIZED_BINDING["normalization_version"]),
        "sidecar_raw_manifest_exact": (
            sidecar_manifest.get("member_count") == RAW_MANIFEST_BINDING["member_count"]
            and sidecar_manifest.get("byte_length") == RAW_MANIFEST_BINDING["byte_length"]
            and sidecar_manifest.get("sha256") == RAW_MANIFEST_BINDING["sha256"]
            and sidecar_members == [{
                "relative_path": RAW_MANIFEST_BINDING["relative_path"],
                "byte_length": RAW_BINDING["bytes"],
                "sha256": RAW_BINDING["sha256"],
            }]),
        "sidecar_output_identity_exact": (
            sidecar.get("tsn_normalized_workbook_identity") == {
                "version": 1,
                "algorithm": "sha256",
                "byte_length": NORMALIZED_BINDING["bytes"],
                "sha256": NORMALIZED_BINDING["sha256"],
            }
            and sidecar.get("tsn_artifact_identity_token") == IDENTITY_TOKEN),
    })
    if not all(checks.values()):
        raise ConservationError(
            f"r7 lifecycle witness/sidecar contract failed: {checks!r}")
    return {"checks": checks, "family": family, "sidecar": sidecar}


def _run_gate(path: Path, label: str) -> dict[str, object]:
    before = capture_file_identity(path)
    process = subprocess.run(
        [sys.executable, str(path)], cwd=str(GENERATOR_PATH.parent.parent),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180, check=False)
    after = capture_file_identity(path)
    if before != after:
        raise ConservationError(f"{label} changed while it executed")
    if process.returncode != 0:
        raise ConservationError(
            f"{label} failed with exit {process.returncode}: {process.stdout}{process.stderr}")
    output = (process.stdout + process.stderr).strip()
    return {
        "status": "executed_pass",
        "command": [sys.executable, str(path)],
        "exit_code": process.returncode,
        "output": output,
        "output_sha256": _sha(output.encode("utf-8")),
        "identity_before": _identity(before),
        "identity_after": _identity(after),
    }


def _loaded_parser_module_paths() -> dict[str, Path]:
    """Return every loaded source/binary module in the PDF parser execution set."""
    prefixes = ("pdfplumber", "pdfminer", "pypdf")
    observed: dict[str, Path] = {}
    for module_name, module in sorted(sys.modules.items()):
        if not any(module_name == prefix or module_name.startswith(prefix + ".")
                   for prefix in prefixes):
            continue
        raw_path = getattr(module, "__file__", None)
        if raw_path is None:
            continue
        observed[f"parser_module::{module_name}"] = Path(raw_path).resolve()
    if not observed:
        raise ConservationError("no loaded PDF parser module files were observed")
    return observed


def _parser_module_manifest(paths: dict[str, Path]) -> tuple[dict[str, object],
                                                              dict[str, FileIdentity]]:
    identities = {
        name: capture_file_identity(path)
        for name, path in sorted(paths.items())
    }
    entries = [
        {
            "module": name.removeprefix("parser_module::"),
            "path": str(paths[name]),
            "identity": _identity(identities[name]),
        }
        for name in sorted(paths)
    ]
    return {
        "package_prefixes": ["pdfplumber", "pdfminer", "pypdf"],
        "module_file_count": len(entries),
        "serialization": "canonical JSON of sorted module/path/full-file-identity entries",
        "ordered_manifest_sha256": _sha(json.dumps(
            entries, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")),
        "entries": entries,
    }, identities


def _mutation_probes(pdf: dict[str, object], expected: list[tuple[str, Decimal]],
                     normalized: list[tuple[int, str, Decimal]],
                     dispositions: list[dict[str, object]],
                     observed_roles: list[str]) -> list[dict[str, object]]:
    probes: list[dict[str, object]] = []

    changed_count = list(expected)
    changed_count[0] = (changed_count[0][0], changed_count[0][1] + 1)
    probes.append({
        "name": "source category count mutation",
        "detected": not _projection_comparison(changed_count, normalized)["ordered_exact"],
    })

    changed_label = list(expected)
    changed_label[1] = (changed_label[1][0] + "!", changed_label[1][1])
    probes.append({
        "name": "source category label mutation",
        "detected": not _projection_comparison(changed_label, normalized)["ordered_exact"],
    })

    swapped = list(normalized)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    swapped_result = _projection_comparison(expected, swapped)
    probes.append({
        "name": "normalized row order swap",
        "detected": (not swapped_result["ordered_exact"] and swapped_result["multiset_exact"]),
    })

    wrong_type = list(normalized)
    source_row, category, count = wrong_type[0]
    wrong_type[0] = (source_row, category, str(count))
    probes.append({
        "name": "same-text normalized Count type mutation",
        "detected": not _projection_comparison(expected, wrong_type)["ordered_exact"],
    })

    gap_rows = list(normalized)
    gap_rows[5] = (gap_rows[5][0] + 1, gap_rows[5][1], gap_rows[5][2])
    probes.append({
        "name": "normalized physical row gap",
        "detected": [row[0] for row in gap_rows] != list(range(2, 33)),
    })

    first_section = pdf["sections"]["highway_groups"]
    duplicate = list(first_section) + [first_section[0]]
    probes.append({
        "name": "duplicate PDF category",
        "detected": len({record.code for record in duplicate}) != len(duplicate),
    })
    dropped = list(first_section[1:])
    probes.append({
        "name": "dropped PDF category",
        "detected": tuple(record.code for record in dropped)
        != EXPECTED_SECTION_CODES["highway_groups"],
    })

    metadata_before = _ordered_digest(
        (key, value) for key, value in sorted(pdf["parameters"].items()))
    mutated_parameters = dict(pdf["parameters"])
    mutated_parameters["event_id"] += "1"
    metadata_after = _ordered_digest(
        (key, value) for key, value in sorted(mutated_parameters.items()))
    probes.append({
        "name": "source-only printed provenance mutation",
        "detected": metadata_before != metadata_after,
    })

    synthetic = {"text": "UNEXPLAINED", "x0": "300.0", "top": "80.0",
                 "x1": "310.0", "bottom": "90.0"}
    probes.append({
        "name": "unclassified PDF layout residue",
        "detected": _role_for_word(3, synthetic) is None,
    })

    nonconserving = [CategoryRecord(
        record.section, record.ordinal, record.code, record.label,
        record.count + (1 if index == 0 else 0), record.page, record.top, record.x0)
        for index, record in enumerate(first_section)]
    mutated_sections = dict(pdf["sections"])
    mutated_sections["highway_groups"] = nonconserving
    validation = _validate_source_categories(mutated_sections, pdf["total"])
    probes.append({
        "name": "classification-axis subtotal mutation",
        "detected": not validation["all_four_axes_equal_total"],
    })

    missing_role = list(dispositions[1:])
    missing_coverage = _role_disposition_coverage(observed_roles, missing_role)
    probes.append({
        "name": "missing source-role disposition",
        "detected": (
            not missing_coverage["exact_one_to_one_coverage"]
            and dispositions[0]["role_id"] in missing_coverage["missing_roles"]),
    })

    duplicate_role = list(dispositions) + [dict(dispositions[0])]
    duplicate_coverage = _role_disposition_coverage(observed_roles, duplicate_role)
    probes.append({
        "name": "duplicate source-role disposition",
        "detected": (
            not duplicate_coverage["exact_one_to_one_coverage"]
            and dispositions[0]["role_id"] in duplicate_coverage["duplicate_roles"]),
    })

    extra_role = list(dispositions) + [{
        "role_id": "page_9.unobserved", "disposition": "invalid test role"}]
    extra_coverage = _role_disposition_coverage(observed_roles, extra_role)
    probes.append({
        "name": "unobserved extra source-role disposition",
        "detected": (
            not extra_coverage["exact_one_to_one_coverage"]
            and "page_9.unobserved" in extra_coverage["extra_roles"]),
    })
    return probes


def _source_digests(pdf: dict[str, object]) -> dict[str, object]:
    physical = sorted(
        pdf["records"], key=lambda record: (record.page, float(record.top), float(record.x0)))
    semantic_rows = [
        (record.section, record.ordinal, record.code, record.label, record.count)
        for record in pdf["records"]
    ] + [("total", 1, "TOTAL", "Total number of Ramps", pdf["total"])]
    physical_rows = [
        (record.page, record.top, record.x0, record.section, record.code,
         record.label, record.count)
        for record in physical
    ]
    section_digests: dict[str, object] = {}
    for section in SECTION_ORDER:
        rows = [
            (record.ordinal, record.code, record.label, record.count)
            for record in pdf["sections"][section]
        ]
        multiset, _counter = _multiset_digest(rows)
        section_digests[section] = {
            "row_count": len(rows),
            "ordered_typed_sha256": _ordered_digest(rows),
            "multiset_typed_sha256": multiset,
            "fields": {
                "code": _field_digest([row[1] for row in rows]),
                "label": _field_digest([row[2] for row in rows]),
                "count": _field_digest([row[3] for row in rows]),
            },
        }
    semantic_multiset, _ = _multiset_digest(semantic_rows)
    physical_multiset, _ = _multiset_digest(physical_rows)
    return {
        "semantic_section_order": {
            "row_count": len(semantic_rows),
            "ordered_typed_sha256": _ordered_digest(semantic_rows),
            "multiset_typed_sha256": semantic_multiset,
        },
        "physical_page_order": {
            "row_count": len(physical_rows),
            "ordered_typed_sha256": _ordered_digest(physical_rows),
            "multiset_typed_sha256": physical_multiset,
        },
        "per_section": section_digests,
    }


def _revalidate(expected: dict[str, FileIdentity], paths: dict[str, Path],
                expected_parser_paths: dict[str, Path] | None = None
                ) -> tuple[bool, dict[str, object]]:
    if set(paths) != set(expected):
        raise ConservationError("revalidation path and identity universes differ")
    observed = {name: capture_file_identity(path) for name, path in paths.items()}
    identity_current = all(
        observed[name] == identity for name, identity in expected.items())
    loaded_set_current = True
    loaded_set_detail: dict[str, object] | None = None
    if expected_parser_paths is not None:
        actual_parser_paths = _loaded_parser_module_paths()
        loaded_set_current = actual_parser_paths == expected_parser_paths
        loaded_set_detail = {
            "current": loaded_set_current,
            "expected": {name: str(path) for name, path in sorted(expected_parser_paths.items())},
            "observed": {name: str(path) for name, path in sorted(actual_parser_paths.items())},
        }
    current = identity_current and loaded_set_current
    details = {
        name: {
            "expected": _identity(expected[name]),
            "observed": _identity(observed[name]),
            "current": observed[name] == expected[name],
        }
        for name in expected
    }
    if loaded_set_detail is not None:
        details["loaded_parser_module_set"] = loaded_set_detail
    return current, details


def run() -> tuple[dict[str, object], dict[str, FileIdentity],
                   dict[str, Path], dict[str, Path]]:
    reader_gate = _run_gate(READER_GATE_PATH, "generic immutable XLSX reader gate")
    summary_gate = _run_gate(SELF_GATE_PATH, "Ramp Summary oracle mutation gate")

    raw_capture = _capture_bound(
        RAW_PDF, RAW_BINDING, "authoritative Ramp Summary PDF", max_bytes=1_000_000)
    normalized_capture = _capture_bound(
        NORMALIZED_XLSX, NORMALIZED_BINDING, "accepted r7 normalized XLSX",
        max_bytes=10_000_000)
    sidecar_capture = _capture_bound(
        NORMALIZED_SIDECAR, SIDECAR_BINDING, "accepted r7 sidecar", max_bytes=1_000_000)
    witness_capture = _capture_bound(
        R7_WITNESS, R7_WITNESS_BINDING, "accepted r7 lifecycle witness",
        max_bytes=2_000_000)

    pdf = _parse_pdf(raw_capture.payload)
    parser_paths = _loaded_parser_module_paths()
    parser_manifest, parser_identities = _parser_module_manifest(parser_paths)
    normalized_rows, normalized_sheet = _load_normalized()
    topology = _normalized_archive_topology(normalized_capture.payload)
    sidecar = _strict_json(sidecar_capture.payload, "r7 normalized sidecar")
    witness = _strict_json(witness_capture.payload, "r7 lifecycle witness")
    if not isinstance(sidecar, dict) or not isinstance(witness, dict):
        raise ConservationError("r7 provenance artifacts must be JSON objects")
    lifecycle = _validate_r7(witness, sidecar)

    expected = _project_source(pdf)
    projection = _projection_comparison(expected, normalized_rows)
    projection_exact = bool(
        projection["ordered_exact"] and projection["multiset_exact"]
        and projection["unexplained_residue_count"] == 0)

    source_only_semantic = [
        "report_date", "reference_date", "submittor", "report_title", "event_id",
        "location_criteria", "report_identifier", "report_time",
    ]
    dispositions = [
        {
            "role_id": "page_1.cover_title",
            "disposition": "comparison_semantic_duplicate_source_only_omitted",
            "normalized_target": None,
            "omitted_facts": ["report_identifier", "report_title"],
            "conservation_impact": True,
        },
        {
            "role_id": "page_1.policy_notice",
            "disposition": "presentation_only_policy_text_digest_bound",
            "normalized_target": None,
            "conservation_impact": False,
        },
        {
            "role_id": "page_2.cover_title",
            "disposition": "comparison_semantic_duplicate_source_only_omitted",
            "normalized_target": None,
            "omitted_facts": ["report_identifier", "report_title"],
            "conservation_impact": True,
        },
        {
            "role_id": "page_2.report_parameters",
            "disposition": "comparison_semantic_source_only_omitted",
            "normalized_target": None,
            "omitted_facts": source_only_semantic[:5],
            "conservation_impact": True,
        },
        {
            "role_id": "page_2.location_criteria",
            "disposition": "comparison_semantic_source_only_omitted",
            "normalized_target": None,
            "omitted_facts": ["location_criteria"],
            "conservation_impact": True,
        },
        {
            "role_id": "page_2.selection_criteria",
            "disposition": "explicit_blank_digest_bound",
            "normalized_target": None,
            "conservation_impact": False,
        },
        {
            "role_id": "page_3.report_header",
            "disposition": "comparison_semantic_source_only_omitted",
            "normalized_target": None,
            "omitted_facts": source_only_semantic[6:],
            "conservation_impact": True,
        },
        {
            "role_id": "page_3.section_headers",
            "disposition": "presentation_structure_reproduced_by_category_prefixes",
            "normalized_target": ["Category"],
            "conservation_impact": False,
        },
        {
            "role_id": "page_3.highway_groups",
            "disposition": "one_to_one_label_prefix_projection",
            "normalized_target": ["Category", "Count"],
            "conservation_impact": False,
        },
        {
            "role_id": "page_3.on_off",
            "disposition": "one_to_one_label_prefix_projection",
            "normalized_target": ["Category", "Count"],
            "conservation_impact": False,
        },
        {
            "role_id": "page_3.population_groups",
            "disposition": "hierarchical_print_label_reassembled_then_prefix_projected",
            "normalized_target": ["Category", "Count"],
            "conservation_impact": False,
        },
        {
            "role_id": "page_3.ramp_types",
            "disposition": "one_to_one_label_prefix_projection",
            "normalized_target": ["Category", "Count"],
            "conservation_impact": False,
        },
        {
            "role_id": "page_3.total",
            "disposition": "one_to_one_canonical_label_projection",
            "normalized_target": ["Category", "Count"],
            "conservation_impact": False,
        },
    ]
    observed_roles = _observed_role_universe(pdf["page_layout_audits"])
    role_coverage = _role_disposition_coverage(observed_roles, dispositions)
    mutations = _mutation_probes(
        pdf, expected, normalized_rows, dispositions, observed_roles)
    mutation_complete = all(probe["detected"] for probe in mutations)
    semantic_omissions = [
        disposition for disposition in dispositions
        if disposition.get("conservation_impact") is True
    ]

    revalidation_paths = {
        "raw_pdf": RAW_PDF,
        "normalized_xlsx": NORMALIZED_XLSX,
        "normalized_sidecar": NORMALIZED_SIDECAR,
        "r7_witness": R7_WITNESS,
        "generator": GENERATOR_PATH,
        "independent_reader": READER_PATH,
        "reader_gate": READER_GATE_PATH,
        "summary_gate": SELF_GATE_PATH,
    }
    revalidation_paths.update(parser_paths)
    start_identities = {
        "raw_pdf": raw_capture.identity,
        "normalized_xlsx": normalized_capture.identity,
        "normalized_sidecar": sidecar_capture.identity,
        "r7_witness": witness_capture.identity,
        "generator": GENERATOR_START,
        "independent_reader": READER_START,
        "reader_gate": READER_GATE_START,
        "summary_gate": capture_file_identity(SELF_GATE_PATH),
    }
    start_identities.update(parser_identities)
    final_current, final_detail = _revalidate(
        start_identities, revalidation_paths, parser_paths)
    all_roles_classified = all(
        not page["roles"]["unclassified_words"] for page in pdf["page_layout_audits"])
    invariants = {
        "raw_private_capture_exact": raw_capture.identity.sha256 == RAW_BINDING["sha256"],
        "strict_pdf_topology_exact": len(pdf["strict_topology"]) == RAW_BINDING["pages"],
        "all_pdf_words_and_layout_roles_classified": all_roles_classified,
        "observed_pdf_roles_have_exact_one_to_one_dispositions": (
            role_coverage["exact_one_to_one_coverage"]),
        "source_category_shape_order_unique": not pdf["validation"]["anomalies"],
        "all_four_classification_axes_equal_printed_total": (
            pdf["validation"]["all_four_axes_equal_total"]),
        "source_physical_order_contiguous": all(
            pdf["validation"]["section_physical_order_contiguous"].values()),
        "normalized_private_capture_exact": (
            normalized_capture.identity.sha256 == NORMALIZED_BINDING["sha256"]),
        "normalized_physical_rows_contiguous": normalized_sheet["physical_rows_contiguous"],
        "normalized_archive_has_no_active_or_external_members": not topology["forbidden_members"],
        "r7_lifecycle_and_sidecar_exact": all(lifecycle["checks"].values()),
        "projection_ordered_and_multiset_exact": projection_exact,
        "unexplained_projection_residue_zero": projection["unexplained_residue_count"] == 0,
        "mutation_probes_all_detected": mutation_complete,
        "dependency_gates_executed_and_hash_stable": (
            reader_gate["status"] == "executed_pass"
            and summary_gate["status"] == "executed_pass"),
        "all_loaded_pdf_parser_modules_hash_bound": (
            parser_manifest["module_file_count"] == len(parser_paths)
            and parser_manifest["module_file_count"] == len(parser_identities)),
        "source_code_and_inputs_current_at_result_build": final_current,
    }
    audit_complete = all(invariants.values())
    normalized_full_conservation = bool(
        audit_complete and projection_exact and not semantic_omissions)

    records_json = [asdict(record) for record in pdf["records"]]
    result = {
        "schema_version": 1,
        "audit": "Stage 6 Ramp Summary authoritative-PDF-to-r7-normalized conservation",
        "methodology": {
            "authority": "exact TSN PDF bytes",
            "independence": (
                "No production parser, normalizer, projector, comparator, report schema, "
                "or evidence adapter imported."),
            "outcomes_separated": [
                "stage6_family_audit_complete", "projection_exact",
                "normalized_full_conservation",
            ],
            "visual_verification": VISUAL_REVIEW,
        },
        "bindings": {
            "raw_pdf": RAW_BINDING,
            "normalized_r7": NORMALIZED_BINDING,
            "normalized_sidecar": SIDECAR_BINDING,
            "r7_lifecycle_witness": R7_WITNESS_BINDING,
        },
        "source_identity": {
            "raw_pdf": _identity(raw_capture.identity),
            "normalized_xlsx": _identity(normalized_capture.identity),
            "normalized_sidecar": _identity(sidecar_capture.identity),
            "r7_witness": _identity(witness_capture.identity),
        },
        "pdf": {
            "strict_topology": pdf["strict_topology"],
            "metadata": pdf["metadata"],
            "page_layout_audits": pdf["page_layout_audits"],
            "parameters": pdf["parameters"],
            "report_header": pdf["report_header"],
            "source_category_records": records_json,
            "printed_total": pdf["total"],
            "source_validation": pdf["validation"],
            "typed_digests": _source_digests(pdf),
        },
        "normalized": {
            "sheet": normalized_sheet,
            "archive_topology": topology,
            "rows": [
                {"source_row": source_row, "category": category,
                 "count": str(count), "count_type": type(count).__name__}
                for source_row, category, count in normalized_rows
            ],
            "typed_digests": {
                "ordered_typed_sha256": _ordered_digest(
                    (category, count) for _row, category, count in normalized_rows),
                "multiset_typed_sha256": _multiset_digest(
                    (category, count) for _row, category, count in normalized_rows)[0],
                "fields": {
                    "Category": _field_digest([row[1] for row in normalized_rows]),
                    "Count": _field_digest([row[2] for row in normalized_rows]),
                },
            },
        },
        "projection": projection,
        "source_role_dispositions": dispositions,
        "source_role_disposition_coverage": role_coverage,
        "nonword_presentation_disposition": {
            "source": "pdf_page_geometry_content_streams_and_graphics",
            "disposition": "presentation_only_exact_digest_bound",
            "normalized_target": None,
            "conservation_impact": False,
        },
        "r7_lifecycle": {
            "checks": lifecycle["checks"],
            "family_result": lifecycle["family"]["result"],
            "family_reuse": lifecycle["family"]["reuse"],
            "family_status_after_build": lifecycle["family"]["status_after_build"],
            "sidecar": lifecycle["sidecar"],
        },
        "anomaly_manifests": {
            "source_category_anomalies": pdf["validation"]["anomalies"],
            "pdf_unclassified_word_residue": [
                {"page": page["page"], "words": page["roles"]["unclassified_words"]}
                for page in pdf["page_layout_audits"]
                if page["roles"]["unclassified_words"]
            ],
            "projection_differences": projection["differences"],
            "normalized_only_or_source_only_rows": projection["differences"],
            "unexplained_residue_count": projection["unexplained_residue_count"],
        },
        "semantic_mutation_probes": mutations,
        "dependency_gates": {
            "generic_immutable_xlsx_reader": reader_gate,
            "ramp_summary_oracle_mutations": summary_gate,
        },
        "provenance": {
            "generator_start": _identity(GENERATOR_START),
            "independent_reader_start": _identity(READER_START),
            "reader_gate_start": _identity(READER_GATE_START),
            "parser_versions": {
                "pdfplumber": pdfplumber.__version__,
                "pypdf": pypdf.__version__,
            },
            "loaded_pdf_parser_module_manifest": parser_manifest,
            "final_revalidation": {
                "all_current": final_current,
                "identities": final_detail,
            },
        },
        "findings": {
            "oracle_blocking": [],
            "product_red": [{
                "finding": "CMP-AUD-146",
                "kind": "printed_report_provenance_omitted",
                "facts": source_only_semantic,
                "evidence": {
                    "pdf_parameters": pdf["parameters"],
                    "pdf_report_header": pdf["report_header"],
                    "normalized_headers": list(NORMALIZED_HEADERS),
                },
                "impact": (
                    "The current Category/Count projection is exact, but normalized bytes "
                    "cannot distinguish source generations that have identical counts and "
                    "different printed report identity/date/scope facts."),
            }],
        },
        "audit_invariants": invariants,
        "projection_exact": projection_exact,
        "stage6_family_audit_complete": audit_complete,
        "normalized_full_conservation": normalized_full_conservation,
    }
    return result, start_identities, revalidation_paths, parser_paths


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", newline="\n", delete=False,
                dir=path.parent, prefix=f".{path.name}.", suffix=".tmp") as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _unlink_if_present(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _write_rejection(path: Path, output: Path, reason: str,
                     result: dict[str, object],
                     postwrite_current: bool,
                     postwrite_detail: dict[str, object]) -> FileIdentity:
    result_identity = capture_file_identity(output)
    rejection = {
        "schema_version": 1,
        "accepted": False,
        "reason": reason,
        "audit": result.get("audit"),
        "result": str(output.resolve()),
        "result_bytes": result_identity.size,
        "result_sha256": result_identity.sha256,
        "projection_exact": result.get("projection_exact", False),
        "stage6_family_audit_complete": result.get(
            "stage6_family_audit_complete", False),
        "normalized_full_conservation": result.get(
            "normalized_full_conservation", False),
        "post_result_write_revalidation": postwrite_current,
        "post_result_write_identities": postwrite_detail,
    }
    _atomic_write_text(path, json.dumps(rejection, indent=2, ensure_ascii=False) + "\n")
    return capture_file_identity(path)


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-open-findings", action="store_true",
        help="exit zero when audit/projection pass but documented product findings remain")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    acceptance_path = args.output.with_suffix(args.output.suffix + ".acceptance.json")
    rejection_path = args.output.with_suffix(args.output.suffix + ".rejection.json")
    # A rerun must never leave a stale positive decision beside a new failed result.
    _unlink_if_present(acceptance_path)
    _unlink_if_present(rejection_path)
    try:
        result, expected_identities, revalidation_paths, parser_paths = run()
    except Exception as exc:
        failure = {
            "schema_version": 1,
            "audit": "Stage 6 Ramp Summary authoritative-PDF-to-r7-normalized conservation",
            "projection_exact": False,
            "stage6_family_audit_complete": False,
            "normalized_full_conservation": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        _atomic_write_text(args.output, json.dumps(failure, indent=2) + "\n")
        rejection_identity = _write_rejection(
            rejection_path, args.output, "oracle_execution_failed", failure, False, {})
        sys.stdout.write(json.dumps(failure, ensure_ascii=False) + "\n")
        sys.stdout.write(json.dumps({
            "accepted": False,
            "rejection": str(rejection_path),
            "rejection_sha256": rejection_identity.sha256,
        }, ensure_ascii=False) + "\n")
        return 2

    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    # Revalidate only after the complete serialized result exists in memory.
    prewrite_current, prewrite_detail = _revalidate(
        expected_identities, revalidation_paths, parser_paths)
    result["publication_revalidation"] = {
        "after_complete_result_serialization": True,
        "before_result_write_all_current": prewrite_current,
        "before_result_write_identities": prewrite_detail,
    }
    result["audit_invariants"]["publication_sources_current_before_write"] = prewrite_current
    result["stage6_family_audit_complete"] = bool(
        result["stage6_family_audit_complete"] and prewrite_current)
    result["normalized_full_conservation"] = bool(
        result["normalized_full_conservation"] and result["stage6_family_audit_complete"])
    serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    _atomic_write_text(args.output, serialized)

    postwrite_current, postwrite_detail = _revalidate(
        expected_identities, revalidation_paths, parser_paths)
    if not postwrite_current:
        result["publication_revalidation"]["post_result_write_all_current"] = False
        result["publication_revalidation"]["post_result_write_identities"] = postwrite_detail
        result["audit_invariants"]["publication_sources_current_after_write"] = False
        result["stage6_family_audit_complete"] = False
        result["normalized_full_conservation"] = False
        _atomic_write_text(args.output, json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        rejection_identity = _write_rejection(
            rejection_path, args.output, "post_result_write_revalidation_failed",
            result, False, postwrite_detail)
        sys.stdout.write(json.dumps({
            "accepted": False,
            "rejection": str(rejection_path),
            "rejection_sha256": rejection_identity.sha256,
        }, ensure_ascii=False) + "\n")
        return 2

    result_identity = capture_file_identity(args.output)
    accepted = bool(
        result["projection_exact"]
        and result["stage6_family_audit_complete"]
        and postwrite_current
        and (result["normalized_full_conservation"] or args.allow_open_findings)
    )
    if not accepted:
        reason = (
            "open_product_findings_not_authorized"
            if (result["stage6_family_audit_complete"]
                and not result["normalized_full_conservation"]
                and not args.allow_open_findings)
            else "audit_or_projection_incomplete"
        )
        rejection_identity = _write_rejection(
            rejection_path, args.output, reason, result, postwrite_current,
            postwrite_detail)
        sys.stdout.write(json.dumps({
            "output": str(args.output),
            "result_bytes": result_identity.size,
            "result_sha256": result_identity.sha256,
            "accepted": False,
            "rejection": str(rejection_path),
            "rejection_bytes": rejection_identity.size,
            "rejection_sha256": rejection_identity.sha256,
            "projection_exact": result["projection_exact"],
            "stage6_family_audit_complete": result["stage6_family_audit_complete"],
            "normalized_full_conservation": result["normalized_full_conservation"],
        }, ensure_ascii=False) + "\n")
        return 1 if reason == "open_product_findings_not_authorized" else 2

    acceptance = {
        "schema_version": 1,
        "accepted": True,
        "audit": result["audit"],
        "result": str(args.output.resolve()),
        "result_bytes": result_identity.size,
        "result_sha256": result_identity.sha256,
        "projection_exact": result["projection_exact"],
        "stage6_family_audit_complete": result["stage6_family_audit_complete"],
        "normalized_full_conservation": result["normalized_full_conservation"],
        "open_product_findings_authorized": bool(
            args.allow_open_findings and not result["normalized_full_conservation"]),
        "post_result_write_revalidation": postwrite_current,
        "post_result_write_identities": postwrite_detail,
    }
    _atomic_write_text(
        acceptance_path, json.dumps(acceptance, indent=2, ensure_ascii=False) + "\n")
    acceptance_identity = capture_file_identity(acceptance_path)
    sys.stdout.write(json.dumps({
        "output": str(args.output),
        "result_bytes": result_identity.size,
        "result_sha256": result_identity.sha256,
        "acceptance": str(acceptance_path),
        "acceptance_bytes": acceptance_identity.size,
        "acceptance_sha256": acceptance_identity.sha256,
        "accepted": True,
        "projection_exact": result["projection_exact"],
        "stage6_family_audit_complete": result["stage6_family_audit_complete"],
        "normalized_full_conservation": result["normalized_full_conservation"],
        "product_findings": len(result["findings"]["product_red"]),
    }, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
