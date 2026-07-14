"""Static packaged-manifest gate: app.spec embeds longPathAware=true.

No PyInstaller build is required.  The gate parses both files structurally so a
comment/string mentioning the setting cannot satisfy it accidentally.
"""
from __future__ import annotations

import ast
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "build" / "app.spec"
MANIFEST = ROOT / "build" / "app.manifest"

ASM_V3 = "urn:schemas-microsoft-com:asm.v3"
LONG_PATH_NS = "http://schemas.microsoft.com/SMI/2016/WindowsSettings"

_failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        if detail:
            print(f"       {detail}")
        _failures.append(name)


def _manifest_assignment(tree: ast.AST):
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name)
                        and target.id == "MANIFEST" for target in node.targets)):
            return node.value
    return None


def _is_build_manifest_join(node: ast.AST | None) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "join"
        and len(node.args) == 2
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "SPECPATH"
        and isinstance(node.args[1], ast.Constant)
        and node.args[1].value == "app.manifest"
    )


def _exe_manifest_keyword(tree: ast.AST):
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "EXE"):
            return next((keyword.value for keyword in node.keywords
                         if keyword.arg == "manifest"), None)
    return None


def main() -> None:
    check("build/app.spec exists", SPEC.is_file(), str(SPEC))
    check("build/app.manifest exists", MANIFEST.is_file(), str(MANIFEST))
    if not SPEC.is_file() or not MANIFEST.is_file():
        return

    try:
        tree = ast.parse(SPEC.read_text(encoding="utf-8"), filename=str(SPEC))
    except (OSError, SyntaxError) as e:
        check("app.spec parses as Python", False, f"{type(e).__name__}: {e}")
        return
    check("app.spec MANIFEST resolves to SPECPATH/app.manifest",
          _is_build_manifest_join(_manifest_assignment(tree)))
    embedded = _exe_manifest_keyword(tree)
    check("app.spec passes MANIFEST to PyInstaller EXE",
          embedded is not None
          and any(isinstance(node, ast.Name) and node.id == "MANIFEST"
                  for node in ast.walk(embedded)),
          ast.dump(embedded) if embedded is not None else "missing keyword")

    try:
        document = ET.parse(MANIFEST)
    except (OSError, ET.ParseError) as e:
        check("app.manifest is well-formed XML", False,
              f"{type(e).__name__}: {e}")
        return
    root = document.getroot()
    settings = root.findall(
        f".//{{{ASM_V3}}}application/{{{ASM_V3}}}windowsSettings/"
        f"{{{LONG_PATH_NS}}}longPathAware")
    check("manifest has exactly one correctly-namespaced longPathAware setting",
          len(settings) == 1, f"found {len(settings)}")
    check("embedded longPathAware value is true",
          len(settings) == 1
          and (settings[0].text or "").strip().casefold() == "true")

    privilege = root.find(f".//{{{ASM_V3}}}requestedExecutionLevel")
    check("long-path manifest preserves asInvoker/no-uiAccess security",
          privilege is not None
          and privilege.attrib.get("level") == "asInvoker"
          and privilege.attrib.get("uiAccess") == "false")


if __name__ == "__main__":
    print("packaged application manifest gate:")
    main()
    if _failures:
        print(f"\n{len(_failures)} check(s) FAILED")
        sys.exit(1)
    print("all good")
