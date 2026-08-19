"""P9: frontend bridge-enum mirror parity — ui/contract.js can't drift from contract.py.

P7a made gui_api.get_initial_state() surface the bridge-enum SSOT
(contract.initial_state_enums: tasks / terminal_kinds / env_access). P9 adds the
FRONTEND mirror ui/contract.js (window.CONTRACT) + has the #mock preview return it in
its init payload (parity with production). This check LOCKS the mirror to the backend
SSOT so the two can't silently diverge:

  * ui/contract.js window.CONTRACT == contract.initial_state_enums() (exact, ordered).
  * mock.js get_initial_state returns `contract: window.CONTRACT` (so the preview's
    init payload carries the same enum surface the real bridge does).

(The #mock REPORT-LIST payload parity is locked separately by
build/check_report_catalog.py::test_mock_parity, against report_catalog — not
duplicated here.)

Pure Python (regex over the JS literals + the real contract module); no browser, no
node. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_ui_contract.py
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT)]

import contract  # noqa: E402

UI = ROOT / "scripts" / "ui"
_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


class _LabelNestingParser(HTMLParser):
    """Detect invalid nested/unbalanced labels without browser auto-repair."""

    def __init__(self):
        super().__init__()
        self.label_depth = 0
        self.nested_labels = 0

    def handle_starttag(self, tag, attrs):
        if tag == "label":
            self.nested_labels += int(self.label_depth > 0)
            self.label_depth += 1

    def handle_endtag(self, tag):
        if tag == "label":
            self.label_depth -= 1


def _str_array(text, name):
    """The ordered list of quoted strings assigned to `name:` in a JS object literal."""
    m = re.search(re.escape(name) + r"\s*:\s*\[(.*?)\]", text, re.S)
    return re.findall(r'"([^"]*)"', m.group(1)) if m else None


def test_contract_enum_parity():
    print("contract mirror: ui/contract.js window.CONTRACT == contract.initial_state_enums():")
    cjs = (UI / "contract.js").read_text(encoding="utf-8")
    check("contract.js sets window.CONTRACT", "window.CONTRACT" in cjs)
    enums = contract.initial_state_enums()
    for name in ("tasks", "terminal_kinds", "env_access"):
        got = _str_array(cjs, name)
        check(f"contract.js {name} == backend ({len(enums[name])} values, exact order)",
              got == enums[name])
        if got != enums[name]:
            print(f"      contract.js: {got}\n      backend:     {enums[name]}")


def test_mock_carries_contract():
    print("payload parity: the #mock init payload carries the contract enum surface:")
    mock = (UI / "mock.js").read_text(encoding="utf-8")
    check("mock.js get_initial_state returns `contract: window.CONTRACT`",
          re.search(r"contract:\s*window\.CONTRACT", mock) is not None)


def test_ui_script_references_exist():
    print("reference integrity: every <script src> index.html names exists in scripts/ui/:")
    html = (UI / "index.html").read_text(encoding="utf-8")
    # The classic-script srcs index.html loads (contract.js, the P9b ui-* modules,
    # app.js) + the conditionally-injected mock.js. A new module that's referenced but
    # missing from the bundle would 404 silently in WebView2 -- catch it offline.
    refs = set(re.findall(r'src="([^"]+\.js)"', html))
    refs.update(re.findall(r'\.src\s*=\s*"([^"]+\.js)"', html))   # the #mock createElement injection
    check("index.html references the P9b ui-* modules",
          {"ui-dom.js", "ui-matrix.js", "ui-settings.js"} <= refs)
    for f in sorted(refs):
        check(f"referenced ui asset exists (no 404): {f}", (UI / f).exists())


def test_baseline_switch_uses_stale_scope():
    """CMP-AUD-099: switching the matrix baseline recomputes ONLY the stale
    (cross-environment) cells — never `all` (which would needlessly rebuild
    baseline-independent vs-TSN / self-check comparisons). The per-row/per-column
    rebuild buttons legitimately keep `all`; only the baseline `onchange` differs."""
    print("CMP-AUD-099: baseline switch recomputes 'stale', not 'all':")
    js = (UI / "ui-matrix.js").read_text(encoding="utf-8")
    m = re.search(r"set_matrix_baseline\(nb\).*?recompute_matrix\((\"|')(\w+)\1",
                  js, re.S)
    check("baseline-switch handler calls recompute_matrix('stale')",
          bool(m) and m.group(2) == "stale")




def test_fast_tsn_toggle_contract():
    print("Fast vs TSN toggle: markup, state sync, bridge call, and mock stay paired:")
    html = (UI / "index.html").read_text(encoding="utf-8")
    app = (UI / "app.js").read_text(encoding="utf-8")
    matrix = (UI / "ui-matrix.js").read_text(encoding="utf-8")
    mock = (UI / "mock.js").read_text(encoding="utf-8")
    check("Everything and by-day each expose exactly one fast-TSN checkbox",
          html.count('id="matrixFastTsn"') == 1
          and html.count('id="dayMatrixFastTsn"') == 1)
    parser = _LabelNestingParser()
    parser.feed(html)
    parser.close()
    check("Fast controls are sibling labels (no browser-dependent nested repair)",
          parser.nested_labels == 0 and parser.label_depth == 0)
    check("both controls call the one persisted bridge endpoint",
          'api.set_setting("fast_tsn_comparisons"' in app)
    check("both controls mirror the shared state key",
          '"matrixFastTsn", "dayMatrixFastTsn"' in matrix
          and 'fast_tsn_comparisons' in matrix)
    check("mock exposes the same state + endpoint",
          'fast_tsn_comparisons: false' in mock
          and 'key === "fast_tsn_comparisons"' in mock
          and 'set_fast_tsn_comparisons: async' not in mock)


def main():
    test_contract_enum_parity()
    test_mock_carries_contract()
    test_ui_script_references_exist()
    test_baseline_switch_uses_stale_scope()
    test_fast_tsn_toggle_contract()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL UI-CONTRACT (enum mirror) CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
