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


def main():
    test_contract_enum_parity()
    test_mock_carries_contract()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL UI-CONTRACT (enum mirror) CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
