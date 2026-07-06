# Contributing

A quick human-facing orientation. The deep knowledge lives in the
[`docs/`](docs/INDEX.md) library; the non-negotiable conventions live in
[`CLAUDE.md`](CLAUDE.md) (written as an AI-session router, but its
**Conventions** section binds humans too).

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
auto-picked-up by `run_checks.py` (glob) but must ALSO be added to
`.github/workflows/checks.yml` — `check_ci_manifest.py` fails CI until they are.

## The three rules people trip on

- **`compare_core.py` is regression-locked.** Any change to its formula/label
  text must be proven cell-for-cell identical for the TSMIS-vs-TSN flavor
  before shipping; new behavior goes through opt-in `CompareSchema` fields.
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
commit messages are short and imperative. `ruff check .` matches CI
(`pyproject.toml`).
