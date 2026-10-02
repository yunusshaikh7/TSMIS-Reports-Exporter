# Contributing

A quick orientation for all contributors. The deep knowledge lives in the
[`docs/`](docs/INDEX.md) library; the non-negotiable conventions live in
[`docs/project-guide.md`](docs/project-guide.md), shared by human contributors and coding agents.

## Setup (dev PC)

1. Python **3.11** on PATH (the hash-locked build is 3.11-only).
2. `powershell -ExecutionPolicy Bypass -File build\build.ps1` once creates
   `build\.venv` with the exact pinned tree (or run the `.bat` setup for the
   console flow's venv).
3. The GUI in dev mode: `run app (GUI preview).bat` — or preview just the UI
   with any static server on `scripts/ui` + `/index.html#mock` (no Python).

## The verification loop (no pytest — by design)

```
build\.venv\Scripts\python.exe build\run_checks.py -j 4    # the WHOLE suite
build\.venv\Scripts\python.exe build\check_<name>.py       # one guard
```

Every fix ships with (or extends) a `build/check_*.py` golden. New checks are
automatically discovered by `run_checks.py`; no per-check YAML entry is needed.
`check_ci_manifest.py` verifies that CI runs the shared runner. The historical
`check_phase*` audit instruments are excluded and run on demand.

## The three rules people trip on

- **`compare_core.py` is correctness-locked.** Preserve correct output; prove
  semantic changes against the approved domain contract, independent oracle,
  and both workbook flavors. Explain and re-bind deliberate canary changes.
  Use opt-in `CompareSchema` fields for report-specific behavior; fix shared
  defects in the shared engine. Performance-only changes remain output-locked.
  See [docs/comparison-engine.md](docs/comparison-engine.md).
- **TSN normalizer changes bump the catalog version.** The TSN library stores
  already-normalized values; bump `normalization_version` in
  `report_catalog.TSN` for the report(s) affected so field libraries
  auto-rebuild (D2) — and re-bless the statewide canary
  ([docs/tsn-parsers.md](docs/tsn-parsers.md)).
- **Real test data and the TSMIS site source are LOCAL ONLY** (never commit,
  never quote into the repo). See
  [docs/verification-and-testing.md](docs/verification-and-testing.md).

## Style

Short version: core modules are console-free (Events sink, no
print/input/sys.exit); every swallowed exception logs `type(e).__name__` + the
first message line (or carries a `# silent-ok: <why>` waiver —
`check_silent_swallows.py` enforces it); name constants over magic values;
commit messages are short and imperative. `ruff check .` uses the same rule set as CI
(`pyproject.toml`; CI currently scopes Ruff to `scripts/`).
