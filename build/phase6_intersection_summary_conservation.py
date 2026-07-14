#!/usr/bin/env python3
"""Independent Stage-6 Intersection Summary PDF-to-r7 conservation oracle.

This audit deliberately imports no application parser, normalizer, comparator,
evidence adapter, report catalog, or production schema.  The authoritative PDF
is captured into private immutable bytes before ``pdfplumber``/``pypdf`` see it;
the r7 workbook is read through the independent stdlib OOXML stream reader.

Three claims are intentionally separate:

* the family audit can be complete when every source fact has a disposition;
* the declared comparison projection can exactly match r7; and
* normalized full conservation can still be false when a many-to-one fold or
  omitted report provenance prevents reconstruction of the source facts.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, Sequence
import zipfile

import pdfplumber
import pypdf

from phase3_xlsx_stream import (
    SCALAR,
    ColumnSpec,
    FileIdentity,
    SheetSpec,
    capture_file_bytes,
    capture_file_identity,
    read_sheet,
)


RAW_PDF = Path(
    r"C:\Users\Yunus\Downloads\TSMIS\tsn_library\intersection_summary\raw"
    r"\Intersection Summary Statewide_TSN.pdf"
)
R7_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
    r"\raw-2026-07-12-r7"
)
NORMALIZED_XLSX = (
    R7_ROOT / "intersection_summary" / "consolidated"
    / "tsn_intersection_summary_normalized.xlsx"
)
NORMALIZED_SIDECAR = Path(str(NORMALIZED_XLSX) + ".outcome.json")
R7_WITNESS = R7_ROOT / "result.json"
SOURCE_FORMAT_RESULT = R7_ROOT.parent / "intersection-tsn-cross-format-oracle-v2.json"

BUILD_DIR = Path(__file__).resolve().parent
REPO_ROOT = BUILD_DIR.parent
GENERATOR_PATH = Path(__file__).resolve()
READER_PATH = BUILD_DIR / "phase3_xlsx_stream.py"
READER_GATE_PATH = BUILD_DIR / "check_phase3_xlsx_stream.py"
FAMILY_GATE_PATH = BUILD_DIR / "check_phase6_intersection_summary_conservation.py"
SOURCE_FORMAT_SCRIPT = BUILD_DIR / "phase4_intersection_tsn_pdf_oracle.py"


RAW_BINDING = {
    "bytes": 12_326,
    "sha256": "c3ad85848764df1b6da53c0bba0f785b3c045e83675f5983555ef514688a7d46",
    "pages": 3,
}
NORMALIZED_BINDING = {
    "bytes": 6_323,
    "sha256": "94befb313416a356a6e9f0363ffae0d065bd03c15ea1fce5bd8e93e0bf59a210",
    "sheet": "Intersection Summary (TSN)",
    "headers": ("Category", "Count"),
    "rows": 58,
}
SIDECAR_BINDING = {
    "bytes": 900,
    "sha256": "aa32f80280182381127cce01af48010543312e67080738b7b0140785530e7a3c",
    "normalization_version": 2,
    "artifact_identity_token": (
        "tsn-normalized-v1:13714e193bc38cd60b40a54da962939a8c802f6f8d506bd6aadf8b4aef350b7d"
    ),
    "raw_manifest_sha256": (
        "3466b857d57afedce3add7ed4d480afc4cb4f4415badf0ea07b9ad67372722c2"
    ),
}
R7_BINDING = {
    "bytes": 173_124,
    "sha256": "b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa",
}
SOURCE_FORMAT_RESULT_BINDING = {
    "bytes": 91_032,
    "sha256": "63f5741203b06ef37245f195953058cf45ec921c04aaa00ccf676e44baba2c2e",
}
SOURCE_FORMAT_SCRIPT_BINDING = {
    "bytes": 49_871,
    "sha256": "ffc364ceb8b6cdbbfb3bff680cc0f3ed77e12c1867978c86122d221de7c78441",
}

PDF_METADATA = {
    "Creator": "Oracle12c AS Reports Services",
    "CreationDate": "D:20250915165412",
    "ModDate": "D:20250915165412",
    "Producer": "Oracle PDF driver",
    "Title": "otm22250.pdf",
    "Author": "Oracle Reports",
}
PAGE_BINDINGS = (
    {
        "page": 1, "width": "792", "height": "612", "rotation": 0,
        "mediabox": ("0", "0", "792", "612"), "word_count": 143,
        "word_sha256": "437567de469b3b1fd3fada109768a66e3efce98a858c481c214e280f2ab3cf45",
        "text_sha256": "595e706a77c08ea2c0481e5535383d6fbf08add44cb584435874f051ecc05c7a",
        "role": "legal_and_presentation_policy",
    },
    {
        "page": 2, "width": "792", "height": "612", "rotation": 0,
        "mediabox": ("0", "0", "792", "612"), "word_count": 37,
        "word_sha256": "b0dcb281cfd394ced3e933f216980e720b3861072a36d1a2eb8bfc9ecd83934b",
        "text_sha256": "c346019e9c2d4568cc8ea38fca8cca8bd9db1d2806acdad53f5795c6435cac3f",
        "role": "comparison_provenance_parameters",
    },
    {
        "page": 3, "width": "792", "height": "612", "rotation": 0,
        "mediabox": ("0", "0", "792", "612"), "word_count": 309,
        "word_sha256": "0d3ef37bedfd17d54bc2a3f602217d2385276d1bd16109523ae0ce4128f82f19",
        "text_sha256": "506325f5a9ea3e191e6684c9a1965f6454817230324d652006bf763b22bff436",
        "role": "authoritative_category_table",
    },
)

REPORT_PROVENANCE = {
    "report_id": "OTM22250",
    "report_date": "09/15/2025",
    "reference_date": "09/15/2025",
    "submitter": "TRLBUGNI",
    "report_title": "Intersection Summary Statewide",
    "event_id": "4843738",
    "location_criteria": "STATEWIDE",
    "printed_generation_time": "04:53 PM",
    "physical_pdf_page": 3,
    "printed_report_page": 1,
    "total_intersections": 16_626,
}

SECTION_ORDER = (
    "HIGHWAY GROUP",
    "RURAL/URBAN/SUBURBAN",
    "INTERSECTION TYPE",
    "LIGHTING TYPE",
    "CONTROL TYPES",
    "MAINLINE NUM OF LANES",
    "MAINLINE MASTARM",
    "MAINLINE LEFT CHANNELIZATION",
    "MAINLINE RIGHT CHANNELIZATION",
    "MAINLINE TRAFFIC FLOW",
)
SECTION_BANDS = {
    "HIGHWAY GROUP": 1,
    "RURAL/URBAN/SUBURBAN": 1,
    "INTERSECTION TYPE": 1,
    "LIGHTING TYPE": 1,
    "CONTROL TYPES": 2,
    "MAINLINE NUM OF LANES": 2,
    "MAINLINE MASTARM": 3,
    "MAINLINE LEFT CHANNELIZATION": 3,
    "MAINLINE RIGHT CHANNELIZATION": 3,
    "MAINLINE TRAFFIC FLOW": 3,
}
SECTION_UNIVERSE_DEFICITS = {
    "HIGHWAY GROUP": 0,
    "RURAL/URBAN/SUBURBAN": 0,
    "INTERSECTION TYPE": 40,
    "LIGHTING TYPE": 0,
    "CONTROL TYPES": 40,
    "MAINLINE NUM OF LANES": 3,
    "MAINLINE MASTARM": 0,
    "MAINLINE LEFT CHANNELIZATION": 30,
    "MAINLINE RIGHT CHANNELIZATION": 3,
    "MAINLINE TRAFFIC FLOW": 0,
}

# Exact physical order and text as printed on the authoritative report page.
EXPECTED_RAW_ROWS = (
    (1, "HIGHWAY GROUP", "R", 166, "R-RIGHT IND ALIGN"),
    (1, "HIGHWAY GROUP", "L", 152, "L-LEFT IND ALIGN"),
    (1, "HIGHWAY GROUP", "X", 0, "X-UNCONSTRUCTED"),
    (1, "HIGHWAY GROUP", "U", 10186, "U-UNDIVIDED"),
    (1, "HIGHWAY GROUP", "D", 6122, "D-DIVIDED"),
    (1, "RURAL/URBAN/SUBURBAN", "R", 346, "R-RURAL -I INSIDE CITY"),
    (1, "RURAL/URBAN/SUBURBAN", "R-O", 8270, "-O OUTSIDE CITY"),
    (1, "RURAL/URBAN/SUBURBAN", "U", 5500, "U-URBAN -I INSIDE CITY"),
    (1, "RURAL/URBAN/SUBURBAN", "U-O", 2510, "-O OUTSIDE CITY"),
    (1, "RURAL/URBAN/SUBURBAN", "+", 0, "+-INVALID DATA"),
    (1, "INTERSECTION TYPE", "F", 5244, "F-FOUR-LEGGED"),
    (1, "INTERSECTION TYPE", "S", 540, "S-OFFSET"),
    (1, "INTERSECTION TYPE", "Y", 949, "Y-WYE"),
    (1, "INTERSECTION TYPE", "M", 141, "M-MULTI-LEGGED"),
    (1, "INTERSECTION TYPE", "T", 9553, "T-TEE"),
    (1, "INTERSECTION TYPE", "Z", 159, "Z-OTHER"),
    (1, "LIGHTING TYPE", "N", 8738, "N-NO LIGHTING"),
    (1, "LIGHTING TYPE", "Y", 7888, "Y-LIGHTING"),
    (1, "LIGHTING TYPE", "+", 0, "+-NO DATA GIVEN"),
    (2, "CONTROL TYPES", "A", 1760, "A-NO CONTROL"),
    (2, "CONTROL TYPES", "B", 11880, "B-STOP SIGN ON CROSS STREET ONLY"),
    (2, "CONTROL TYPES", "C", 98, "C-STOP SIGN ON MAINLINE ONLY"),
    (2, "CONTROL TYPES", "D", 78, "D-FOUR-WAY STOP SIGNS"),
    (2, "CONTROL TYPES", "E", 30, "E-FOUR-WAY FLASHER (RED ON CROSS STREET)"),
    (2, "CONTROL TYPES", "F", 7, "F-FOUR WAY FLASHER (RED ON ALL)"),
    (2, "CONTROL TYPES", "G", 29, "G-FOUR WAY FLASHER (RED ON ALL)"),
    (2, "CONTROL TYPES", "H", 22, "H-YIELD SIGNS (ON CROSS STREET ONLY)"),
    (2, "CONTROL TYPES", "I", 2, "I-YEILD SIGN (ON MAINLINE ONLY)"),
    (2, "CONTROL TYPES", "J", 207, "J-SIGNAL PRETIMED (2) (2 PHASE)"),
    (2, "CONTROL TYPES", "K", 36, "K-SIGNAL PRETIMED (M) (MULTI-PHASE)"),
    (2, "CONTROL TYPES", "L", 107, "L-SIGNALS SEMI-TRAFFIC ACTUATED (2)"),
    (2, "CONTROL TYPES", "M", 65, "M-SIGNALS SEMI-TRAFFIC ACTUATED (M)"),
    (2, "CONTROL TYPES", "N", 210, "N-SIGNALS FULL-TRAFFIC ACTUATED (2)"),
    (2, "CONTROL TYPES", "P", 2023, "P-SIGNALS FULL-TRAFFIC ACTUATED (M)"),
    (2, "CONTROL TYPES", "Z", 32, "Z-OTHER"),
    (2, "CONTROL TYPES", "+", 0, "+-NO DATA GIVEN"),
    (2, "MAINLINE NUM OF LANES", "1", 1, "1"),
    (2, "MAINLINE NUM OF LANES", "2", 10374, "2"),
    (2, "MAINLINE NUM OF LANES", "3", 578, "3"),
    (2, "MAINLINE NUM OF LANES", "4", 4465, "4"),
    (2, "MAINLINE NUM OF LANES", "5", 227, "5"),
    (2, "MAINLINE NUM OF LANES", "6", 845, "6"),
    (2, "MAINLINE NUM OF LANES", "7", 22, "7"),
    (2, "MAINLINE NUM OF LANES", "8", 111, "8"),
    (2, "MAINLINE NUM OF LANES", "+", 0, "+-NO DATA GIVEN"),
    (3, "MAINLINE MASTARM", "Y", 2504, "Y-YES"),
    (3, "MAINLINE MASTARM", "N", 14122, "N-NO"),
    (3, "MAINLINE MASTARM", "+", 0, "+-NO DATA GIVEN"),
    (3, "MAINLINE LEFT CHANNELIZATION", "C", 1335, "C-CURBED MEDIAN LEFT CHAN"),
    (3, "MAINLINE LEFT CHANNELIZATION", "N", 10347, "N-NO LEFT TURN CHAN"),
    (3, "MAINLINE LEFT CHANNELIZATION", "P", 4897, "P-PAINTED LEFT TURN CHAN"),
    (3, "MAINLINE LEFT CHANNELIZATION", "R", 17, "R-RAISED BARS LEFT CHAN"),
    (3, "MAINLINE LEFT CHANNELIZATION", "+", 0, "+-NO DATA GIVEN"),
    (3, "MAINLINE RIGHT CHANNELIZATION", "Y", 2046, "Y-FREE RIGHT TURNS"),
    (3, "MAINLINE RIGHT CHANNELIZATION", "N", 14577, "N-NO FREE RIGHT TURNS"),
    (3, "MAINLINE RIGHT CHANNELIZATION", "+", 0, "+-NO DATA FOUND"),
    (3, "MAINLINE TRAFFIC FLOW", "N", 646, "N-2 WAY TRAFFIC - NO LEFT TURNS"),
    (3, "MAINLINE TRAFFIC FLOW", "P", 15599, "P-2 WAY TRAFFIC WITH LEFT TURN"),
    (3, "MAINLINE TRAFFIC FLOW", "R", 38, "R-2 WAY TRAFFIC - LEFT TURN RESTRICT"),
    (3, "MAINLINE TRAFFIC FLOW", "W", 326, "W- ONE WAY TRAFFIC"),
    (3, "MAINLINE TRAFFIC FLOW", "Z", 17, "Z-OTHERS"),
    (3, "MAINLINE TRAFFIC FLOW", "+", 0, "+-NO DATA FOUND"),
)

# Independent declared comparison projection.  Labels are hard-bound audit spec,
# not imported production constants.
EXPECTED_NORMALIZED_ROWS = (
    ("HIGHWAY GROUP: R - RIGHT IND ALIGN", 166),
    ("HIGHWAY GROUP: L - LEFT IND ALIGN", 152),
    ("HIGHWAY GROUP: X - UNCONSTRUCTED", 0),
    ("HIGHWAY GROUP: U - UNDIVIDED", 10186),
    ("HIGHWAY GROUP: D - DIVIDED", 6122),
    ("RURAL/URBAN/SUBURBAN: R - RURAL -I INSIDE CITY", 346),
    ("RURAL/URBAN/SUBURBAN: R-O - RURAL -O OUTSIDE CITY", 8270),
    ("RURAL/URBAN/SUBURBAN: U - URBAN -I INSIDE CITY", 5500),
    ("RURAL/URBAN/SUBURBAN: U-O - URBAN -O OUTSIDE CITY", 2510),
    ("RURAL/URBAN/SUBURBAN: + - INVALID DATA", 0),
    ("INTERSECTION TYPE: F - FOUR-LEGGED", 5244),
    ("INTERSECTION TYPE: M - MULTI-LEGGED", 141),
    ("INTERSECTION TYPE: S - OFFSET", 540),
    ("INTERSECTION TYPE: T - TEE", 9553),
    ("INTERSECTION TYPE: Y - WYE", 949),
    ("INTERSECTION TYPE: Z - OTHER", 159),
    ("LIGHTING TYPE: N - NO LIGHTING", 8738),
    ("LIGHTING TYPE: Y - LIGHTING", 7888),
    ("LIGHTING TYPE: + - NO DATA GIVEN", 0),
    ("CONTROL TYPES: A - NO CONTROL", 1760),
    ("CONTROL TYPES: B - STOP SIGNS ON CROSS ST ONLY", 11880),
    ("CONTROL TYPES: C - STOP SIGNS ON MAINLINE ONLY", 98),
    ("CONTROL TYPES: D - FOUR-WAY STOP SIGNS", 78),
    ("CONTROL TYPES: E - 4-WAY FLASHER (RED/CROSS ST)", 30),
    ("CONTROL TYPES: F - 4-WAY FLASHER (RED/MAINLINE)", 7),
    ("CONTROL TYPES: G - 4-WAY FLASHER (RED ON ALL)", 29),
    ("CONTROL TYPES: H - YIELD SIGNS (CROSS ST ONLY)", 22),
    ("CONTROL TYPES: I - YIELD SIGNS (MAIN LINE ONLY)", 2),
    ("CONTROL TYPES: S - SIGNALIZED (incl. TSN J-P)", 2648),
    ("CONTROL TYPES: Z - OTHER", 32),
    ("CONTROL TYPES: + - NO DATA GIVEN", 0),
    ("MAINLINE NUM OF LANES: 1 lanes", 1),
    ("MAINLINE NUM OF LANES: 2 lanes", 10374),
    ("MAINLINE NUM OF LANES: 3 lanes", 578),
    ("MAINLINE NUM OF LANES: 4 lanes", 4465),
    ("MAINLINE NUM OF LANES: 5 lanes", 227),
    ("MAINLINE NUM OF LANES: 6 lanes", 845),
    ("MAINLINE NUM OF LANES: 7 lanes", 22),
    ("MAINLINE NUM OF LANES: 8 lanes", 111),
    ("MAINLINE NUM OF LANES: + - NO DATA GIVEN", 0),
    ("MAINLINE MASTARM: Y - YES", 2504),
    ("MAINLINE MASTARM: N - NO", 14122),
    ("MAINLINE MASTARM: + - NO DATA GIVEN", 0),
    ("MAINLINE LEFT CHANNELIZATION: C - CURBED MEDIAN LEFT TURN CHAN", 1335),
    ("MAINLINE LEFT CHANNELIZATION: N - NO LEFT TURN CHANNELIZATION", 10347),
    ("MAINLINE LEFT CHANNELIZATION: P - PAINTED LEFT TURN CHAN", 4897),
    ("MAINLINE LEFT CHANNELIZATION: R - RAISED BARS LEFT TURN CHAN", 17),
    ("MAINLINE LEFT CHANNELIZATION: + - NO DATA GIVEN", 0),
    ("MAINLINE RIGHT CHANNELIZATION: Y - FREE RIGHT TURNS", 2046),
    ("MAINLINE RIGHT CHANNELIZATION: N - NO FREE RIGHT TURNS", 14577),
    ("MAINLINE RIGHT CHANNELIZATION: + - NO DATA GIVEN", 0),
    ("MAINLINE TRAFFIC FLOW: N - 2 WAY - NO LEFT TURNS", 646),
    ("MAINLINE TRAFFIC FLOW: P - 2 WAY WITH LEFT TURN", 15599),
    ("MAINLINE TRAFFIC FLOW: R - 2 WAY - LEFT TURN RESTRICT", 38),
    ("MAINLINE TRAFFIC FLOW: W - ONE WAY TRAFFIC", 326),
    ("MAINLINE TRAFFIC FLOW: Z - OTHERS", 17),
    ("MAINLINE TRAFFIC FLOW: + - NO DATA GIVEN", 0),
    ("Total Intersections", 16626),
)

LEGACY_SIGNAL_CODES = frozenset(("J", "K", "L", "M", "N", "P"))
LEGACY_SIGNAL_COUNTS = {"J": 207, "K": 36, "L": 107, "M": 65, "N": 210, "P": 2023}


class ConservationError(ValueError):
    """A bound source or independent conservation contract failed."""


def _identity_dict(identity: FileIdentity) -> dict[str, object]:
    return asdict(identity)


def _require_identity(identity: FileIdentity, binding: dict[str, object], label: str) -> None:
    if identity.size != binding["bytes"] or identity.sha256 != binding["sha256"]:
        raise ConservationError(
            f"{label} identity mismatch: {identity.size}/{identity.sha256} != "
            f"{binding['bytes']}/{binding['sha256']}"
        )


def _typed(value: object) -> list[object]:
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["bool", value]
    if isinstance(value, Decimal):
        item = value.as_tuple()
        return ["decimal", item.sign, list(item.digits), item.exponent]
    if isinstance(value, str):
        return ["str", value]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, float):
        return ["float", value.hex()]
    raise TypeError(f"unsupported typed scalar: {type(value).__name__}")


def _row_wire(row: Sequence[object]) -> bytes:
    return json.dumps(
        [_typed(value) for value in row], ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def _typed_row_sha256(row: Sequence[object]) -> str:
    return hashlib.sha256(_row_wire(row)).hexdigest()


def _ordered_digest(rows: Iterable[Sequence[object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        payload = _row_wire(row)
        digest.update(str(len(payload)).encode("ascii") + b":" + payload + b"\n")
    return digest.hexdigest()


def _multiset_digest(rows: Iterable[Sequence[object]]) -> tuple[str, int]:
    counter = Counter(hashlib.sha256(_row_wire(row)).hexdigest() for row in rows)
    payload = json.dumps(sorted(counter.items()), separators=(",", ":")).encode("ascii")
    return hashlib.sha256(payload).hexdigest(), sum(counter.values())


def _dataset_digests(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> dict[str, object]:
    fields = {}
    for index, header in enumerate(headers):
        column = [(row[index],) for row in rows]
        fields[header] = {
            "ordered_typed_sha256": _ordered_digest(column),
            "multiset_typed_sha256": _multiset_digest(column)[0],
        }
    return {
        "rows": len(rows),
        "ordered_typed_sha256": _ordered_digest(rows),
        "multiset_typed_sha256": _multiset_digest(rows)[0],
        "fields": fields,
    }


def _word_digest(words: Sequence[dict[str, object]]) -> str:
    projected = [
        {
            key: (word[key] if key == "text" else str(word[key]))
            for key in ("text", "x0", "x1", "top", "bottom")
        }
        for word in words
    ]
    payload = json.dumps(projected, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _page_rows(words: Sequence[dict[str, object]], left: float, right: float):
    selected = [word for word in words if left <= float(word["x0"]) < right]
    rows: list[list[dict[str, object]]] = []
    for word in sorted(selected, key=lambda item: (float(item["top"]), float(item["x0"]))):
        if rows and abs(float(word["top"]) - float(rows[-1][0]["top"])) <= 3:
            rows[-1].append(word)
        else:
            rows.append([word])
    for row in rows:
        row.sort(key=lambda item: float(item["x0"]))
    return rows


def _section_heading(line: str) -> str | None:
    normalized = re.sub(r"[^A-Z0-9/+ ]+", " ", line.upper())
    normalized = " ".join(normalized.split())
    matches = [section for section in SECTION_ORDER if section in normalized]
    if len(matches) > 1:
        raise ConservationError(f"ambiguous section heading: {line!r}")
    return matches[0] if matches else None


def _source_code(section: str, descriptor: str, rural_parent: str | None):
    first = descriptor.split()[0].upper()
    if section == "RURAL/URBAN/SUBURBAN":
        if first.startswith("R-"):
            return "R", "R", "explicit_rural_parent"
        if first.startswith("U-"):
            return "U", "U", "explicit_urban_parent"
        if first.startswith("-O"):
            if rural_parent not in {"R", "U"}:
                raise ConservationError("outside-city continuation has no Rural/Urban parent")
            return f"{rural_parent}-O", rural_parent, "parent_bound_outside_city"
        if first.startswith("+"):
            return "+", rural_parent, "explicit_invalid_data"
        raise ConservationError(f"unknown Rural/Urban descriptor: {descriptor!r}")
    if section == "MAINLINE NUM OF LANES":
        code = "+" if first.startswith("+") else first
    else:
        code = first.split("-", 1)[0]
        if code.startswith("+"):
            code = "+"
    if not code:
        raise ConservationError(f"empty category code in {section}: {descriptor!r}")
    return code, rural_parent, "explicit_code"


def _extract_pdf(payload: bytes) -> dict[str, object]:
    strict_reader = pypdf.PdfReader(io.BytesIO(payload), strict=True)
    if strict_reader.is_encrypted:
        raise ConservationError("authoritative PDF may not be encrypted")
    if len(strict_reader.pages) != RAW_BINDING["pages"]:
        raise ConservationError("authoritative PDF page count changed")

    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        metadata = dict(pdf.metadata or {})
        if metadata != PDF_METADATA:
            raise ConservationError(f"PDF metadata changed: {metadata!r}")
        pages = []
        page_texts = []
        page_words = []
        for index, page in enumerate(pdf.pages):
            text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
            words = page.extract_words(
                x_tolerance=3, y_tolerance=3,
                keep_blank_chars=False, use_text_flow=False,
            )
            binding = PAGE_BINDINGS[index]
            observed = {
                "page": index + 1,
                "width": str(page.width),
                "height": str(page.height),
                "rotation": strict_reader.pages[index].rotation,
                "mediabox": tuple(str(value) for value in strict_reader.pages[index].mediabox),
                "word_count": len(words),
                "word_sha256": _word_digest(words),
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "role": binding["role"],
            }
            if observed != binding:
                raise ConservationError(
                    f"PDF page {index + 1} topology/text binding changed: {observed!r}"
                )
            pages.append(observed)
            page_texts.append(text)
            page_words.append(words)

    page2 = page_texts[1]
    provenance_checks = {
        "report_id": "OTM22250" in page2,
        "report_date": re.search(r"REPORT DATE\s*:\s*09/15/2025", page2) is not None,
        "reference_date": re.search(r"REFERENCE DATE\s*:\s*09/15/2025", page2) is not None,
        "submitter": re.search(r"SUBMITTOR\s*:\s*TRLBUGNI", page2) is not None,
        "title": "Intersection Summary Statewide" in page2,
        "event_id": re.search(r"EVENT ID\s*:\s*4843738", page2) is not None,
        "statewide": "STATEWIDE" in page2,
    }
    if not all(provenance_checks.values()):
        raise ConservationError(f"report parameter extraction changed: {provenance_checks}")

    page3 = page_texts[2]
    header_checks = {
        "report_id": "OTM22250" in page3,
        "date": "09/15/2025" in page3,
        "time": "04:53 PM" in page3,
        "title": "TSAR-INTERSECTION SUMMARY" in page3,
        "printed_page": re.search(r"Page#\s+1", page3) is not None,
        "event_id": re.search(r"Event ID\s+4843738", page3) is not None,
    }
    total_match = re.search(r"Total Intersections\s*=\s*([0-9,]+)", page3)
    total = int(total_match.group(1).replace(",", "")) if total_match else None
    if not all(header_checks.values()) or total != REPORT_PROVENANCE["total_intersections"]:
        raise ConservationError(
            f"report page header/total extraction changed: {header_checks}, total={total}"
        )

    bands = ((0.0, 190.0), (190.0, 495.0), (495.0, 793.0))
    records = []
    parent_events = []
    for band_number, (left, right) in enumerate(bands, 1):
        section = None
        rural_parent = None
        section_seen = []
        for row in _page_rows(page_words[2], left, right):
            tokens = [str(word["text"]) for word in row]
            line = " ".join(tokens)
            heading = _section_heading(line)
            if heading:
                if SECTION_BANDS[heading] != band_number:
                    raise ConservationError(
                        f"section {heading} moved to unexpected band {band_number}"
                    )
                if heading in section_seen:
                    raise ConservationError(f"duplicate/noncontiguous section {heading}")
                section_seen.append(heading)
                section = heading
                rural_parent = None
                continue
            if section is None or not tokens or not re.fullmatch(r"[0-9,]+", tokens[0]):
                continue
            if len(tokens) < 2:
                raise ConservationError(f"category row has no descriptor: {line!r}")
            count = int(tokens[0].replace(",", ""))
            descriptor = " ".join(tokens[1:])
            code, rural_parent, relation = _source_code(section, descriptor, rural_parent)
            record = {
                "physical_pdf_page": 3,
                "printed_report_page": 1,
                "band": band_number,
                "section": section,
                "code": code,
                "count": count,
                "descriptor": descriptor,
                "top": str(row[0]["top"]),
                "bottom": str(max(float(word["bottom"]) for word in row)),
                "x0": str(min(float(word["x0"]) for word in row)),
                "x1": str(max(float(word["x1"]) for word in row)),
                "parent_relation": relation,
            }
            records.append(record)
            if relation == "parent_bound_outside_city":
                parent_events.append({
                    "descriptor": descriptor,
                    "resolved_code": code,
                    "band": band_number,
                    "top": record["top"],
                })

    core = tuple(
        (row["band"], row["section"], row["code"], row["count"], row["descriptor"])
        for row in records
    )
    if core != EXPECTED_RAW_ROWS:
        raise ConservationError("independent PDF category extraction differs from exact source binding")
    if len(parent_events) != 2 or [event["resolved_code"] for event in parent_events] != ["R-O", "U-O"]:
        raise ConservationError(f"Rural/Urban parent disambiguation changed: {parent_events}")
    keys = [(row["section"], row["code"]) for row in records]
    if len(keys) != len(set(keys)):
        raise ConservationError("raw PDF contains duplicate section/code categories")

    original_word_digest = _word_digest(page_words[2])
    coordinate_mutation = deepcopy(page_words[2])
    coordinate_mutation[0]["x0"] = float(coordinate_mutation[0]["x0"]) + 0.125
    text_mutation = deepcopy(page_words[2])
    text_mutation[0]["text"] = str(text_mutation[0]["text"]) + "#MUT"
    page_word_stream_mutation = {
        "name": "authoritative report-page word text/coordinate topology drift",
        "original_word_sha256": original_word_digest,
        "coordinate_mutation_word_sha256": _word_digest(coordinate_mutation),
        "text_mutation_word_sha256": _word_digest(text_mutation),
        "detected": (
            _word_digest(coordinate_mutation) != original_word_digest
            and _word_digest(text_mutation) != original_word_digest
        ),
    }

    return {
        "metadata": metadata,
        "pages": pages,
        "report_provenance": REPORT_PROVENANCE,
        "parameter_checks": provenance_checks,
        "report_page_header_checks": header_checks,
        "raw_category_rows": records,
        "raw_category_count": len(records),
        "rural_urban_parent_disambiguations": parent_events,
        "page_word_stream_mutation_probe": page_word_stream_mutation,
        "total": total,
    }


def _normalized_label_map() -> dict[tuple[str, str], str]:
    result = {}
    for label, _count in EXPECTED_NORMALIZED_ROWS[:-1]:
        section, rest = label.split(": ", 1)
        code = rest.split(" ", 1)[0]
        result[(section, code)] = label
    return result


def _project_records(
    records: Sequence[dict[str, object]], total: int, *, enforce_fixed: bool = True
):
    labels = _normalized_label_map()
    contributions: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    dispositions = []
    for index, record in enumerate(records):
        section = str(record["section"])
        code = str(record["code"])
        target_code = "S" if section == "CONTROL TYPES" and code in LEGACY_SIGNAL_CODES else code
        key = (section, target_code)
        if key not in labels:
            raise ConservationError(f"source category has no declared normalized disposition: {section}/{code}")
        contribution = {
            "source_ordinal": index + 1,
            "source_section": section,
            "source_code": code,
            "source_count": int(record["count"]),
            "source_descriptor": str(record["descriptor"]),
            "normalized_category": labels[key],
            "normalized_code": target_code,
            "source_category_typed_sha256": _typed_row_sha256((
                record.get("physical_pdf_page"), record.get("printed_report_page"),
                record.get("band"), section, code, int(record["count"]),
                str(record["descriptor"]), record.get("top"), record.get("bottom"),
                record.get("x0"), record.get("x1"),
            )),
        }
        contributions[key].append(contribution)
        if section == "CONTROL TYPES" and code in LEGACY_SIGNAL_CODES:
            relation = "noninjective_legacy_signal_fold"
        elif section == "RURAL/URBAN/SUBURBAN" and code in {"R-O", "U-O"}:
            relation = "parent_disambiguated_count_preserving"
        else:
            relation = "code_and_count_preserving_canonical_label"
        dispositions.append({**contribution, "relation": relation})

    projected = []
    per_category = []
    for expected_label, _expected_count in EXPECTED_NORMALIZED_ROWS[:-1]:
        section, rest = expected_label.split(": ", 1)
        code = rest.split(" ", 1)[0]
        items = contributions[(section, code)]
        if not items:
            raise ConservationError(f"normalized category has no source contribution: {expected_label}")
        count = sum(item["source_count"] for item in items)
        projected.append((expected_label, Decimal(count)))
        contribution_rows = [
            (item["source_section"], item["source_code"], item["source_count"],
             item["source_descriptor"], item["source_category_typed_sha256"])
            for item in items
        ]
        per_category.append({
            "normalized_category": expected_label,
            "source_contribution_count": len(items),
            "source_contributions": items,
            "projected_count": count,
            "source_contributions_ordered_typed_sha256": _ordered_digest(contribution_rows),
            "source_contributions_multiset_typed_sha256": _multiset_digest(
                contribution_rows
            )[0],
            "projected_typed_row_sha256": _typed_row_sha256(
                (expected_label, Decimal(count))
            ),
        })
    total_source_typed_sha256 = _typed_row_sha256((
        3, 1, "REPORT TOTAL", "Total Intersections", total
    ))
    total_contribution_rows = [(
        "REPORT TOTAL", "TOTAL", total, "Total Intersections",
        total_source_typed_sha256,
    )]
    per_category.append({
        "normalized_category": "Total Intersections",
        "source_contribution_count": 1,
        "source_contributions": [{
            "source_ordinal": "report_total",
            "source_section": "REPORT TOTAL",
            "source_code": "TOTAL",
            "source_count": total,
            "source_descriptor": "Total Intersections",
            "normalized_category": "Total Intersections",
            "normalized_code": "TOTAL",
            "source_category_typed_sha256": total_source_typed_sha256,
            "relation": "printed_report_total_to_normalized_total",
        }],
        "projected_count": total,
        "source_contributions_ordered_typed_sha256": _ordered_digest(
            total_contribution_rows
        ),
        "source_contributions_multiset_typed_sha256": _multiset_digest(
            total_contribution_rows
        )[0],
        "projected_typed_row_sha256": _typed_row_sha256(
            ("Total Intersections", Decimal(total))
        ),
    })
    projected.append(("Total Intersections", Decimal(total)))
    expected = [(label, Decimal(count)) for label, count in EXPECTED_NORMALIZED_ROWS]
    if enforce_fixed and projected != expected:
        mismatches = [
            {"ordinal": index + 1, "projected": actual, "expected": wanted}
            for index, (actual, wanted) in enumerate(zip(projected, expected))
            if actual != wanted
        ]
        if len(projected) != len(expected):
            mismatches.append({
                "kind": "row_count", "projected": len(projected), "expected": len(expected)
            })
        raise ConservationError(
            "independent source projection differs from fixed comparison contract: "
            f"{mismatches[:10]!r}"
        )
    if len(dispositions) != len(records):
        raise ConservationError("not every raw category has exactly one disposition")
    if Counter(item["source_ordinal"] for item in dispositions) != Counter(range(1, len(records) + 1)):
        raise ConservationError("raw category disposition multiplicity changed")
    return projected, dispositions, per_category


def _section_conservation(records: Sequence[dict[str, object]], total: int):
    rows = []
    for section in SECTION_ORDER:
        members = [record for record in records if record["section"] == section]
        subtotal = sum(int(record["count"]) for record in members)
        deficit = total - subtotal
        expected_deficit = SECTION_UNIVERSE_DEFICITS[section]
        rows.append({
            "section": section,
            "printed_category_rows": len(members),
            "printed_subtotal": subtotal,
            "printed_total_intersections": total,
            "printed_taxonomy_deficit": deficit,
            "expected_detail_values_outside_printed_taxonomy": expected_deficit,
            "accounted_universe": subtotal + expected_deficit,
            "pass": deficit == expected_deficit and subtotal + expected_deficit == total,
            "ordered_typed_sha256": _ordered_digest([
                (record["code"], record["count"], record["descriptor"])
                for record in members
            ]),
            "multiset_typed_sha256": _multiset_digest([
                (record["code"], record["count"], record["descriptor"])
                for record in members
            ])[0],
        })
    if not all(item["pass"] for item in rows):
        raise ConservationError("section subtotal/universe conservation changed")
    return rows


def _xlsx_package_topology(payload: bytes) -> dict[str, object]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload), "r") as archive:
            infos = archive.infolist()
            members = [
                (info.filename, info.file_size, info.compress_size, info.CRC)
                for info in infos
            ]
    except zipfile.BadZipFile as exc:
        raise ConservationError("normalized source is not a readable XLSX package") from exc
    if len(members) != len({member[0] for member in members}):
        raise ConservationError("normalized XLSX contains duplicate package members")
    return {
        "member_count": len(members),
        "uncompressed_bytes": sum(member[1] for member in members),
        "compressed_bytes": sum(member[2] for member in members),
        "ordered_member_topology_sha256": _ordered_digest(members),
        "members": [
            {"name": name, "bytes": size, "compressed_bytes": compressed, "crc32": crc}
            for name, size, compressed, crc in members
        ],
    }


def _manifest_digest(members: Sequence[dict[str, object]], keys: Sequence[str]) -> str:
    payload = b"".join(
        ("\t".join(str(member[key]) for key in keys) + "\n").encode("utf-8")
        for member in members
    )
    return hashlib.sha256(payload).hexdigest()


def _package_manifest(root: Path) -> dict[str, object]:
    root = root.resolve()
    candidates = [root] if root.is_file() else [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() in {".py", ".pyd", ".dll"}
    ]
    members = []
    for path in sorted(candidates, key=lambda item: (
            item.name.casefold() if root.is_file()
            else item.relative_to(root).as_posix().casefold())):
        data = path.read_bytes()
        members.append({
            "relative_path": path.name if root.is_file() else path.relative_to(root).as_posix(),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    return {
        "root": str(root),
        "member_count": len(members),
        "bytes": sum(int(member["bytes"]) for member in members),
        "sha256": _manifest_digest(members, ("relative_path", "bytes", "sha256")),
    }


def _site_packages_marker(path: Path) -> bool:
    return any(part.casefold() == "site-packages" for part in path.parts)


def _loaded_site_package_roots() -> dict[str, Path]:
    roots = {}
    for module_name, module in sorted(sys.modules.items()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        path = Path(raw_path).resolve()
        if not path.is_file() or not _site_packages_marker(path):
            continue
        top = module_name.split(".", 1)[0]
        site_index = next(
            index for index, part in enumerate(path.parts)
            if part.casefold() == "site-packages"
        )
        site_root = Path(*path.parts[:site_index + 1])
        first = path.parts[site_index + 1]
        candidate = site_root / first
        roots[top] = candidate if candidate.exists() else path
    return roots


def _parser_package_manifests() -> dict[str, object]:
    roots = _loaded_site_package_roots()
    manifests = {
        name: _package_manifest(root)
        for name, root in sorted(roots.items(), key=lambda item: item[0].casefold())
    }
    return {
        "observed_top_level_packages": sorted(manifests),
        "manifests": manifests,
    }


def _loaded_parser_module_manifest() -> dict[str, object]:
    runtime_root = Path(sys.executable).resolve().parent
    members = []
    seen_names = set()
    for module_name, module in sorted(sys.modules.items()):
        raw_path = getattr(module, "__file__", None)
        if not raw_path:
            continue
        path = Path(raw_path).resolve()
        if not path.is_file() or not _site_packages_marker(path):
            continue
        if module_name in seen_names:
            raise ConservationError(f"duplicate loaded parser module name: {module_name}")
        seen_names.add(module_name)
        data = path.read_bytes()
        try:
            relative = path.relative_to(runtime_root).as_posix()
        except ValueError:
            relative = str(path)
        members.append({
            "module": module_name,
            "relative_path": relative,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    members.sort(key=lambda item: (str(item["module"]).casefold(), str(item["relative_path"]).casefold()))
    required = {"pdfplumber", "pdfminer", "pypdf"}
    observed = {str(item["module"]).split(".", 1)[0] for item in members}
    if not required <= observed:
        raise ConservationError(
            f"loaded parser-module manifest lacks required packages: {sorted(required - observed)}"
        )
    return {
        "member_count": len(members),
        "bytes": sum(int(member["bytes"]) for member in members),
        "sha256": _manifest_digest(
            members, ("module", "relative_path", "bytes", "sha256")
        ),
        "observed_top_level_packages": sorted(observed),
        "members": members,
    }


def _parser_versions() -> dict[str, str]:
    versions = {}
    for name in ("pdfplumber", "pdfminer", "pypdf", "PIL", "cryptography", "charset_normalizer"):
        module = sys.modules.get(name)
        if module is None:
            continue
        value = getattr(module, "__version__", None)
        if value is not None:
            versions[name] = str(value)
    return versions


def _same_version_dependency_drift_probe(
    loaded_manifest: dict[str, object], versions: dict[str, str]
) -> dict[str, object]:
    mutated = deepcopy(loaded_manifest)
    members = mutated.get("members", [])
    if not members:
        raise ConservationError("cannot mutation-test an empty parser-module manifest")
    original = dict(members[0])
    members[0]["sha256"] = "0" * 64
    mutated["sha256"] = _manifest_digest(
        members, ("module", "relative_path", "bytes", "sha256")
    )
    same_versions = deepcopy(versions)
    detected = same_versions == versions and mutated != loaded_manifest
    return {
        "name": "same-version internal parser-module drift",
        "mutated_module": original["module"],
        "versions_unchanged": same_versions == versions,
        "manifest_changed": mutated["sha256"] != loaded_manifest["sha256"],
        "detected": detected,
    }


def _json_document(captured, label: str) -> dict[str, object]:
    try:
        value = json.loads(captured.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConservationError(f"{label} is not exact UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ConservationError(f"{label} JSON root is not an object")
    return value


def _validate_sidecar(document: dict[str, object]) -> dict[str, object]:
    raw_manifest = document.get("tsn_raw_manifest")
    workbook = document.get("tsn_normalized_workbook_identity")
    checks = {
        "schema_version": document.get("schema_version") == 1,
        "completion": document.get("completion") == "complete",
        "zero_skipped": document.get("skipped_inputs") == 0,
        "zero_failed": document.get("failed_inputs") == 0,
        "normalization_version": document.get("tsn_normalization_version") == 2,
        "artifact_token": document.get("tsn_artifact_identity_token") == SIDECAR_BINDING["artifact_identity_token"],
        "raw_manifest": (
            isinstance(raw_manifest, dict)
            and raw_manifest.get("member_count") == 1
            and raw_manifest.get("byte_length") == RAW_BINDING["bytes"]
            and raw_manifest.get("sha256") == SIDECAR_BINDING["raw_manifest_sha256"]
            and raw_manifest.get("members") == [{
                "relative_path": "Intersection Summary Statewide_TSN.pdf",
                "byte_length": RAW_BINDING["bytes"],
                "sha256": RAW_BINDING["sha256"],
            }]
        ),
        "normalized_identity": (
            isinstance(workbook, dict)
            and workbook.get("byte_length") == NORMALIZED_BINDING["bytes"]
            and workbook.get("sha256") == NORMALIZED_BINDING["sha256"]
        ),
    }
    if not all(checks.values()):
        raise ConservationError(f"r7 normalized sidecar claims changed: {checks}")
    return checks


def _validate_r7(document: dict[str, object]) -> dict[str, object]:
    families = [item for item in document.get("families", []) if item.get("report") == "intersection_summary"]
    generated = document.get("generated_output_artifact_manifest", {}).get("members", [])
    generated_rows = [
        item for item in generated
        if item.get("relative_path") in {
            "intersection_summary/consolidated/tsn_intersection_summary_normalized.xlsx",
            "intersection_summary/consolidated/tsn_intersection_summary_normalized.xlsx.outcome.json",
        }
    ]
    family = families[0] if len(families) == 1 else {}
    output = family.get("output", {})
    result = family.get("result", {})
    reuse = family.get("reuse", {})
    status = family.get("status_after_build", {})
    checks = {
        "top_level_acceptance": document.get("acceptance") == "complete",
        "seven_families": document.get("completed_family_count") == 7 == document.get("expected_family_count"),
        "source_universe_stable": document.get("source_universe_stable") is True,
        "generated_universe_exact": document.get("generated_output_artifact_universe_exact") is True,
        "exact_one_family": len(families) == 1,
        "normalization_version": family.get("normalization_version") == 2,
        "output_binding": (
            output.get("bytes") == NORMALIZED_BINDING["bytes"]
            and output.get("sha256") == NORMALIZED_BINDING["sha256"]
            and output.get("sidecar_sha256") == SIDECAR_BINDING["sha256"]
        ),
        "sheet_binding": output.get("sheets") == [{
            "data_rows": 58,
            "distinct_first_column_values": 58,
            "header": ["Category", "Count"],
            "name": "Intersection Summary (TSN)",
        }],
        "producer_complete": (
            result.get("status") == "ok"
            and result.get("completion") == "complete"
            and result.get("skipped_inputs") == 0
            and result.get("failed_inputs") == 0
        ),
        "reuse_certified_unchanged": (
            reuse.get("certified") is True
            and reuse.get("output_unchanged") is True
            and reuse.get("sidecar_unchanged") is True
        ),
        "status_current": (
            status.get("current") is True
            and status.get("producer_complete") is True
            and status.get("coherent_snapshot_current") is True
            and status.get("identity_token_current") is True
            and status.get("identity_token") == SIDECAR_BINDING["artifact_identity_token"]
        ),
        "generated_artifacts_exact": sorted(
            (item.get("relative_path"), item.get("bytes"), item.get("sha256"))
            for item in generated_rows
        ) == sorted((
            ("intersection_summary/consolidated/tsn_intersection_summary_normalized.xlsx",
             NORMALIZED_BINDING["bytes"], NORMALIZED_BINDING["sha256"]),
            ("intersection_summary/consolidated/tsn_intersection_summary_normalized.xlsx.outcome.json",
             SIDECAR_BINDING["bytes"], SIDECAR_BINDING["sha256"]),
        )),
    }
    if not all(checks.values()):
        raise ConservationError(f"r7 lifecycle witness claims changed: {checks}")
    return checks


def _validate_source_format_evidence(
    document: dict[str, object],
    raw_rows: Sequence[dict[str, object]],
    projected_rows: Sequence[Sequence[object]],
    sections: Sequence[dict[str, object]],
) -> dict[str, object]:
    summary = document.get("summary_from_detail", {})
    evidence_raw = summary.get("pdf_metadata", {}).get("raw_category_rows", [])
    evidence_raw_core = [
        (item.get("band"), item.get("section"), item.get("code"), item.get("count"), item.get("text"))
        for item in evidence_raw
    ]
    current_core = [
        (item["band"], item["section"], item["code"], item["count"], item["descriptor"])
        for item in raw_rows
    ]
    projected_by_key = {}
    for label, count in projected_rows[:-1]:
        section, rest = str(label).split(": ", 1)
        projected_by_key[(section, rest.split(" ", 1)[0])] = int(count)
    evidence_folded = {
        (item.get("section"), item.get("code")): item.get("pdf")
        for item in summary.get("normalized_cells", [])
    }
    evidence_sections = {
        item.get("section"): (
            item.get("pdf_sum"), item.get("xlsx_rows_excluded_by_print_taxonomy"),
            item.get("xlsx_rows_accounted"), item.get("pass"),
        )
        for item in summary.get("section_conservation", [])
    }
    current_sections = {
        item["section"]: (
            item["printed_subtotal"], item["expected_detail_values_outside_printed_taxonomy"],
            item["accounted_universe"], item["pass"],
        )
        for item in sections
    }
    checks = {
        "accepted_status": document.get("status") == "pass",
        "zero_unresolved_gates": document.get("unresolved_gate_count") == 0,
        "summary_zero_unresolved": summary.get("unresolved") == [],
        "independently_reproduced_raw_rows": evidence_raw_core == current_core == list(EXPECTED_RAW_ROWS),
        "independently_reproduced_folded_cells": evidence_folded == projected_by_key,
        "independently_reproduced_section_universes": evidence_sections == current_sections,
        "accepted_normalized_category_count": summary.get("normalized_categories_including_total") == 58,
        "accepted_total": summary.get("pdf_total") == 16_626,
    }
    if not all(checks.values()):
        raise ConservationError(f"accepted source-format evidence reproduction failed: {checks}")
    return checks


def _run_gate(path: Path) -> dict[str, object]:
    process = subprocess.run(
        [sys.executable, str(path)], cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=180, check=False,
    )
    return {
        "path": str(path),
        "returncode": process.returncode,
        "stdout_sha256": hashlib.sha256(process.stdout.encode("utf-8")).hexdigest(),
        "stderr_sha256": hashlib.sha256(process.stderr.encode("utf-8")).hexdigest(),
        "stdout_tail": process.stdout[-2_000:],
        "stderr_tail": process.stderr[-2_000:],
        "pass": process.returncode == 0,
    }


def _mutation_probes(
    raw_rows: Sequence[dict[str, object]],
    projected_rows: Sequence[Sequence[object]],
    normalized_rows: Sequence[Sequence[object]],
    pdf_result: dict[str, object],
    sidecar_document: dict[str, object],
    r7_document: dict[str, object],
) -> list[dict[str, object]]:
    probes = []
    raw_core = [
        (item["band"], item["section"], item["code"], item["count"], item["descriptor"])
        for item in raw_rows
    ]

    reordered = list(raw_core)
    reordered[0], reordered[1] = reordered[1], reordered[0]
    probes.append({
        "name": "raw physical category reorder",
        "detected": (
            _ordered_digest(reordered) != _ordered_digest(raw_core)
            and _multiset_digest(reordered)[0] == _multiset_digest(raw_core)[0]
        ),
    })

    multiplicity = list(raw_core[:-1]) + [raw_core[0]]
    probes.append({
        "name": "raw drop plus duplicate",
        "detected": _multiset_digest(multiplicity)[0] != _multiset_digest(raw_core)[0],
    })

    changed = deepcopy(list(raw_rows))
    changed[28]["count"] = int(changed[28]["count"]) + 1  # J signal subtype
    changed_projection, _dispositions, _per_category = _project_records(
        changed, 16_626, enforce_fixed=False
    )
    changed_deltas = [
        {"ordinal": index + 1, "before": before, "after": after}
        for index, (before, after) in enumerate(zip(projected_rows, changed_projection))
        if before != after
    ]
    try:
        _project_records(changed, 16_626, enforce_fixed=True)
        changed_rejected = False
    except ConservationError:
        changed_rejected = True
    probes.append({
        "name": "legacy J contribution mutation",
        "detected": (
            changed_rejected
            and changed_deltas == [{
                "ordinal": 29,
                "before": (
                    "CONTROL TYPES: S - SIGNALIZED (incl. TSN J-P)", Decimal(2648)
                ),
                "after": (
                    "CONTROL TYPES: S - SIGNALIZED (incl. TSN J-P)", Decimal(2649)
                ),
            }]
        ),
        "expected_rejection": "J 207->208 produces sole S 2648->2649 delta",
        "observed_projected_deltas": [
            {
                "ordinal": item["ordinal"],
                "before_typed_row": [_typed(value) for value in item["before"]],
                "after_typed_row": [_typed(value) for value in item["after"]],
            }
            for item in changed_deltas
        ],
    })

    missing_signal = [row for row in raw_rows if not (
        row["section"] == "CONTROL TYPES" and row["code"] == "K"
    )]
    try:
        _project_records(missing_signal, 16_626)
        missing_detected = False
    except ConservationError:
        missing_detected = True
    probes.append({"name": "missing legacy control subtype", "detected": missing_detected})

    try:
        _project_records(raw_rows, 16_627)
        total_detected = False
    except ConservationError:
        total_detected = True
    probes.append({
        "name": "printed Total Intersections mutation",
        "detected": total_detected,
        "expected_rejection": "Total 16626->16627 changes only the required final row",
    })

    probes.append(dict(pdf_result["page_word_stream_mutation_probe"]))

    blind_raw = deepcopy(list(raw_rows))
    blind_raw[24]["descriptor"] = str(blind_raw[24]["descriptor"]) + "#MUT"
    blind_raw[24]["band"] = 3
    blind_projection, _blind_dispositions, _blind_categories = _project_records(
        blind_raw, 16_626, enforce_fixed=False
    )
    blind_core = [
        (item["band"], item["section"], item["code"], item["count"], item["descriptor"])
        for item in blind_raw
    ]
    probes.append({
        "name": "raw descriptor and physical-band drift hidden from Category/Count",
        "detected": (
            _ordered_digest(blind_core) != _ordered_digest(raw_core)
            and blind_projection == list(projected_rows)
        ),
        "expected_effect": (
            "raw ordered typed digest changes while comparison projection remains equal"
        ),
    })

    _baseline_projection, _baseline_dispositions, baseline_categories = _project_records(
        raw_rows, 16_626, enforce_fixed=False
    )
    isolated_raw = deepcopy(list(raw_rows))
    isolated_raw[0]["count"] = int(isolated_raw[0]["count"]) + 1
    isolated_projection, _isolated_dispositions, isolated_categories = _project_records(
        isolated_raw, 16_626, enforce_fixed=False
    )
    baseline_by_category = {
        item["normalized_category"]: (
            item["source_contributions_ordered_typed_sha256"],
            item["source_contributions_multiset_typed_sha256"],
            item["projected_typed_row_sha256"],
        )
        for item in baseline_categories
    }
    isolated_by_category = {
        item["normalized_category"]: (
            item["source_contributions_ordered_typed_sha256"],
            item["source_contributions_multiset_typed_sha256"],
            item["projected_typed_row_sha256"],
        )
        for item in isolated_categories
    }
    isolated_changed_categories = [
        category for category in baseline_by_category
        if baseline_by_category[category] != isolated_by_category[category]
    ]
    isolated_target_deltas = [
        index + 1 for index, (before, after)
        in enumerate(zip(projected_rows, isolated_projection))
        if before != after
    ]
    probes.append({
        "name": "one-category typed-digest isolation",
        "detected": (
            isolated_changed_categories == ["HIGHWAY GROUP: R - RIGHT IND ALIGN"]
            and isolated_target_deltas == [1]
        ),
        "changed_per_category_digests": isolated_changed_categories,
        "changed_projected_row_ordinals": isolated_target_deltas,
    })

    try:
        _source_code("RURAL/URBAN/SUBURBAN", "-O OUTSIDE CITY", None)
        orphan_detected = False
    except ConservationError:
        orphan_detected = True
    probes.append({"name": "orphan outside-city continuation", "detected": orphan_detected})

    wrong_parent = _source_code("RURAL/URBAN/SUBURBAN", "-O OUTSIDE CITY", "U")[0]
    probes.append({
        "name": "outside-city parent swap",
        "detected": wrong_parent == "U-O" and wrong_parent != "R-O",
    })

    count_changed = [list(row) for row in normalized_rows]
    count_changed[0][1] = Decimal(count_changed[0][1]) + 1
    probes.append({
        "name": "normalized count mutation",
        "detected": _ordered_digest(count_changed) != _ordered_digest(normalized_rows),
    })

    type_changed = [list(row) for row in normalized_rows]
    type_changed[0][1] = str(type_changed[0][1])
    probes.append({
        "name": "same-text normalized type mutation",
        "detected": _ordered_digest(type_changed) != _ordered_digest(normalized_rows),
    })

    normalized_reorder = list(normalized_rows)
    normalized_reorder[0], normalized_reorder[1] = normalized_reorder[1], normalized_reorder[0]
    probes.append({
        "name": "normalized row reorder",
        "detected": (
            _ordered_digest(normalized_reorder) != _ordered_digest(normalized_rows)
            and _multiset_digest(normalized_reorder)[0] == _multiset_digest(normalized_rows)[0]
        ),
    })

    fake_sidecar = {
        "schema_version": 1, "completion": "incomplete", "skipped_inputs": 0,
        "failed_inputs": 0, "tsn_normalization_version": 2,
        "tsn_artifact_identity_token": SIDECAR_BINDING["artifact_identity_token"],
        "tsn_raw_manifest": {}, "tsn_normalized_workbook_identity": {},
    }
    try:
        _validate_sidecar(fake_sidecar)
        sidecar_detected = False
    except ConservationError:
        sidecar_detected = True
    probes.append({"name": "incomplete sidecar", "detected": sidecar_detected})

    sidecar_manifest = deepcopy(sidecar_document)
    sidecar_manifest["tsn_raw_manifest"]["sha256"] = "0" * 64
    try:
        _validate_sidecar(sidecar_manifest)
        sidecar_manifest_detected = False
    except ConservationError:
        sidecar_manifest_detected = True
    probes.append({
        "name": "same-completion sidecar raw-manifest drift",
        "detected": (
            sidecar_manifest.get("completion") == sidecar_document.get("completion")
            and sidecar_manifest_detected
        ),
    })

    r7_changed = deepcopy(r7_document)
    target = next(
        item for item in r7_changed["families"]
        if item.get("report") == "intersection_summary"
    )
    target["output"]["sha256"] = "0" * 64
    try:
        _validate_r7(r7_changed)
        r7_detected = False
    except ConservationError:
        r7_detected = True
    probes.append({
        "name": "r7 normalized output-hash drift",
        "detected": r7_detected,
    })

    probes.append({
        "name": "Control F label semantic drift remains visible",
        "detected": (
            raw_rows[24]["descriptor"] == "F-FOUR WAY FLASHER (RED ON ALL)"
            and projected_rows[24][0] == "CONTROL TYPES: F - 4-WAY FLASHER (RED/MAINLINE)"
        ),
    })
    return probes


def run() -> dict[str, object]:
    required_paths = (
        RAW_PDF, NORMALIZED_XLSX, NORMALIZED_SIDECAR, R7_WITNESS,
        SOURCE_FORMAT_RESULT, SOURCE_FORMAT_SCRIPT, READER_PATH,
        READER_GATE_PATH, FAMILY_GATE_PATH, GENERATOR_PATH,
    )
    missing = [str(path) for path in required_paths if not path.is_file()]
    if missing:
        raise ConservationError(f"required bound audit inputs are missing: {missing}")

    code_paths = {
        "generator": GENERATOR_PATH,
        "xlsx_reader": READER_PATH,
        "xlsx_reader_gate": READER_GATE_PATH,
        "family_gate": FAMILY_GATE_PATH,
        "accepted_source_format_script": SOURCE_FORMAT_SCRIPT,
    }
    code_initial = {label: capture_file_identity(path) for label, path in code_paths.items()}
    _require_identity(
        code_initial["accepted_source_format_script"],
        SOURCE_FORMAT_SCRIPT_BINDING,
        "accepted source-format oracle script",
    )

    raw_capture = capture_file_bytes(RAW_PDF, max_bytes=20 * 1024 * 1024)
    _require_identity(raw_capture.identity, RAW_BINDING, "authoritative Intersection Summary PDF")
    normalized_capture = capture_file_bytes(NORMALIZED_XLSX, max_bytes=20 * 1024 * 1024)
    _require_identity(normalized_capture.identity, NORMALIZED_BINDING, "r7 normalized workbook")
    sidecar_capture = capture_file_bytes(NORMALIZED_SIDECAR, max_bytes=1024 * 1024)
    _require_identity(sidecar_capture.identity, SIDECAR_BINDING, "r7 normalized sidecar")
    r7_capture = capture_file_bytes(R7_WITNESS, max_bytes=1024 * 1024)
    _require_identity(r7_capture.identity, R7_BINDING, "accepted r7 lifecycle witness")
    source_format_capture = capture_file_bytes(SOURCE_FORMAT_RESULT, max_bytes=1024 * 1024)
    _require_identity(
        source_format_capture.identity,
        SOURCE_FORMAT_RESULT_BINDING,
        "accepted Intersection source-format oracle result",
    )

    dependency_pre_parse = {
        "package_manifests": _parser_package_manifests(),
        "versions": _parser_versions(),
    }
    reader_gate = _run_gate(READER_GATE_PATH)
    family_gate = _run_gate(FAMILY_GATE_PATH)
    if not reader_gate["pass"] or not family_gate["pass"]:
        raise ConservationError(
            f"executed dependency gate failed: reader={reader_gate['returncode']}, "
            f"family={family_gate['returncode']}"
        )

    pdf_result = _extract_pdf(raw_capture.payload)
    dependency_initial = {
        "package_manifests": _parser_package_manifests(),
        "loaded_executable_modules": _loaded_parser_module_manifest(),
        "versions": _parser_versions(),
    }
    dependencies_stable_during_parse = (
        dependency_pre_parse["package_manifests"]
        == dependency_initial["package_manifests"]
        and dependency_pre_parse["versions"] == dependency_initial["versions"]
    )
    dependency_drift_probe = _same_version_dependency_drift_probe(
        dependency_initial["loaded_executable_modules"],
        dependency_initial["versions"],
    )
    raw_rows = pdf_result["raw_category_rows"]
    projected_rows, dispositions, per_category = _project_records(
        raw_rows, int(pdf_result["total"])
    )
    sections = _section_conservation(raw_rows, int(pdf_result["total"]))

    normalized_spec = SheetSpec(
        NORMALIZED_BINDING["sheet"],
        tuple(ColumnSpec(header, SCALAR) for header in NORMALIZED_BINDING["headers"]),
        exact_schema=True,
    )
    normalized_sheet = read_sheet(NORMALIZED_XLSX, normalized_spec)
    normalized_rows = [tuple(row.values) for row in normalized_sheet.rows]
    if len(normalized_rows) != 58:
        raise ConservationError(f"normalized row count changed: {len(normalized_rows)}")
    if [row.source_row for row in normalized_sheet.rows] != list(range(2, 60)):
        raise ConservationError("normalized physical rows are not contiguous 2..59")
    if any(not isinstance(row[0], str) or not row[0] for row in normalized_rows):
        raise ConservationError("normalized Category must be nonblank text")
    if any(not isinstance(row[1], Decimal) or not row[1].is_finite()
           or row[1] != row[1].to_integral_value() or row[1] < 0
           for row in normalized_rows):
        raise ConservationError("normalized Count must be a nonnegative integral Decimal")
    if len({row[0] for row in normalized_rows}) != len(normalized_rows):
        raise ConservationError("normalized Category keys are not unique")

    sidecar_document = _json_document(sidecar_capture, "normalized sidecar")
    r7_document = _json_document(r7_capture, "r7 lifecycle witness")
    source_format_document = _json_document(source_format_capture, "source-format result")
    sidecar_checks = _validate_sidecar(sidecar_document)
    r7_checks = _validate_r7(r7_document)
    source_format_checks = _validate_source_format_evidence(
        source_format_document, raw_rows, projected_rows, sections
    )

    projection_exact = normalized_rows == list(projected_rows)
    projection_residue = [] if projection_exact else [{
        "kind": "normalized_projection_mismatch",
        "projected_ordered_sha256": _ordered_digest(projected_rows),
        "normalized_ordered_sha256": _ordered_digest(normalized_rows),
    }]
    mutations = _mutation_probes(
        raw_rows, projected_rows, normalized_rows,
        pdf_result, sidecar_document, r7_document,
    )

    raw_digest_rows = [
        (
            row["physical_pdf_page"], row["printed_report_page"], row["band"],
            row["section"], row["code"], row["count"], row["descriptor"],
            row["top"], row["bottom"], row["x0"], row["x1"],
        )
        for row in raw_rows
    ]
    raw_digests = _dataset_digests(
        (
            "physical_pdf_page", "printed_report_page", "band", "section", "code",
            "count", "descriptor", "top", "bottom", "x0", "x1",
        ),
        raw_digest_rows,
    )
    projected_digests = _dataset_digests(("Category", "Count"), projected_rows)
    normalized_digests = _dataset_digests(("Category", "Count"), normalized_rows)
    package_topology = _xlsx_package_topology(normalized_capture.payload)

    label_drift = {
        "source_section": "CONTROL TYPES",
        "source_code": "F",
        "source_descriptor": "F-FOUR WAY FLASHER (RED ON ALL)",
        "source_count": 7,
        "normalized_category": "CONTROL TYPES: F - 4-WAY FLASHER (RED/MAINLINE)",
        "classification": "semantic_label_drift_not_silently_equivalent",
    }
    fold_finding = {
        "id": "IS-S6-001",
        "severity": "P1",
        "status": "open",
        "title": "Normalized Intersection Summary irreversibly folds six TSN signal categories",
        "source_counts": LEGACY_SIGNAL_COUNTS,
        "folded_target": "CONTROL TYPES: S - SIGNALIZED (incl. TSN J-P)",
        "folded_count": sum(LEGACY_SIGNAL_COUNTS.values()),
        "impact": (
            "The comparison projection is exact, but J/K/L/M/N/P identities, labels, and "
            "individual counts cannot be reconstructed from normalized bytes."
        ),
        "requirement": (
            "Preserve the six source rows in a source-bound normalized layer while retaining "
            "the S aggregate as the comparison projection."
        ),
    }
    label_finding = {
        "id": "IS-S6-002",
        "severity": "P1",
        "status": "open",
        "title": "Control F is semantically relabelled from RED ON ALL to RED/MAINLINE",
        "evidence": label_drift,
        "requirement": (
            "Retain the exact TSN source descriptor and keep any canonical comparison label "
            "as a separately named projection; do not claim textual equivalence."
        ),
    }
    provenance_finding = {
        "id": "IS-S6-003",
        "severity": "P1",
        "status": "open",
        "title": "Normalized Intersection Summary omits report-level comparison provenance",
        "omitted_fields": [
            "report_id", "report_date", "reference_date", "submitter", "report_title",
            "event_id", "location_criteria", "printed_generation_time",
        ],
        "source_values": {
            key: REPORT_PROVENANCE[key]
            for key in (
                "report_id", "report_date", "reference_date", "submitter", "report_title",
                "event_id", "location_criteria", "printed_generation_time",
            )
        },
        "requirement": "Retain typed report provenance in normalized bytes or an immutable paired layer.",
    }

    # All expensive source-derived work is complete before this final acceptance check.
    code_final = {label: capture_file_identity(path) for label, path in code_paths.items()}
    dependency_final = {
        "package_manifests": _parser_package_manifests(),
        "loaded_executable_modules": _loaded_parser_module_manifest(),
        "versions": _parser_versions(),
    }
    source_final = {
        "raw_pdf": capture_file_identity(RAW_PDF),
        "normalized_xlsx": capture_file_identity(NORMALIZED_XLSX),
        "normalized_sidecar": capture_file_identity(NORMALIZED_SIDECAR),
        "r7_witness": capture_file_identity(R7_WITNESS),
        "source_format_result": capture_file_identity(SOURCE_FORMAT_RESULT),
    }
    final_current = (
        code_initial == code_final
        and dependency_initial == dependency_final
        and source_final["raw_pdf"] == raw_capture.identity
        and source_final["normalized_xlsx"] == normalized_sheet.pre_identity
        and source_final["normalized_xlsx"] == normalized_capture.identity
        and source_final["normalized_sidecar"] == sidecar_capture.identity
        and source_final["r7_witness"] == r7_capture.identity
        and source_final["source_format_result"] == source_format_capture.identity
        and normalized_sheet.pre_identity == normalized_sheet.post_identity
    )

    audit_invariants = {
        "authoritative_pdf_exact_private_capture": raw_capture.identity.sha256 == RAW_BINDING["sha256"],
        "exact_pdf_metadata_page_topology_and_text": pdf_result["pages"] == list(PAGE_BINDINGS),
        "exact_62_source_category_rows": len(raw_rows) == 62,
        "rural_urban_parent_disambiguation_exact": len(pdf_result["rural_urban_parent_disambiguations"]) == 2,
        "every_source_category_disposed_once": len(dispositions) == len(raw_rows) == 62,
        "section_subtotals_and_universes_conserved": all(item["pass"] for item in sections),
        "normalized_schema_rows_types_and_contiguity_exact": len(normalized_rows) == 58,
        "per_category_typed_digest_ledger_covers_all_58_normalized_rows": (
            len(per_category) == len(normalized_rows) == 58
            and [item["normalized_category"] for item in per_category]
            == [str(row[0]) for row in normalized_rows]
        ),
        "sidecar_exact_and_complete": all(sidecar_checks.values()),
        "r7_lifecycle_witness_exact_and_current": all(r7_checks.values()),
        "accepted_source_format_evidence_independently_reproduced": all(source_format_checks.values()),
        "reader_and_family_dependency_gates_executed_and_passed": reader_gate["pass"] and family_gate["pass"],
        "parser_packages_stable_across_private_pdf_parse": dependencies_stable_during_parse,
        "every_loaded_parser_module_hash_bound_and_revalidated": dependency_initial == dependency_final,
        "same_version_internal_parser_module_drift_detected": dependency_drift_probe["detected"],
        "mutation_probes_all_detected": all(item["detected"] for item in mutations),
        "zero_unexplained_projection_residue": not projection_residue,
        "final_source_code_dependency_revalidation_current": final_current,
    }
    audit_complete = all(audit_invariants.values())
    normalized_raw_granularity_conservation = False
    normalized_full_conservation = False

    return {
        "schema_version": 2,
        "audit": "Stage 6 Intersection Summary authoritative PDF-to-r7 conservation",
        "independence": {
            "application_parsers_imported": False,
            "application_normalizers_imported": False,
            "application_comparators_imported": False,
            "application_schemas_imported": False,
            "pdf_reader": "pdfplumber+pypdf over privately captured immutable bytes",
            "xlsx_reader": "build/phase3_xlsx_stream.py stdlib OOXML reader",
            "accepted_source_format_oracle_used_as": "hash-bound evidence/spec only; no code imported",
        },
        "bindings": {
            "raw_pdf": RAW_BINDING,
            "normalized_r7": NORMALIZED_BINDING,
            "normalized_sidecar": SIDECAR_BINDING,
            "r7_lifecycle_witness": R7_BINDING,
            "accepted_source_format_result": SOURCE_FORMAT_RESULT_BINDING,
            "accepted_source_format_script": SOURCE_FORMAT_SCRIPT_BINDING,
        },
        "source_identity": {
            "raw_pdf": {
                "path": str(RAW_PDF),
                "private_capture": _identity_dict(raw_capture.identity),
                "acceptance_revalidation": _identity_dict(source_final["raw_pdf"]),
            },
            "normalized_xlsx": {
                "path": str(NORMALIZED_XLSX),
                "private_package_capture": _identity_dict(normalized_capture.identity),
                "worksheet_pre_read": _identity_dict(normalized_sheet.pre_identity),
                "worksheet_post_read": _identity_dict(normalized_sheet.post_identity),
                "acceptance_revalidation": _identity_dict(source_final["normalized_xlsx"]),
                "package_topology": package_topology,
            },
            "normalized_sidecar": {
                "path": str(NORMALIZED_SIDECAR),
                "private_capture": _identity_dict(sidecar_capture.identity),
                "accepted_claims": sidecar_checks,
                "acceptance_revalidation": _identity_dict(source_final["normalized_sidecar"]),
            },
            "r7_lifecycle_witness": {
                "path": str(R7_WITNESS),
                "private_capture": _identity_dict(r7_capture.identity),
                "accepted_claims": r7_checks,
                "acceptance_revalidation": _identity_dict(source_final["r7_witness"]),
            },
            "accepted_source_format_evidence": {
                "path": str(SOURCE_FORMAT_RESULT),
                "private_capture": _identity_dict(source_format_capture.identity),
                "independently_reproduced_claims": source_format_checks,
                "acceptance_revalidation": _identity_dict(source_final["source_format_result"]),
            },
        },
        "code_provenance": {
            label: {
                "initial": _identity_dict(code_initial[label]),
                "acceptance_revalidation_after_all_digests": _identity_dict(code_final[label]),
            }
            for label in code_paths
        },
        "dependency_provenance": {
            "pre_private_pdf_parse_package_capture": dependency_pre_parse,
            "initial": dependency_initial,
            "acceptance_revalidation_after_all_digests": dependency_final,
            "same_version_internal_module_drift_mutation": dependency_drift_probe,
            "executed_gates": {
                "xlsx_reader": reader_gate,
                "family_semantics": family_gate,
            },
        },
        "pdf_extraction": pdf_result,
        "source_category_dispositions": dispositions,
        "per_normalized_category_conservation": per_category,
        "section_subtotal_and_universe_conservation": sections,
        "raw_category_digests": raw_digests,
        "independent_projection_digests": projected_digests,
        "normalized_digests": normalized_digests,
        "projection_comparison": {
            "raw_category_rows": len(raw_rows),
            "projected_category_rows": len(projected_rows) - 1,
            "projected_rows_including_total": len(projected_rows),
            "normalized_rows": len(normalized_rows),
            "ordered_exact": normalized_rows == list(projected_rows),
            "multiset_exact": _multiset_digest(normalized_rows)[0] == _multiset_digest(projected_rows)[0],
            "unexplained_residue": projection_residue,
            "legacy_signal_fold": fold_finding,
            "control_f_label_classification": label_drift,
        },
        "anomaly_manifest": {
            "unexplained_source_rows": [],
            "unexplained_normalized_rows": projection_residue,
            "duplicate_source_section_codes": [],
            "duplicate_normalized_categories": [],
            "parent_disambiguations": pdf_result["rural_urban_parent_disambiguations"],
            "classified_section_taxonomy_deficits": SECTION_UNIVERSE_DEFICITS,
            "classified_noninjective_fold": fold_finding,
            "classified_semantic_label_drift": label_drift,
            "unexplained_residue_count": len(projection_residue),
        },
        "semantic_mutation_probes": mutations,
        "findings": {
            "blocking": [fold_finding, label_finding, provenance_finding],
            "presentation_only": [{
                "source": "physical PDF page 1",
                "role": "legal/policy notice and page presentation geometry",
                "disposition": "exact page text/topology digest-bound; not a comparison semantic claim",
            }],
        },
        "audit_invariants": audit_invariants,
        "projection_exact": projection_exact,
        "normalized_comparison_projection_conservation": projection_exact and audit_complete,
        "normalized_raw_granularity_conservation": normalized_raw_granularity_conservation,
        "stage6_family_audit_complete": audit_complete,
        "normalized_full_conservation": normalized_full_conservation,
        "post_result_write_revalidation_protocol": (
            "main() hashes raw PDF, normalized XLSX, sidecar, r7 witness, source-format evidence, "
            "generator, both executed gate scripts, independent reader, source-format script, and "
            "PDF dependency manifests after final result bytes are written; detached acceptance is "
            "the only accepted publication record."
        ),
    }


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-open-findings", action="store_true",
        help="exit zero when the audit is complete but documented product findings remain",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = run()
    except Exception as exc:
        failure = {
            "schema_version": 2,
            "audit": "Stage 6 Intersection Summary authoritative PDF-to-r7 conservation",
            "projection_exact": False,
            "stage6_family_audit_complete": False,
            "normalized_full_conservation": False,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(failure, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        sys.stdout.write(json.dumps(failure, ensure_ascii=False) + "\n")
        return 2

    result["publication_serialization_gate"] = {
        "canonical_typed_mutation_diagnostics": True,
        "full_result_json_roundtrip": True,
        "method": (
            "serialize the complete successful result, parse it, serialize the parsed value "
            "with identical options, and require byte equality before publication"
        ),
    }
    result["audit_invariants"]["full_result_json_roundtrip_gate"] = True
    result["stage6_family_audit_complete"] = all(result["audit_invariants"].values())
    try:
        payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        roundtrip = json.dumps(
            json.loads(payload), indent=2, ensure_ascii=False
        ) + "\n"
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stdout.write(json.dumps({
            "output": str(args.output),
            "stage6_family_audit_complete": False,
            "error": f"full-result JSON serialization gate failed: {exc}",
        }, ensure_ascii=False) + "\n")
        return 2
    if payload != roundtrip:
        sys.stdout.write(json.dumps({
            "output": str(args.output),
            "stage6_family_audit_complete": False,
            "error": "full-result JSON round-trip bytes changed",
        }, ensure_ascii=False) + "\n")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")

    accepted_paths = {
        "raw_pdf": RAW_PDF,
        "normalized_xlsx": NORMALIZED_XLSX,
        "normalized_sidecar": NORMALIZED_SIDECAR,
        "r7_witness": R7_WITNESS,
        "source_format_result": SOURCE_FORMAT_RESULT,
        "generator": GENERATOR_PATH,
        "xlsx_reader": READER_PATH,
        "xlsx_reader_gate": READER_GATE_PATH,
        "family_gate": FAMILY_GATE_PATH,
        "accepted_source_format_script": SOURCE_FORMAT_SCRIPT,
    }
    post_identities = {label: capture_file_identity(path) for label, path in accepted_paths.items()}
    expected = {
        "raw_pdf": result["source_identity"]["raw_pdf"]["acceptance_revalidation"],
        "normalized_xlsx": result["source_identity"]["normalized_xlsx"]["acceptance_revalidation"],
        "normalized_sidecar": result["source_identity"]["normalized_sidecar"]["acceptance_revalidation"],
        "r7_witness": result["source_identity"]["r7_lifecycle_witness"]["acceptance_revalidation"],
        "source_format_result": result["source_identity"]["accepted_source_format_evidence"]["acceptance_revalidation"],
        **{
            label: result["code_provenance"][label]["acceptance_revalidation_after_all_digests"]
            for label in (
                "generator", "xlsx_reader", "xlsx_reader_gate", "family_gate",
                "accepted_source_format_script",
            )
        },
    }
    post_dependencies = {
        "package_manifests": _parser_package_manifests(),
        "loaded_executable_modules": _loaded_parser_module_manifest(),
        "versions": _parser_versions(),
    }
    post_current = (
        all(_identity_dict(post_identities[label]) == expected[label] for label in accepted_paths)
        and post_dependencies
        == result["dependency_provenance"]["acceptance_revalidation_after_all_digests"]
    )
    result_bytes = args.output.read_bytes()
    acceptance_path = args.output.with_suffix(args.output.suffix + ".acceptance.json")
    acceptance = {
        "schema_version": 1,
        "result": str(args.output.resolve()),
        "result_bytes": len(result_bytes),
        "result_sha256": hashlib.sha256(result_bytes).hexdigest(),
        "projection_exact": result["projection_exact"],
        "stage6_family_audit_complete": result["stage6_family_audit_complete"],
        "normalized_full_conservation": result["normalized_full_conservation"],
        "post_result_write_revalidation": post_current,
        "post_result_write_identities": {
            label: _identity_dict(identity) for label, identity in post_identities.items()
        },
        "post_result_write_dependency_manifests": post_dependencies,
    }
    acceptance_path.write_text(
        json.dumps(acceptance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if not post_current:
        sys.stdout.write(json.dumps({
            "output": str(args.output),
            "acceptance_record": str(acceptance_path),
            "post_result_write_revalidation": False,
        }) + "\n")
        return 3

    sys.stdout.write(json.dumps({
        "output": str(args.output),
        "acceptance_record": str(acceptance_path),
        "result_sha256": acceptance["result_sha256"],
        "projection_exact": result["projection_exact"],
        "stage6_family_audit_complete": result["stage6_family_audit_complete"],
        "normalized_full_conservation": result["normalized_full_conservation"],
        "blocking_findings": len(result["findings"]["blocking"]),
        "post_result_write_revalidation": True,
    }, ensure_ascii=False) + "\n")
    if not result["stage6_family_audit_complete"]:
        return 2
    if not result["normalized_full_conservation"] and not args.allow_open_findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
