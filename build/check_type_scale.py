"""The UI type scale: six steps, every one a whole pixel.

`scripts/ui/app.css` carried 13 distinct font sizes across 101 declarations, six
of them half-pixels (9.5 / 10.5 / 11.5 / 12.5 / 13.5). That is the inconsistency
a user actually sees, and it is worst exactly where it matters: a 1366x768 work
PC runs at 150% DPI, where a .5px size falls between device pixels and Windows
rounds it inconsistently from one element to the next.

The half-pixels were never a finer scale — each sat in the same ROLE as its
integer neighbour — so each pair collapsed onto one token.

This guard fails on the two ways the scale erodes: a raw px font-size (bypassing
the tokens) and a token that is not a whole pixel. It deliberately does NOT cap
the token count at six forever — but adding one is a decision, and it has to be
made here, in the open.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "scripts" / "ui" / "app.css"

EXPECTED = {
    "--text-2xs": 10,
    "--text-xs": 11,
    "--text-sm": 12,
    "--text-base": 13,
    "--text-lg": 15,
    "--text-xl": 17,
}

_failures = []


def check(name, condition, detail=""):
    print(f"  [{'OK ' if condition else 'FAIL'}] {name}")
    if not condition:
        _failures.append(name)
        if detail:
            print(f"       {detail}")


def main():
    print("UI type scale:")
    css = CSS.read_text(encoding="utf-8")

    # The token block is the ONE place a px font size may be written.
    declared = dict(re.findall(r"(--text-[a-z0-9]+):\s*([0-9.]+)px;", css))
    check("all six scale tokens are declared",
          set(declared) == set(EXPECTED),
          f"declared={sorted(declared)} expected={sorted(EXPECTED)}")
    for token, px in EXPECTED.items():
        got = declared.get(token)
        check(f"{token} is {px}px",
              got is not None and float(got) == px, f"got {got!r}")

    check("every token is a WHOLE pixel (the half-pixel class is closed)",
          all(float(v).is_integer() for v in declared.values()),
          f"non-integer: {[k for k, v in declared.items() if not float(v).is_integer()]}")

    # No font-size outside the token block may be a raw px value.
    body = css.split("--text-xl:", 1)[-1]
    raw = re.findall(r"font-size:\s*([0-9.]+px)", body)
    check("no raw px font-size outside the token block",
          not raw,
          f"{len(raw)} raw value(s): {sorted(set(raw))} — use var(--text-*)")

    used = set(re.findall(r"font-size:\s*var\((--text-[a-z0-9]+)\)", css))
    check("every font-size uses a declared token",
          used <= set(declared), f"undeclared: {sorted(used - set(declared))}")
    check("every declared token is actually used (no dead step)",
          set(declared) <= used, f"unused: {sorted(set(declared) - used)}")

    # The fixture has to be able to fail: prove the raw-value regex matches one.
    check("the raw-value probe really matches a raw declaration (it has teeth)",
          bool(re.findall(r"font-size:\s*([0-9.]+px)", "a { font-size: 12.5px; }")))

    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print(f"ALL TYPE-SCALE CHECKS PASSED ({len(declared)} steps, "
          f"{len(re.findall(r'font-size:', css))} declarations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
