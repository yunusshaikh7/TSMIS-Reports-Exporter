"""Cross-environment comparison MATRIX engine (Everything tab).

A thin ORCHESTRATION layer over the already-audited cross-environment comparison
(`compare_env`) and the always-current Export-Everything store. It NEVER
recomputes report contents and NEVER touches `compare_core` — it only:

  * enumerates the report x environment cells from the store,
  * computes per-cell EXPORT freshness (newest file mtime) via report_library,
  * computes per-cell COMPARISON freshness (the comparison workbook's mtime vs
    the two source folders' newest export mtime),
  * orchestrates `compare_env.<adapter>.compare_folders(...)` to (re)build a
    cell's comparison of (report, env) against the BASELINE env, writing into
    <dest>/comparisons/<baseline>/, and
  * caches each comparison's verdict + discrepancy counts in a sidecar so the
    snapshot (which the GUI renders) stays a pure, offline filesystem read.

Console-free like the rest of the core: progress is reported through the Events
sink and exceptions are raised — never print/input/sys.exit. Only gui_api /
gui_worker drive it.
"""

# S4 (v0.19.0): matrix.py is now the FACADE over the state/build split. Every
# public (and check-visible private) name re-exports here, and the build side
# resolves its patchable collaborators through THIS module at call time — so
# `matrix.<name>` stays the one true patch/monkeypatch point.
from matrix_state import (                                       # noqa: F401
    BASELINE_DEFAULT, COMPARISONS_DIRNAME, _MTIME_TOL_S, _NEQ,
    _cell_input_fingerprint, _cmp_state, _inputs_changed, _mode_by_id,
    _pdf_self_comparator, _results_path, _row_defs, _row_modes, _safe_mtime,
    _staleness, _tsn_results_path, apply_order, comparison_path,
    comparison_state, comparisons_root, default_env_label, env_keys,
    load_results, load_tsn_results, matrix_snapshot, mode_out_path,
    out_path_for_cell, read_counts, record_result, record_tsn_result,
    tsn_capable, tsn_comparator_for, tsn_comparisons_root, tsn_input_root,
    tsn_source, tsn_subdir_for, tsn_supported)
from matrix_build import (                                       # noqa: F401
    _FORMULAS_TWIN_MAX_ROWS, _comparison_row_count, _consolidate_store_folder,
    _consolidated_filename, _consolidated_stale, _ensure_consolidated,
    _formulas_sibling, _pdf_store_consolidator, _try_formulas,
    build_cell_comparison, build_comparison, cells_to_rebuild,
    consolidate_and_compare_tsn, consolidate_tsn_pdfs, consolidated_state,
    consolidated_store_path)
