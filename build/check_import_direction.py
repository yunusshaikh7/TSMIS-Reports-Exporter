"""Diagnostic check: no module-level import cycles in scripts/.

A static guard on the package's import direction. It parses every scripts/*.py
for the sibling modules it imports AT MODULE LOAD TIME -- including imports
nested inside module-scope `try` / `if` / `with` blocks, but excluding function
and class bodies (those run later and can't form an import-time cycle). It
asserts the resulting graph is acyclic (no strongly-connected component > 1) and
that no module imports itself. The v0.18.0 engine decomposition (P8a/P8b)
extracts common.py into a layered, acyclic module set behind a re-export shim;
this check is the tripwire that a later move never introduces an upward /
circular import.

Pure stdlib (ast only); no imports are executed. Run from the repo root:
    build\\.venv\\Scripts\\python.exe build\\check_import_direction.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

_failures = []


def check(name, cond):
    print(f"  [{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        _failures.append(name)


def _import_time_deps(tree, local):
    """Sibling modules imported at MODULE LOAD TIME by `tree`. Descends into
    module-scope compound statements (`try` / `if` / `with` / `for` / `while`
    and their handler/else/finally bodies) but NOT into function or class
    bodies, which execute later and cannot form an import-time cycle. Self-edges
    are KEPT (so a self-import is detectable)."""
    deps = set()

    def visit(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue                       # body runs at call time, not import time
            if isinstance(child, ast.Import):
                for alias in child.names:
                    top = alias.name.split(".")[0]
                    if top in local:
                        deps.add(top)
            elif isinstance(child, ast.ImportFrom) and child.level == 0 and child.module:
                top = child.module.split(".")[0]
                if top in local:
                    deps.add(top)
            visit(child)                       # recurse into module-level compound bodies

    visit(tree)
    return deps


def _build_graph():
    local = {p.stem for p in SCRIPTS.glob("*.py")}
    return {p.stem: _import_time_deps(ast.parse(p.read_text(encoding="utf-8")), local)
            for p in sorted(SCRIPTS.glob("*.py"))}


def _sccs(graph):
    """Tarjan's strongly-connected components."""
    sys.setrecursionlimit(10000)
    index, low, on_stack, stack, out = {}, {}, {}, [], []
    counter = [0]

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack[v] = True
        for w in graph.get(v, ()):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif on_stack.get(w):
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                comp.append(w)
                if w == v:
                    break
            out.append(comp)

    for v in graph:
        if v not in index:
            strong(v)
    return out


def _cycles(graph):
    return [sorted(c) for c in _sccs(graph) if len(c) > 1]


def _self_loops(graph):
    return sorted(v for v in graph if v in graph[v])


def test_self_tests():
    """Prove the analysis detects the failure modes it guards against -- a real
    future cycle must not slip past (the old col_offset==0 + self-strip version
    silently could not detect any of these)."""
    print("analyzer self-tests (detection is real, not vacuous):")
    local = {"a", "b", "d", "e", "self"}
    deps = lambda src: _import_time_deps(ast.parse(src), local)
    check("direct self-import -> self-edge kept",
          "self" in deps("import self\n"))
    check("module-scope try-import counts (the old filter missed it)",
          "b" in deps("try:\n    import b\nexcept Exception:\n    b = None\n"))
    check("module-scope conditional import counts",
          "d" in deps("if True:\n    import d\n"))
    check("function-local import is ignored (deferred -> no import-time edge)",
          "e" not in deps("def f():\n    import e\n"))
    g = {
        "a": deps("try:\n    import b\nexcept Exception:\n    pass\n"),
        "b": deps("if True:\n    import a\n"),
    }
    check("cycle via try/conditional imports detected", _cycles(g) == [["a", "b"]])
    check("self-loop detected", _self_loops({"x": {"x"}}) == ["x"])


def main():
    test_self_tests()
    graph = _build_graph()
    print(f"scripts/ import-time graph: {len(graph)} modules")
    self_loops = _self_loops(graph)
    check("no module imports itself", not self_loops)
    if self_loops:
        print("   self-import:", self_loops)
    cycles = _cycles(graph)
    check("no module-level import cycles", not cycles)
    for c in cycles:
        print("   cycle:", " <-> ".join(c))
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {_failures}")
        return 1
    print("ALL IMPORT-DIRECTION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
