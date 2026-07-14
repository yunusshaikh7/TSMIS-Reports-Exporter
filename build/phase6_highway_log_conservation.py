"""Independent Stage-6 Highway Log raw-PDF conservation oracle.

This audit deliberately does not import the application's Highway Log parser,
normalizer, column constants, comparator, or evidence adapters.  It captures the
exact authoritative D01-D12 PDF bytes, parses those private payloads with an
independent character-coordinate implementation, reads the accepted r7 workbook
through the generic Phase-3 OOXML reader, and classifies every source claim and
every source-to-normalized residue.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Iterable, Mapping, Sequence
import zipfile

import pdfplumber

BUILD_DIR = Path(__file__).resolve().parent
REPO_ROOT = BUILD_DIR.parent
sys.path.insert(0, str(BUILD_DIR))
from phase3_xlsx_stream import (  # noqa: E402
    ColumnSpec,
    FileIdentity,
    SheetSpec,
    XlsxLimits,
    XlsxSecurityError,
    capture_file_bytes,
    capture_file_identity,
    read_sheet,
)


RAW_DIR = Path(
    r"C:\Users\Yunus\Downloads\TSMIS\tsn_library\highway_log\raw"
)
R7_ROOT = Path(
    r"C:\Users\Yunus\.codex\visualizations\2026\07\10"
    r"\019f4e12-9bbf-7000-949a-019b80f60bdd\phase4_tsn_rebaseline"
)
R7_RUN = R7_ROOT / "raw-2026-07-12-r7"
NORMALIZED_XLSX = (
    R7_RUN / "highway_log" / "consolidated"
    / "tsn_highway_log_consolidated.xlsx"
)
NORMALIZED_SIDECAR = Path(str(NORMALIZED_XLSX) + ".outcome.json")
R7_RESULT = R7_RUN / "result.json"
RESULT_DIR = R7_ROOT.parent / "phase6_tsn_conservation"
DEFAULT_RESULT = RESULT_DIR / "highway_log_conservation_r1.json"
FAMILY_GATE = BUILD_DIR / "check_phase6_highway_log_conservation.py"
READER = BUILD_DIR / "phase3_xlsx_stream.py"
READER_GATE = BUILD_DIR / "check_phase3_xlsx_stream.py"
VISUAL_SAMPLER = BUILD_DIR / "render_phase6_highway_log_visual_sample.py"
VISUAL_MANIFEST = REPO_ROOT / "tmp" / "pdfs" / "phase6-hl-visual-r2" / "manifest.json"

HEADERS = (
    "Route", "Location", "Length (MI) [MI]", "NA [N/A]", "Cnty Odom",
    "City", "RU [R/U]", "SPD", "TER", "HG [H/G]", "AC [A/C]",
    "LB ST [LB T]", "LB # Lns [LB Lns]", "LB SF [LB F]",
    "LB OT-SH Total [LB OT]", "LB OT-SH Treated [LB TR]",
    "LB T-W Wid [LB T-W]", "LB IN-SH Total [LB IN]",
    "LB IN-SH Treated [LB SH]", "Med TY/CL/BA [Med TCB]",
    "Med Wid/Var [Med Wid]", "RB ST [RB T]", "RB # Lns [RB Lns]",
    "RB SF [RB F]", "RB IN-SH Total [RB IN]",
    "RB IN-SH Treated [RB SH]", "RB T-W Wid [RB T-W]",
    "RB OT-SH Total [RB OT]", "RB OT-SH Treated [RB SH]",
    "Description", "Date of Rec", "Sig Chg. Date",
)
SHEET_NAME = "Highway Log"

SOURCE_KEYS = (
    "location", "mi", "na", "cnty_odom", "city", "ru", "spd", "ter",
    "hg", "ac", "lb_t", "lb_lns", "lb_f", "lb_ot", "lb_tr", "lb_tw",
    "lb_in", "lb_sh", "med_tcb", "med_wid", "rb_t", "rb_lns", "rb_f",
    "rb_in", "rb_sh", "rb_tw", "rb_ot", "rb_sh2", "adt_back", "adt_pp",
    "adt_ahead", "rec", "sig",
)
PROJECTED_KEYS = (
    "location", "mi", "na", "cnty_odom", "city", "ru", "spd", "ter",
    "hg", "ac", "lb_t", "lb_lns", "lb_f", "lb_ot", "lb_tr", "lb_tw",
    "lb_in", "lb_sh", "med_tcb", "med_wid", "rb_t", "rb_lns", "rb_f",
    "rb_in", "rb_sh", "rb_tw", "rb_ot", "rb_sh2", "description", "rec",
    "sig",
)
SOURCE_HEADERS = (
    "District Owner", "County Owner", "Route Owner", "Route Owner Qualifier",
    "Owner Header Occurrence",
    *SOURCE_KEYS,
    "Description (Whitespace Join)",
)

# Independently transcribed from the fixed OTM52010 page geometry.  No production
# module or constant is imported by this oracle.
COLUMN_WINDOWS = (
    ("location", 0.0, 50.0), ("mi", 50.0, 73.0),
    ("na", 73.0, 82.0), ("cnty_odom", 82.0, 112.0),
    ("city", 112.0, 132.0), ("ru", 132.0, 147.0),
    ("spd", 147.0, 160.0), ("ter", 160.0, 171.0),
    ("hg", 171.0, 184.0), ("ac", 184.0, 197.0),
    ("lb_t", 197.0, 208.0), ("lb_lns", 208.0, 219.0),
    ("lb_f", 219.0, 230.0), ("lb_ot", 230.0, 241.0),
    ("lb_tr", 241.0, 253.0), ("lb_tw", 253.0, 268.0),
    ("lb_in", 268.0, 279.0), ("lb_sh", 279.0, 291.0),
    ("med_tcb", 291.0, 308.0), ("med_wid", 308.0, 326.0),
    ("rb_t", 326.0, 338.0), ("rb_lns", 338.0, 350.0),
    ("rb_f", 350.0, 361.0), ("rb_in", 361.0, 372.0),
    ("rb_sh", 372.0, 386.0), ("rb_tw", 386.0, 398.0),
    ("rb_ot", 398.0, 410.0), ("rb_sh2", 410.0, 424.0),
    ("adt_back", 424.0, 448.0), ("adt_pp", 448.0, 459.0),
    ("adt_ahead", 459.0, 486.0), ("rec", 486.0, 519.0),
    ("sig", 519.0, 612.0),
)

RAW_BINDINGS = (
    ("D01 Highway Log TSN.pdf", 1_633_209, "0e26d5ef011891f0a77be774e3b655a18a7add616c5139676ab99950e54ddc34", 116),
    ("D02 Highway Log TSN.pdf", 2_045_757, "d610f137d88c41cf61d239aa29c6ecad1c2621d307d4c984a8ea5aa15289b6a4", 149),
    ("D03 Highway Log TSN.pdf", 2_725_260, "139b14eb4893ee6427153def005262589d1e2dc4bdb2766831579d284307081f", 205),
    ("D04 Highway Log TSN.pdf", 4_376_185, "6046fd7a8f60cf3a85d497cd13278fc936d949221820b75235eaab1a263e8433", 330),
    ("D05 Highway Log TSN.pdf", 2_060_100, "633ac80514b4791886ee58c8b41be166fd75a03ed0e8c974369fe521035799f5", 154),
    ("D06 Highway Log TSN.pdf", 2_226_816, "ac6409f35047a0ecfac93ba00347cf355dbf99bb41e5da69788c3c4a4d387282", 168),
    ("D07 Highway Log TSN.pdf", 3_626_589, "7d1151142d103df72e8b3f6ba9193001a88a2806c580ab4dda775053dd0a4371", 287),
    ("D08 Highway Log TSN.pdf", 2_744_102, "e2efb38281e9bfcc18a02a54bdc4ad1068045fdcbd812f00584e6c6092109cd3", 217),
    ("D09 Highway Log TSN.pdf", 844_675, "38470f27cc49ee1d2eb0813ef653a1348a17522a519a903155ef995ea8c63903", 63),
    ("D10 Highway Log TSN.pdf", 2_080_827, "f6aff2dba133da9d66a46d81ffa5f723f38aab5e48a6d8b1824dbfb4a085c123", 157),
    ("D11 Highway Log TSN.pdf", 2_311_316, "d7a1eba4ddf75d98874e42a379b7cf189699436dcebe557bffd140b287091a76", 179),
    ("D12 Highway Log TSN.pdf", 1_237_155, "36e56bf834063a11be8f2c24cc1e3c93cfd89ac4bc745dd8a494ed6311b39a97", 96),
)
DOCUMENT_CLAIM_BINDINGS = {
    name: {
        "district": f"{index:02d}",
        "creation_date": f"D:2025091515{minute}",
        "modification_date": f"D:2025091515{minute}",
    }
    for index, (name, minute) in enumerate((
        ("D01 Highway Log TSN.pdf", "2304"),
        ("D02 Highway Log TSN.pdf", "2520"),
        ("D03 Highway Log TSN.pdf", "2834"),
        ("D04 Highway Log TSN.pdf", "2944"),
        ("D05 Highway Log TSN.pdf", "3115"),
        ("D06 Highway Log TSN.pdf", "3221"),
        ("D07 Highway Log TSN.pdf", "3456"),
        ("D08 Highway Log TSN.pdf", "3639"),
        ("D09 Highway Log TSN.pdf", "3749"),
        ("D10 Highway Log TSN.pdf", "3936"),
        ("D11 Highway Log TSN.pdf", "4117"),
        ("D12 Highway Log TSN.pdf", "4242"),
    ), 1)
}
NON_SOURCE_BINDING = (
    "_PUT TSN FILES HERE.txt", 446,
    "fcb06a243e57f311692a7c0019025adfda20c9a98fa0ab29b7c0bf8d419ac0d5",
)
NORMALIZED_BINDING = {
    "bytes": 6_663_062,
    "sha256": "fe5c20c244716d345e9e3bc7d2ef1442f1e40a5da4a6220685d3bf7c00ca18aa",
}
SIDECAR_BINDING = {
    "bytes": 2_521,
    "sha256": "6a746ce16773724954391894cbfb61dfccdb30c6c763750644deed081c533b1e",
}
RAW_MANIFEST_SHA256 = (
    "a4157d2c0ea82f7b5bbab59233fb1663bf8985c69cfdcaa36744e1f5f011ff20"
)
ARTIFACT_IDENTITY_TOKEN = (
    "tsn-normalized-v1:dfd4c2250319d0c0efd56f4f16ae293b"
    "f8e18dd8eeea28116ed64822d5f92996"
)
R7_RESULT_BINDING = {
    "bytes": 173_124,
    "sha256": "b2af1ce140de93e70db76b96c0a775ff79287d7b47ab092ce02fb11c18e18caa",
}
VISUAL_SAMPLER_BINDING = {
    "bytes": 8_544,
    "sha256": "348af384ba2107b5274f5bc9b0fcc15b84e869efabe682d015b5b91ccf4bedef",
}
VISUAL_MANIFEST_BINDING = {
    "bytes": 12_253,
    "sha256": "3fb092931924c3b8e6db406a25d00265e101d948c97438d3303bf1a2797c602e",
}
EXPECTED = {
    "members": 12,
    "raw_bytes": 27_911_991,
    "pages": 2_121,
    "cover_pages": 12,
    "data_pages": 2_109,
    "projected_rows": 60_083,
    "routes": 263,
    "district_route_owners": 369,
    "ditto_cells": 22_396,
    "role_right": 1_027,
    "role_left": 965,
    "role_combined": 58_091,
    "location_plain": 39_968,
    "location_leading_prefix": 18_938,
    "location_equation_suffix": 1_177,
    "owner_header_lines": 2_363,
    "description_lines": 23_094,
    "description_separator_lines": 3,
    "total_claim_lines": 13_549,
}
EXPECTED_ROWS_BY_DISTRICT = {
    "01": 3_693, "02": 4_575, "03": 5_882, "04": 9_285,
    "05": 4_506, "06": 4_792, "07": 7_562, "08": 5_914,
    "09": 1_885, "10": 4_481, "11": 4_940, "12": 2_568,
}

Y_TOLERANCE = 3.0
WORD_GAP = 1.5
HEADER_BAND = 56.0
DESC_X0_MIN = 60.0
DESC_X0_MAX = 110.0
LOCATION_RE = re.compile(r"^[A-Z]?\d{3}\.\d{3}[A-Z]?$")
GROUP_RE = re.compile(
    r"^(\d{2})\s+([A-Z]{2,4})\s+(\d{1,3}[A-Z]?)(?:\s+([A-Z]))?$"
)
GROUP_LIKE_RE = re.compile(r"^\d{1,2}\s+[A-Z0-9.]{2,5}\s+")
PLUS_RE = re.compile(r"^\++$")
VOLUME_RE = re.compile(
    r"^\*\s+\*\s+Volume Location Totals Length\s+"
    r"(?P<length>\d{3}\.\d{3})\s+DVM\s+(?P<dvm>[\d,]+)\s+"
    r"County Cumulative DVM\s+(?P<cumulative>[\d,]+)$"
)
MILEAGE_RE = re.compile(
    r"^(?:(?:\*+\s+)+)?"
    r"(?P<label>CITY TOTALS?|COUNTY TOTALS?|DISTRICT TOTALS?|STATE TOTALS?|"
    r"CUMULATIVE|ROUTE TOTALS?)\s+\(MILEAGE\)\s+TOTAL\s+"
    r"(?P<total>-?\d{3}\.\d{3})\s+CONST\s+(?P<const>-?\d{3}\.\d{3})\s+"
    r"UNCONST\s+(?P<unconst>-?\d{3}\.\d{3})$"
)
DVMS_RE = re.compile(r"^\(DVMS\)\s+(?P<dvms>[\d,]+)$")
WITHIN_DVMS_RE = re.compile(
    r"^\(within District\)\s+\(DVMS\)\s+(?P<dvms>[\d,]+)$"
)
END_REPORT_RE = re.compile(r"^\*{3}\s+End of Report\s+\*{3}$")
NUMBER_OR_OVERFLOW_RE = re.compile(r"-?[\d,]+(?:\.\d+)?|\*+")
NUMERIC_FRAGMENT_RE = re.compile(r"^[\d,.*+()$ -]+$")
VOLUME_LENGTH_FRAGMENT_RE = re.compile(
    r"^Length\s+\d{3}\.\d{3}\s+DVM\s+[\d,]+$"
)
DESCRIPTION_SEPARATOR_RE = re.compile(r"^-{23}$")

EXPECTED_TOTAL_KINDS = {
    "dvms_continuation": 2_444,
    "end_of_report": 12,
    "mileage_summary": 2_905,
    "route_dvms": 368,
    "total_fragment": 220,
    "volume_location": 7_600,
}
EXPECTED_TOTAL_FRAGMENT_CLASSES = {
    "county_cumulative_dvm_fragment": 3,
    "cumulative_mileage_fragment": 1,
    "dvms_blank_or_overflow_fragment": 116,
    "mileage_continuation_fragment": 3,
    "numeric_total_fragment": 12,
    "route_dvms_blank_or_overflow_fragment": 12,
    "starred_total_fragment": 51,
    "total_label_fragment": 18,
    "volume_length_fragment": 4,
}
EXPECTED_TOTALS_BY_DISTRICT = {
    "01": 578, "02": 734, "03": 1_398, "04": 2_436,
    "05": 993, "06": 1_201, "07": 1_887, "08": 1_215,
    "09": 308, "10": 1_026, "11": 1_073, "12": 700,
}
EXPECTED_LINE_CLASSIFICATION_BY_DISTRICT = {
    "01": {"cover": 4, "data": 3_693, "description": 1_061,
           "owner_header": 120, "page_header": 575, "total": 578},
    "02": {"cover": 4, "data": 4_575, "description": 1_608,
           "description_separator": 1, "owner_header": 166,
           "page_header": 740, "total": 734},
    "03": {"cover": 4, "data": 5_882, "description": 2_132,
           "owner_header": 253, "page_header": 1_020, "total": 1_398},
    "04": {"cover": 4, "data": 9_285, "description": 3_381,
           "owner_header": 384, "page_header": 1_645, "total": 2_436},
    "05": {"cover": 4, "data": 4_506, "description": 1_378,
           "owner_header": 194, "page_header": 765, "total": 993},
    "06": {"cover": 4, "data": 4_792, "description": 1_804,
           "owner_header": 196, "page_header": 835, "total": 1_201},
    "07": {"cover": 4, "data": 7_562, "description": 3_645,
           "description_separator": 1, "owner_header": 288,
           "page_header": 1_430, "total": 1_887},
    "08": {"cover": 4, "data": 5_914, "description": 2_609,
           "owner_header": 223, "page_header": 1_080, "total": 1_215},
    "09": {"cover": 4, "data": 1_885, "description": 521,
           "owner_header": 66, "page_header": 310, "total": 308},
    "10": {"cover": 4, "data": 4_481, "description": 1_698,
           "owner_header": 190, "page_header": 780, "total": 1_026},
    "11": {"cover": 4, "data": 4_940, "description": 2_269,
           "owner_header": 181, "page_header": 890, "total": 1_073},
    "12": {"cover": 4, "data": 2_568, "description": 988,
           "description_separator": 1, "owner_header": 102,
           "page_header": 475, "total": 700},
}

# Frozen after the candidate crawl was independently inspected against the
# authoritative D01-D12 source PDFs.  These are terminal acceptance contracts,
# not values derived from the current crawl at runtime.
EXPECTED_PARSER_MODULE_MANIFEST = {
    "member_count": 47,
    "manifest_sha256": "d9e0eaaf67b32611c7469f14a980a91c29ad329e2c927f3b9ff1cdd68953fe5d",
}
EXPECTED_DESCRIPTION_SEPARATOR_MANIFEST_SHA256 = (
    "97f76644d0659e36d9625476b6950f582d95a06ea94c2b6b54b85a24e29cec85"
)
EXPECTED_DATASET_DIGESTS = {
    "raw_source": {
        "row_count": 60_083, "column_count": 39,
        "headers_sha256": "58f523e5549c9cd0ba92b3d49e56a0c808e7ec61ea09d3a921e2fdae67049630",
        "ordered_typed_sha256": "64010894f6865d8b6d5b3e1b4fda2fa030e42044f637bebd3b02a4f9307f554e",
        "multiset_typed_sha256": "d5dfb4937e49c6c7de33b040d002b297557da5026c9d52027b32a2efa2406e49",
    },
    "raw_source_provenance": {
        "row_count": 60_083, "column_count": 12,
        "headers_sha256": "3573b7438dff748cf17f0c82142b28d39ed17cd98916f28b39af112ca8f84302",
        "ordered_typed_sha256": "c3bab833a96bd283513f6c224a56f4abefcf81cd03b804bb27242041a5d4582b",
        "multiset_typed_sha256": "50136b3c1480d9c9918089305c1947a242cac91734edf2d0a599d70dd6c22308",
    },
    "raw_totals_claims": {
        "row_count": 13_549, "column_count": 14,
        "headers_sha256": "4bb8082bb1330343fc83542d327fd75d1e8ed76dc4cd2d68204c1aa05e8011f1",
        "ordered_typed_sha256": "dbc07046439e7d9905f344efef3374a067ede52f521bc4cf58df94ff69524ffa",
        "multiset_typed_sha256": "53e208149f7e6ac29d1d97c45c01edc28cf5797d45a7b152874a75bab6e3fc3b",
    },
    "raw_description_separators": {
        "row_count": 3, "column_count": 15,
        "headers_sha256": "ea02f3c516d5459c5d3c60d317d665d0755497c145c7b23d684992a5c751d71c",
        "ordered_typed_sha256": "2c53f6a936899546483966392e9f930c79c44fd7eb99cbe0c7e0225f30ea8801",
        "multiset_typed_sha256": "c995d8152cdab41c2296b714556690740a11e13cd911e205cdb9a9d2fcac8a39",
    },
    "document_metadata": {
        "row_count": 12, "column_count": 9,
        "headers_sha256": "14aba2273880687d02690d055730d3eb1140fab5baf57e09bb81a74976e9e36b",
        "ordered_typed_sha256": "5e5665830b215c18c27334e50bcc38b35417ed1652075b323b89bff6f69cab2f",
        "multiset_typed_sha256": "7565ceb79bcd43d5bd2480f9f5c461347fe2bae3448dd8324bb53b9f85c151e7",
    },
    "projected": {
        "row_count": 60_083, "column_count": 32,
        "headers_sha256": "a5f0d57c56e3b087e4f958b0dc1a6346cae85e59af9b46dbd55944c2ada9054c",
        "ordered_typed_sha256": "d9cbec71742c6621721044d8836ea33da7dae73a40b2366b4a0d0d4202de45b4",
        "multiset_typed_sha256": "e5c62e5a785fb84011d8a7d37a2d1df1dc90e0daee5cdc7af83cb55c0ee81d89",
    },
}
EXPECTED_COLLISION_CENSUS = {
    "route_plus_printed_location": {
        "row_count": 60_083, "distinct_keys": 59_156,
        "duplicate_group_count": 798, "rows_in_duplicate_groups": 1_725,
        "max_multiplicity": 10,
        "multiplicity_histogram": {2: 728, 3: 51, 4: 6, 5: 3, 6: 3,
                                   7: 1, 8: 3, 9: 2, 10: 1},
        "ordered_key_sha256": "b67659c21eb03f06191be566b1fa94ef446b4e10374601ffe9f1ce6f26410b65",
        "multiset_key_sha256": "9f605c4f4da2a4e0d58e9033bd266ef4f33d157d9584b87e798224e509e1b05f",
    },
    "route_plus_printed_location_plus_roadbed": {
        "row_count": 60_083, "distinct_keys": 59_482,
        "duplicate_group_count": 508, "rows_in_duplicate_groups": 1_109,
        "max_multiplicity": 10,
        "multiplicity_histogram": {2: 471, 3: 19, 4: 6, 5: 3, 6: 2,
                                   7: 1, 8: 3, 9: 2, 10: 1},
        "ordered_key_sha256": "7124b786535dc76b048da59a28353c52741a65d815f6f03d1b2a586b53b1e912",
        "multiset_key_sha256": "6f407bd53a11e79d799fe9a0676c40a463f184c29d3619bfe41cfc7658920585",
    },
    "full_physical_owner_location_roadbed": {
        "row_count": 60_083, "distinct_keys": 60_004,
        "duplicate_group_count": 77, "rows_in_duplicate_groups": 156,
        "max_multiplicity": 4, "multiplicity_histogram": {2: 76, 4: 1},
        "ordered_key_sha256": "02ad55bad41cdf2528b397a0d6697be2fc7de4f5d47914d03e387cfef25c5f41",
        "multiset_key_sha256": "a72f003b5c32977a8e3c73abeb9e0321cc1135a36cf31197f8fd1155e38bd4b8",
    },
    "full_physical_occurrence_ordinal": {
        "row_count": 60_083, "distinct_keys": 60_083,
        "duplicate_group_count": 0, "rows_in_duplicate_groups": 0,
        "max_multiplicity": 1, "multiplicity_histogram": {},
        "ordered_key_sha256": "4ae7493d3418fd91fbaec6ddb2d9d389ede3c931dab3323c96a9c591d3f1f73a",
        "multiset_key_sha256": "be85caede2591df1133ce45d912d63b0e1f01f36fd4d7e3c0f1e74a3a2ce2b5e",
    },
}
EXPECTED_TOTAL_RECONCILIATION = {
    "claim_count": 13_549,
    "mileage_summary_count": 2_905,
    "mileage_total_equals_constructed_plus_unconstructed_count": 2_905,
    "mileage_arithmetic_failure_count": 0,
    "mileage_arithmetic_failure_manifest_sha256": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "volume_progression_assessable_interval_count": 5_451,
    "volume_progression_assessable_manifest_sha256": "3ea4666a3af31642d39f9fee2246facd7e32a3bbfc626fd1c8757a54f53fa555",
    "volume_progression_exact_interval_count": 4_675,
    "volume_progression_rounding_interval_count": 776,
    "volume_progression_accepted_interval_count": 5_451,
    "volume_progression_delta_histogram": {-1: 496, 0: 4_675, 1: 280},
    "volume_progression_failure_count": 0,
    "volume_progression_failure_manifest_sha256": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "volume_progression_rounding_manifest_sha256": "be371f638c2cc6aacb1547e91726e71e1a4c6a96bec16a9865ad48a49e3d0504",
    "volume_progression_reset_claim_count": 79,
    "volume_progression_reset_manifest_sha256": "17dba14eb3256bd081360ca965dc82cf8376eec8cb902edce4557f02238e0d65",
    "volume_progression_fragment_obscured_interval_count": 8,
    "volume_progression_fragment_obscured_manifest_sha256": "87825ca3922f11cb2f9e41154eac71841174aba43f5b7e38ed94cd7c19e68191",
    "mileage_to_dvms_pair_count": 2_905,
    "mileage_to_dvms_unpaired_summary_count": 0,
    "mileage_to_dvms_unpaired_summary_manifest_sha256": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "mileage_to_dvms_unassociated_continuation_count": 35,
    "mileage_to_dvms_unassociated_continuation_kind_counts": {
        "dvms_continuation": 27,
        "total_fragment:dvms_blank_or_overflow_fragment": 8,
    },
    "mileage_to_dvms_unassociated_continuation_manifest_sha256": "7cecd052f1f5ceb548ef9a64dfbe9f9baa8dfa954a817d6c4a81095a088fcc9e",
    "mileage_to_dvms_max_pending_depth": 1,
    "mileage_to_dvms_page_gap_histogram": {0: 2_873, 1: 28, 2: 4},
    "mileage_to_dvms_pair_manifest_sha256": "a5c6b54a44fd9d14d793b7888cfda9c5e4c7f37467123c4652582b79d2de57dc",
}

DOCUMENT_MANIFEST_FIELDS = (
    "member", "district", "page_count", "cover_text_sha256",
    "page_header_count", "page_header_manifest_sha256",
    "owner_header_count", "owner_header_manifest_sha256",
    "description_separator_count", "description_separator_manifest_sha256",
    "total_claim_count", "total_claim_manifest_sha256",
)
EXPECTED_DOCUMENT_MANIFESTS = (
    ("D01 Highway Log TSN.pdf", "01", 116, "ba12d62242fcef43796d05a88cb3ff7e363bcb8472c7a15fdb1ca56bbba8617c", 115, "67aa466e34f40c4abc9c3b606d5512e5b28f711a6104f10e3ccd2eda57d768c1", 120, "ab10ae97bd74beac64b4d0458d13593a87cc641b6ccabd1ce266664b3a4f7786", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 578, "8b4b275c65500c5a12be7a65f153fc178d1399444df2c79a88554d8da8ec43d9"),
    ("D02 Highway Log TSN.pdf", "02", 149, "6f06a4ef502480e381f33e7f06d980dfccc425c3af38949a62400bd0a63535b5", 148, "ced2b2d6800a21c65b1439f957244248ad175439a0888c08316ddbcfc402e09a", 166, "19de31cd5cf299c8c38069323fdf8116c4318bd5c368ddd620a3448c0a5f3c00", 1, "ab078d190954bf594b2437b977d0d4c33add82bb0916dba70b2fadd975014540", 734, "5a626a3862f1c24c02d8a46a74427d1c415d3577048e5d3d6591d9b772ec2da9"),
    ("D03 Highway Log TSN.pdf", "03", 205, "c25806af9f77a35ed74f543bf7169467858cff5f29561d115cbc402a4b81d3bf", 204, "7735240be3c89e78aad81860e4aa62f5d3a26fc9d0fef81975dee1de0f94c198", 253, "3166d96116bfb2db08cf45b1de9d169a612b0a9d12fade656e2af1ae85281826", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 1398, "a6e10cb403cc664156f8ed70c8cb9904ff595ec03a66b946b2024cfb41ff0161"),
    ("D04 Highway Log TSN.pdf", "04", 330, "7150d5796aabdb2a30e6e7ab1f839363227ba216938641951c0b38d911979eaa", 329, "8c4a38e6de4f839fe0825f4fa73401a73e4b1578da60a2bdf86accd22dc8f2d2", 384, "cf29fe4a1963b238fb632529f17738b62e3aa2b24a3554e3ce7c400bd1b836aa", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 2436, "9ed352e2ba0731bc5d0b4f48e8c4a75346124019e2e763ddb20e9993010bd019"),
    ("D05 Highway Log TSN.pdf", "05", 154, "42136792ab6daa4a0198427305cdf91ef1ab21df4950d806a7d94b39689637a7", 153, "6f8be16391fd5bd2f9b61514d3bcd5f426fafcd44dc56147580be63ae402286c", 194, "ede1cabe09b8e87fafeac6883bb5674ab4f25f89b1ff076e36c7a6036fc0babe", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 993, "c26775af1f3e47e90ccdb4df327a9f81d6182f860f2c4e7f5fda325a23e77820"),
    ("D06 Highway Log TSN.pdf", "06", 168, "f257ab5c2fa267478f750704690c57c9008e7730c095da5a633badaba60ab40a", 167, "8c7e8310f3a1df926b6930288be0dc33b3cd95c1813046b88e0783fa18fcf525", 196, "2d5cdb586d77b2086a935523da0be6d8a2f9e36c5f3396f82a3ca75b2d7101f7", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 1201, "23928538af2083c611567d75f58075b17e4a03103c851d4fdae33f2374b6bd87"),
    ("D07 Highway Log TSN.pdf", "07", 287, "20bf72a2360c99d405b9629dca20bf1673f300648ba34b3f551742d1109826e0", 286, "f7b49b0e194e0f99591075ebeacf8c146ac29cc69ad2af6b3b9e1d7f324621a6", 288, "713895b8e76f1266101bb5052ed7f6f16d2745f83116f2af581e21b5dd7e261a", 1, "2b72591e4535cc1c5c318147c8519b8207dee55f3a627fb28029b40a3ba0077e", 1887, "4bcb055fc09572727acc4ec72e33f812d2bffb5d82e5d8e09934b143c0c6f1a0"),
    ("D08 Highway Log TSN.pdf", "08", 217, "46989d018453bf648d78da84ea1ab70e6f172847943c3badf9d86880fdd85148", 216, "7dbbe81d8f2ae9f6345c2fcf83c898c5c8ef83962d79a361576692e3d0b85fed", 223, "d38fb0115c2502219a3794d37bb0e88e9c652267368fcfedb37550918c5b8f92", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 1215, "8f235fb394f129b053cfa5154ee4e71b337a63923786ad17237e6fad2ba933f1"),
    ("D09 Highway Log TSN.pdf", "09", 63, "dab5a8bd0c78000c917ecfed229b40442f3cbcc23a47e8df7458738068513376", 62, "988cd9d69fe573e83563289e9d7f5138ec2deb6c71f6104b7f0f1ea61e52cbbd", 66, "cda08502e098f68268811f8d67f5f606aea4b0976739f9ec0b781a30e4e86059", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 308, "9240ec7e9b7761c407cc749760c62c4614037286c64d096d3cb585fd65f7e711"),
    ("D10 Highway Log TSN.pdf", "10", 157, "e06a516dadf952a1bdaf5db5c0203a63e45cde03c877c69d366160c8f655f7a2", 156, "9fe236aaca80546fcf520580c653a9b5d0a5b8366f384d86cbfeb73accebe6ad", 190, "5074705a026a0923a75b61bbf2f9204deb9a932144ecdbd32ae391fe29557a17", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 1026, "780b055cfcb27f45814fa44ec106444da845ce07154158ce509e13afbfad84de"),
    ("D11 Highway Log TSN.pdf", "11", 179, "aff35ac890830201dfbf0078882e656d16eba091a58d62c93a637b3bb358f11b", 178, "395ea60d99b080bbb05b85a94dfbc341e9ebeb53ba6e42dab5423f290bf3d98a", 181, "6d5a3c98a0b4fa4cf61dc378d57b1d646712334a3be30beffd805e71bcdcf05e", 0, "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570", 1073, "08f491cf1bfdb11ec87242d2a392316c4adf11d2458c09085c8cde082e63fd71"),
    ("D12 Highway Log TSN.pdf", "12", 96, "28215e79dde2806087d71fb9acb7ef0e63fc725874ee18d51f4a196bd161e284", 95, "617269a2bdd0113e5fa0d63534dfd247c4600b561473f4bb484afff5153fd16c", 102, "833ab10d39baf74e7a0fcd0ed60c5296a6161396855768265189827346a01aaf", 1, "219b877258c04199fe2c3b43fb387d0550178956f0b97ad9bc21699596190f98", 700, "0eea7478e7ab24df1980fead26c91a38ad1786f7954b36620f9764bda7924fd8"),
)

STATIC_PAGE_HEADER = (
    "OTM52010",
    None,
    "Location and Distance S T Left Roadbed Median Right Roadbed ADT Information",
    "Length N Cnty R P E H A S # S OT-SH T-W IN-SH TCBWid S # S IN-SH T-W OT-SH Look P Look Date of Sig.",
    "Location MI A Odom City U D R G C T Lns F TO TR Wid TO TR YLA Var T Lns F TO TR Wid TO TR Back P Ahead Rec Chg.",
)


class ConservationError(ValueError):
    pass


class ConservationInvariantError(ConservationError):
    def __init__(self, failed: Sequence[str], diagnostic: dict[str, object]):
        self.failed = tuple(failed)
        self.diagnostic = diagnostic
        super().__init__(f"Stage-6 Highway Log invariants failed: {list(failed)}")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _typed(value: object) -> list[object]:
    if value is None:
        return ["null"]
    if type(value) is bool:
        return ["bool", value]
    if isinstance(value, Decimal):
        token = value.as_tuple()
        return ["decimal", token.sign, list(token.digits), token.exponent]
    if isinstance(value, datetime):
        return ["datetime", value.isoformat()]
    if isinstance(value, date):
        return ["date", value.isoformat()]
    if isinstance(value, int):
        return ["int", value]
    if isinstance(value, float):
        return ["float", value.hex()]
    if isinstance(value, str):
        return ["str", value]
    raise TypeError(f"unsupported typed value: {type(value).__name__}")


def _row_wire(row: Sequence[object]) -> bytes:
    return json.dumps([_typed(value) for value in row], ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _ordered_digest(rows: Iterable[Sequence[object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        wire = _row_wire(row)
        digest.update(len(wire).to_bytes(8, "big"))
        digest.update(wire)
    return digest.hexdigest()


def _multiset_digest(rows: Iterable[Sequence[object]]) -> tuple[str, Counter[str]]:
    counts = Counter(_sha(_row_wire(row)) for row in rows)
    digest = hashlib.sha256()
    for item, count in sorted(counts.items()):
        digest.update(f"{item}\t{count}\n".encode("ascii"))
    return digest.hexdigest(), counts


def _field_digest(values: Sequence[object]) -> dict[str, object]:
    rows = [(value,) for value in values]
    multiset, counts = _multiset_digest(rows)
    return {
        "ordered_typed_sha256": _ordered_digest(rows),
        "multiset_typed_sha256": multiset,
        "distinct_typed_values": len(counts),
        "type_counts": dict(sorted(Counter(_typed(v)[0] for v in values).items())),
        "null_count": sum(value is None for value in values),
        "empty_string_count": sum(value == "" for value in values),
    }


def _dataset_digests(headers: Sequence[str], rows: Sequence[Sequence[object]]) -> dict[str, object]:
    multiset, _counts = _multiset_digest(rows)
    return {
        "row_count": len(rows),
        "column_count": len(headers),
        "headers": list(headers),
        "headers_sha256": _sha(_json_bytes(list(headers))),
        "ordered_typed_sha256": _ordered_digest(rows),
        "multiset_typed_sha256": multiset,
        "fields": {
            header: _field_digest([row[index] for row in rows])
            for index, header in enumerate(headers)
        },
    }


def _dataset_contract(
    document: Mapping[str, object], expected: Mapping[str, object],
) -> dict[str, bool]:
    decisive = (
        "row_count", "column_count", "headers_sha256",
        "ordered_typed_sha256", "multiset_typed_sha256",
    )
    headers = document.get("headers")
    fields = document.get("fields")
    checks = {
        "schema_exact": set(document) == {
            "row_count", "column_count", "headers", "headers_sha256",
            "ordered_typed_sha256", "multiset_typed_sha256", "fields",
        },
        "expected_schema_exact": set(expected) == set(decisive),
        "headers_are_strings": isinstance(headers, list)
            and all(isinstance(header, str) for header in headers),
        "column_count_self_consistent": isinstance(headers, list)
            and document.get("column_count") == len(headers),
        "headers_digest_self_consistent": isinstance(headers, list)
            and document.get("headers_sha256") == _sha(_json_bytes(headers)),
        "field_universe_matches_headers": isinstance(headers, list)
            and isinstance(fields, Mapping)
            and set(fields) == set(headers) and len(fields) == len(headers),
    }
    checks.update({
        f"frozen_{key}_exact": document.get(key) == expected.get(key)
        for key in decisive
    })
    return checks


def _exact_frozen_subset(
    document: Mapping[str, object], expected: Mapping[str, object],
) -> dict[str, bool]:
    return {
        "all_expected_keys_present": set(expected) <= set(document),
        **{
            f"frozen_{key}_exact": document.get(key) == value
            for key, value in expected.items()
        },
    }


def _identity_dict(identity: FileIdentity) -> dict[str, object]:
    return asdict(identity)


def _stable_identity(identity: FileIdentity) -> dict[str, object]:
    return {
        "canonical_path": identity.canonical_path,
        "size": identity.size,
        "sha256": identity.sha256,
    }


def _require_identity(identity: FileIdentity, binding: Mapping[str, object], label: str) -> None:
    if identity.size != binding["bytes"] or identity.sha256 != binding["sha256"]:
        raise ConservationError(
            f"{label} binding mismatch: {identity.size}/{identity.sha256}"
        )


def _norm_route(token: str) -> str:
    match = re.fullmatch(r"(\d{1,3})([A-Za-z]?)", token.strip())
    if not match:
        raise ConservationError(f"invalid route token {token!r}")
    return match.group(1).zfill(3) + match.group(2).upper()


def _cluster_page_chars(page) -> list[dict[str, object]]:
    """Cluster nonblank glyphs with an independently implemented anchor-top rule."""
    chars = sorted(
        (dict(char) for char in page.chars if str(char.get("text", "")).strip()),
        key=lambda char: (float(char["top"]), float(char["x0"])),
    )
    clusters: list[list[dict[str, object]]] = []
    for char in chars:
        if (not clusters
                or abs(float(char["top"]) - float(clusters[-1][0]["top"])) > Y_TOLERANCE):
            clusters.append([char])
        else:
            clusters[-1].append(char)
    lines = []
    for cluster in clusters:
        cluster.sort(key=lambda char: float(char["x0"]))
        words: list[dict[str, object]] = []
        for char in cluster:
            if (not words
                    or float(char["x0"]) - float(words[-1]["x1"]) >= WORD_GAP):
                words.append({
                    "text": str(char["text"]),
                    "x0": float(char["x0"]),
                    "x1": float(char["x1"]),
                })
            else:
                words[-1]["text"] = str(words[-1]["text"]) + str(char["text"])
                words[-1]["x1"] = float(char["x1"])
        text = " ".join(str(word["text"]) for word in words)
        lines.append({
            "top": float(cluster[0]["top"]),
            "x0": float(words[0]["x0"]),
            "text": text,
            "words": words,
            "chars": cluster,
        })
    return lines


def _assign_columns(chars: Sequence[Mapping[str, object]]) -> tuple[dict[str, str | None], int]:
    values: dict[str, str] = {}
    last_x1: dict[str, float] = {}
    unassigned = 0
    for char in chars:
        center = (float(char["x0"]) + float(char["x1"])) / 2
        target = None
        for name, left, right in COLUMN_WINDOWS:
            if left <= center < right:
                target = name
                break
        if target is None:
            unassigned += 1
            continue
        if (target in values
                and float(char["x0"]) - last_x1[target] >= WORD_GAP):
            values[target] += " "
        values[target] = values.get(target, "") + str(char["text"])
        last_x1[target] = float(char["x1"])
    return ({name: values.get(name) or None for name in SOURCE_KEYS}, unassigned)


def _validate_pdf_metadata(metadata: Mapping[str, object], name: str,
                           claim: Mapping[str, str]) -> dict[str, str]:
    actual = {str(key): str(value) for key, value in sorted(metadata.items())}
    expected = {
        "Author": "Oracle Reports",
        "CreationDate": claim["creation_date"],
        "Creator": "Oracle12c AS Reports Services",
        "ModDate": claim["modification_date"],
        "Producer": "Oracle PDF driver",
        "Title": "otm52010.pdf",
    }
    if actual != expected:
        raise ConservationError(f"{name}: PDF metadata changed: {actual}")
    return actual


def _validate_cover(lines: Sequence[Mapping[str, object]], district: str,
                    name: str) -> dict[str, object]:
    expected = (
        "CALIFORNIA DEPARTMENT OF TRANSPORTATION",
        "California State Highway Log",
        "2025",
        f"District {district}",
    )
    actual = tuple(str(line["text"]) for line in lines)
    if actual != expected:
        raise ConservationError(f"{name}: exact cover claim changed: {actual}")
    return {
        "line_count": len(lines),
        "text_sha256": _sha("\n".join(actual).encode("utf-8")),
        "lines": list(actual),
    }


def _validate_page_header(lines: Sequence[Mapping[str, object]], physical_page: int,
                          name: str) -> dict[str, object]:
    header = [line for line in lines if float(line["top"]) < HEADER_BAND]
    expected = list(STATIC_PAGE_HEADER)
    expected[1] = (
        f"Date09/15/25 California State Highway Log Page {physical_page - 1}"
    )
    actual = [str(line["text"]) for line in header]
    if actual != expected:
        raise ConservationError(
            f"{name} p{physical_page}: exact five-line page header changed: {actual}"
        )
    return {
        "physical_page": physical_page,
        "printed_page": physical_page - 1,
        "line_count": len(header),
        "text_sha256": _sha("\n".join(actual).encode("utf-8")),
    }


def _decimal_miles(token: str) -> Decimal:
    return Decimal(token)


def _integer_count(token: str) -> int:
    return int(token.replace(",", ""))


def _fragment_numbers(text: str) -> list[object]:
    values: list[object] = []
    for token in NUMBER_OR_OVERFLOW_RE.findall(text):
        if set(token) == {"*"}:
            values.append({"overflow": token})
        elif "." in token:
            values.append(str(Decimal(token.replace(",", ""))))
        else:
            values.append(int(token.replace(",", "")))
    return values


def _parse_total(text: str, x0: float = 0.0) -> dict[str, object] | None:
    match = VOLUME_RE.fullmatch(text)
    if match:
        return {
            "kind": "volume_location",
            "length": str(_decimal_miles(match.group("length"))),
            "dvm": _integer_count(match.group("dvm")),
            "county_cumulative_dvm": _integer_count(match.group("cumulative")),
        }
    match = MILEAGE_RE.fullmatch(text)
    if match:
        total = _decimal_miles(match.group("total"))
        constructed = _decimal_miles(match.group("const"))
        unconstructed = _decimal_miles(match.group("unconst"))
        return {
            "kind": "mileage_summary",
            "label": match.group("label"),
            "total": str(total),
            "constructed": str(constructed),
            "unconstructed": str(unconstructed),
            "arithmetic_exact": total == constructed + unconstructed,
        }
    match = DVMS_RE.fullmatch(text)
    if match:
        return {"kind": "dvms_continuation", "dvms": _integer_count(match.group("dvms"))}
    match = WITHIN_DVMS_RE.fullmatch(text)
    if match:
        return {"kind": "route_dvms", "dvms": _integer_count(match.group("dvms"))}
    if END_REPORT_RE.fullmatch(text):
        return {"kind": "end_of_report"}
    upper = text.upper()
    fragment_class = None
    if text.startswith("*"):
        fragment_class = "starred_total_fragment"
    elif upper.startswith("(DVMS"):
        fragment_class = "dvms_blank_or_overflow_fragment"
    elif upper.startswith("(WITHIN DISTRICT)"):
        fragment_class = "route_dvms_blank_or_overflow_fragment"
    elif upper.startswith("CUMULATIVE"):
        fragment_class = "cumulative_mileage_fragment"
    elif upper.startswith("(MILEAGE)"):
        fragment_class = "mileage_continuation_fragment"
    elif upper.startswith("TOTAL"):
        fragment_class = "total_label_fragment"
    elif VOLUME_LENGTH_FRAGMENT_RE.fullmatch(text):
        fragment_class = "volume_length_fragment"
    elif upper.startswith("COUNTY CUMULATIVE DVM"):
        fragment_class = "county_cumulative_dvm_fragment"
    elif x0 > DESC_X0_MAX and NUMERIC_FRAGMENT_RE.fullmatch(text):
        fragment_class = "numeric_total_fragment"
    if fragment_class is not None:
        return {
            "kind": "total_fragment",
            "fragment_class": fragment_class,
            "typed_numeric_or_overflow_tokens": _fragment_numbers(text),
        }
    return None


def _total_candidate(text: str, x0: float = 0.0) -> bool:
    upper = text.upper()
    return (
        text.startswith("*")
        or upper.startswith("(DVM")
        or upper.startswith("(WITHIN DISTRICT)")
        or upper.startswith("CUMULATIVE")
        or upper.startswith("(MILEAGE)")
        or upper.startswith("TOTAL")
        or VOLUME_LENGTH_FRAGMENT_RE.fullmatch(text) is not None
        or upper.startswith("COUNTY CUMULATIVE DVM")
        or " TOTALS " in f" {upper} "
        or "END OF REPORT" in upper
        or (x0 > DESC_X0_MAX and NUMERIC_FRAGMENT_RE.fullmatch(text) is not None)
    )


def _classify_raw_names(names: Sequence[str]) -> tuple[list[str], str]:
    expected_sources = [name for name, _size, _digest, _pages in RAW_BINDINGS]
    expected_all = sorted([*expected_sources, NON_SOURCE_BINDING[0]])
    actual = sorted(names)
    if actual != expected_all:
        raise ConservationError(
            f"raw role universe changed: expected {expected_all}, got {actual}"
        )
    return expected_sources, NON_SOURCE_BINDING[0]


def _capture_raw() -> tuple[list[dict[str, object]], dict[str, bytes], dict[str, object]]:
    actual_names = [path.name for path in RAW_DIR.iterdir() if path.is_file()]
    source_names, non_source_name = _classify_raw_names(actual_names)
    identities = []
    payloads: dict[str, bytes] = {}
    for name, size, digest, _pages in RAW_BINDINGS:
        if name not in source_names:
            raise ConservationError(f"bound source role missing: {name}")
        captured = capture_file_bytes(RAW_DIR / name, max_bytes=size)
        _require_identity(captured.identity, {"bytes": size, "sha256": digest}, name)
        identities.append(_identity_dict(captured.identity))
        payloads[name] = captured.payload
    non_source = capture_file_identity(RAW_DIR / non_source_name)
    _require_identity(
        non_source,
        {"bytes": NON_SOURCE_BINDING[1], "sha256": NON_SOURCE_BINDING[2]},
        non_source_name,
    )
    if sum(int(identity["size"]) for identity in identities) != EXPECTED["raw_bytes"]:
        raise ConservationError("raw source byte total changed")
    return identities, payloads, _identity_dict(non_source)


def _parse_document(name: str, payload: bytes, expected_pages: int) -> tuple[list[dict[str, object]], dict[str, object]]:
    claim = DOCUMENT_CLAIM_BINDINGS.get(name)
    if claim is None:
        raise ConservationError(f"{name}: document claim binding missing")
    district = claim["district"]
    records: list[dict[str, object]] = []
    totals: list[dict[str, object]] = []
    description_separators: list[dict[str, object]] = []
    owner_headers: list[dict[str, object]] = []
    page_headers: list[dict[str, object]] = []
    line_counts: Counter[str] = Counter()
    unclassified: list[dict[str, object]] = []
    unparsed_totals: list[dict[str, object]] = []
    route: str | None = None
    route_qualifier: str | None = None
    county: str | None = None
    owner_occurrence = 0
    last_record: dict[str, object] | None = None
    sequence = 0

    with pdfplumber.open(io.BytesIO(payload)) as pdf:
        metadata = _validate_pdf_metadata(pdf.metadata or {}, name, claim)
        if len(pdf.pages) != expected_pages:
            raise ConservationError(
                f"{name}: expected {expected_pages} pages, got {len(pdf.pages)}"
            )
        cover_lines = _cluster_page_chars(pdf.pages[0])
        cover = _validate_cover(cover_lines, district, name)
        line_counts["cover"] += len(cover_lines)
        expected_line_total = len(cover_lines)
        first_box = (
            float(pdf.pages[0].width), float(pdf.pages[0].height),
            int(pdf.pages[0].rotation or 0),
        )
        if first_box != (612.0, 792.0, 0):
            raise ConservationError(f"{name}: page geometry changed: {first_box}")

        for physical_page, page in enumerate(pdf.pages[1:], 2):
            if (float(page.width), float(page.height), int(page.rotation or 0)) != first_box:
                raise ConservationError(f"{name} p{physical_page}: page geometry drift")
            lines = _cluster_page_chars(page)
            expected_line_total += len(lines)
            page_header = _validate_page_header(lines, physical_page, name)
            page_headers.append(page_header)
            line_counts["page_header"] += page_header["line_count"]

            for line_number, line in enumerate(lines, 1):
                if float(line["top"]) < HEADER_BAND:
                    continue
                text = str(line["text"])
                words = line["words"]
                provenance = {
                    "member": name,
                    "district": district,
                    "county": county,
                    "route": route,
                    "route_qualifier": route_qualifier,
                    "owner_occurrence": owner_occurrence,
                    "physical_page": physical_page,
                    "printed_page": physical_page - 1,
                    "line": line_number,
                    "top": format(float(line["top"]), ".3f"),
                    "x0": format(float(line["x0"]), ".3f"),
                    "raw_text": text,
                }

                group = GROUP_RE.fullmatch(text)
                if group and 250.0 <= float(line["x0"]) <= 305.0:
                    owner_district = group.group(1)
                    if owner_district != district:
                        raise ConservationError(
                            f"{name} p{physical_page}: owner district {owner_district}"
                        )
                    county = group.group(2)
                    route = _norm_route(group.group(3))
                    route_qualifier = group.group(4)
                    owner_occurrence += 1
                    last_record = None
                    owner_headers.append({
                        **provenance,
                        "county": county,
                        "route": route,
                        "route_qualifier": route_qualifier,
                        "owner_occurrence": owner_occurrence,
                    })
                    line_counts["owner_header"] += 1
                    continue
                if (250.0 <= float(line["x0"]) <= 305.0
                        and GROUP_LIKE_RE.match(text)):
                    raise ConservationError(
                        f"{name} p{physical_page}: malformed owner header {text!r}"
                    )

                first_text = str(words[0]["text"])
                if LOCATION_RE.fullmatch(first_text) and float(line["x0"]) < 50.0:
                    if route is None or county is None:
                        raise ConservationError(
                            f"{name} p{physical_page}: data precedes exact owner"
                        )
                    fields, unassigned = _assign_columns(line["chars"])
                    if unassigned:
                        raise ConservationError(
                            f"{name} p{physical_page}: {unassigned} data glyphs unassigned"
                        )
                    if fields["location"] != first_text:
                        raise ConservationError(
                            f"{name} p{physical_page}: location assignment differs from classifier"
                        )
                    sequence += 1
                    record = {
                        **provenance,
                        "county": county,
                        "route": route,
                        "route_qualifier": route_qualifier,
                        "sequence": sequence,
                        "fields": fields,
                        "description_lines": [],
                        "description": None,
                        "production_description": None,
                    }
                    records.append(record)
                    last_record = record
                    line_counts["data"] += 1
                    continue

                if DESCRIPTION_SEPARATOR_RE.fullmatch(text):
                    if (
                        last_record is None
                        or not (DESC_X0_MIN <= float(line["x0"]) <= DESC_X0_MAX)
                    ):
                        raise ConservationError(
                            f"{name} p{physical_page}: orphan/moved Description "
                            f"separator {text!r}"
                        )
                    description_separators.append({
                        **provenance,
                        "record_sequence": last_record["sequence"],
                        "record_location": last_record["fields"]["location"],
                        "normalized_disposition": "blank",
                    })
                    line_counts["description_separator"] += 1
                    continue

                parsed_total = _parse_total(text, float(line["x0"]))
                if parsed_total is not None or _total_candidate(text, float(line["x0"])):
                    claim_row = {**provenance, **(parsed_total or {"kind": "unparsed_total"})}
                    totals.append(claim_row)
                    if parsed_total is None:
                        unparsed_totals.append(claim_row)
                    last_record = None
                    line_counts["total"] += 1
                    continue

                if (last_record is not None
                        and DESC_X0_MIN <= float(line["x0"]) <= DESC_X0_MAX):
                    last_record["description_lines"].append(text)
                    last_record["description"] = " ".join(last_record["description_lines"])
                    last_record["production_description"] = ", ".join(
                        last_record["description_lines"]
                    )
                    line_counts["description"] += 1
                    continue

                unclassified.append(provenance)
                line_counts["unclassified"] += 1

        total_lines = sum(line_counts.values())
        if total_lines != expected_line_total:
            raise ConservationError(
                f"{name}: line-accounting mismatch {total_lines}/{expected_line_total}"
            )

    return records, {
        "member": name,
        "district": district,
        "page_count": expected_pages,
        "page_geometry": {"width": 612, "height": 792, "rotation": 0},
        "pdf_metadata": metadata,
        "cover": cover,
        "page_header_count": len(page_headers),
        "page_header_manifest_sha256": _sha(_json_bytes(page_headers)),
        "page_headers": page_headers,
        "owner_header_count": len(owner_headers),
        "owner_header_manifest_sha256": _sha(_json_bytes(owner_headers)),
        "owner_headers": owner_headers,
        "description_separator_count": len(description_separators),
        "description_separator_manifest_sha256": _sha(
            _json_bytes(description_separators)
        ),
        "description_separators": description_separators,
        "total_claim_count": len(totals),
        "total_claim_manifest_sha256": _sha(_json_bytes(totals)),
        "totals": totals,
        "line_classification": dict(sorted(line_counts.items())),
        "unparsed_totals": unparsed_totals,
        "unclassified_lines": unclassified,
    }


def _source_row(record: Mapping[str, object]) -> tuple[object, ...]:
    fields = record["fields"]
    return (
        record["district"], record["county"], record["route"],
        record["route_qualifier"],
        record["owner_occurrence"],
        *(fields[key] for key in SOURCE_KEYS), record["description"],
    )


def _sorted_records(records: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        records,
        key=lambda record: (
            str(record["district"]), str(record["route"]), int(record["sequence"]),
        ),
    )


def _roadbed_role(record: Mapping[str, object]) -> str:
    fields = record["fields"]
    left = sum(
        bool(PLUS_RE.fullmatch(str(fields[key] or "")))
        for key in ("lb_t", "lb_lns", "lb_f", "lb_ot", "lb_tr", "lb_tw", "lb_in", "lb_sh")
    )
    right = sum(
        bool(PLUS_RE.fullmatch(str(fields[key] or "")))
        for key in ("rb_t", "rb_lns", "rb_f", "rb_in", "rb_sh", "rb_tw", "rb_ot", "rb_sh2")
    )
    if left and not right:
        return "R"
    if right and not left:
        return "L"
    return "combined"


def _location_class(location: object) -> str:
    text = str(location or "")
    if text.endswith("E"):
        return "equation_suffix"
    if text[:1].isalpha():
        return "leading_prefix"
    return "plain"


def _collision_summary(keys: Sequence[tuple[object, ...]]) -> dict[str, object]:
    counts = Counter(keys)
    collisions = {key: count for key, count in counts.items() if count > 1}
    return {
        "row_count": len(keys),
        "distinct_keys": len(counts),
        "duplicate_group_count": len(collisions),
        "rows_in_duplicate_groups": sum(collisions.values()),
        "max_multiplicity": max(collisions.values(), default=1),
        "multiplicity_histogram": dict(sorted(Counter(collisions.values()).items())),
        "ordered_key_sha256": _ordered_digest(keys),
        "multiset_key_sha256": _multiset_digest(keys)[0],
    }


def _collision_census_exact(census: Mapping[str, object]) -> bool:
    return census == EXPECTED_COLLISION_CENSUS


def _normalize_source_value(key: str, value: object) -> object:
    if value is None:
        return None
    text = str(value)
    if key == "mi":
        match = re.fullmatch(r"(\d+)\.(\d+)", text)
        if match:
            return f"{int(match.group(1)):03d}.{match.group(2)}"
    if key in {"lb_tw", "rb_tw"} and re.fullmatch(r"\d{3,}", text):
        return text.lstrip("0").rjust(2, "0")
    return value


def _project_record(record: Mapping[str, object], *, production_join: bool = False) -> tuple[object, ...]:
    fields = record["fields"]
    values: list[object] = [record["route"]]
    for key in PROJECTED_KEYS:
        if key == "description":
            value = (
                record["production_description"]
                if production_join else record["description"]
            )
        else:
            value = fields[key]
        values.append(_normalize_source_value(key, value))
    return tuple(values)


def _compare_projection(expected: Sequence[Sequence[object]], actual_rows) -> dict[str, object]:
    actual = [row.values for row in actual_rows]
    mismatches: list[dict[str, object]] = []
    for ordinal, (left, right) in enumerate(zip(expected, actual)):
        for column, (expected_value, actual_value) in enumerate(zip(left, right)):
            if _typed(expected_value) != _typed(actual_value):
                mismatches.append({
                    "ordinal": ordinal,
                    "normalized_source_row": actual_rows[ordinal].source_row,
                    "field": HEADERS[column],
                    "expected": _typed(expected_value),
                    "actual": _typed(actual_value),
                })
    missing_or_extra = abs(len(expected) - len(actual))
    expected_multiset, _ = _multiset_digest(expected)
    actual_multiset, _ = _multiset_digest(actual)
    return {
        "expected_rows": len(expected),
        "actual_rows": len(actual),
        "missing_or_extra_row_count": missing_or_extra,
        "typed_cell_mismatch_count": len(mismatches),
        "typed_cell_mismatches_by_field": dict(sorted(Counter(
            item["field"] for item in mismatches
        ).items())),
        "mismatches": mismatches,
        "ordered_exact": not missing_or_extra and not mismatches,
        "multiset_exact": expected_multiset == actual_multiset,
        "expected_ordered_sha256": _ordered_digest(expected),
        "actual_ordered_sha256": _ordered_digest(actual),
        "expected_multiset_sha256": expected_multiset,
        "actual_multiset_sha256": actual_multiset,
    }


def _classify_projection_residue(projection: Mapping[str, object],
                                 records: Sequence[Mapping[str, object]]) -> dict[str, object]:
    punctuation = []
    unexplained = []
    for mismatch in projection["mismatches"]:
        ordinal = int(mismatch["ordinal"])
        record = records[ordinal]
        production = _normalize_source_value(
            "description", record["production_description"]
        )
        if (
            mismatch["field"] == "Description"
            and len(record["description_lines"]) > 1
            and mismatch["expected"] == _typed(record["description"])
            and mismatch["actual"] == _typed(production)
        ):
            punctuation.append({
                **mismatch,
                "member": record["member"],
                "district": record["district"],
                "county": record["county"],
                "route": record["route"],
                "route_qualifier": record["route_qualifier"],
                "location": record["fields"]["location"],
                "physical_page": record["physical_page"],
                "printed_page": record["printed_page"],
                "source_line": record["line"],
                "source_description_lines": list(record["description_lines"]),
                "whitespace_join": record["description"],
                "normalized_comma_join": record["production_description"],
            })
        else:
            unexplained.append(mismatch)
    return {
        "invented_description_comma": {
            "count": len(punctuation),
            "manifest_sha256": _sha(_json_bytes(punctuation)),
            "manifest": punctuation,
        },
        "unexplained": unexplained,
        "unexplained_count": len(unexplained)
            + int(projection["missing_or_extra_row_count"]),
    }


def _disposition(kind: str, targets: Sequence[str], role: str) -> dict[str, object]:
    return {"kind": kind, "normalized_targets": list(targets), "role": role}


RAW_ROLE_UNIVERSE = frozenset({
    "DISTRICT_OWNER", "COUNTY_OWNER", "ROUTE_OWNER", "ROUTE_OWNER_QUALIFIER",
    "OWNER_OCCURRENCE", "LOCATION", "MI", "NA", "CNTY_ODOM", "CITY", "RU",
    "SPD", "TER", "HG", "AC", "LB_T", "LB_LNS", "LB_F", "LB_OT", "LB_TR",
    "LB_TW", "LB_IN", "LB_SH", "MED_TCB", "MED_WID", "RB_T", "RB_LNS",
    "RB_F", "RB_IN", "RB_SH", "RB_TW", "RB_OT", "RB_SH2", "ADT_BACK",
    "ADT_PP", "ADT_AHEAD", "DESCRIPTION", "DESCRIPTION_SEPARATOR", "REC", "SIG",
    "MEMBER", "PHYSICAL_PAGE", "PRINTED_PAGE", "LINE_TOP_X", "RAW_TEXT",
    "TOTALS", "COVER", "PAGE_HEADER", "PDF_METADATA", "PAGE_GEOMETRY",
})


FIELD_DISPOSITIONS = {
    "DISTRICT_OWNER": _disposition("identity_source_only", (), "exact printed district owner"),
    "COUNTY_OWNER": _disposition("identity_source_only", (), "exact printed county owner"),
    "ROUTE_OWNER": _disposition("projected", ("Route",), "base route repeated on each normalized row"),
    "ROUTE_OWNER_QUALIFIER": _disposition("identity_source_only", (), "separately printed owner qualifier; semantics not inferred"),
    "OWNER_OCCURRENCE": _disposition("audit_provenance", (), "one-based physical owner-header occurrence within the source member"),
    "LOCATION": _disposition("projected", ("Location",), "complete printed Location token"),
    "MI": _disposition("normalized", ("Length (MI) [MI]",), "integer part zero-padded to three digits"),
    "NA": _disposition("projected", ("NA [N/A]",), "non-add mileage marker"),
    "CNTY_ODOM": _disposition("projected", ("Cnty Odom",), "county odometer"),
    "CITY": _disposition("projected", ("City",), "printed city code"),
    "RU": _disposition("projected", ("RU [R/U]",), "rural/urban code"),
    "SPD": _disposition("projected", ("SPD",), "printed design speed"),
    "TER": _disposition("projected", ("TER",), "printed terrain code"),
    "HG": _disposition("projected", ("HG [H/G]",), "printed highway-group code"),
    "AC": _disposition("projected", ("AC [A/C]",), "printed access-control code"),
    "LB_T": _disposition("projected", ("LB ST [LB T]",), "left roadbed surface type"),
    "LB_LNS": _disposition("projected", ("LB # Lns [LB Lns]",), "left roadbed lane count"),
    "LB_F": _disposition("projected", ("LB SF [LB F]",), "left roadbed feature"),
    "LB_OT": _disposition("projected", ("LB OT-SH Total [LB OT]",), "left outside shoulder total"),
    "LB_TR": _disposition("projected", ("LB OT-SH Treated [LB TR]",), "left outside shoulder treated"),
    "LB_TW": _disposition("normalized", ("LB T-W Wid [LB T-W]",), "left traveled-way leading zeros stripped"),
    "LB_IN": _disposition("projected", ("LB IN-SH Total [LB IN]",), "left inside shoulder total"),
    "LB_SH": _disposition("projected", ("LB IN-SH Treated [LB SH]",), "left inside shoulder treated"),
    "MED_TCB": _disposition("projected", ("Med TY/CL/BA [Med TCB]",), "median type/curb/barrier"),
    "MED_WID": _disposition("projected", ("Med Wid/Var [Med Wid]",), "median width/variance"),
    "RB_T": _disposition("projected", ("RB ST [RB T]",), "right roadbed surface type"),
    "RB_LNS": _disposition("projected", ("RB # Lns [RB Lns]",), "right roadbed lane count"),
    "RB_F": _disposition("projected", ("RB SF [RB F]",), "right roadbed feature"),
    "RB_IN": _disposition("projected", ("RB IN-SH Total [RB IN]",), "right inside shoulder total"),
    "RB_SH": _disposition("projected", ("RB IN-SH Treated [RB SH]",), "right inside shoulder treated"),
    "RB_TW": _disposition("normalized", ("RB T-W Wid [RB T-W]",), "right traveled-way leading zeros stripped"),
    "RB_OT": _disposition("projected", ("RB OT-SH Total [RB OT]",), "right outside shoulder total"),
    "RB_SH2": _disposition("projected", ("RB OT-SH Treated [RB SH]",), "right outside shoulder treated"),
    "ADT_BACK": _disposition("source_only", (), "TSN Look Back ADT claim"),
    "ADT_PP": _disposition("source_only", (), "TSN ADT P/P flag"),
    "ADT_AHEAD": _disposition("source_only", (), "TSN Look Ahead ADT claim"),
    "DESCRIPTION": _disposition("projected", ("Description",), "exact single-baseline source Description or null in the authoritative corpus"),
    "DESCRIPTION_SEPARATOR": _disposition("normalized_blank_marker", ("Description",), "exact 23-hyphen printed marker maps to a null Description on its owning row"),
    "REC": _disposition("projected", ("Date of Rec",), "printed date of record"),
    "SIG": _disposition("projected", ("Sig Chg. Date",), "printed significant-change date"),
    "MEMBER": _disposition("audit_provenance", (), "owning exact PDF member"),
    "PHYSICAL_PAGE": _disposition("audit_provenance", (), "one-based physical PDF page"),
    "PRINTED_PAGE": _disposition("audit_provenance", (), "printed page number"),
    "LINE_TOP_X": _disposition("audit_provenance", (), "line ordinal and exact top/x0 coordinates"),
    "RAW_TEXT": _disposition("audit_provenance", (), "exact independently clustered source line"),
    "TOTALS": _disposition("aggregate_source_only", (), "typed volume/mileage/DVMS claims and page fragments"),
    "COVER": _disposition("structural_source_only", (), "exact district cover text"),
    "PAGE_HEADER": _disposition("structural_source_only", (), "exact report/date/title/printed-page header"),
    "PDF_METADATA": _disposition("structural_source_only", (), "exact Oracle metadata and timestamps"),
    "PAGE_GEOMETRY": _disposition("structural_source_only", (), "exact letter page box and rotation"),
}


def _field_coverage(dispositions: Mapping[str, object] = FIELD_DISPOSITIONS) -> dict[str, object]:
    expected = set(RAW_ROLE_UNIVERSE)
    allowed = {
        "projected", "normalized", "projected_with_defect", "source_only",
        "identity_source_only", "audit_provenance", "aggregate_source_only",
        "structural_source_only", "normalized_blank_marker",
    }
    errors = []
    targets: list[str] = []
    conditional_targets: list[str] = []
    for field, disposition in dispositions.items():
        if set(disposition) != {"kind", "normalized_targets", "role"}:
            errors.append(f"{field}: disposition keys")
        if disposition.get("kind") not in allowed:
            errors.append(f"{field}: disposition kind")
        declared_targets = disposition.get("normalized_targets")
        if not isinstance(declared_targets, list):
            errors.append(f"{field}: target type")
        elif disposition.get("kind") == "normalized_blank_marker":
            conditional_targets.extend(declared_targets)
        else:
            targets.extend(declared_targets)
        if not disposition.get("role"):
            errors.append(f"{field}: role")
    target_counts = Counter(targets)
    return {
        "raw_role_count": len(expected),
        "declared_disposition_count": len(dispositions),
        "unexplained_raw_roles": sorted(expected - set(dispositions)),
        "extraneous_disposition_roles": sorted(set(dispositions) - expected),
        "unexplained_normalized_fields": sorted(set(HEADERS) - set(targets)),
        "conditional_normalized_targets": sorted(conditional_targets),
        "multiply_targeted_normalized_fields": sorted(
            target for target, count in target_counts.items() if count != 1
        ),
        "structure_errors": errors,
        "exact": (
            set(dispositions) == expected
            and target_counts == Counter({header: 1 for header in HEADERS})
            and Counter(conditional_targets) == Counter({"Description": 1})
            and not errors
        ),
    }


def _family_xlsx_limits() -> XlsxLimits:
    return XlsxLimits(
        max_source_bytes=16 * 1024 * 1024,
        max_xml_events=20_000_000,
    )


def _validate_sidecar(document: Mapping[str, object],
                      raw_members: Sequence[Mapping[str, object]]) -> dict[str, bool]:
    raw_manifest = document.get("tsn_raw_manifest")
    if not isinstance(raw_manifest, dict):
        raise ConservationError("sidecar raw manifest missing")
    expected_members = [
        {"relative_path": name, "byte_length": size, "sha256": digest}
        for name, size, digest, _pages in RAW_BINDINGS
    ]
    checks = {
        "root_schema": set(document) == {
            "schema_version", "completion", "skipped_inputs", "failed_inputs",
            "built_at_mtime", "tsn_normalization_version", "tsn_raw_manifest",
            "tsn_normalized_workbook_identity", "tsn_artifact_identity_token",
        },
        "schema_version": document.get("schema_version") == 1,
        "completion": document.get("completion") == "complete",
        "skipped_inputs": document.get("skipped_inputs") == 0,
        "failed_inputs": document.get("failed_inputs") == 0,
        "normalization_version": document.get("tsn_normalization_version") == 4,
        "built_at_type": type(document.get("built_at_mtime")) is float,
        "manifest_schema": set(raw_manifest) == {
            "version", "algorithm", "serialization", "root_scope", "member_count",
            "byte_length", "sha256", "members",
        },
        "manifest_header": (
            raw_manifest.get("version") == 1
            and raw_manifest.get("algorithm") == "sha256"
            and raw_manifest.get("serialization")
            == "relative_path\\tbyte_length\\tmember_sha256\\n"
            and raw_manifest.get("root_scope") == "report_raw_dir"
        ),
        "manifest_sha256": raw_manifest.get("sha256") == RAW_MANIFEST_SHA256,
        "manifest_members": raw_manifest.get("members") == expected_members,
        "manifest_count": raw_manifest.get("member_count") == EXPECTED["members"],
        "manifest_bytes": raw_manifest.get("byte_length") == EXPECTED["raw_bytes"],
        "normalized_identity": document.get("tsn_normalized_workbook_identity") == {
            "version": 1, "algorithm": "sha256",
            "byte_length": NORMALIZED_BINDING["bytes"],
            "sha256": NORMALIZED_BINDING["sha256"],
        },
        "artifact_identity_token": document.get("tsn_artifact_identity_token")
            == ARTIFACT_IDENTITY_TOKEN,
        "captured_raw_members": [
            [Path(str(item["canonical_path"])).name, item["size"], item["sha256"]]
            for item in raw_members
        ] == [[name, size, digest] for name, size, digest, _pages in RAW_BINDINGS],
    }
    if not all(checks.values()):
        raise ConservationError(f"sidecar contract failed: {checks}")
    return checks


def _accepted_terminal(value: object) -> bool:
    return type(value) is str and value == "complete"


def _validate_r7(document: Mapping[str, object]) -> dict[str, bool]:
    family = next((item for item in document.get("families") or []
                   if item.get("report") == "highway_log"), None)
    if not isinstance(family, dict):
        raise ConservationError("r7 Highway Log family missing")
    output = family.get("output") or {}
    result = family.get("result") or {}
    reuse = family.get("reuse") or {}
    sheets = output.get("sheets") or []
    primary = sheets[0] if sheets else {}
    legend = sheets[1] if len(sheets) > 1 else {}
    checks = {
        "run_accepted": _accepted_terminal(document.get("acceptance")),
        "seven_families": document.get("completed_family_count") == 7,
        "source_stable": document.get("source_universe_stable") is True,
        "code_stable": document.get("code_provenance_stable") is True,
        "family_complete": result.get("completion") == "complete",
        "family_zero_skipped": result.get("skipped_inputs") == 0,
        "family_zero_failed": result.get("failed_inputs") == 0,
        "builder_certificate": family.get("builder_certificate_matches") is True,
        "normalization_version": family.get("normalization_version") == 4,
        "output_identity": (
            output.get("bytes") == NORMALIZED_BINDING["bytes"]
            and output.get("sha256") == NORMALIZED_BINDING["sha256"]
        ),
        "sidecar_identity": output.get("sidecar_sha256") == SIDECAR_BINDING["sha256"],
        "primary_sheet": (
            primary.get("name") == SHEET_NAME
            and primary.get("header") == list(HEADERS)
            and primary.get("data_rows") == EXPECTED["projected_rows"]
            and primary.get("distinct_first_column_values") == EXPECTED["routes"]
        ),
        "legend_sheet": legend.get("name") == "Legend" and legend.get("data_rows") == 33,
        "reuse_certified": reuse.get("certified") is True,
        "reuse_unchanged": (
            reuse.get("output_unchanged") is True
            and reuse.get("sidecar_unchanged") is True
        ),
    }
    if not all(checks.values()):
        raise ConservationError(f"r7 lifecycle contract failed: {checks}")
    return checks


def _file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sample_roles(page_count: int) -> tuple[tuple[str, int], ...]:
    return (
        ("first", 1),
        ("middle", (page_count + 1) // 2),
        ("final", page_count),
    )


def _validate_visual_manifest(document: Mapping[str, object], *,
                              verify_files: bool = True) -> dict[str, object]:
    if set(document) != {
        "schema_version", "sample_complete", "dpi", "sample_count", "renderer",
        "non_source_role", "samples",
    }:
        raise ConservationError("visual manifest role universe changed")
    if not (
        document.get("schema_version") == 1
        and document.get("sample_complete") is True
        and document.get("dpi") == 120
        and document.get("sample_count") == 36
    ):
        raise ConservationError("visual manifest header claims changed")
    if document.get("renderer") != {
        "name": "pdftoppm.exe", "size": 50_176,
        "sha256": "742cbbd9a00931ad16c6618410bc40471375d639a45c61c1d86f3dcfc54b6388",
    }:
        raise ConservationError("visual renderer binding changed")
    if document.get("non_source_role") != {
        "name": NON_SOURCE_BINDING[0], "size": NON_SOURCE_BINDING[1],
        "sha256": NON_SOURCE_BINDING[2],
    }:
        raise ConservationError("visual non-source role binding changed")
    samples = document.get("samples")
    if not isinstance(samples, list) or len(samples) != 36:
        raise ConservationError("visual sample universe is not exactly 36 roles")
    expected = []
    for index, (name, size, digest, pages) in enumerate(RAW_BINDINGS, 1):
        for role, page in _sample_roles(pages):
            expected.append({
                "member": name,
                "source_size": size,
                "source_sha256": digest,
                "source_page_count": pages,
                "role": role,
                "physical_page": page,
                "output_name": f"d{index:02d}_p{page:03d}.png",
            })
    image_roles: defaultdict[str, list[str]] = defaultdict(list)
    for sample, expected_role in zip(samples, expected):
        if set(sample) != {
            "member", "source_size", "source_sha256", "source_page_count",
            "role", "physical_page", "output_name", "image_size", "image_sha256",
        }:
            raise ConservationError("visual sample member keys changed")
        if any(sample.get(key) != value for key, value in expected_role.items()):
            raise ConservationError(f"visual sample source/page role changed: {sample}")
        if not isinstance(sample.get("image_size"), int) or sample["image_size"] < 1:
            raise ConservationError("visual sample image size invalid")
        digest = sample.get("image_sha256")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ConservationError("visual sample image digest invalid")
        image_roles[str(sample["member"])].append(digest)
        if verify_files:
            path = VISUAL_MANIFEST.parent / str(sample["output_name"])
            if (
                not path.is_file()
                or path.stat().st_size != sample["image_size"]
                or _file_sha(path) != digest
            ):
                raise ConservationError(f"visual sample bytes changed: {path.name}")
    if any(len(set(digests)) != 3 for digests in image_roles.values()):
        raise ConservationError("same-document visual page roles alias")
    if verify_files:
        expected_files = {item["output_name"] for item in expected} | {"manifest.json"}
        actual_files = {path.name for path in VISUAL_MANIFEST.parent.iterdir() if path.is_file()}
        if actual_files != expected_files:
            raise ConservationError("visual output member universe changed")
    return {
        "exact": True,
        "sample_count": len(samples),
        "member_count": len(image_roles),
        "same_document_alias_count": 0,
        "sample_manifest_sha256": _sha(_json_bytes(samples)),
    }


def _run_gate(path: Path) -> dict[str, object]:
    before = capture_file_identity(path)
    completed = subprocess.run(
        [sys.executable, str(path)], cwd=REPO_ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", timeout=240,
    )
    after = capture_file_identity(path)
    if before != after or completed.returncode != 0:
        raise ConservationError(
            f"gate failed or changed: {path.name}: {completed.stdout[-2000:]}"
        )
    return {
        "path": str(path),
        "identity": _identity_dict(after),
        "returncode": completed.returncode,
        "stdout_sha256": _sha(completed.stdout.encode("utf-8")),
        "stdout_tail": completed.stdout.strip().splitlines()[-1:] or [],
    }


def _loaded_module_manifest() -> dict[str, object]:
    prefixes = ("pdfplumber", "pdfminer", "PIL", "pypdfium2")
    members = []
    for name, module in sorted(sys.modules.items()):
        if not name.startswith(prefixes):
            continue
        path_text = getattr(module, "__file__", None)
        if not path_text:
            continue
        path = Path(path_text)
        if path.suffix == ".pyc" and path.with_suffix(".py").is_file():
            path = path.with_suffix(".py")
        if not path.is_file():
            continue
        identity = capture_file_identity(path)
        members.append({"module": name, **_identity_dict(identity)})
    wire = [[item["module"], item["size"], item["sha256"]] for item in members]
    return {
        "member_count": len(members),
        "manifest_sha256": _sha(_json_bytes(wire)),
        "members": members,
    }


def _validate_parser_module_manifest(
    document: Mapping[str, object], *, verify_files: bool = True,
) -> dict[str, bool]:
    member_keys = {
        "module", "canonical_path", "size", "mtime_ns", "device", "inode",
        "sha256",
    }
    members = document.get("members")
    member_list = members if isinstance(members, list) else []
    member_schema_exact = bool(member_list) and all(
        isinstance(member, Mapping) and set(member) == member_keys
        for member in member_list
    )
    names = [
        member.get("module") for member in member_list
        if isinstance(member, Mapping)
    ]
    names_valid = len(names) == len(member_list) and all(
        isinstance(name, str) for name in names
    )
    wire = [
        [member.get("module"), member.get("size"), member.get("sha256")]
        for member in member_list if isinstance(member, Mapping)
    ]
    current_identities_exact = True
    if verify_files and member_schema_exact:
        for member in member_list:
            try:
                current = _identity_dict(capture_file_identity(
                    Path(str(member["canonical_path"]))
                ))
            except (OSError, ValueError):
                current_identities_exact = False
                break
            recorded = {key: member[key] for key in member_keys if key != "module"}
            if current != recorded:
                current_identities_exact = False
                break
    elif verify_files:
        current_identities_exact = False
    checks = {
        "root_schema_exact": set(document) == {
            "member_count", "manifest_sha256", "members",
        },
        "member_schema_exact": member_schema_exact,
        "declared_member_count_self_consistent":
            document.get("member_count") == len(member_list),
        "member_names_sorted_unique": names_valid
            and names == sorted(names) and len(set(names)) == len(names),
        "module_prefix_universe_exact": names_valid and all(
            name.startswith(("pdfplumber", "pdfminer", "PIL", "pypdfium2"))
            for name in names
        ),
        "manifest_digest_self_consistent": len(wire) == len(member_list)
            and document.get("manifest_sha256") == _sha(_json_bytes(wire)),
        "frozen_member_count_exact": document.get("member_count")
            == EXPECTED_PARSER_MODULE_MANIFEST["member_count"],
        "frozen_manifest_digest_exact": document.get("manifest_sha256")
            == EXPECTED_PARSER_MODULE_MANIFEST["manifest_sha256"],
        "current_module_file_identities_exact": current_identities_exact,
    }
    return checks


def _xlsx_topology(path: Path) -> dict[str, object]:
    with zipfile.ZipFile(path, "r") as archive:
        workbook = archive.read("xl/workbook.xml")
        rels = archive.read("xl/_rels/workbook.xml.rels")
        sheet_names = re.findall(br'<sheet\s+name="([^"]+)"', workbook)
        formula_cells = 0
        error_cells = 0
        for name in archive.namelist():
            if name.startswith("xl/worksheets/") and name.endswith(".xml"):
                payload = archive.read(name)
                formula_cells += len(re.findall(br"<f(?:\s|>)", payload))
                error_cells += len(re.findall(br'<c[^>]*\bt="e"', payload))
    names = [name.decode("utf-8") for name in sheet_names]
    return {
        "workbook_xml_sha256": _sha(workbook),
        "workbook_relationships_sha256": _sha(rels),
        "sheet_names": names,
        "formula_cell_count": formula_cells,
        "error_cell_count": error_cells,
        "exact": names == ["Highway Log", "Legend"]
            and formula_cells == 0 and error_cells == 0,
    }


def _parse_payloads(payloads: Mapping[str, bytes]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    records = []
    documents = []
    for name, _size, _digest, pages in RAW_BINDINGS:
        print(f"PROGRESS parsing {name} ({pages} pages)", flush=True)
        parsed, document = _parse_document(name, payloads[name], pages)
        records.extend(parsed)
        documents.append(document)
        print(
            f"PROGRESS parsed {name}: {len(parsed)} data rows, "
            f"{document['total_claim_count']} totals, "
            f"{len(document['unclassified_lines'])} unclassified, "
            f"{len(document['unparsed_totals'])} unparsed totals",
            flush=True,
        )
    return _sorted_records(records), documents


def _document_manifest_snapshot(
    documents: Sequence[Mapping[str, object]],
) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            document["member"], document["district"], document["page_count"],
            document["cover"]["text_sha256"],
            document["page_header_count"],
            document["page_header_manifest_sha256"],
            document["owner_header_count"],
            document["owner_header_manifest_sha256"],
            document["description_separator_count"],
            document["description_separator_manifest_sha256"],
            document["total_claim_count"], document["total_claim_manifest_sha256"],
        )
        for document in documents
    )


def _document_manifests_exact(
    snapshot: Sequence[Sequence[object]],
) -> bool:
    return tuple(tuple(row) for row in snapshot) == EXPECTED_DOCUMENT_MANIFESTS


def _corpus_metrics(raw_identities: Sequence[Mapping[str, object]],
                    non_source: Mapping[str, object],
                    ordered: Sequence[dict[str, object]],
                    documents: Sequence[dict[str, object]]) -> dict[str, object]:
    total_claims = [item for document in documents for item in document["totals"]]
    description_separators = [
        item
        for document in documents
        for item in document["description_separators"]
    ]
    header_qualifiers = Counter(
        item["route_qualifier"]
        for document in documents for item in document["owner_headers"]
    )
    record_qualifiers = Counter(record["route_qualifier"] for record in ordered)
    ditto_domain = Counter(
        str(record["fields"][key])
        for record in ordered for key in SOURCE_KEYS
        if PLUS_RE.fullmatch(str(record["fields"][key] or ""))
    )
    roles = Counter(_roadbed_role(record) for record in ordered)
    locations = Counter(_location_class(record["fields"]["location"]) for record in ordered)
    description_line_counts = Counter(len(record["description_lines"]) for record in ordered)
    weak_keys = [
        (record["route"], record["fields"]["location"])
        for record in ordered
    ]
    roadbed_keys = [(*key, _roadbed_role(record)) for key, record in zip(weak_keys, ordered)]
    physical_keys = [
        (
            record["district"], record["county"], record["route"],
            record["route_qualifier"], record["fields"]["location"],
            _roadbed_role(record),
        )
        for record in ordered
    ]
    seen: Counter[tuple[object, ...]] = Counter()
    occurrence_keys = []
    for key in physical_keys:
        ordinal = seen[key]
        seen[key] += 1
        occurrence_keys.append((*key, ordinal))
    arithmetic_failures = [
        item for item in total_claims
        if item["kind"] == "mileage_summary" and not item["arithmetic_exact"]
    ]
    return {
        "raw_identities": raw_identities,
        "non_source": non_source,
        "record_count": len(ordered),
        "source_ordered_sha256": _ordered_digest([_source_row(record) for record in ordered]),
        "line_classification": dict(sorted(sum(
            (Counter(document["line_classification"]) for document in documents),
            Counter(),
        ).items())),
        "unclassified_lines": [
            item for document in documents for item in document["unclassified_lines"]
        ],
        "unparsed_totals": [
            item for document in documents for item in document["unparsed_totals"]
        ],
        "total_kinds": dict(sorted(Counter(
            item["kind"] for item in total_claims
        ).items())),
        "total_fragment_classes": dict(sorted(Counter(
            item.get("fragment_class") for item in total_claims
            if item["kind"] == "total_fragment"
        ).items())),
        "description_separators": {
            "count": len(description_separators),
            "manifest_sha256": _sha(_json_bytes(description_separators)),
            "manifest": description_separators,
        },
        "mileage_arithmetic_failure_count": len(arithmetic_failures),
        "mileage_arithmetic_failure_examples": arithmetic_failures[:20],
        "route_counts": {
            "statewide_routes": len({record["route"] for record in ordered}),
            "district_route_owners": len({
                (record["district"], record["route"]) for record in ordered
            }),
            "district_county_route_qualifier_owners": len({
                (record["district"], record["county"], record["route"],
                 record["route_qualifier"])
                for record in ordered
            }),
            "counties": len({record["county"] for record in ordered}),
        },
        "rows_by_district": dict(sorted(Counter(
            record["district"] for record in ordered
        ).items())),
        "route_qualifiers": {
            "record_counts": {str(key): value for key, value in sorted(
                record_qualifiers.items(), key=lambda item: str(item[0]))
            },
            "owner_header_counts": {str(key): value for key, value in sorted(
                header_qualifiers.items(), key=lambda item: str(item[0]))
            },
        },
        "owner_occurrences": {
            "count": sum(len(document["owner_headers"]) for document in documents),
            "record_counts_by_occurrence": {
                f"{member}#{occurrence}": count
                for (member, occurrence), count in sorted(Counter(
                    (record["member"], record["owner_occurrence"])
                    for record in ordered
                ).items())
            },
        },
        "ditto_domain": dict(sorted(ditto_domain.items())),
        "ditto_cell_count": sum(ditto_domain.values()),
        "roadbed_roles": dict(sorted(roles.items())),
        "location_classes": dict(sorted(locations.items())),
        "description_line_multiplicity": {
            "histogram": dict(sorted(description_line_counts.items())),
            "records_with_multiple_lines": sum(
                count for lines, count in description_line_counts.items() if lines > 1
            ),
            "max_lines": max(description_line_counts, default=0),
        },
        "adt_fields": {
            key: _field_digest([record["fields"][key] for record in ordered])
            for key in ("adt_back", "adt_pp", "adt_ahead")
        },
        "identity_and_collision_census": {
            "route_plus_printed_location": _collision_summary(weak_keys),
            "route_plus_printed_location_plus_roadbed": _collision_summary(roadbed_keys),
            "full_physical_owner_location_roadbed": _collision_summary(physical_keys),
            "full_physical_occurrence_ordinal": _collision_summary(occurrence_keys),
        },
        "documents": documents,
    }


def _probe() -> dict[str, object]:
    raw_identities, payloads, non_source = _capture_raw()
    ordered, documents = _parse_payloads(payloads)
    return _corpus_metrics(raw_identities, non_source, ordered, documents)


def _normalized_spec() -> SheetSpec:
    return SheetSpec(
        SHEET_NAME,
        tuple(ColumnSpec(header) for header in HEADERS),
        exact_schema=True,
    )


def _prove_default_xlsx_limit_rejects() -> dict[str, object]:
    try:
        read_sheet(
            NORMALIZED_XLSX,
            _normalized_spec(),
            limits=XlsxLimits(max_source_bytes=16 * 1024 * 1024),
        )
    except XlsxSecurityError as exc:
        message = str(exc)
        if message != "XLSX XML exceeds the event limit":
            raise ConservationError(
                f"default-limit rejection changed: {type(exc).__name__}: {message}"
            ) from exc
        return {
            "rejected": True,
            "exception": type(exc).__name__,
            "message": message,
            "default_max_xml_events": XlsxLimits().max_xml_events,
        }
    raise ConservationError("default XLSX XML-event limit unexpectedly admitted Highway Log")


def _total_claim_rows(documents: Sequence[Mapping[str, object]]) -> tuple[list[tuple[object, ...]], tuple[str, ...]]:
    headers = (
        "Member", "District", "County", "Route", "Route Qualifier",
        "Owner Occurrence",
        "Physical Page", "Printed Page", "Line", "Top", "X0", "Kind",
        "Raw Text", "Parsed Claim JSON",
    )
    rows = []
    provenance = {
        "member", "district", "county", "route", "route_qualifier",
        "owner_occurrence", "physical_page", "printed_page", "line", "top", "x0",
        "raw_text",
    }
    for document in documents:
        for claim in document["totals"]:
            parsed = {key: value for key, value in claim.items() if key not in provenance}
            rows.append((
                claim["member"], claim["district"], claim["county"], claim["route"],
                claim["route_qualifier"], claim["owner_occurrence"],
                claim["physical_page"],
                claim["printed_page"], claim["line"], claim["top"], claim["x0"],
                claim["kind"], claim["raw_text"],
                json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            ))
    return rows, headers


def _description_separator_rows(
    documents: Sequence[Mapping[str, object]],
) -> tuple[list[tuple[object, ...]], tuple[str, ...]]:
    headers = (
        "Member", "District", "County", "Route", "Route Qualifier",
        "Owner Occurrence", "Record Sequence", "Record Location",
        "Physical Page", "Printed Page", "Line", "Top", "X0", "Raw Text",
        "Normalized Disposition",
    )
    rows = []
    for document in documents:
        for marker in document["description_separators"]:
            rows.append((
                marker["member"], marker["district"], marker["county"],
                marker["route"], marker["route_qualifier"],
                marker["owner_occurrence"], marker["record_sequence"],
                marker["record_location"], marker["physical_page"],
                marker["printed_page"], marker["line"], marker["top"],
                marker["x0"], marker["raw_text"],
                marker["normalized_disposition"],
            ))
    return rows, headers


def _reconcile_totals(documents: Sequence[Mapping[str, object]]) -> dict[str, object]:
    claims = [claim for document in documents for claim in document["totals"]]
    kinds = Counter(claim["kind"] for claim in claims)
    fragment_classes = Counter(
        claim["fragment_class"] for claim in claims if claim["kind"] == "total_fragment"
    )
    mileage = [claim for claim in claims if claim["kind"] == "mileage_summary"]
    mileage_failures = [claim for claim in mileage if not claim["arithmetic_exact"]]

    # Reconcile only within a physical owner-header occurrence. Repeated printed
    # owner text is not proof of one cumulative sequence. A zero-DVM/zero-cumulative
    # claim is an explicit printed reset. Fragment-obscured intervals remain exact
    # source claims but are not guessed into arithmetic rows.
    prior: dict[tuple[object, ...], int] = {}
    obscured: set[tuple[object, ...]] = set()
    assessable = []
    obscured_intervals = []
    reset_claims = []
    for claim in claims:
        key = (claim["member"], claim["owner_occurrence"])
        if claim["kind"] == "total_fragment":
            if claim.get("fragment_class") in {
                "starred_total_fragment", "volume_length_fragment",
                "county_cumulative_dvm_fragment", "numeric_total_fragment",
            }:
                obscured.add(key)
            continue
        if claim["kind"] != "volume_location":
            continue
        current = int(claim["county_cumulative_dvm"])
        dvm = int(claim["dvm"])
        if current == 0 and dvm == 0:
            reset_claims.append({
                "member": claim["member"],
                "physical_page": claim["physical_page"],
                "line": claim["line"],
                "owner_occurrence": claim["owner_occurrence"],
                "owner": [claim["district"], claim["county"], claim["route"],
                          claim["route_qualifier"]],
                "previous_cumulative_dvm": prior.get(key),
                "printed_cumulative_dvm": current,
                "dvm": dvm,
            })
            prior[key] = 0
            obscured.discard(key)
            continue
        if key in prior and key not in obscured:
            delta = current - prior[key] - dvm
            assessable.append({
                "member": claim["member"], "physical_page": claim["physical_page"],
                "line": claim["line"],
                "owner_occurrence": claim["owner_occurrence"],
                "owner": [claim["district"], claim["county"], claim["route"],
                          claim["route_qualifier"]],
                "previous_cumulative_dvm": prior[key], "dvm": dvm,
                "printed_cumulative_dvm": current, "delta": delta,
                "classification": (
                    "exact" if delta == 0
                    else "printed_rounding" if delta in {-1, 1}
                    else "failure"
                ),
            })
        elif key in prior:
            obscured_intervals.append({
                "member": claim["member"], "physical_page": claim["physical_page"],
                "line": claim["line"],
                "owner_occurrence": claim["owner_occurrence"],
                "owner": [claim["district"], claim["county"], claim["route"],
                          claim["route_qualifier"]],
                "previous_complete_cumulative_dvm": prior[key],
                "next_complete_cumulative_dvm": current,
            })
        prior[key] = current
        obscured.discard(key)
    progression_failures = [
        item for item in assessable if item["classification"] == "failure"
    ]
    progression_rounding = [
        item for item in assessable if item["classification"] == "printed_rounding"
    ]

    dvms_pairs = []
    unpaired_summaries = []
    unassociated_continuations = []
    max_pending_depth = 0
    for document in documents:
        pending: deque[Mapping[str, object]] = deque()
        for claim in document["totals"]:
            if claim["kind"] == "mileage_summary":
                pending.append(claim)
                max_pending_depth = max(max_pending_depth, len(pending))
                continue
            eligible = claim["kind"] in {"dvms_continuation", "route_dvms"} or (
                claim["kind"] == "total_fragment"
                and claim.get("fragment_class") in {
                    "dvms_blank_or_overflow_fragment",
                    "route_dvms_blank_or_overflow_fragment",
                }
            )
            if not eligible:
                continue
            if not pending:
                unassociated_continuations.append(claim)
                continue
            summary = pending.popleft()
            dvms_pairs.append({
                "summary_member": summary["member"],
                "summary_page": summary["physical_page"],
                "summary_line": summary["line"],
                "summary_label": summary["label"],
                "summary_owner_occurrence": summary["owner_occurrence"],
                "continuation_page": claim["physical_page"],
                "continuation_line": claim["line"],
                "continuation_kind": claim["kind"],
                "continuation_fragment_class": claim.get("fragment_class"),
                "continuation_raw_text": claim["raw_text"],
                "page_gap": claim["physical_page"] - summary["physical_page"],
            })
        unpaired_summaries.extend(pending)
    progression_delta_histogram = dict(sorted(Counter(
        item["delta"] for item in assessable
    ).items()))
    return {
        "claim_count": len(claims),
        "kind_counts": dict(sorted(kinds.items())),
        "fragment_class_counts": dict(sorted(fragment_classes.items())),
        "mileage_summary_count": len(mileage),
        "mileage_total_equals_constructed_plus_unconstructed_count": (
            len(mileage) - len(mileage_failures)
        ),
        "mileage_arithmetic_failure_count": len(mileage_failures),
        "mileage_arithmetic_failures": mileage_failures,
        "mileage_arithmetic_failure_manifest_sha256": _sha(
            _json_bytes(mileage_failures)
        ),
        "volume_progression_assessable_interval_count": len(assessable),
        "volume_progression_assessable_manifest_sha256": _sha(
            _json_bytes(assessable)
        ),
        "volume_progression_exact_interval_count": (
            sum(item["classification"] == "exact" for item in assessable)
        ),
        "volume_progression_rounding_interval_count": len(progression_rounding),
        "volume_progression_accepted_interval_count": (
            len(assessable) - len(progression_failures)
        ),
        "volume_progression_delta_histogram": progression_delta_histogram,
        "volume_progression_failure_count": len(progression_failures),
        "volume_progression_failures": progression_failures,
        "volume_progression_failure_manifest_sha256": _sha(
            _json_bytes(progression_failures)
        ),
        "volume_progression_rounding_manifest_sha256": _sha(
            _json_bytes(progression_rounding)
        ),
        "volume_progression_reset_claim_count": len(reset_claims),
        "volume_progression_reset_manifest_sha256": _sha(
            _json_bytes(reset_claims)
        ),
        "volume_progression_reset_claims": reset_claims,
        "volume_progression_fragment_obscured_interval_count": len(obscured_intervals),
        "volume_progression_fragment_obscured_manifest_sha256": _sha(
            _json_bytes(obscured_intervals)
        ),
        "volume_progression_fragment_obscured_intervals": obscured_intervals,
        "mileage_to_dvms_pair_count": len(dvms_pairs),
        "mileage_to_dvms_unpaired_summary_count": len(unpaired_summaries),
        "mileage_to_dvms_unpaired_summary_manifest_sha256": _sha(
            _json_bytes(unpaired_summaries)
        ),
        "mileage_to_dvms_unpaired_summaries": unpaired_summaries,
        "mileage_to_dvms_unassociated_continuation_count": len(
            unassociated_continuations
        ),
        "mileage_to_dvms_unassociated_continuation_kind_counts": dict(sorted(
            Counter(
                claim["kind"] if claim["kind"] != "total_fragment"
                else f"total_fragment:{claim['fragment_class']}"
                for claim in unassociated_continuations
            ).items()
        )),
        "mileage_to_dvms_unassociated_continuation_manifest_sha256": _sha(
            _json_bytes(unassociated_continuations)
        ),
        "mileage_to_dvms_unassociated_continuations": unassociated_continuations,
        "mileage_to_dvms_max_pending_depth": max_pending_depth,
        "mileage_to_dvms_page_gap_histogram": dict(sorted(Counter(
            pair["page_gap"] for pair in dvms_pairs
        ).items())),
        "mileage_to_dvms_pair_manifest_sha256": _sha(_json_bytes(dvms_pairs)),
        "mileage_to_dvms_pairs": dvms_pairs,
    }


def _total_reconciliation_contract(
    reconciliation: Mapping[str, object],
) -> dict[str, bool]:
    return _exact_frozen_subset(
        reconciliation, EXPECTED_TOTAL_RECONCILIATION
    )


def _mutation_probes(source_rows: Sequence[Sequence[object]],
                     projected_rows: Sequence[Sequence[object]],
                     total_rows: Sequence[Sequence[object]],
                     separator_rows: Sequence[Sequence[object]],
                     metadata_rows: Sequence[Sequence[object]]) -> dict[str, object]:
    source_base = _ordered_digest(source_rows)
    projected_base = _ordered_digest(projected_rows)
    total_base = _ordered_digest(total_rows)
    separator_base = _ordered_digest(separator_rows)
    metadata_base = _ordered_digest(metadata_rows)
    probes: dict[str, bool] = {}
    for column, header in enumerate(SOURCE_HEADERS):
        changed = list(source_rows)
        row = list(changed[0])
        row[column] = f"MUTATED-{column}"
        changed[0] = tuple(row)
        probes[f"source_field_{header}"] = _ordered_digest(changed) != source_base
    probes["source_delete"] = _ordered_digest(source_rows[:-1]) != source_base
    probes["source_add"] = _ordered_digest([*source_rows, source_rows[-1]]) != source_base
    swapped = list(source_rows)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    probes["source_order"] = (
        _ordered_digest(swapped) != source_base
        and _multiset_digest(swapped)[0] == _multiset_digest(source_rows)[0]
    )
    changed_projected = list(projected_rows)
    projected_row = list(changed_projected[0]); projected_row[1] = "999.999"
    changed_projected[0] = tuple(projected_row)
    probes["projected_cell"] = _ordered_digest(changed_projected) != projected_base
    changed_totals = list(total_rows)
    total_row = list(changed_totals[0]); total_row[-2] = "MUTATED"
    changed_totals[0] = tuple(total_row)
    probes["total_claim"] = _ordered_digest(changed_totals) != total_base
    changed_separators = list(separator_rows)
    separator_row = list(changed_separators[0]); separator_row[-2] = "-" * 22
    changed_separators[0] = tuple(separator_row)
    probes["description_separator_change"] = (
        _ordered_digest(changed_separators) != separator_base
    )
    probes["description_separator_delete"] = (
        _ordered_digest(separator_rows[:-1]) != separator_base
    )
    probes["description_separator_add"] = (
        _ordered_digest([*separator_rows, separator_rows[-1]]) != separator_base
    )
    swapped_separators = list(separator_rows)
    swapped_separators[0], swapped_separators[1] = (
        swapped_separators[1], swapped_separators[0]
    )
    probes["description_separator_order"] = (
        _ordered_digest(swapped_separators) != separator_base
        and _multiset_digest(swapped_separators)[0]
        == _multiset_digest(separator_rows)[0]
    )
    changed_metadata = list(metadata_rows)
    metadata_row = list(changed_metadata[0]); metadata_row[-1] = "MUTATED"
    changed_metadata[0] = tuple(metadata_row)
    probes["metadata"] = _ordered_digest(changed_metadata) != metadata_base
    missing = deepcopy(FIELD_DISPOSITIONS); missing.pop("ADT_BACK")
    probes["disposition_missing"] = not _field_coverage(missing)["exact"]
    extra = deepcopy(FIELD_DISPOSITIONS)
    extra["INVENTED"] = _disposition("source_only", (), "mutation")
    probes["disposition_extra"] = not _field_coverage(extra)["exact"]
    duplicate = deepcopy(FIELD_DISPOSITIONS)
    duplicate["ADT_BACK"] = _disposition("source_only", ("Route",), "mutation")
    probes["disposition_duplicate_target"] = not _field_coverage(duplicate)["exact"]
    probes["lower_xlsx_event_limit_distinct"] = (
        XlsxLimits().max_xml_events < _family_xlsx_limits().max_xml_events
    )
    return {
        "probe_count": len(probes),
        "detected_count": sum(probes.values()),
        "all_detected": all(probes.values()),
        "probes": probes,
    }


def run() -> dict[str, object]:
    code_before = {
        "oracle": capture_file_identity(Path(__file__)),
        "family_gate": capture_file_identity(FAMILY_GATE),
        "reader": capture_file_identity(READER),
        "reader_gate": capture_file_identity(READER_GATE),
        "visual_sampler": capture_file_identity(VISUAL_SAMPLER),
    }
    modules_before = _loaded_module_manifest()
    modules_before_checks = _validate_parser_module_manifest(modules_before)
    reader_gate = _run_gate(READER_GATE)
    family_gate = _run_gate(FAMILY_GATE)

    visual_sampler_identity = code_before["visual_sampler"]
    _require_identity(visual_sampler_identity, VISUAL_SAMPLER_BINDING, "visual sampler")
    visual_capture = capture_file_bytes(
        VISUAL_MANIFEST, max_bytes=VISUAL_MANIFEST_BINDING["bytes"]
    )
    _require_identity(visual_capture.identity, VISUAL_MANIFEST_BINDING, "visual manifest")
    try:
        visual_document = json.loads(visual_capture.payload)
    except json.JSONDecodeError as exc:
        raise ConservationError("visual manifest JSON malformed") from exc
    visual_checks = _validate_visual_manifest(visual_document)

    default_limit_rejection = _prove_default_xlsx_limit_rejects()
    family_limits = _family_xlsx_limits()
    normalized_sheet = read_sheet(
        NORMALIZED_XLSX, _normalized_spec(), limits=family_limits
    )
    _require_identity(normalized_sheet.post_identity, NORMALIZED_BINDING, "normalized workbook")
    if normalized_sheet.pre_identity != normalized_sheet.post_identity:
        raise ConservationError("normalized workbook changed across read")

    sidecar_capture = capture_file_bytes(
        NORMALIZED_SIDECAR, max_bytes=SIDECAR_BINDING["bytes"]
    )
    lifecycle_capture = capture_file_bytes(
        R7_RESULT, max_bytes=R7_RESULT_BINDING["bytes"]
    )
    _require_identity(sidecar_capture.identity, SIDECAR_BINDING, "normalized sidecar")
    _require_identity(lifecycle_capture.identity, R7_RESULT_BINDING, "r7 lifecycle result")
    try:
        sidecar = json.loads(sidecar_capture.payload)
        lifecycle = json.loads(lifecycle_capture.payload)
    except json.JSONDecodeError as exc:
        raise ConservationError("bound lifecycle JSON malformed") from exc

    raw_identities, payloads, non_source_identity = _capture_raw()
    sidecar_checks = _validate_sidecar(sidecar, raw_identities)
    lifecycle_checks = _validate_r7(lifecycle)
    records, documents = _parse_payloads(payloads)
    payloads.clear()
    corpus = _corpus_metrics(raw_identities, non_source_identity, records, documents)

    source_rows = [_source_row(record) for record in records]
    projected_rows = [_project_record(record) for record in records]
    production_rows = [_project_record(record, production_join=True) for record in records]
    normalized_rows = [row.values for row in normalized_sheet.rows]
    projection = _compare_projection(projected_rows, normalized_sheet.rows)
    residue = _classify_projection_residue(projection, records)

    total_rows, total_headers = _total_claim_rows(documents)
    separator_rows, separator_headers = _description_separator_rows(documents)
    total_reconciliation = _reconcile_totals(documents)
    provenance_headers = (
        "Member", "District", "County", "Route", "Route Qualifier",
        "Owner Occurrence", "Physical Page", "Printed Page", "Line", "Top", "X0",
        "Raw Text",
    )
    provenance_rows = [
        (
            record["member"], record["district"], record["county"], record["route"],
            record["route_qualifier"], record["owner_occurrence"],
            record["physical_page"], record["printed_page"], record["line"],
            record["top"], record["x0"], record["raw_text"],
        )
        for record in records
    ]
    metadata_headers = (
        "Member", "District", "Pages", "Cover SHA256", "Page Header Manifest SHA256",
        "Owner Header Manifest SHA256", "Description Separator Manifest SHA256",
        "Totals Manifest SHA256", "PDF Metadata JSON",
    )
    metadata_rows = [
        (
            document["member"], document["district"], document["page_count"],
            document["cover"]["text_sha256"], document["page_header_manifest_sha256"],
            document["owner_header_manifest_sha256"],
            document["description_separator_manifest_sha256"],
            document["total_claim_manifest_sha256"],
            json.dumps(document["pdf_metadata"], sort_keys=True, separators=(",", ":")),
        )
        for document in documents
    ]
    mutations = _mutation_probes(
        source_rows, projected_rows, total_rows, separator_rows, metadata_rows
    )
    coverage = _field_coverage()
    topology = _xlsx_topology(NORMALIZED_XLSX)
    document_manifest_snapshot = _document_manifest_snapshot(documents)
    dataset_digests = {
        "raw_source": _dataset_digests(SOURCE_HEADERS, source_rows),
        "raw_source_provenance": _dataset_digests(
            provenance_headers, provenance_rows
        ),
        "raw_totals_claims": _dataset_digests(total_headers, total_rows),
        "raw_description_separators": _dataset_digests(
            separator_headers, separator_rows
        ),
        "document_metadata": _dataset_digests(metadata_headers, metadata_rows),
        "independently_projected": _dataset_digests(HEADERS, projected_rows),
        "production_join_projected": _dataset_digests(HEADERS, production_rows),
        "normalized": _dataset_digests(HEADERS, normalized_rows),
    }
    dataset_contracts = {
        name: _dataset_contract(
            digest,
            EXPECTED_DATASET_DIGESTS[
                "projected" if name in {
                    "independently_projected", "production_join_projected",
                    "normalized",
                } else name
            ],
        )
        for name, digest in dataset_digests.items()
    }
    total_reconciliation_contract = _total_reconciliation_contract(
        total_reconciliation
    )
    modules_after = _loaded_module_manifest()
    modules_after_checks = _validate_parser_module_manifest(modules_after)

    line_classification = corpus["line_classification"]
    expected_line_classification = {
        "cover": 48,
        "data": EXPECTED["projected_rows"],
        "description": EXPECTED["description_lines"],
        "description_separator": EXPECTED["description_separator_lines"],
        "owner_header": EXPECTED["owner_header_lines"],
        "page_header": EXPECTED["data_pages"] * 5,
        "total": EXPECTED["total_claim_lines"],
    }

    raw_after = [
        capture_file_identity(RAW_DIR / name)
        for name, _size, _digest, _pages in RAW_BINDINGS
    ]
    non_source_after = capture_file_identity(RAW_DIR / NON_SOURCE_BINDING[0])
    code_after = {
        "oracle": capture_file_identity(Path(__file__)),
        "family_gate": capture_file_identity(FAMILY_GATE),
        "reader": capture_file_identity(READER),
        "reader_gate": capture_file_identity(READER_GATE),
        "visual_sampler": capture_file_identity(VISUAL_SAMPLER),
    }
    tracked_current = (
        [FileIdentity(**identity) for identity in raw_identities] == raw_after
        and FileIdentity(**non_source_identity) == non_source_after
        and normalized_sheet.post_identity == capture_file_identity(NORMALIZED_XLSX)
        and sidecar_capture.identity == capture_file_identity(NORMALIZED_SIDECAR)
        and lifecycle_capture.identity == capture_file_identity(R7_RESULT)
        and visual_capture.identity == capture_file_identity(VISUAL_MANIFEST)
        and code_before == code_after
    )

    invariants = {
        "raw_source_bindings_exact": len(raw_identities) == EXPECTED["members"],
        "raw_page_universe_exact": sum(document["page_count"] for document in documents)
            == EXPECTED["pages"],
        "cover_and_data_page_universe_exact": len(documents) == EXPECTED["cover_pages"]
            and sum(document["page_header_count"] for document in documents)
            == EXPECTED["data_pages"],
        "every_source_line_classified": line_classification == expected_line_classification,
        "per_document_line_classification_exact": {
            document["district"]: document["line_classification"]
            for document in documents
        } == EXPECTED_LINE_CLASSIFICATION_BY_DISTRICT,
        "no_unclassified_lines": not corpus["unclassified_lines"],
        "no_unparsed_total_lines": not corpus["unparsed_totals"],
        "source_and_normalized_row_counts_exact": len(records) == EXPECTED["projected_rows"]
            and len(normalized_sheet.rows) == EXPECTED["projected_rows"],
        "rows_by_district_exact": corpus["rows_by_district"] == EXPECTED_ROWS_BY_DISTRICT,
        "route_owner_universe_exact": corpus["route_counts"]["statewide_routes"]
            == EXPECTED["routes"]
            and corpus["route_counts"]["district_route_owners"]
            == EXPECTED["district_route_owners"],
        "ditto_universe_exact": corpus["ditto_cell_count"] == EXPECTED["ditto_cells"]
            and corpus["ditto_domain"] == {"+": 5_684, "++": 13_360, "+++": 3_352},
        "roadbed_roles_exact": corpus["roadbed_roles"] == {
            "L": EXPECTED["role_left"], "R": EXPECTED["role_right"],
            "combined": EXPECTED["role_combined"],
        },
        "location_classes_exact": corpus["location_classes"] == {
            "plain": EXPECTED["location_plain"],
            "leading_prefix": EXPECTED["location_leading_prefix"],
            "equation_suffix": EXPECTED["location_equation_suffix"],
        },
        "description_multiplicity_exact": corpus["description_line_multiplicity"] == {
            "histogram": {0: 36_989, 1: 23_094},
            "records_with_multiple_lines": 0,
            "max_lines": 1,
        },
        "normalized_rows_contiguous": [row.source_row for row in normalized_sheet.rows]
            == list(range(2, EXPECTED["projected_rows"] + 2)),
        "production_projection_matches_normalized": dataset_digests
            ["production_join_projected"]["ordered_typed_sha256"]
            == dataset_digests["normalized"]["ordered_typed_sha256"]
            and dataset_digests["production_join_projected"]
            ["multiset_typed_sha256"]
            == dataset_digests["normalized"]["multiset_typed_sha256"],
        "independent_projection_matches_normalized": projection["ordered_exact"]
            and projection["multiset_exact"]
            and dataset_digests["independently_projected"]
            ["ordered_typed_sha256"]
            == dataset_digests["normalized"]["ordered_typed_sha256"]
            and dataset_digests["independently_projected"]
            ["multiset_typed_sha256"]
            == dataset_digests["normalized"]["multiset_typed_sha256"],
        "projection_residue_fully_classified": residue["unexplained_count"] == 0
            and projection["typed_cell_mismatch_count"] == 0
            and residue["invented_description_comma"]["count"] == 0,
        "frozen_dataset_digests_exact": all(
            all(contract.values()) for contract in dataset_contracts.values()
        ),
        "identity_and_collision_census_exact": _collision_census_exact(
            corpus["identity_and_collision_census"]
        ),
        "per_document_manifests_exact": _document_manifests_exact(
            document_manifest_snapshot
        ),
        "field_dispositions_complete": coverage["exact"],
        "totals_claim_universe_typed": total_reconciliation["claim_count"]
            == EXPECTED["total_claim_lines"]
            and total_reconciliation["kind_counts"] == EXPECTED_TOTAL_KINDS
            and total_reconciliation["fragment_class_counts"]
            == EXPECTED_TOTAL_FRAGMENT_CLASSES
            and {
                document["district"]: document["total_claim_count"]
                for document in documents
            } == EXPECTED_TOTALS_BY_DISTRICT,
        "description_separator_universe_exact": corpus["description_separators"]
            ["count"] == EXPECTED["description_separator_lines"]
            and corpus["description_separators"]["manifest_sha256"]
            == EXPECTED_DESCRIPTION_SEPARATOR_MANIFEST_SHA256,
        "totals_reconciliation_semantically_closed": all(
            total_reconciliation_contract.values()
        ),
        "parser_module_manifest_frozen_and_stable":
            all(modules_before_checks.values())
            and all(modules_after_checks.values())
            and modules_before == modules_after,
        "default_reader_limit_red_and_family_limit_green": default_limit_rejection["rejected"]
            and family_limits.max_xml_events == 20_000_000,
        "sidecar_contract_exact": all(sidecar_checks.values()),
        "r7_lifecycle_contract_exact": all(lifecycle_checks.values()),
        "visual_manifest_exact": visual_checks["exact"],
        "workbook_topology_exact": topology["exact"],
        "semantic_mutations_all_detected": mutations["all_detected"],
        "reader_and_family_gates_green": reader_gate["returncode"] == 0
            and family_gate["returncode"] == 0,
        "tracked_identities_current": tracked_current,
    }
    result = {
        "schema_version": 1,
        "audit": "Stage 6 Highway Log raw-PDF-to-normalized conservation",
        "independence": {
            "application_parsers_imported": False,
            "application_normalizers_imported": False,
            "application_column_constants_imported": False,
            "application_comparators_imported": False,
            "application_evidence_adapters_imported": False,
            "pdf_parser": "independent pdfplumber glyph clustering and fixed-coordinate assignment over private captured bytes",
            "xlsx_reader": "build/phase3_xlsx_stream.py generic stdlib OOXML reader with explicit bounded family limit",
        },
        "bindings": {
            "raw": {
                "members": len(raw_identities), "bytes": EXPECTED["raw_bytes"],
                "member_identities": raw_identities,
                "member_set_sha256": _sha(_json_bytes([
                    [Path(str(item["canonical_path"])).name, item["size"], item["sha256"]]
                    for item in raw_identities
                ])),
                "non_source_role": {
                    "identity": non_source_identity, "included_in_source_totals": False,
                },
            },
            "normalized": {
                **NORMALIZED_BINDING, "sheet": SHEET_NAME,
                "rows": EXPECTED["projected_rows"], "columns": len(HEADERS),
                "identity": _identity_dict(normalized_sheet.post_identity),
                "xlsx_limits": asdict(family_limits),
                "default_limit_red_reproduction": default_limit_rejection,
            },
            "normalized_sidecar": {
                **SIDECAR_BINDING, "identity": _identity_dict(sidecar_capture.identity),
                "contract": sidecar_checks,
            },
            "r7_lifecycle_witness": {
                **R7_RESULT_BINDING, "identity": _identity_dict(lifecycle_capture.identity),
                "contract": lifecycle_checks,
            },
            "visual_source_sample": {
                "sampler": {**VISUAL_SAMPLER_BINDING,
                            "identity": _identity_dict(visual_sampler_identity)},
                "manifest": {**VISUAL_MANIFEST_BINDING,
                             "identity": _identity_dict(visual_capture.identity)},
                "contract": visual_checks,
                "human_review": {
                    "fresh_roles_inspected": 36,
                    "coverage": "first/middle/final of each D01-D12 source PDF",
                    "source_visual_defects_found": 0,
                },
            },
        },
        "provenance": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pdfplumber": importlib.metadata.version("pdfplumber"),
            "pdfminer_six": importlib.metadata.version("pdfminer.six"),
            "loaded_parser_module_manifest": modules_after,
            "parser_module_stability": {
                "before": modules_before,
                "after": modules_after,
                "before_contract": modules_before_checks,
                "after_contract": modules_after_checks,
                "exact_across_crawl": modules_before == modules_after,
            },
            "code_identities": {
                name: _identity_dict(identity) for name, identity in code_after.items()
            },
            "executed_gates": {"reader": reader_gate, "family": family_gate},
            "xlsx_topology": topology,
        },
        "field_dispositions": FIELD_DISPOSITIONS,
        "field_coverage": coverage,
        "dataset_digest_contracts": dataset_contracts,
        "raw_source_digests": dataset_digests["raw_source"],
        "raw_source_provenance_digests": dataset_digests["raw_source_provenance"],
        "raw_totals_claim_digests": dataset_digests["raw_totals_claims"],
        "raw_description_separator_digests": dataset_digests
            ["raw_description_separators"],
        "document_metadata_digests": dataset_digests["document_metadata"],
        "independently_projected_digests": dataset_digests
            ["independently_projected"],
        "production_join_projected_digests": dataset_digests
            ["production_join_projected"],
        "normalized_digests": dataset_digests["normalized"],
        "projection_comparison": projection,
        "classified_projection_residue": residue,
        "unexplained_projection_residue_count": residue["unexplained_count"],
        "identity_and_collision_census": corpus["identity_and_collision_census"],
        "identity_and_collision_census_exact": _collision_census_exact(
            corpus["identity_and_collision_census"]
        ),
        "document_manifest_contract": {
            "fields": list(DOCUMENT_MANIFEST_FIELDS),
            "actual": [list(row) for row in document_manifest_snapshot],
            "expected": [list(row) for row in EXPECTED_DOCUMENT_MANIFESTS],
            "exact": _document_manifests_exact(document_manifest_snapshot),
        },
        "source_census": {
            key: value for key, value in corpus.items()
            if key not in {
                "documents", "raw_identities", "non_source", "unclassified_lines",
                "unparsed_totals", "identity_and_collision_census",
            }
        },
        "totals_reconciliation": total_reconciliation,
        "totals_reconciliation_contract": total_reconciliation_contract,
        "documents": documents,
        "semantic_mutation_probes": mutations,
        "findings": {
            "product": [
                {"id": "CMP-AUD-045", "status": "verified", "role": "physical identity loses district/county owner"},
                {"id": "CMP-AUD-157", "status": "verified", "role": "owner/qualifier, ADT, totals, and provenance source claims dropped"},
            ],
            "audit_gate": [
                {"id": f"CMP-AUD-{number:03d}", "status": "resolved"}
                for number in range(167, 183)
            ],
        },
        "audit_invariants": invariants,
        "failed_invariants": [],
        "terminal_status": "pending",
        "accepted": False,
        "projection_exact": projection["ordered_exact"],
        "stage6_family_audit_complete": False,
        "normalized_full_conservation": False,
    }
    return _finalize_invariant_result(result, invariants)


def _finalize_invariant_result(
    document: dict[str, object], invariants: Mapping[str, bool]
) -> dict[str, object]:
    failed = [name for name, passed in invariants.items() if not passed]
    document["audit_invariants"] = dict(invariants)
    document["failed_invariants"] = failed
    document["accepted"] = not failed
    document["stage6_family_audit_complete"] = not failed
    document["terminal_status"] = (
        "accepted" if not failed else "rejected_invariant_failure"
    )
    if failed:
        raise ConservationInvariantError(failed, document)
    return document


def _write_json(path: Path, document: Mapping[str, object]) -> FileIdentity:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, indent=2
    ).encode("utf-8") + b"\n"
    temporary = path.with_name(path.name + ".tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return capture_file_identity(path)


def _output_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def _validate_output_paths(
    result_path: Path, acceptance_path: Path, diagnostic_path: Path
) -> None:
    paths = (result_path, acceptance_path, diagnostic_path)
    if len({_output_key(path) for path in paths}) != len(paths):
        raise ConservationError(
            "result, acceptance, and rejected diagnostic paths must be distinct"
        )


def _write_rejected_diagnostic(
    path: Path,
    document: Mapping[str, object],
    *,
    result_path: Path,
    acceptance_path: Path,
) -> FileIdentity:
    _validate_output_paths(result_path, acceptance_path, path)
    if not (
        document.get("accepted") is False
        and document.get("stage6_family_audit_complete") is False
        and document.get("terminal_status") == "rejected_invariant_failure"
        and bool(document.get("failed_invariants"))
    ):
        raise ConservationError("diagnostic does not satisfy rejected-result contract")
    identity = _write_json(path, document)
    committed = json.loads(path.read_text(encoding="utf-8"))
    if not (
        committed.get("accepted") is False
        and committed.get("stage6_family_audit_complete") is False
        and committed.get("terminal_status") == "rejected_invariant_failure"
        and bool(committed.get("failed_invariants"))
    ):
        raise ConservationError("committed diagnostic changed rejection contract")
    return identity


def _acceptance(result_path: Path, result_identity: FileIdentity) -> dict[str, object]:
    tracked = {
        "result": result_identity,
        "oracle": capture_file_identity(Path(__file__)),
        "family_gate": capture_file_identity(FAMILY_GATE),
        "reader": capture_file_identity(READER),
        "reader_gate": capture_file_identity(READER_GATE),
        "visual_sampler": capture_file_identity(VISUAL_SAMPLER),
        "visual_manifest": capture_file_identity(VISUAL_MANIFEST),
        "normalized": capture_file_identity(NORMALIZED_XLSX),
        "sidecar": capture_file_identity(NORMALIZED_SIDECAR),
        "lifecycle": capture_file_identity(R7_RESULT),
    }
    raw = [
        capture_file_identity(RAW_DIR / name)
        for name, _size, _digest, _pages in RAW_BINDINGS
    ]
    non_source = capture_file_identity(RAW_DIR / NON_SOURCE_BINDING[0])
    return {
        "schema_version": 1,
        "decision": "accepted_stage6_family_audit",
        "result_path": str(result_path),
        "tracked_identities": {
            name: _stable_identity(identity) for name, identity in tracked.items()
        },
        "raw_member_identities": [_stable_identity(identity) for identity in raw],
        "non_source_role_identity": _stable_identity(non_source),
        "required_result_flags": {
            "accepted": True,
            "terminal_status": "accepted",
            "stage6_family_audit_complete": True,
            "projection_exact": True,
            "normalized_full_conservation": False,
            "unexplained_projection_residue_count": 0,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--probe-output", type=Path)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--acceptance", type=Path)
    parser.add_argument("--diagnostic", type=Path)
    args = parser.parse_args(argv)
    if args.probe:
        try:
            result = _probe()
        except Exception as exc:
            print(f"FAIL phase6 Highway Log probe: {type(exc).__name__}: {exc}")
            return 1
        if args.probe_output is not None:
            args.probe_output.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(
                result, ensure_ascii=False, sort_keys=True, indent=2
            ).encode("utf-8") + b"\n"
            args.probe_output.write_bytes(payload)
            print(
                f"PROGRESS wrote probe {args.probe_output}: "
                f"{len(payload)} bytes/{_sha(payload)}",
                flush=True,
            )
        summary = {
            key: value for key, value in result.items()
            if key not in {"documents", "raw_identities", "unclassified_lines", "unparsed_totals"}
        }
        summary["unclassified_count"] = len(result["unclassified_lines"])
        summary["unparsed_total_count"] = len(result["unparsed_totals"])
        summary["unclassified_examples"] = result["unclassified_lines"][:20]
        summary["unparsed_total_examples"] = result["unparsed_totals"][:50]
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    acceptance_path = args.acceptance or Path(str(args.result) + ".acceptance.json")
    diagnostic_path = args.diagnostic or Path(str(args.result) + ".diagnostic.json")
    try:
        _validate_output_paths(args.result, acceptance_path, diagnostic_path)
        result = run()
        result_identity = _write_json(args.result, result)
        committed = json.loads(args.result.read_text(encoding="utf-8"))
        if not (
            committed.get("accepted") is True
            and committed.get("terminal_status") == "accepted"
            and committed.get("failed_invariants") == []
            and committed.get("stage6_family_audit_complete") is True
            and committed.get("projection_exact") is True
            and committed.get("normalized_full_conservation") is False
            and committed.get("unexplained_projection_residue_count") == 0
        ):
            raise ConservationError("committed result flags do not satisfy audit contract")
        acceptance_identity = _write_json(
            acceptance_path, _acceptance(args.result, result_identity)
        )
    except ConservationInvariantError as exc:
        try:
            diagnostic_identity = _write_rejected_diagnostic(
                diagnostic_path,
                exc.diagnostic,
                result_path=args.result,
                acceptance_path=acceptance_path,
            )
        except Exception as diagnostic_exc:
            print(
                "FAIL phase6 Highway Log conservation and diagnostic publication: "
                f"{type(diagnostic_exc).__name__}: {diagnostic_exc}"
            )
            return 1
        print(
            f"FAIL phase6 Highway Log conservation: {type(exc).__name__}: {exc}; "
            f"rejected diagnostic {diagnostic_identity.size} bytes "
            f"{diagnostic_identity.sha256}"
        )
        return 1
    except Exception as exc:
        print(f"FAIL phase6 Highway Log conservation: {type(exc).__name__}: {exc}")
        return 1
    print(
        "PASS phase6 Highway Log conservation: "
        f"{result_identity.size} bytes {result_identity.sha256}; "
        f"acceptance {acceptance_identity.size} bytes {acceptance_identity.sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
