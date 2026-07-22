/* TSMIS Reports Exporter -- browser design-preview mock (#mock).
 *
 * Classic <script>, loaded by index.html ONLY when the URL carries #mock, and
 * ONLY after app.js (it reads app.js's top-level bindings -- `S`, `boot`). It is
 * never loaded by the real pywebview app, so the simulated checks / login /
 * exports / consolidation can never reach a user.
 *
 * mock.js OWNS the mock boot (RR2-C3): it defines makeMockApi, then boots the UI
 * against it -- app.js auto-boots only in production. The report lists + the bridge
 * enums it serves are locked to the backend SoT by build/check_ui_contract.py
 * (report_catalog / contract.py), so this preview can't drift into a 2nd backend.
 */

function makeMockApi() {
  const MOCK_TODAY = "2026-06-20";   // the by-day matrix's EXPORTABLE column in #mock
  const ROUTES = [];
  for (let i = 1; i <= 280; i++) {
    ROUTES.push(String(i).padStart(3, "0"));
    if (i === 5) ROUTES.push("005S");
    if (i === 14) ROUTES.push("014U");
    if (i === 101) ROUTES.push("101U");
  }
  // In PICKER display order (P-D), mirroring the real init.reports: flat top-level
  // reports first in the TSMIS site's order (Highway Log, its PDF, then Sequence),
  // then the TSAR family groups. group/short carry the family header + leaf label
  // (omitted for a flat report). Stable keys live in report_catalog, not here.
  const REPORTS = [
    { key: "highway_log", label: "Highway Log", fmt: "Excel" },
    { key: "highway_log_pdf", label: "Highway Log (PDF)", fmt: "PDF" },
    { key: "highway_sequence", label: "Highway Sequence Listing", fmt: "Excel" },
    // v0.24.0 PDF editions (ids 11/12), next to their Excel siblings in the picker.
    { key: "highway_sequence_pdf", label: "Highway Sequence Listing (PDF)", fmt: "PDF" },
    // v0.25.1: the dev site's embedded-SSRS Route History — reserved, app-DISABLED
    // (shown greyed); third among the site's flat options.
    { key: "route_history", label: "Route History Table", fmt: "SSRS", disabled: true },
    { key: "ramp_summary", label: "TSAR: Ramp Summary", fmt: "PDF", group: "Ramp", short: "Summary" },
    // v0.25.1: Ramp Summary's Excel sibling (the site's rs_exportToExcel, id 13).
    { key: "ramp_summary_excel", label: "TSAR: Ramp Summary (Excel)", fmt: "Excel", group: "Ramp", short: "Summary (Excel)" },
    { key: "ramp_detail", label: "TSAR: Ramp Detail", fmt: "Excel", group: "Ramp", short: "Detail" },
    { key: "ramp_detail_pdf", label: "TSAR: Ramp Detail (PDF)", fmt: "PDF", group: "Ramp", short: "Detail (PDF)" },
    { key: "intersection_summary", label: "Intersection Summary", fmt: "Excel", group: "Intersection", short: "Summary" },
    // v0.25.1: Intersection Summary's print edition (ints_printAll, id 14).
    { key: "intersection_summary_pdf", label: "Intersection Summary (PDF)", fmt: "PDF", group: "Intersection", short: "Summary (PDF)" },
    { key: "intersection_detail", label: "Intersection Detail", fmt: "Excel", group: "Intersection", short: "Detail" },
    { key: "intersection_detail_pdf", label: "Intersection Detail (PDF)", fmt: "PDF", group: "Intersection", short: "Detail (PDF)" },
    // The "Highway" TSAR group — export enabled v0.19.1 (Detail/Summary) + the Highway
    // Detail (PDF) edition v0.19.2 (next to its Excel sibling, like Intersection Detail).
    { key: "highway_detail", label: "Highway Detail", fmt: "Excel", group: "Highway", short: "Detail" },
    { key: "highway_detail_pdf", label: "Highway Detail (PDF)", fmt: "PDF", group: "Highway", short: "Detail (PDF)" },
    { key: "highway_summary", label: "Highway Summary", fmt: "Excel", group: "Highway", short: "Summary" },
    // 2026-07-22: the dev site 7.21 "Clean Road Files" group (ids 16/17/18) —
    // reserved, app-DISABLED (shown greyed) until the site un-greys them.
    { key: "clean_highway", label: "Clean Road: Highway", fmt: "Excel", group: "Clean Road", short: "Highway", disabled: true },
    { key: "clean_intersection", label: "Clean Road: Intersection", fmt: "Excel", group: "Clean Road", short: "Intersection", disabled: true },
    { key: "clean_ramp", label: "Clean Road: Ramp", fmt: "Excel", group: "Clean Road", short: "Ramp", disabled: true },
  ];
  // The Consolidate radios carry each row's stable `cons:*` key (P3) — this list
  // matches reports.CONSOLIDATE_REPORTS (9 rows as of CR-002: both Intersection
  // consolidators + the new Int-Detail-PDF), NOT the 8-row export REPORTS above.
  // consolidate_info/start_consolidate resolve by that key, so the preview mirrors
  // the real bridge.
  const CONS_REPORTS = [
    { key: "cons:ramp_summary", label: "TSAR: Ramp Summary" },
    { key: "cons:ramp_detail", label: "TSAR: Ramp Detail" },
    { key: "cons:ramp_detail_pdf", label: "TSMIS Ramp Detail (PDF)" },
    { key: "cons:highway_sequence", label: "Highway Sequence Listing" },
    { key: "cons:highway_sequence_pdf", label: "TSMIS Highway Sequence (PDF)" },
    { key: "cons:intersection_summary", label: "Intersection Summary" },
    { key: "cons:intersection_detail", label: "Intersection Detail" },
    { key: "cons:intersection_detail_pdf", label: "TSMIS Intersection Detail (PDF)" },
    { key: "cons:highway_log_excel", label: "TSMIS Highway Log (Excel)" },
    { key: "cons:highway_log_pdf", label: "TSMIS Highway Log (PDF)" },
    { key: "cons:tsn_highway_log", label: "TSN Highway Log (PDF)" },
    { key: "cons:highway_detail", label: "Highway Detail" },
    { key: "cons:highway_detail_pdf", label: "TSMIS Highway Detail (PDF)" },
  ];
  // Mock selection travels by KEY too (P3), so the preview exercises the same
  // bridge contract as production. These map a key back to its mock row.
  const repByKey = (k) => REPORTS.find((r) => r.key === k) || {};
  const consByKey = (k) => CONS_REPORTS.find((r) => r.key === k) || {};
  const st = {
    task: null, fast_run: false,
    authed: false, device_ok: false,
    logins: { file: { valid: false, age_h: null },
              device: { ok: false, primed: true } },
    export_browser: { normal: "sign in to export", fast: "Google Chrome ×3",
                      dot: "warn", cls_label: "Google Chrome" },
    auth_dot: "bad", auth_text: "No saved login — click Log in",
    login_phase: null, login_label: "Log in",
    checks: {
      browser_msedge: { status: "busy", text: "Microsoft Edge: checking…" },
      browser_chrome: { status: "busy", text: "Google Chrome: checking…" },
      output: { status: "busy", text: "Output folder: checking…" },
      tools: { status: "busy", text: "Report tools: checking…" },
    },
    checks_running: true,
    days: ["2026-06-11 ssor-prod", "2026-06-11 ars-prod", "2026-06-08 ssor-dev", "2026-06-02"],
    can_save_report: false,
    update: { phase: "idle" },
    // Seeded as if a "Check all environments" scan had run, so the Export-tab and
    // matrix env-flag overlays are visible in #mock. Keys = registry labels (must
    // match EXPORT_REPORTS / the matrices' row_labels).
    env_access: {
      "ssor-prod": { key: "ssor-prod", source: "ssor", environment: "prod",
        label: "SSOR / Prod", status: "reports_off", checked_at: "09:14",
        detail: "Signed in, but some report types are greyed out on this site.",
        url: "https://tsmis.dot.ca.gov/",
        reports: { "TSAR: Ramp Summary": "ok", "TSAR: Ramp Detail": "ok",
          "Highway Sequence Listing": "ok", "Highway Log": "greyed",
          "Highway Log (PDF)": "greyed", "Intersection Summary": "ok",
          "Intersection Detail": "missing" } },
      "ars-test": { key: "ars-test", source: "ars", environment: "test",
        label: "ARS / Test", status: "denied", checked_at: "09:14",
        detail: "Authenticated but not in the TSMIS group.", url: "", reports: {} },
    },
    matrix: null,
    matrix_queue: [],            // v0.16.0 pending jobs
    matrix_current: null,        // v0.16.0 running job
    matrix_fast: { on: false, workers: 3 },
    matrix_formulas: false,
    matrix_baseline: "ssor-prod",
    matrix_hidden: [],
    matrix_hidden_envs: [],
    matrix_modes: {},            // row_key -> mode id
    matrix_tsn_files: {},        // subdir -> picked file path
    matrix_row_order: [],        // drag-to-reorder row preference (Everything)
    matrix_env_order: [],        // drag-to-reorder env-column preference
    mock_tsn_pdfs: false,        // TSN already consolidated → vs-TSN shows real
                                 // diffs (set true to demo the consolidate-first
                                 // state: every vs-TSN cell shows "consolidate")
    day_matrix_source: "ssor-prod",
    day_matrix_days: [],
    day_matrix_hidden: [],
    day_matrix_row_order: [],    // drag-to-reorder row preference (by-day)
    day_matrix_formulas: false,
    baseline_matrix_source: "ssor-prod",   // v0.26.0 "vs Baseline" matrix
    baseline_matrix_days: [],
    baseline_matrix_baseline: "",          // "" = unset, "store", "day:<date>"
    baseline_matrix_hidden: [],
    baseline_matrix_row_order: [],
    baseline_matrix_formulas: false,
    evidence: {                  // v0.21.0 visual-evidence toggle (shared); v0.22.0 per-report;
      // v0.24.0 Highway Log (raw-sourced prints) + the named unsupported rows;
      // v0.25.0 Highway Sequence (raw-sourced like Highway Log);
      // v0.26.0 Ramp Detail (statewide print like Intersection Detail)
      on: false, examples: 2, layout: "pair", ready: true, deps_ok: true, tsn_pdfs: 38,
      rows: ["highway_detail", "highway_detail_pdf",
             "highway_log", "highway_log_pdf",
             "highway_sequence", "highway_sequence_pdf",
             "intersection_detail", "intersection_detail_pdf",
             "ramp_detail", "ramp_detail_pdf"],
      dir: "C:\\demo\\tsn_library\\highway_detail\\pdf",
      reports: [
        { key: "highway_detail", label: "Highway Detail", tsn_pdfs: 12,
          dir: "C:\\demo\\tsn_library\\highway_detail\\pdf", source: "pdf" },
        { key: "highway_log", label: "Highway Log", tsn_pdfs: 12,
          dir: "C:\\demo\\tsn_library\\highway_log\\raw", source: "raw" },
        { key: "highway_sequence", label: "Highway Sequence", tsn_pdfs: 12,
          dir: "C:\\demo\\tsn_library\\highway_sequence\\raw", source: "raw" },
        { key: "intersection_detail", label: "Intersection Detail", tsn_pdfs: 1,
          dir: "C:\\demo\\tsn_library\\intersection_detail\\pdf", source: "pdf" },
        { key: "ramp_detail", label: "Ramp Detail", tsn_pdfs: 1,
          dir: "C:\\demo\\tsn_library\\ramp_detail\\pdf", source: "pdf" },
      ],
      row_reports: {
        highway_detail: "highway_detail", highway_detail_pdf: "highway_detail",
        highway_log: "highway_log", highway_log_pdf: "highway_log",
        highway_sequence: "highway_sequence",
        highway_sequence_pdf: "highway_sequence",
        intersection_detail: "intersection_detail",
        intersection_detail_pdf: "intersection_detail",
        ramp_detail: "ramp_detail",
        ramp_detail_pdf: "ramp_detail",
      },
      unsupported: ["TSAR: Ramp Summary", "Intersection Summary"],
    },
  };
  const mockSettings = {
    report_timeout_min: 6, fast_timeout_min: 10, retry_timeout_min: 15,
    county_timeout_s: 60, fast_workers: 3, debug_logging: false, ui_devtools: false,
    env_check_after_signin: true, env_check_after_start: false, notify_on_finish: true,
  };
  const mockUrlOverrides = {};
  const mockChromium = { bundled: false, downloaded: false, downloaded_mb: 0,
                         active: false, dir: "C:\\Tools\\TSMIS Exporter\\data\\ms-playwright" };
  // Settings ▸ TSN reports panel — one row per registered report (mixed states so
  // the green/amber dots, the "Rebuild" disabled-until-raw, and the Import/Rebuild
  // buttons are all verifiable in #mock).
  // `cons` (consolidated workbook EXISTS) is independent of `current` (exists AND
  // not older than the raw) — exactly as the real bridge reports them — so every
  // panel state is reachable in #mock: current (cons+current), STALE (cons, not
  // current), raw-only/not-built (no cons), and no-raw.
  const mockTsnLib = {
    ramp_summary:        { label: "TSN Ramp Summary", raw_kind: "statewide_pdf", raw_count: 1, present: true, cons: true, current: true },
    ramp_detail:         { label: "TSN Ramp Detail", raw_kind: "statewide_xlsx", raw_count: 1, present: true, cons: true, current: true },
    intersection_summary:{ label: "TSN Intersection Summary", raw_kind: "statewide_pdf", raw_count: 1, present: true, cons: true, current: false },   // STALE
    intersection_detail: { label: "TSN Intersection Detail", raw_kind: "statewide_xlsx", raw_count: 1, present: true, cons: false, current: false }, // raw imported, not built
    highway_sequence:    { label: "TSN Highway Sequence", raw_kind: "district_pdfs", raw_count: 12, present: true, cons: true, current: false },      // STALE
    highway_log:         { label: "TSN Highway Log", raw_kind: "district_pdfs", raw_count: 0, present: false, cons: false, current: false },          // no raw
  };
  const MOCK_TSN_ROOT = "C:\\Tools\\TSMIS Exporter\\data\\tsn_library";
  // The manually-stocked ArcGIS layer drop-zone (staged only — nothing reads it yet).
  const MOCK_ARCGIS = {
    root: "C:\\Tools\\TSMIS Exporter\\data\\arcgis_layers",
    count: 2,
    files: [{ name: "IMLayers.xlsx", size: 111634434 },
            { name: "Layers7.20.xlsx", size: 355772572 }],
  };
  // Evidence prints are the SECOND TSN asset (the images crop from them). Mixed
  // states again so every panel case is reachable in #mock: prints present, prints
  // MISSING, prints covered by the report's own raw, and no evidence support.
  const mockTsnEvidence = {
    ramp_detail:         { pdfs: 1, in_raw: false },
    intersection_detail: { pdfs: 0, in_raw: false },   // MISSING -> evidence can't render
    highway_sequence:    { pdfs: 12, in_raw: true },   // same district prints as raw
    highway_log:         { pdfs: 0, in_raw: true },    // no raw yet, so no prints either
  };
  function mockTsnLibraryRows() {
    return Object.entries(mockTsnLib).map(([report, m]) => {
      const ev = mockTsnEvidence[report];
      return {
        report, label: m.label, raw_kind: m.raw_kind,
        raw_present: m.present, raw_count: m.raw_count,
        consolidated_present: m.cons, current: m.current,
        raw_dir: `${MOCK_TSN_ROOT}\\${report}\\raw`,
        evidence_supported: !!ev,
        evidence_pdfs: ev ? ev.pdfs : 0,
        evidence_dir: ev
          ? `${MOCK_TSN_ROOT}\\${report}\\${ev.in_raw ? "raw" : "pdf"}` : "",
        evidence_in_raw: !!(ev && ev.in_raw),
        // Mirrors the bridge's first-failing-condition reason so the panel's
        // "why is it stale" line is verifiable in #mock.
        stale_reason: m.current ? ""
          : !m.present ? "no raw TSN files imported yet"
          : !m.cons ? "not built yet — rebuild it"
          : (m.stale_reason
             || "built by an older normalizer — rebuild it (expected once after an app update)"),
      };
    });
  }
  function mockSiteUrlRows() {
    const rows = [];
    for (const src of ["ssor", "ars"]) {
      for (const env of ["prod", "test", "dev"]) {
        const key = `${src}-${env}`;
        const dflt = `https://tsmis.dot.ca.gov/index.html?env=${env}&src=${src}`;
        rows.push({ key, source: src, environment: env,
                    label: `${src.toUpperCase()} · ${env[0].toUpperCase()}${env.slice(1)}`,
                    default: dflt, url: mockUrlOverrides[key] || dflt,
                    custom: !!mockUrlOverrides[key] });
      }
    }
    return rows;
  }
  function mockSettingsPayload() {
    return {
      values: { ...mockSettings }, defaults: { ...mockSettings },
      site_urls: mockSiteUrlRows(), chromium: { ...mockChromium },
      tsn_library: mockTsnLibraryRows(), tsn_library_root: MOCK_TSN_ROOT,
      arcgis_layers: { ...MOCK_ARCGIS },
      meta: {
        version: "0.26.2 (preview)", build: "portable app",
        variant: "system browser", update_support: "ok",
        data_root: "C:\\Tools\\TSMIS Exporter",
        output_root: "C:\\Tools\\TSMIS Exporter\\output",
        log_file: "C:\\Tools\\TSMIS Exporter\\data\\logs\\tsmis.log",
        failures_dir: "C:\\Tools\\TSMIS Exporter\\data\\failures",
        auth_state: "none", max_workers: 30,
      },
    };
  }
  let timer = null;
  let mockCompareOverwrite = null;
  const push = (...evs) => dispatch(evs);
  const pushState = () => push({ t: "state", s: JSON.parse(JSON.stringify(st)) });

  // A canned 5-row x 6-env snapshot exercising every cell + mode state so the grid,
  // colours, mode dropdowns and TSN pickers are all verifiable in #mock.
  function mockMatrixModes(rk) {
    if (rk === "highway_log") return [
      { id: "env", label: "Cross-environment", kind: "env", supported: true },
      { id: "tsn", label: "vs TSN", kind: "tsn", supported: true },
      { id: "vs_pdf", label: "vs TSMIS PDF", kind: "self", supported: true }];
    if (rk === "highway_log_pdf") return [
      { id: "env", label: "Cross-environment", kind: "env", supported: true },   // v0.17.0: PDF cross-env coded
      { id: "tsn", label: "vs TSN", kind: "tsn", supported: true },
      { id: "vs_excel", label: "vs TSMIS Excel", kind: "self", supported: true }];
    if (rk === "intersection_detail_pdf") return [   // CR-002: the exact HL-PDF parallel
      { id: "env", label: "Cross-environment", kind: "env", supported: true },
      { id: "tsn", label: "vs TSN", kind: "tsn", supported: true },
      { id: "vs_excel", label: "vs TSMIS Excel", kind: "self", supported: true }];
    if (rk === "highway_sequence_pdf") return [      // v0.25.0: the HD/HL-PDF parallel
      { id: "env", label: "Cross-environment", kind: "env", supported: true },
      { id: "tsn", label: "vs TSN", kind: "tsn", supported: true },
      { id: "vs_excel", label: "vs TSMIS Excel", kind: "self", supported: true }];
    if (rk === "ramp_detail_pdf") return [           // v0.26.0: the HSL-PDF parallel
      { id: "env", label: "Cross-environment", kind: "env", supported: true },
      { id: "tsn", label: "vs TSN", kind: "tsn", supported: true },
      { id: "vs_excel", label: "vs TSMIS Excel", kind: "self", supported: true }];
    return [
      { id: "env", label: "Cross-environment", kind: "env", supported: true },
      { id: "tsn", label: "vs TSN", kind: "tsn", supported: true }];   // all reports vs-TSN as of v0.17.0
  }
  function mockCmp(s) {
    if (s === "needtsn") return { supported: true, built: false, stale: true,
      reason: "missing", missing_side: "tsn", verdict: null, diff_cells: null, one_sided: null };
    if (s === "missing") return { supported: true, built: false, stale: true,
      reason: "missing", missing_side: "cell", verdict: null, diff_cells: null, one_sided: null };
    if (s === "notbuilt") return { supported: true, built: false, stale: true,
      reason: "missing", missing_side: null, verdict: null, diff_cells: null, one_sided: null };
    if (s === "stale") return { supported: true, built: true, stale: true,
      reason: "cell_newer", missing_side: null, completion: "complete",
      verdict: "diff", diff_cells: 18, one_sided: 2 };
    // CMP-AUD-089: a cell whose LAST refresh failed — the previous result stands,
    // marked, so the preview exercises the attempt overlay too.
    if (s === "attempt") return { supported: true, built: true, stale: false,
      reason: "fresh", missing_side: null, completion: "complete", verdict: "match",
      diff_cells: 0, one_sided: 0,
      last_attempt: { status: "error", reason: "the rebuild could not finish", at: 0 } };
    return { supported: true, built: true, stale: false, reason: "fresh", missing_side: null,
             completion: "complete",
             verdict: (s[0] === 0 && s[1] === 0) ? "match" : "diff", diff_cells: s[0], one_sided: s[1] };
  }
  function mockApplyOrder(keys, order) {
    if (!order || !order.length) return keys.slice();
    const ks = new Set(keys);
    const front = order.filter((k) => ks.has(k));
    const fs = new Set(front);
    return front.concat(keys.filter((k) => !fs.has(k)));
  }
  function mockMatrixSnapshot(baseline) {
    const allEnvs = ["ssor-prod", "ssor-test", "ssor-dev", "ars-prod", "ars-test", "ars-dev"];
    const henv = st.matrix_hidden_envs || [];
    const envs = mockApplyOrder(allEnvs.filter((e) => henv.indexOf(e) < 0), st.matrix_env_order);
    const allRows = [
      { key: "ramp_summary", label: "TSAR: Ramp Summary", tsn_capable: true },
      { key: "ramp_detail", label: "TSAR: Ramp Detail", tsn_capable: true },
      { key: "highway_sequence", label: "Highway Sequence Listing", tsn_capable: true },
      { key: "highway_log", label: "Highway Log", tsn_capable: true },
      { key: "intersection_summary", label: "Intersection Summary", tsn_capable: true },
      { key: "intersection_detail", label: "Intersection Detail", tsn_capable: true },
      { key: "highway_log_pdf", label: "Highway Log (PDF)", tsn_capable: true },
      { key: "intersection_detail_pdf", label: "Intersection Detail (PDF)", tsn_capable: true },
      { key: "highway_sequence_pdf", label: "Highway Sequence Listing (PDF)", tsn_capable: true },
      { key: "ramp_detail_pdf", label: "TSAR: Ramp Detail (PDF)", tsn_capable: true },
    ];
    const rowLabels = {}; allRows.forEach((r) => { rowLabels[r.key] = r.label; });
    const hidden = st.matrix_hidden || [];
    const rows = mockApplyOrder(
      allRows.map((r) => r.key).filter((k) => hidden.indexOf(k) < 0), st.matrix_row_order);
    const envLabels = {};
    allEnvs.forEach((e) => { const [s, v] = e.split("-");
      envLabels[e] = `${s.toUpperCase()} / ${v[0].toUpperCase()}${v.slice(1)}`; });
    // env-mode samples (vs the baseline column).
    const envSample = {
      // CMP-AUD-089: ramp_summary/ars-prod carries a FAILED last refresh — the
      // previous match stands, marked, so the preview shows the overlay in the
      // default (cross-environment) mode too.
      ramp_summary: { "ssor-test": [42, 0], "ssor-dev": [42, 0], "ars-prod": "attempt", "ars-test": [48, 0], "ars-dev": "stale" },
      ramp_detail: { "ssor-test": [25, 10], "ssor-dev": [25, 10], "ars-prod": [0, 0], "ars-test": [31, 10], "ars-dev": "missing" },
      highway_sequence: { "ssor-test": [25, 12], "ssor-dev": [23, 12], "ars-prod": [2, 0], "ars-test": [560, 156], "ars-dev": [102, 44] },
      highway_log: { "ssor-test": [7, 1], "ssor-dev": [7, 1], "ars-prod": [0, 0], "ars-test": [88, 12], "ars-dev": "stale" },
      intersection_summary: { "ssor-test": [3, 0], "ssor-dev": [3, 0], "ars-prod": [0, 0], "ars-test": [40, 2], "ars-dev": "stale" },
      intersection_detail: { "ssor-test": [12, 3], "ssor-dev": [12, 3], "ars-prod": [0, 0], "ars-test": [210, 44], "ars-dev": "stale" },
      highway_log_pdf: { "ssor-test": [7, 1], "ssor-dev": [7, 1], "ars-prod": [0, 0], "ars-test": [88, 12], "ars-dev": "stale" },
      intersection_detail_pdf: { "ssor-test": [12, 3], "ssor-dev": [12, 3], "ars-prod": [0, 0], "ars-test": [210, 44], "ars-dev": "stale" },
      highway_sequence_pdf: { "ssor-test": [25, 12], "ssor-dev": [23, 12], "ars-prod": [2, 0], "ars-test": [560, 156], "ars-dev": [102, 44] },
      ramp_detail_pdf: { "ssor-test": [25, 10], "ssor-dev": [25, 10], "ars-prod": [0, 0], "ars-test": [31, 10], "ars-dev": "missing" },
    };
    const cells = {}, modes = {}, rowModes = {}, tsnMeta = {};
    rows.forEach((rk) => {
      const avail = mockMatrixModes(rk);
      let selId = (st.matrix_modes || {})[rk] || "env";
      if (!avail.some((m) => m.id === selId)) selId = "env";
      const mode = avail.find((m) => m.id === selId) || avail[0];
      modes[rk] = mode.id; rowModes[rk] = avail;
      // Per-row TSN dataset: each PDF report SHARES its Excel sibling's TSN dataset
      // (highway_log_pdf→highway_log, intersection_detail_pdf→intersection_detail,
      // highway_sequence_pdf→highway_sequence, ramp_detail_pdf→ramp_detail); every
      // other report has its OWN (mirrors the real matrix + the by-day mock).
      const tsnSub = (rk === "highway_log_pdf") ? "highway_log"
        : (rk === "intersection_detail_pdf") ? "intersection_detail"
        : (rk === "highway_sequence_pdf") ? "highway_sequence"
        : (rk === "ramp_detail_pdf") ? "ramp_detail" : rk;
      const isPdfs = (tsnSub === "highway_log" || tsnSub === "highway_sequence");
      const tsnFile = (st.matrix_tsn_files || {})[tsnSub];
      const srcKind = tsnFile ? "file" : (isPdfs && st.mock_tsn_pdfs) ? "pdfs" : "consolidated";
      if (mode.kind === "tsn") {
        tsnMeta[rk] = { supported: mode.supported,
          fmt: (rk === "highway_log_pdf" || rk === "intersection_detail_pdf"
                || rk === "highway_sequence_pdf" || rk === "ramp_detail_pdf")
            ? "pdf" : "excel",
          source_kind: srcKind, pdf_count: srcKind === "pdfs" ? 12 : undefined,
          source_path: tsnFile || (srcKind === "consolidated"
            ? `…\\_tsn_input\\${tsnSub}\\tsn_${tsnSub}_consolidated.xlsx` : undefined),
          tsn_subdir: tsnSub, file: tsnFile || null,
          input_dir: `C:\\Tools\\TSMIS Exporter\\output\\All Reports (current)\\_tsn_input\\${tsnSub}` };
      }
      cells[rk] = {};
      envs.forEach((env, i) => {
        const isB = mode.kind === "env" && env === baseline;
        let cmp;
        if (!mode.supported) cmp = { supported: false };
        else if (isB) cmp = null;
        else if (mode.kind === "env") {
          const s = (envSample[rk] || {})[env];
          cmp = mockCmp(s || "missing");
        } else if (mode.kind === "tsn") {
          cmp = (srcKind === "pdfs" || srcKind === "none") ? mockCmp("needtsn")
            : mockCmp(["ssor-prod", "ssor-test"].indexOf(env) >= 0 ? [4, 1]
                : env === "ars-prod" ? [0, 0] : env === "ars-dev" ? "stale"
                  : env === "ars-test" ? "attempt" : [73, 9]);
        } else {                               // self (PDF vs Excel) — per env
          cmp = mockCmp(env === baseline ? [11, 0] : i % 4 === 0 ? "notbuilt" : [11, 0]);
        }
        cells[rk][env] = { export: { present: true, mtime: 0,
                                     age_seconds: env.endsWith("dev") ? 5 * 86400 : 2 * 3600 },
                           is_baseline: isB, cmp,
                           comparison: mode.kind === "env" ? cmp : undefined };
      });
    });
    return { dest: st.batch_dest || "C:\\Tools\\TSMIS Exporter\\output\\All Reports (current)",
             baseline, rows, row_labels: rowLabels, all_rows: allRows, hidden,
             modes, row_modes: rowModes, tsn_meta: tsnMeta,
             envs, all_envs: allEnvs, hidden_envs: henv, env_labels: envLabels, cells };
  }
  const MOCK_DAY_AVAIL = {
    "ssor-prod": ["2026-06-18", "2026-06-17", "2026-06-11"],
    "ars-prod": ["2026-06-17", "2026-06-11"],
    "ssor-test": ["2026-06-16"], "ssor-dev": [], "ars-test": [], "ars-dev": [],
  };
  // The 12 matrix report rows (shared by the by-day and vs-Baseline mocks —
  // parity with reports.matrix_rows(): Highway Detail included since v0.20.0).
  const MOCK_DAY_ROWS = [
    { key: "highway_log", label: "Highway Log", supported: true },
    { key: "highway_log_pdf", label: "Highway Log (PDF)", supported: true },
    { key: "ramp_summary", label: "TSAR: Ramp Summary", supported: true },
    { key: "ramp_detail", label: "TSAR: Ramp Detail", supported: true },
    { key: "ramp_detail_pdf", label: "TSAR: Ramp Detail (PDF)", supported: true },
    { key: "highway_sequence", label: "Highway Sequence Listing", supported: true },
    { key: "highway_sequence_pdf", label: "Highway Sequence Listing (PDF)", supported: true },
    { key: "highway_detail", label: "Highway Detail", supported: true },
    { key: "highway_detail_pdf", label: "Highway Detail (PDF)", supported: true },
    { key: "intersection_summary", label: "Intersection Summary", supported: true },
    { key: "intersection_detail", label: "Intersection Detail", supported: true },
    { key: "intersection_detail_pdf", label: "Intersection Detail (PDF)", supported: true },
  ];
  function mockDayMatrixSnapshot() {
    const source = st.day_matrix_source || "ssor-prod";
    const days = st.day_matrix_days || [];
    const allRows = MOCK_DAY_ROWS;
    const hidden = st.day_matrix_hidden || [];
    const _visible = allRows.filter((r) => hidden.indexOf(r.key) < 0);
    const _byKey = {}; _visible.forEach((r) => { _byKey[r.key] = r; });
    const shown = mockApplyOrder(_visible.map((r) => r.key), st.day_matrix_row_order)
      .map((k) => _byKey[k]);
    const rowLabels = {}, rowSupported = {};
    allRows.forEach((r) => { rowLabels[r.key] = r.label; rowSupported[r.key] = r.supported; });
    // Per-row TSN datasets (parity with the real engine + the Everything mock):
    // Highway Log (×2) and Highway Sequence are district PDFs (the "12 TSN PDFs →
    // Consolidate" state); the rest resolve to a statewide workbook. A picked file
    // (matrix_tsn_files) overrides per report.
    const tsnMeta = {};
    shown.forEach((r) => {
      const sub = r.key;
      // Each PDF row shares its Excel sibling's TSN dataset (highway_log_pdf→
      // highway_log, intersection_detail_pdf→intersection_detail,
      // highway_sequence_pdf→highway_sequence, ramp_detail_pdf→ramp_detail) —
      // mirror the real engine (and the Everything mock) so the picker
      // reads/writes matrix_tsn_files under the right key.
      const tsnSub = (sub === "highway_log_pdf") ? "highway_log"
        : (sub === "intersection_detail_pdf") ? "intersection_detail"
        : (sub === "highway_sequence_pdf") ? "highway_sequence"
        : (sub === "highway_detail_pdf") ? "highway_detail"
        : (sub === "ramp_detail_pdf") ? "ramp_detail" : sub;
      const isPdfs = (tsnSub === "highway_log" || tsnSub === "highway_sequence");
      const file = (st.matrix_tsn_files || {})[tsnSub];
      const kind = file ? "file" : (isPdfs && st.mock_tsn_pdfs) ? "pdfs" : "consolidated";
      tsnMeta[sub] = {
        supported: !!r.supported,
        fmt: (sub === "highway_log_pdf" || sub === "intersection_detail_pdf"
              || sub === "highway_sequence_pdf" || sub === "highway_detail_pdf"
              || sub === "ramp_detail_pdf") ? "pdf" : "excel",
        source_kind: kind, pdf_count: kind === "pdfs" ? 12 : undefined,
        source_path: file || (kind === "consolidated"
          ? `…\\_tsn_input\\${tsnSub}\\tsn_${tsnSub}_consolidated.xlsx` : undefined),
        tsn_subdir: tsnSub, file: file || null,
        input_dir: `C:\\Tools\\TSMIS Exporter\\output\\All Reports (current)\\_tsn_input\\${tsnSub}` };
    });
    const cells = {};
    shown.forEach((r) => {
      cells[r.key] = {};
      const tsnReady = (tsnMeta[r.key] || {}).source_kind !== "pdfs";
      days.forEach((d, i) => {
        const present = !(r.key === "highway_log_pdf" && d === "2026-06-11");
        let cmp;
        if (!r.supported) cmp = { supported: false };
        else if (!present) cmp = mockCmp("missing");
        else if (!tsnReady) cmp = mockCmp("needtsn");
        else cmp = mockCmp(i === 0 ? [4, 1] : i === 1 ? [0, 0] : "notbuilt");
        cells[r.key][d] = { export: { present, mtime: 0,
          age_seconds: present ? (i + 1) * 86400 : null }, cmp };
      });
    });
    return { source, sources: ["ssor-prod", "ssor-test", "ssor-dev", "ars-prod", "ars-test", "ars-dev"]
               .map((k) => { const [s, v] = k.split("-");
                 return { key: k, label: `${s.toUpperCase()} / ${v[0].toUpperCase()}${v.slice(1)}` }; }),
             days, today: MOCK_TODAY, rows: shown.map((r) => r.key), row_labels: rowLabels,
             row_supported: rowSupported, all_rows: allRows, hidden,
             tsn_meta: tsnMeta, cells,
             day_consolidated: Object.fromEntries(days.map((d, i) =>
               [d, { exists: i % 3 !== 0, fresh: i % 2 === 0, actionable: i % 4 !== 0 }])),
             available_days: MOCK_DAY_AVAIL[source] || [] };
  }
  // v0.26.0 "vs Baseline" matrix mock — day columns within one source, each cell
  // vs the picked baseline (an earlier day, or the Everything store).
  function mockBaselineOptions(source) {
    const days = MOCK_DAY_AVAIL[source] || [];
    const total = MOCK_DAY_ROWS.length;
    const opts = days.length
      ? [{ id: "store", label: "All Reports store", present: total, total }]
      : [];
    days.forEach((d, i) => opts.push({
      id: `day:${d}`, label: d, present: total - (i === days.length - 1 ? 3 : 0),
      total }));
    return opts;
  }
  function mockBaselineMatrixSnapshot() {
    const source = st.baseline_matrix_source || "ssor-prod";
    const days = st.baseline_matrix_days || [];
    const blId = st.baseline_matrix_baseline || "";
    const blDate = blId.indexOf("day:") === 0 ? blId.slice(4) : null;
    const hidden = st.baseline_matrix_hidden || [];
    const _visible = MOCK_DAY_ROWS.filter((r) => hidden.indexOf(r.key) < 0);
    const _byKey = {}; _visible.forEach((r) => { _byKey[r.key] = r; });
    const shown = mockApplyOrder(_visible.map((r) => r.key), st.baseline_matrix_row_order)
      .map((k) => _byKey[k]);
    const rowLabels = {}, rowSupported = {};
    MOCK_DAY_ROWS.forEach((r) => { rowLabels[r.key] = r.label; rowSupported[r.key] = r.supported; });
    const blPresent = {};
    shown.forEach((r, i) => {
      // the store covers everything; the oldest day misses a few reports —
      // exercises the "baseline not exported" cell state
      blPresent[r.key] = { present: !(blDate === "2026-06-11" && i % 4 === 3), mtime: 0 };
    });
    const cells = {};
    shown.forEach((r, ri) => {
      cells[r.key] = {};
      days.forEach((d, i) => {
        const present = !(r.key === "highway_log_pdf" && d === "2026-06-11");
        let cmp;
        if (!r.supported) cmp = { supported: false };
        else if (!blId) cmp = mockCmp("missing");
        else if (d === blDate) cmp = { supported: true, is_baseline: true };
        else if (!present) cmp = mockCmp("missing");
        else if (!blPresent[r.key].present) cmp = { supported: true, built: false,
          stale: false, missing_side: "baseline" };
        else cmp = mockCmp(i === 0 ? (ri % 3 === 0 ? [7, 2] : [0, 0]) : "notbuilt");
        cells[r.key][d] = { export: { present, mtime: 0,
          age_seconds: present ? (i + 1) * 86400 : null }, cmp };
      });
    });
    return { source,
             sources: ["ssor-prod", "ssor-test", "ssor-dev", "ars-prod", "ars-test", "ars-dev"]
               .map((k) => { const [s, v] = k.split("-");
                 return { key: k, label: `${s.toUpperCase()} / ${v[0].toUpperCase()}${v.slice(1)}` }; }),
             days,
             baseline: { id: blId || null, kind: blId === "store" ? "store" : blDate ? "day" : null,
                         date: blDate,
                         label: blId ? (blId === "store"
                           ? `${source.toUpperCase()} (store)` : `${source.toUpperCase()} ${blDate}`) : null,
                         dir: blId ? "C:\\demo\\baseline" : null, present: blPresent },
             rows: shown.map((r) => r.key), row_labels: rowLabels,
             row_supported: rowSupported, all_rows: MOCK_DAY_ROWS, hidden, cells,
             available_days: MOCK_DAY_AVAIL[source] || [],
             baseline_options: mockBaselineOptions(source) };
  }
  // v0.16.0 mock job queue — mirrors gui_api: enqueue, run one at a time, auto-
  // advance. `kind` drives the run-mode/icon; `total` feeds the compare progress.
  let mockJobSeq = 0;
  function mockEnqueue(kind, scope, label, opts) {
    opts = opts || {};
    mockJobSeq++;
    const job = { id: mockJobSeq, kind, scope, label, status: "queued",
                  fast: !!opts.fast, total: opts.total || 1,
                  which: opts.which || "env",
                  mode: kind === "export" ? "export" : "consolidate" };
    st.matrix_queue = [...(st.matrix_queue || []), job];
    if (st.task || st.matrix_current) {
      push({ t: "log", text: `Queued (#${st.matrix_queue.length}): ${label}.` });
    }
    pushState();
    mockTryStartNext();
    return { ok: true, job_id: job.id, queued: st.matrix_queue.length };
  }
  function mockTryStartNext() {
    if (st.task || st.matrix_current || !(st.matrix_queue || []).length) return;
    const job = st.matrix_queue.shift();
    st.task = "matrix";
    st.matrix_current = { ...job, status: "running" };
    if (job.kind !== "export") {
      st.matrix = { phase: "comparing", row: null, cell: null, done: 0, total: job.total };
    }
    pushState();
    const workers = job.fast ? (st.matrix_fast.workers || 3) : 1;
    push({ t: "run_started", mode: job.mode, label: job.label, workers },
         { t: "log", text: job.label });
    setTimeout(() => {
      const finished = st.matrix_current;
      st.task = null; st.matrix = null; st.matrix_current = null;
      // PRODUCTION order (v0.18.4 lesson): run_ended -> state -> matrix_refresh.
      // The mock used to push state first, which made order-sensitive bugs
      // (the queue-phantom) unreproducible in #mock.
      push({ t: "run_ended" });
      pushState();
      push({ t: "matrix_refresh" });
      // A by-day EXPORT chains a compare for the same scope (mirrors the real
      // bridge's export -> consolidate -> compare so the column fills itself).
      if (finished && finished.kind === "export" && finished.which === "day") {
        const cs = finished.scope === "cell" ? "cell" : finished.scope === "row" ? "row" : "column";
        mockEnqueue("compare", cs, finished.label.replace(/^Export /, "Compare "),
                    { which: "day", total: finished.total });
      } else {
        mockTryStartNext();      // auto-advance
      }
    }, 700);
  }

  // A fake TSMIS page screenshot (canvas → JPEG base64) so the preview modal
  // can be styled without the real app.
  function mockShotB64(envLabel, detail) {
    const c = document.createElement("canvas");
    c.width = 1280; c.height = 720;
    const g = c.getContext("2d");
    g.fillStyle = "#f4f6f9"; g.fillRect(0, 0, 1280, 720);
    g.fillStyle = "#1f3864"; g.fillRect(0, 0, 1280, 64);
    g.fillStyle = "#ffffff"; g.font = "bold 26px Segoe UI";
    g.fillText("TSMIS — Transportation System Management", 24, 42);
    g.fillStyle = "#c00000"; g.font = "bold 30px Segoe UI";
    g.fillText(envLabel, 1020, 44);
    g.fillStyle = "#222"; g.font = "20px Segoe UI";
    g.fillText("(mock screenshot) " + detail, 24, 120);
    g.strokeStyle = "#bbb";
    for (let i = 0; i < 14; i++) {
      g.strokeRect(24, 150 + i * 38, 1230, 38);
    }
    return c.toDataURL("image/jpeg", 0.75).split(",")[1];
  }

  function finishChecks() {
    st.checks.output = { status: "ok", text: "Output folder: writable" };
    st.checks.tools = { status: "ok", text: "Report tools (PDF/Excel): ready" };
    st.checks.browser_msedge = { status: "ok", text: "Microsoft Edge: ready" };
    st.checks.browser_chrome = { status: "bad", text: "Google Chrome: not installed" };
    st.checks_running = false;
    // simulate the launch update check finding a new release
    st.update = { phase: "available", version: "9.9.9", url: "#", size_mb: 148, can_apply: true };
    pushState();
    push({ t: "log", text: "Update available: v9.9.9 (148 MB) — click ‘Update to v9.9.9’ in the title bar to install it." });
  }

  function runMockExport(reports, routes, fast, workers, autoConsolidate) {
    st.task = "export"; st.fast_run = fast; st.last_summary = null;
    st.auth_dot = "busy";
    st.auth_text = reports.length > 1 ? `Exporting ${reports.length} report(s)…`
                                      : `Exporting ${repByKey(reports[0]).label}…`;
    pushState();
    const names = reports.map((k) => repByKey(k).label).join(", ");
    const nWorkers = fast ? workers : 1;
    let msg = `Starting export: ${names}`;
    if (routes.length !== ROUTES.length) msg += `   ·   ${routes.length} routes`;
    if (fast) msg += `   ·   FAST MODE (${workers} browsers)`;
    push({ t: "log", text: msg },
         { t: "run_started", mode: "export", label: "Working…", workers: nWorkers });
    for (let w = 1; w <= nWorkers; w++) {
      push({ t: "wstatus", w, text: "Starting browser…" });
    }

    const total = routes.length;
    let done = 0;
    let tick = 0;
    const counts = { saved: 0, empty: 0, skipped: 0, failed: 0, exists: 0 };
    timer = setInterval(() => {
      tick++;
      if (done >= total) {
        clearInterval(timer); timer = null;
        push({ t: "log", text: "" },
             { t: "log", text: `Done. ${total} routes handled — saved ${counts.saved}, already had ${counts.exists}, empty ${counts.empty}, skipped ${counts.skipped}, failed ${counts.failed}.` });
        if (autoConsolidate) {
          const AUTO_CONS = ["ramp_summary", "ramp_detail", "highway_sequence", "highway_log"];
          reports.filter((k) => AUTO_CONS.includes(k)).forEach((k) =>
            push({ t: "log", text: `Auto-consolidating ${repByKey(k).label}… done.` }));
        }
        // P1: the producer-owned outcome, mirroring the backend's outcome.py +
        // _build_export_summary (a skipped/failed run is partial, all-empty is
        // no_data). A plain mock export writes to a dated folder, so artifact is
        // new_unpromoted (no store swap).
        const completion = counts.failed || counts.skipped ? "partial"
          : (counts.saved + counts.exists) > 0 ? "complete"
            : counts.empty > 0 ? "no_data" : "no_data";
        const artifact = "new_unpromoted";
        push({ t: "run_ended", completion, artifact });
        st.task = null; st.fast_run = false; st.can_save_report = true;
        const failedRoutes = routes.slice(0, counts.failed);
        st.last_summary = {
          reports: reports.map((k, n) => ({ label: repByKey(k).label, ...counts,
            completion, artifact, failed_routes: n === 0 ? failedRoutes : [] })),
          totals: { ...counts }, failed_total: counts.failed, cancelled: false,
          completion, artifact,
          run_folder: "C:\\Tools\\TSMIS Exporter\\output\\2026-06-17 ssor-prod",
        };
        st.auth_dot = st.authed ? "ok" : "bad";
        st.auth_text = st.authed ? "Session ready" : "No saved login — click Log in";
        pushState();
        return;
      }
      const route = routes[done];
      const r = Math.random();
      const status = r < 0.82 ? "saved" : r < 0.88 ? "exists" : r < 0.94 ? "empty" : r < 0.97 ? "skipped" : "failed";
      counts[status === "exists" ? "exists" : status === "saved" ? "saved" : status === "empty" ? "empty" : status === "skipped" ? "skipped" : "failed"]++;
      done++;
      const w = 1 + (tick % nWorkers);
      push({ t: "wstatus", w, text: `[${String(done).padStart(3)}/${total}] Route ${route}: working… (${(Math.random() * 60 + 3).toFixed(0)}s)` });
      if (status === "saved") push({ t: "log", text: `Route ${route}: saved (${(Math.random() * 3 + 0.4).toFixed(1)} MB, ${(Math.random() * 40 + 8).toFixed(0)}s)` });
      if (status === "failed") push({ t: "log", text: `Route ${route}: FAILED — TSMIS site error (see failures folder)` });
      push({ t: "progress", p: { done, total, route, report: repByKey(reports[0]).label, report_i: 1, report_n: reports.length, ...counts } });
    }, fast ? 120 : 350);
  }

  function runMockBatch(reports, envs, fast, workers, auto) {
    st.task = "batch"; st.fast_run = fast; st.auth_dot = "busy";
    st.auth_text = "Export Everything…"; st.batch_resume = null;
    pushState();
    push({ t: "log", text: `Starting Export Everything: ${reports.length} report type(s) `
            + `across ${envs.length} environment(s)`
            + (fast ? `   ·   FAST MODE (${workers} browsers)` : "")
            + (auto ? "   ·   auto-consolidate" : "") },
         { t: "run_started", mode: "batch", label: "Working…", workers: fast ? workers : 1 });
    const envLabel = (key) => {
      const [s, e] = key.split("-");
      const sl = ((S.init.sources || []).find((x) => x.id === s) || {}).label || s.toUpperCase();
      const el = ((S.init.envs || []).find((x) => x.id === e) || {}).label || e;
      return `${sl} / ${el}`;
    };
    const stepViews = (curIdx) => envs.map((key, j) => ({
      key, label: envLabel(key),
      state: j < curIdx ? "done" : j === curIdx ? "running" : "pending",
    }));
    const reps = reports.map((k) => repByKey(k));
    const ROUTES_DEMO = ["005", "010", "099", "101"];
    let ei = 0;
    const nextEnv = () => {
      if (ei >= envs.length) {
        push({ t: "log", text: "" },
             { t: "log", text: `Export Everything finished — all ${envs.length} environment(s) done.` },
             { t: "run_ended" });
        st.task = null; st.fast_run = false; st.batch = null; st.batch_resume = null;
        st.auth_dot = st.authed ? "ok" : "bad";
        st.auth_text = st.authed ? "Session ready" : "No saved login — click Log in";
        pushState();
        return;
      }
      const key = envs[ei];
      st.batch = { label: envLabel(key), done: ei, total: envs.length,
                   src: key.split("-")[0], env: key.split("-")[1], steps: stepViews(ei) };
      pushState();
      push({ t: "log", text: "" },
           { t: "log", text: `========== ${key.toUpperCase()}  (${ei + 1} of ${envs.length}) ==========` });
      let ri = 0;
      const nextReport = () => {
        if (ri >= reps.length) { ei++; timer = setTimeout(nextEnv, 250); return; }
        const rep = reps[ri];
        let k = 0;
        const tick = () => {
          k++;
          const done = Math.min(k, ROUTES_DEMO.length);
          push({ t: "progress", p: {
            done, total: ROUTES_DEMO.length,
            route: ROUTES_DEMO[Math.min(k - 1, ROUTES_DEMO.length - 1)],
            report: rep.label, report_i: ri + 1, report_n: reps.length,
            saved: done, empty: 0, skipped: 0, failed: 0, exists: 0 } });
          if (k >= ROUTES_DEMO.length) {
            push({ t: "log", text: `  ${rep.label}: exported${auto && ri < 4 ? ", consolidated" : ""}` });
            ri++; timer = setTimeout(nextReport, 160);
          } else {
            timer = setTimeout(tick, fast ? 80 : 170);
          }
        };
        timer = setTimeout(tick, 110);
      };
      nextReport();
    };
    timer = setTimeout(nextEnv, 350);
  }

  const mockApi = {
    get_initial_state: async () => ({
      // P9: mirror the backend's bridge-enum surface (gui_api.get_initial_state ->
      // contract.initial_state_enums) so the preview's init payload matches production.
      contract: window.CONTRACT,
      app_name: "TSMIS Exporter", version: "0.26.2 (preview)",
      output_root: "C:\\Tools\\TSMIS Exporter\\output",
      log_dir: "C:\\Tools\\TSMIS Exporter\\data\\logs",
      // Mirror the real gate: Intersection is enabled (dev site); the reserved Highway
      // pair is DISABLED groundwork (greyed). Each carries its stable export-op `key`
      // (the selection contract, P3) plus display-order `idx`; `disabled` defaults false
      // and each entry may override it (the Highway pair sets it true).
      reports: REPORTS.map((r, i) => ({ idx: i, disabled: false, ...r })),
      cons_reports: [
        { key: "cons:highway_log_excel", label: "TSMIS Highway Log (Excel)", group: null, short: null, fmt: "Excel" },
        { key: "cons:highway_log_pdf", label: "TSMIS Highway Log (PDF)", group: null, short: null, fmt: "PDF" },
        { key: "cons:tsn_highway_log", label: "TSN Highway Log (PDF)", group: null, short: null, fmt: "PDF" },
        { key: "cons:highway_sequence", label: "Highway Sequence Listing", group: null, short: null, fmt: "Excel" },
        { key: "cons:highway_sequence_pdf", label: "TSMIS Highway Sequence (PDF)", group: null, short: null, fmt: "PDF" },
        { key: "cons:ramp_summary", label: "TSAR: Ramp Summary", group: "Ramp", short: "Summary", fmt: "PDF" },
        { key: "cons:ramp_detail", label: "TSAR: Ramp Detail", group: "Ramp", short: "Detail", fmt: "Excel" },
        { key: "cons:ramp_detail_pdf", label: "TSMIS Ramp Detail (PDF)", group: "Ramp", short: "Detail (PDF)", fmt: "PDF" },
        { key: "cons:intersection_summary", label: "Intersection Summary", group: "Intersection", short: "Summary", fmt: "Excel" },
        { key: "cons:intersection_detail", label: "Intersection Detail", group: "Intersection", short: "Detail", fmt: "Excel" },
        { key: "cons:intersection_detail_pdf", label: "TSMIS Intersection Detail (PDF)", group: "Intersection", short: "Detail (PDF)", fmt: "PDF" },
        { key: "cons:highway_detail", label: "Highway Detail", group: "Highway", short: "Detail", fmt: "Excel" },
        { key: "cons:highway_detail_pdf", label: "TSMIS Highway Detail (PDF)", group: "Highway", short: "Detail (PDF)", fmt: "PDF" },
      ],
      compare_groups: [
        { id: "env", label: "Cross-environment" },
        { id: "tsn", label: "vs TSN" },
        { id: "self", label: "Self-consistency" },
      ],
      // Mirrors the real reports.COMPARE_REPORTS (26 rows as of v0.25.0: every report
      // has a cross-env ("— between environments") AND a vs-TSN comparator, plus each
      // PDF edition's PDF↔Excel + PDF↔TSN self/vs-TSN checks). Each row carries its
      // stable `cmp:*` key (P3), so selection/routing resolves by key — the order just
      // mirrors the registry for display parity.
      compare_reports: [
        { key: "cmp:highway_log:env", label: "Highway Log — between environments", kind: "folders", group: "env", family_group: null, subdir: "highway_log", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:highway_log_pdf:env", label: "Highway Log (PDF) — between environments", kind: "folders", group: "env", family_group: null, subdir: "highway_log_pdf", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:highway_log:tsn", label: "Highway Log — TSMIS vs TSN", kind: "files", group: "tsn", family_group: null, subdir: null, file_a_label: "TSMIS", file_b_label: "TSN", file_a_shape: "a per-route workbook (one route) or a consolidated workbook (all routes)", file_b_shape: "a per-route workbook (one route) or a consolidated workbook (all routes)" },
        { key: "cmp:highway_log:pdf_vs_tsn", label: "Highway Log — TSMIS (PDF) vs TSN (PDF)", kind: "files", group: "tsn", family_group: null, subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSN (PDF)", file_a_shape: "a per-route workbook (one route) or a consolidated workbook (all routes)", file_b_shape: "a per-route workbook (one route) or a consolidated workbook (all routes)" },
        { key: "cmp:highway_log:pdf_vs_excel", label: "Highway Log — TSMIS (PDF) vs TSMIS (Excel)", kind: "files", group: "self", family_group: null, subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSMIS (Excel)", file_a_shape: "a per-route workbook (one route) or a consolidated workbook (all routes)", file_b_shape: "a per-route workbook (one route) or a consolidated workbook (all routes)" },
        { key: "cmp:highway_sequence:env", label: "Highway Sequence Listing — between environments", kind: "folders", group: "env", family_group: null, subdir: "highway_sequence", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:highway_sequence:tsn", label: "Highway Sequence Listing — TSMIS vs TSN", kind: "files", group: "tsn", family_group: null, subdir: null, file_a_label: "TSMIS", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:highway_sequence:pdf_vs_tsn", label: "Highway Sequence Listing — TSMIS (PDF) vs TSN", kind: "files", group: "tsn", family_group: null, subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:highway_sequence:pdf_vs_excel", label: "Highway Sequence Listing — TSMIS (PDF) vs TSMIS (Excel)", kind: "files", group: "self", family_group: null, subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSMIS (Excel)", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:highway_sequence_pdf:env", label: "Highway Sequence Listing (PDF) — between environments", kind: "folders", group: "env", family_group: null, subdir: "highway_sequence_pdf", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:ramp_summary:env", label: "TSAR: Ramp Summary — between environments", kind: "folders", group: "env", family_group: "Ramp", subdir: "ramp_summary", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:ramp_summary:tsn", label: "TSAR: Ramp Summary — TSMIS vs TSN", kind: "files", group: "tsn", family_group: "Ramp", subdir: null, file_a_label: "TSMIS", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "the raw statewide TSN PDF, or the normalized TSN workbook" },
        { key: "cmp:ramp_detail:env", label: "TSAR: Ramp Detail — between environments", kind: "folders", group: "env", family_group: "Ramp", subdir: "ramp_detail", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:ramp_detail:tsn", label: "TSAR: Ramp Detail — TSMIS vs TSN", kind: "files", group: "tsn", family_group: "Ramp", subdir: null, file_a_label: "TSMIS", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:ramp_detail:pdf_vs_tsn", label: "TSAR: Ramp Detail — TSMIS (PDF) vs TSN", kind: "files", group: "tsn", family_group: "Ramp", subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:ramp_detail:pdf_vs_excel", label: "TSAR: Ramp Detail — TSMIS (PDF) vs TSMIS (Excel)", kind: "files", group: "self", family_group: "Ramp", subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSMIS (Excel)", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:ramp_detail_pdf:env", label: "TSAR: Ramp Detail (PDF) — between environments", kind: "folders", group: "env", family_group: "Ramp", subdir: "ramp_detail_pdf", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:intersection_summary:env", label: "Intersection Summary — between environments", kind: "folders", group: "env", family_group: "Intersection", subdir: "intersection_summary", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:intersection_summary:tsn", label: "Intersection Summary — TSMIS vs TSN", kind: "files", group: "tsn", family_group: "Intersection", subdir: null, file_a_label: "TSMIS", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "the raw statewide TSN PDF, or the normalized TSN workbook" },
        { key: "cmp:intersection_detail:env", label: "Intersection Detail — between environments", kind: "folders", group: "env", family_group: "Intersection", subdir: "intersection_detail", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:intersection_detail:tsn", label: "Intersection Detail — TSMIS vs TSN", kind: "files", group: "tsn", family_group: "Intersection", subdir: null, file_a_label: "TSMIS", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:intersection_detail:pdf_vs_tsn", label: "Intersection Detail — TSMIS (PDF) vs TSN", kind: "files", group: "tsn", family_group: "Intersection", subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:intersection_detail:pdf_vs_excel", label: "Intersection Detail — TSMIS (PDF) vs TSMIS (Excel)", kind: "files", group: "self", family_group: "Intersection", subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSMIS (Excel)", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:intersection_detail_pdf:env", label: "Intersection Detail (PDF) — between environments", kind: "folders", group: "env", family_group: "Intersection", subdir: "intersection_detail_pdf", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:highway_detail:env", label: "Highway Detail — between environments", kind: "folders", group: "env", family_group: "Highway", subdir: "highway_detail", file_a_label: "TSMIS", file_b_label: "TSN" },
        { key: "cmp:highway_detail:tsn", label: "Highway Detail — TSMIS vs TSN", kind: "files", group: "tsn", family_group: "Highway", subdir: null, file_a_label: "TSMIS", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:highway_detail:pdf_vs_tsn", label: "Highway Detail — TSMIS (PDF) vs TSN", kind: "files", group: "tsn", family_group: "Highway", subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSN", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:highway_detail:pdf_vs_excel", label: "Highway Detail — TSMIS (PDF) vs TSMIS (Excel)", kind: "files", group: "self", family_group: "Highway", subdir: null, file_a_label: "TSMIS (PDF)", file_b_label: "TSMIS (Excel)", file_a_shape: "a consolidated workbook (all routes)", file_b_shape: "a consolidated workbook (all routes)" },
        { key: "cmp:highway_detail_pdf:env", label: "Highway Detail (PDF) — between environments", kind: "folders", group: "env", family_group: "Highway", subdir: "highway_detail_pdf", file_a_label: "TSMIS", file_b_label: "TSN" },
      ],
      batch_resume: null,
      batch_dest: "C:\\Tools\\TSMIS Exporter\\output\\All Reports (current)",
      routes: ROUTES,
      channels: [
        { id: "msedge", label: "Microsoft Edge", short: "Edge" },
        { id: "chrome", label: "Google Chrome", short: "Chrome" },
      ],
      channel: "msedge",
      sources: [{ id: "ssor", label: "SSOR" }, { id: "ars", label: "ARS" }],
      envs: [{ id: "prod", label: "Prod" }, { id: "test", label: "Test" }, { id: "dev", label: "Dev" }],
      site: { source: "ssor", environment: "prod" },
      fast: { default: 3, max: 30 },
      settings: mockSettingsPayload(),
      state: JSON.parse(JSON.stringify(st)),
    }),
    set_site_url: async (src, env, url) => {
      const key = `${src}-${env}`;
      if (url && !/^https?:\/\/.+/.test(url)) {
        return { error: "That doesn't look like a usable web address — it needs to start with https:// (or http://).",
                 site_urls: mockSiteUrlRows() };
      }
      const dflt = `https://tsmis.dot.ca.gov/index.html?env=${env}&src=${src}`;
      if (!url || url === dflt) delete mockUrlOverrides[key];
      else mockUrlOverrides[key] = url;
      push({ t: "log", text: url && url !== dflt
        ? `Site address for ${key} changed to ${url} (used from the next sign-in or export on).`
        : `Site address for ${key} reset to the default.` });
      return { ok: true, site_urls: mockSiteUrlRows() };
    },
    apply_site_preset: async (preset) => {
      if (preset !== "dev" && preset !== "prod") return { error: "Unknown site preset." };
      for (const src of ["ssor", "ars"]) for (const env of ["prod", "test", "dev"]) {
        const key = `${src}-${env}`;
        if (preset === "dev") mockUrlOverrides[key] = `https://tsmis-dev.dot.ca.gov/index.html?env=${env}&src=${src}`;
        else delete mockUrlOverrides[key];
      }
      push({ t: "log", text: "All site addresses set to the "
        + (preset === "dev" ? "development site (tsmis-dev.dot.ca.gov)." : "built-in production addresses.") });
      return { ok: true, site_urls: mockSiteUrlRows() };
    },
    download_chromium: async () => {
      st.task = "chromium"; st.auth_dot = "busy"; st.auth_text = "Downloading…";
      pushState();
      push({ t: "log", text: "Downloading the Built-in Chromium (~170 MB)…" },
           { t: "run_started", mode: "consolidate", label: "Downloading the Built-in Chromium…" });
      let pct = 0;
      const t2 = setInterval(() => {
        pct += 18;
        if (pct < 100) { push({ t: "log", text: `  Chromium 142.0.7444.52 (playwright build) — ${pct}% of 168 MiB` }); return; }
        clearInterval(t2);
        mockChromium.downloaded = true; mockChromium.downloaded_mb = 170;
        push({ t: "log", text: "Built-in Chromium downloaded. Restart the app, then pick it under Settings ▸ Export browser (browsers are probed at startup)." },
             { t: "settings", s: mockSettingsPayload() },
             { t: "run_ended" },
             { t: "modal", kind: "info", title: "Built-in Chromium downloaded",
               message: "The browser is in place. Restart the app, then choose it under Settings ▸ Export browser." });
        st.task = null; st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 500);
      return { ok: true };
    },
    delete_chromium: async () => {
      st.task = "chromium"; pushState();
      push({ t: "log", text: "Removing the downloaded Built-in Chromium…" },
           { t: "run_started", mode: "consolidate", label: "Removing the Built-in Chromium…" });
      setTimeout(() => {
        mockChromium.downloaded = false; mockChromium.downloaded_mb = 0;
        push({ t: "log", text: "Downloaded Built-in Chromium removed." },
             { t: "settings", s: mockSettingsPayload() },
             { t: "run_ended" });
        st.task = null; pushState();
      }, 1200);
      return { ok: true };
    },
    request_preview: async (w) => {
      setTimeout(() => {
        push({ t: "preview", w, img: mockShotB64("SSOR PROD", `Browser ${w} — Route 005 — Highway Log`), note: `Route 005`,
               url: "https://tsmis.dot.ca.gov/index.html?env=prod&src=ssor" });
      }, 900);
      return { ok: true };
    },
    verify_environment: async () => {
      st.task = "envcheck"; st.auth_dot = "busy"; st.auth_text = "Checking SSOR / Prod…";
      pushState();
      push({ t: "log", text: "Verifying environment: opening TSMIS on SSOR / Prod…" },
           { t: "run_started", mode: "consolidate", label: "Checking SSOR / Prod…" });
      setTimeout(() => {
        const match = Math.random() > 0.3;
        push({ t: "log", text: match ? "Environment check: the page is running SSOR / Prod — matches your selection."
                                     : "WARNING: the page is running SSOR / Dev, but SSOR / Prod is selected. Exports would hit SSOR / Dev." },
             { t: "preview", w: 0, img: mockShotB64(match ? "SSOR PROD" : "SSOR DEV", "Verify environment"),
               note: "Verify environment",
               url: `https://tsmis.dot.ca.gov/index.html?env=${match ? "prod" : "dev"}&src=ssor`,
               env_info: { ok: true, env: match ? "prod" : "dev", src: "ssor", matches: match, wanted: "SSOR / Prod" } },
             { t: "run_ended" });
        st.task = null; st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 1600);
      return { ok: true };
    },
    check_environments: async () => {
      if (st.task) return { error: "A task is already running." };
      st.task = "envscan"; st.auth_dot = "busy"; st.auth_text = "Checking environments…";
      const combos = [];
      for (const s of ["ssor", "ars"]) for (const e of ["prod", "test", "dev"]) combos.push([s, e]);
      const entry = (s, e, status, detail, reports) => ({
        key: `${s}-${e}`, source: s, environment: e,
        label: `${s.toUpperCase()} / ${e[0].toUpperCase()}${e.slice(1)}`,
        status, detail, reports: reports || {},
        url: `https://tsmis.dot.ca.gov/index.html?env=${e}&src=${s}`,
        checked_at: new Date().toTimeString().slice(0, 5),
      });
      const allReports = (over) => Object.fromEntries(
        REPORTS.map((r) => [r.label, (over || {})[r.label] || "ok"]));
      st.env_access = {};
      combos.forEach(([s, e]) => { st.env_access[`${s}-${e}`] = entry(s, e, "checking", "Checking…"); });
      pushState();
      push({ t: "log", text: "Checking sign-in and report access for every environment (six sites — this can take a few minutes)…" },
           { t: "run_started", mode: "consolidate", label: "Checking all environments…" });
      combos.forEach(([s, e], i) => setTimeout(() => {
        const broken = s === "ssor" && e === "test";   // the demo's bad site
        const greyed = s === "ars" && e === "dev";     // …and its greyed report
        let it;
        if (broken) {
          it = entry(s, e, "no_reports",
            "Signs in, but the report form couldn't load its data — reports would fail here.",
            allReports());
        } else if (greyed) {
          it = entry(s, e, "reports_off",
            "Sign-in and report data OK, but unavailable here: TSAR: Ramp Detail.",
            allReports({ "TSAR: Ramp Detail": "greyed" }));
        } else {
          it = entry(s, e, "ok", "Sign-in and report data OK.", allReports());
        }
        st.env_access[it.key] = it;
        push({ t: "log", text: `  ${it.label}: ${it.status === "ok" ? "OK" : "PROBLEM"} — ${it.detail}` });
        pushState();
        if (i === combos.length - 1) {
          push({ t: "log", text: "Environment check done: 4 of 6 sites OK — details next to each address in Settings." },
               { t: "run_ended" });
          st.task = null; st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
          pushState();
        }
      }, 650 * (i + 1)));
      return { ok: true };
    },
    get_settings: async () => ({ values: { ...mockSettings }, defaults: { ...mockSettings },
                                 export_browser: { value: mockSettings.export_browser || "auto",
                                   chrome_ok: true, chromium_present: true,
                                   labels: { chromium: "Built-in Chromium", chrome: "Google Chrome" } },
                                 tsn_library: mockTsnLibraryRows(), tsn_library_root: MOCK_TSN_ROOT,
                                 arcgis_layers: { ...MOCK_ARCGIS },
                                 meta: { update_support: "ok" } }),
    tsn_library_status: async () => ({ reports: mockTsnLibraryRows() }),
    open_tsn_library_folder: async () => { push({ t: "log", text: `(mock) open TSN library folder: ${MOCK_TSN_ROOT}` }); return { ok: true }; },
    import_tsn_raw: async (report) => {
      const m = mockTsnLib[report];
      if (!m) return { error: "Unknown TSN report." };
      m.present = true;
      m.raw_count = m.raw_count || (m.raw_kind === "district_pdfs" ? 12 : 1);
      m.current = false;                       // freshly imported raw → consolidated stale
      push({ t: "log", text: `Imported raw file(s) for ${m.label}. Rebuild to use them.` });
      return { ok: true, imported: m.raw_count, reports: mockTsnLibraryRows() };
    },
    rebuild_tsn_library: async (report) => {
      const m = mockTsnLib[report];
      if (!m) return { error: "Unknown TSN report." };
      if (!m.present) return { error: "No raw files imported yet — import first." };
      st.task = "consolidate"; pushState();
      push({ t: "log", text: `Rebuilding TSN library: ${m.label}…` },
           { t: "run_started", mode: "consolidate", label: `Rebuilding ${m.label}…` });
      setTimeout(() => {
        m.cons = true; m.current = true;       // a rebuild produces a current consolidated
        push({ t: "log", text: `${m.label} consolidated workbook ready.` }, { t: "run_ended" });
        st.task = null; pushState();           // → the "state" handler refreshes the panel
      }, 700);
      return { ok: true };
    },
    rebuild_stale_tsn_libraries: async () => {
      const stale = Object.keys(mockTsnLib)
        .filter((k) => mockTsnLib[k].present && !mockTsnLib[k].current);
      if (!stale.length) return { error: "Every imported TSN report is already up to date." };
      const labels = stale.map((k) => mockTsnLib[k].label).join(", ");
      const headline = `Rebuilding ${stale.length} out-of-date TSN report`
        + (stale.length === 1 ? "" : "s");
      st.task = "consolidate"; pushState();
      push({ t: "log", text: `${headline}: ${labels}…` },
           { t: "run_started", mode: "consolidate", label: `${headline}…` });
      setTimeout(() => {
        stale.forEach((k) => { mockTsnLib[k].cons = true; mockTsnLib[k].current = true; });
        push({ t: "log", text: `${stale.length} TSN report(s) rebuilt.` }, { t: "run_ended" });
        st.task = null; pushState();
      }, 700);
      return { ok: true, reports: stale.length };
    },
    set_setting: async (key, value) => {
      const numeric = typeof mockSettings[key] === "number";
      const boolish = typeof mockSettings[key] === "boolean";
      // fast_workers floors at 2 (the matrix's effective minimum), like the engine.
      const floor = key === "fast_workers" ? 2 : 1;
      mockSettings[key] = numeric ? Math.max(floor, parseInt(value, 10) || mockSettings[key])
                        : boolish ? !!value : value;
      push({ t: "log", text: `(mock) setting ${key} = ${mockSettings[key]}` });
      // The snapshot derives the matrix worker count from fast_workers — mirror it
      // so the matrix-corner spinner round-trips like the real bridge.
      if (key === "fast_workers") {
        st.matrix_fast = { ...st.matrix_fast, workers: mockSettings.fast_workers };
        pushState();
      }
      return { ok: true, values: { ...mockSettings } };
    },
    reset_preview: async (includeInput) => ({
      targets: ["export run folder '2026-06-11 ssor-prod'", "export run folder '2026-06-11 ars-prod'",
                "output folder 'consolidated'", "output folder 'tsmis_highway_log_pdf'",
                "TSMIS Highway Log (PDF) consolidated workbook", "Export Everything store",
                "output folder 'run_reports'", "failure screenshots"]
        .concat(includeInput ? ["TSN input PDFs"] : []),
      files: includeInput ? 1480 : 1398, mb: includeInput ? 612.4 : 540.1,
      token: "mock-reset-token",        // real bridge issues a single-use confirm token
    }),
    start_reset: async (_includeInput, _token) => {
      st.task = "reset"; st.auth_dot = "busy"; st.auth_text = "Deleting reports…";
      pushState();
      push({ t: "log", text: "Deleting all reports…" },
           { t: "run_started", mode: "consolidate", label: "Deleting reports…" });
      setTimeout(() => {
        push({ t: "log", text: "  Deleted export run folder '2026-06-11 ssor-prod'." },
             { t: "log", text: "  Deleted failure screenshots." },
             { t: "log", text: "Done — deleted 1,398 file(s), freed 540.1 MB. Logs, your login and settings were kept." },
             { t: "run_ended" });
        st.task = null; st.days = []; st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 1800);
      return { ok: true };
    },
    run_validation: async () => {
      st.task = "validate"; st.auth_dot = "busy"; st.auth_text = "Validating…";
      pushState();
      push({ t: "log", text: "Validating: processing the samples on this PC…" },
           { t: "run_started", mode: "consolidate", label: "Validating the samples…" });
      setTimeout(() => {
        push({ t: "log", text: "Validation: TSN highway_log library current (raw files: 12)." },
             { t: "log", text: "Validation: comparing highway_log (ssor-prod) vs TSN… 969 diff cells [4.2s]" },
             { t: "log", text: "Validation complete: 6 of 6 sample comparisons OK. Evidence bundle saved:" },
             { t: "log", text: "  C:\\Users\\you\\AppData\\Local\\TSMIS Exporter\\tsmis_evidence_20260706_141530.zip" },
             { t: "run_ended" },
             { t: "state", s: st },
             { t: "modal", kind: "info", title: "Validation complete",
               message: "Processed 6 sample comparison(s); 6 succeeded.\n\nThe evidence bundle (everything a maintainer needs) was saved to:\nC:\\Users\\you\\AppData\\Local\\TSMIS Exporter\\tsmis_evidence_20260706_141530.zip" });
        st.task = null; st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 1400);
      return { ok: true };
    },
    save_support_bundle: async () => {
      push({ t: "log", text: "Support bundle saved (12 files): C:\\Users\\you\\Desktop\\tsmis_support.zip" });
      return { saved: true };
    },
    capture_site_source: async () => {                       // v0.26.0
      st.task = "consolidate"; st.auth_dot = "busy"; st.auth_text = "Capturing…";
      pushState();
      push({ t: "log", text: "Capturing the website source (SSOR-PROD)…" },
           { t: "run_started", mode: "consolidate", label: "Capturing site source…" });
      setTimeout(() => {
        push({ t: "log", text: "Signing in and opening the report page…" },
             { t: "log", text: "Saving the page (rendered DOM + raw HTML)…" },
             { t: "log", text: "Fetching 6 same-origin script/style file(s) (2 third-party skipped)…" },
             { t: "log", text: "  [ 1/6] Scripts__customreport.js (48,112 bytes)" },
             { t: "log", text: "  [ 2/6] Scripts__site.js (12,004 bytes)" },
             { t: "log", text: "✓ Captured 8 file(s)." },
             { t: "log", text: "  Folder: C:\\Tools\\TSMIS Exporter\\output\\site-capture\\2026-07-10 ssor-prod 141530" },
             { t: "run_ended" });
        st.task = null; st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 1200);
      return { ok: true };
    },
    open_site_captures_folder: async () =>
      push({ t: "log", text: "(mock) would open the site-capture folder" }),
    clear_saved_login: async () => {
      st.authed = false; st.auth_dot = "bad"; st.auth_text = "No saved login — click Log in";
      st.logins.file = { valid: false, age_h: null };
      push({ t: "log", text: "Saved login deleted — click 'Log in' to sign in again." });
      pushState();
      return { ok: true, removed: true };
    },
    open_failures_folder: async () => push({ t: "log", text: "(mock) would open the failures folder" }),
    ui_ready: async () => { setTimeout(finishChecks, 900); },
    ui_event: async () => {},
    log_js_error: async (m) => console.error("js error:", m),
    set_export_browser: async (ch) => {
      mockSettings.export_browser = (ch === "auto" ? "" : ch);
      const label = ch === "chromium" ? "Built-in Chromium"
        : ch === "chrome" ? "Google Chrome" : "automatic (Chrome-first)";
      st.export_browser = { ...st.export_browser,
        cls_label: ch === "chromium" ? "Built-in Chromium" : "Google Chrome" };
      push({ t: "log", text: `Export browser set to ${label} (Microsoft Edge is still `
            + `used for one-click sign-in and as a fallback).` }, { t: "state", s: st });
      return { ok: true };
    },
    set_site: async (src, env) => {
      push({ t: "log", text: `Site set to ${src.toUpperCase()} / ${env} (used by the next sign-in or export).` });
      // Simulate the quiet background active-env check: prove Edge one-click +
      // refresh this env's report flags (no modal, no per-combo log line).
      st.device_ok = true;
      st.logins = { ...st.logins, device: { ...st.logins.device, ok: true } };
      st.export_browser = { ...st.export_browser, normal: "Microsoft Edge · one-click", dot: "ok" };
      st.env_access = { ...st.env_access,
        [`${src}-${env}`]: { key: `${src}-${env}`, source: src, environment: env,
          label: `${src.toUpperCase()} / ${env[0].toUpperCase()}${env.slice(1)}`,
          status: "reports_off", checked_at: "now", url: "",
          detail: "Signed in; some report types are greyed out here.",
          reports: { "Highway Log": "greyed", "Intersection Detail": "missing" } } };
      push({ t: "state", s: st }, { t: "matrix_refresh" });
      return { ok: true };
    },
    start_checks: async () => {
      Object.keys(st.checks).forEach((k) => { st.checks[k] = { status: "busy", text: "checking…" }; });
      st.checks_running = true; pushState();
      setTimeout(finishChecks, 1200);
    },
    parse_routes_preview: async (raw) => {
      const toks = raw.split(/[\s,;]+/).filter(Boolean);
      const out = [];
      for (const t of toks) {
        const m = t.match(/^0*(\d+)([a-zA-Z]?)$/);
        const canon = m ? m[1].padStart(3, "0") + (m[2] || "").toUpperCase() : null;
        if (!canon || !ROUTES.includes(canon)) return { ok: false, error: `Unknown route: '${t}'. Routes look like 5, 99, 101 or 101U.` };
        if (!out.includes(canon)) out.push(canon);
      }
      return { ok: true, count: out.length, routes: ROUTES.filter((r) => out.includes(r)) };
    },
    start_export: async (reports, routesText, fast, workers, autoConsolidate) => {
      // Mock keeps runs short: a typed subset caps at 24 routes, "all" at 32.
      const routes = routesText ? ROUTES.slice(0, 24) : ROUTES.slice(0, 32);
      runMockExport(reports, routes, fast, workers, autoConsolidate);
      return { ok: true };
    },
    start_batch_export: async (reports, envs, fast, workers, auto) => {
      runMockBatch(reports, envs, fast, workers, auto);
      return { ok: true };
    },
    retry_failed: async () => {
      const s = st.last_summary;
      if (!s || !s.failed_total) return { error: "There are no failed routes to retry." };
      runMockExport(["ramp_summary"], ROUTES.slice(0, Math.max(2, s.failed_total)), false, 1, false);
      return { ok: true };
    },
    open_run_folder: async () => { push({ t: "log", text: "(mock) opened run folder" }); return { ok: true }; },
    resume_batch: async () => {
      const r = st.batch_resume || { pending: 1, reports: [] };
      st.batch_resume = null;
      const reps = (r.reports && r.reports.length) ? r.reports
        : ["ramp_summary", "ramp_detail", "highway_sequence", "highway_log"];
      const envs = Array.from({ length: r.pending || 1 }, (_, i) => `env-${i + 1}`);
      runMockBatch(reps, envs, false, 1, true);
      return { ok: true };
    },
    discard_batch: async () => { st.batch_resume = null; pushState(); return { ok: true }; },
    report_library_info: async () => ({
      dest: st.batch_dest || "C:\\Tools\\TSMIS Exporter\\output\\All Reports (current)",
      // One row per ENABLED export report — matches the real report_library_info
      // (Intersection is now enabled too, so it appears here).
      reports: [
        { label: "TSAR: Ramp Summary", subdir: "ramp_summary", present: true, mtime: 0, age_seconds: 2 * 3600 },
        { label: "TSAR: Ramp Detail", subdir: "ramp_detail", present: true, mtime: 0, age_seconds: 2 * 3600 },
        { label: "Highway Sequence Listing", subdir: "highway_sequence", present: true, mtime: 0, age_seconds: 3 * 3600 },
        { label: "Highway Log", subdir: "highway_log", present: true, mtime: 0, age_seconds: 6 * 86400 },
        { label: "Highway Log (PDF)", subdir: "highway_log_pdf", present: true, mtime: 0, age_seconds: 6 * 86400 },
        { label: "Intersection Summary", subdir: "intersection_summary", present: false, mtime: 0, age_seconds: null },
        { label: "Intersection Detail", subdir: "intersection_detail", present: false, mtime: 0, age_seconds: null },
      ],
    }),
    matrix_info: async () => mockMatrixSnapshot(st.matrix_baseline || "ssor-prod"),
    set_matrix_report: async (rk, visible) => {
      const hidden = new Set(st.matrix_hidden || []);
      if (visible) hidden.delete(rk); else hidden.add(rk);
      if (hidden.size >= 5) return { error: "Keep at least one report on the matrix." };
      st.matrix_hidden = [...hidden];
      return { ok: true, hidden: st.matrix_hidden };
    },
    set_matrix_row_order: async (keys) => {
      st.matrix_row_order = (keys || []).filter((k) => typeof k === "string");
      return { ok: true, order: st.matrix_row_order };
    },
    set_matrix_env_order: async (keys) => {
      st.matrix_env_order = (keys || []).filter((k) => typeof k === "string");
      return { ok: true, order: st.matrix_env_order };
    },
    set_day_matrix_row_order: async (keys) => {
      st.day_matrix_row_order = (keys || []).filter((k) => typeof k === "string");
      return { ok: true, order: st.day_matrix_row_order };
    },
    set_matrix_env: async (env, visible) => {
      const hidden = new Set(st.matrix_hidden_envs || []);
      if (visible) hidden.delete(env); else hidden.add(env);
      if (hidden.size >= 6) return { error: "Keep at least one environment on the matrix." };
      st.matrix_hidden_envs = [...hidden];
      return { ok: true, hidden_envs: st.matrix_hidden_envs };
    },
    set_matrix_row_mode: async (rk, mode) => {
      const avail = mockMatrixModes(rk);
      const m = avail.find((x) => x.id === mode);
      if (!m) return { error: "Unknown comparison mode for this report." };
      if (!m.supported) return { error: "That comparison isn't available yet for this report." };
      st.matrix_modes = { ...(st.matrix_modes || {}), [rk]: mode };
      return { ok: true, mode };
    },
    set_all_matrix_modes: async (mode) => {
      if (mode !== "env" && mode !== "tsn") return { error: "Pick Cross-environment or vs TSN." };
      // Mirror gui_api.set_all_matrix_modes: apply to EVERY row that supports the
      // mode (all reports are vs-TSN capable as of v0.17.0) — derived from the
      // snapshot so it can't go stale. "env" clears all rows to cross-environment.
      const next = {};
      if (mode === "tsn") {
        const snap = mockMatrixSnapshot(st.matrix_baseline || "ssor-prod");
        snap.rows.forEach((rk) => {
          const modes = (snap.row_modes || {})[rk] || [];
          if (modes.some((m) => m.id === "tsn" && m.supported)) next[rk] = "tsn";
        });
      }
      st.matrix_modes = next;
      return { ok: true, mode };
    },
    set_matrix_tsn_file: async (subdir, path) => {
      st.matrix_tsn_files = { ...(st.matrix_tsn_files || {}) };
      if (path) st.matrix_tsn_files[subdir] = path; else delete st.matrix_tsn_files[subdir];
      return { ok: true };
    },
    pick_matrix_tsn_file: async (subdir) => {
      st.matrix_tsn_files = { ...(st.matrix_tsn_files || {}), [subdir]: "C:\\Users\\you\\Desktop\\tsn_highway_log.xlsx" };
      push({ t: "log", text: `(mock) picked TSN file for ${subdir}` });
      return { ok: true, path: st.matrix_tsn_files[subdir] };
    },
    consolidate_matrix_tsn: async (subdir) => {
      st.mock_tsn_pdfs = false;               // pretend the PDFs are now consolidated
      return mockEnqueue("tsn_consolidate", "consolidate",
                         "Consolidate TSN Highway Log PDFs", { total: 1 });
    },
    set_matrix_baseline: async (b) => {
      st.matrix_baseline = b;
      push({ t: "log", text: `Matrix baseline set to ${b}.` });
      pushState();
      return { baseline: b, recompute_pending: 5 };
    },
    set_matrix_fast: async (on) => {
      st.matrix_fast = { on: !!on, workers: st.matrix_fast.workers || 3 };
      push({ t: "log", text: `Matrix fast mode ${on ? "on" : "off"}.` });
      pushState();
      return { ok: true, on: !!on };
    },
    set_matrix_formulas: async (on) => {
      st.matrix_formulas = !!on;
      push({ t: "log", text: `Matrix live-formulas workbook ${on ? "on" : "off"}.` });
      pushState();
      return { ok: true, on: !!on };
    },
    set_day_matrix_formulas: async (on) => {
      st.day_matrix_formulas = !!on;
      push({ t: "log", text: `By-day live-formulas workbook ${on ? "on" : "off"}.` });
      pushState();
      return { ok: true, on: !!on };
    },
    set_evidence_images: async (on) => {
      st.evidence = { ...st.evidence, on: !!on };
      push({ t: "log", text: `Evidence images ${on ? "on" : "off"}.` });
      pushState();
      return { ok: true, on: !!on };
    },
    set_evidence_examples: async (n) => {
      const v = Math.max(1, Math.min(10, n | 0 || 2));
      st.evidence = { ...st.evidence, examples: v };
      push({ t: "log", text: `Evidence images: ${v} example(s) per column.` });
      pushState();
      return { ok: true, examples: v };
    },
    set_evidence_layout: async (layout) => {
      const v = ["pair", "stacked", "both"].includes(layout) ? layout : "pair";
      st.evidence = { ...st.evidence, layout: v };
      const label = { pair: "side-by-side", stacked: "stacked", both: "both layouts" }[v];
      push({ t: "log", text: `Evidence images: ${label}.` });
      pushState();
      return { ok: true, layout: v };
    },
    refresh_cell_export: async (rk, env) =>
      mockEnqueue("export", "cell", `Re-export ${rk} — ${env}`, { fast: st.matrix_fast.on }),
    refresh_row_export: async (rk) =>
      mockEnqueue("export", "row", `Re-export ${rk} — all environments`, { fast: st.matrix_fast.on }),
    refresh_column_export: async (env) =>
      mockEnqueue("export", "column", `Re-export all reports — ${env}`, { fast: st.matrix_fast.on }),
    refresh_cell_comparison: async (rk, env) =>
      mockEnqueue("compare", "cell", `Rebuild ${rk} — ${env}`, { total: 1 }),
    matrix_evidence_cell: async (rk, env) =>
      mockEnqueue("evidence", "cell", `Evidence images ${rk} — ${env}`, { total: 1 }),
    recompute_matrix: async (scope, row, env) => {
      const n = row ? 5 : env ? 4 : scope === "all" ? 18 : 6;
      const label = row ? `Rebuild ${row} — all environments`
        : env ? `Rebuild all reports — ${env}`
        : scope === "all" ? "Rebuild all comparisons" : "Refresh stale comparisons";
      return mockEnqueue("compare", row ? "row" : env ? "column" : scope, label, { total: n });
    },
    matrix_queue_remove: async (id) => {
      st.matrix_queue = (st.matrix_queue || []).filter((j) => j.id !== id);
      pushState(); return { ok: true, removed: true };
    },
    matrix_queue_move: async (id, dir) => {
      const q = [...(st.matrix_queue || [])];
      const i = q.findIndex((j) => j.id === id);
      const s = dir === "up" ? i - 1 : i + 1;
      if (i >= 0 && s >= 0 && s < q.length) { [q[i], q[s]] = [q[s], q[i]]; st.matrix_queue = q; pushState(); }
      return { ok: true, moved: i >= 0 };
    },
    matrix_queue_clear: async () => {
      const n = (st.matrix_queue || []).length;
      st.matrix_queue = [];
      if (n) push({ t: "log", text: `Cleared ${n} queued matrix job(s).` });
      pushState(); return { ok: true, cleared: n };
    },
    matrix_stop_all: async () => {
      const n = (st.matrix_queue || []).length;
      st.matrix_queue = [];
      const running = st.task === "matrix";
      if (n || running) push({ t: "log", text: `Stopping matrix work — cleared ${n} queued.` });
      pushState(); return { ok: true, cleared: n, cancelling: running };
    },
    open_cell_comparison: async (rk, env) => {
      push({ t: "log", text: `(mock) open comparison workbook: ${env}_${rk}.xlsx` });
      return { ok: true };
    },
    open_comparisons_folder: async () => {
      push({ t: "log", text: "(mock) open comparisons folder" });
      return { ok: true };
    },
    // ---- Compare-tab "TSN by day" matrix (shares the queue) ----
    day_matrix_info: async () => mockDayMatrixSnapshot(),
    set_day_matrix_source: async (s) => {
      st.day_matrix_source = s; st.day_matrix_days = [];
      pushState(); return { ok: true, source: s };
    },
    add_day_matrix_day: async (d) => {
      const avail = MOCK_DAY_AVAIL[st.day_matrix_source] || [];
      if (avail.indexOf(d) < 0) return { error: "That day has no Highway Log export for this source." };
      if ((st.day_matrix_days || []).indexOf(d) < 0) st.day_matrix_days = [...(st.day_matrix_days || []), d];
      pushState(); return { ok: true, days: st.day_matrix_days };
    },
    remove_day_matrix_day: async (d) => {
      st.day_matrix_days = (st.day_matrix_days || []).filter((x) => x !== d);
      pushState(); return { ok: true, days: st.day_matrix_days };
    },
    set_day_matrix_report: async (rk, visible) => {
      const hidden = new Set(st.day_matrix_hidden || []);
      if (visible) hidden.delete(rk); else hidden.add(rk);
      st.day_matrix_hidden = [...hidden];
      return { ok: true, hidden: st.day_matrix_hidden };
    },
    build_day_cell: async (rk, d) =>
      mockEnqueue("compare", "cell", `Rebuild ${rk} — ${d} vs TSN`, { total: 1 }),
    day_matrix_evidence_cell: async (rk, d) =>
      mockEnqueue("evidence", "cell", `Evidence images ${rk} — ${d}`,
                  { which: "day", total: 1 }),
    rebuild_day_matrix: async (scope, row, date) => {
      if (!(st.day_matrix_days || []).length) return { ok: true, nothing: true };
      const n = row ? (st.day_matrix_days || []).length : date ? 2 : 4;
      const label = row ? `Rebuild ${row} — all days vs TSN`
        : date ? `Rebuild all reports — ${date} vs TSN`
        : scope === "all" ? "Rebuild all by-day comparisons" : "Refresh stale by-day comparisons";
      return mockEnqueue("compare", row ? "row" : date ? "column" : scope, label, { total: n });
    },
    open_day_cell_comparison: async (rk, d) => {
      push({ t: "log", text: `(mock) open by-day comparison: ${d} ${rk}_vs_tsn.xlsx` });
      return { ok: true };
    },
    export_day_column: async () => {
      if ((st.day_matrix_days || []).indexOf(MOCK_TODAY) < 0)
        st.day_matrix_days = [...(st.day_matrix_days || []), MOCK_TODAY];
      return mockEnqueue("export", "column", `Export all reports — ${MOCK_TODAY}`,
                         { which: "day", total: 7, fast: !!(st.matrix_fast || {}).on });
    },
    export_day_row: async (rk) => {
      if ((st.day_matrix_days || []).indexOf(MOCK_TODAY) < 0)
        st.day_matrix_days = [...(st.day_matrix_days || []), MOCK_TODAY];
      return mockEnqueue("export", "row", `Export ${rk} — ${MOCK_TODAY}`,
                         { which: "day", total: 1, fast: !!(st.matrix_fast || {}).on });
    },
    export_day_cell: async (rk, d) => {
      if (d !== MOCK_TODAY) return { error: "Only today's column can be exported." };
      if ((st.day_matrix_days || []).indexOf(MOCK_TODAY) < 0)
        st.day_matrix_days = [...(st.day_matrix_days || []), MOCK_TODAY];
      return mockEnqueue("export", "cell", `Export ${rk} — ${d}`,
                         { which: "day", total: 1, fast: !!(st.matrix_fast || {}).on });
    },
    open_day_comparisons_folder: async () => {
      push({ t: "log", text: "(mock) open by-day comparisons folder" });
      return { ok: true };
    },
    // ---- Compare-tab "vs Baseline" matrix (v0.26.0; shares the queue) ----
    baseline_matrix_info: async () => mockBaselineMatrixSnapshot(),
    set_baseline_matrix_source: async (s) => {
      st.baseline_matrix_source = s; st.baseline_matrix_days = [];
      st.baseline_matrix_baseline = "";
      pushState(); return { ok: true, source: s };
    },
    set_baseline_matrix_baseline: async (b) => {
      b = b || "";
      if (b && !mockBaselineOptions(st.baseline_matrix_source || "ssor-prod")
            .some((o) => o.id === b))
        return { error: "That baseline has no exports for this source." };
      st.baseline_matrix_baseline = b;
      if (b) push({ t: "log", text: `vs-Baseline matrix baseline set to ${b}.` });
      pushState(); return { ok: true, baseline: b };
    },
    add_baseline_matrix_day: async (d) => {
      const avail = MOCK_DAY_AVAIL[st.baseline_matrix_source] || [];
      if (avail.indexOf(d) < 0) return { error: "That day has no export for this source." };
      if ((st.baseline_matrix_days || []).indexOf(d) < 0)
        st.baseline_matrix_days = [...(st.baseline_matrix_days || []), d];
      pushState(); return { ok: true, days: st.baseline_matrix_days };
    },
    remove_baseline_matrix_day: async (d) => {
      st.baseline_matrix_days = (st.baseline_matrix_days || []).filter((x) => x !== d);
      pushState(); return { ok: true, days: st.baseline_matrix_days };
    },
    set_baseline_matrix_report: async (rk, visible) => {
      const hidden = new Set(st.baseline_matrix_hidden || []);
      if (visible) hidden.delete(rk); else hidden.add(rk);
      st.baseline_matrix_hidden = [...hidden];
      return { ok: true, hidden: st.baseline_matrix_hidden };
    },
    set_baseline_matrix_row_order: async (keys) => {
      st.baseline_matrix_row_order = keys || [];
      pushState(); return { ok: true, order: st.baseline_matrix_row_order };
    },
    set_baseline_matrix_formulas: async (on) => {
      st.baseline_matrix_formulas = !!on;
      push({ t: "log", text: `vs-Baseline live-formulas workbook ${on ? "on" : "off"}.` });
      pushState();
      return { ok: true, on: !!on };
    },
    build_baseline_matrix_cell: async (rk, d) =>
      mockEnqueue("compare", "cell", `Rebuild ${rk} — ${d} vs baseline`,
                  { which: "baseline", total: 1 }),
    rebuild_baseline_matrix: async (scope, row, date) => {
      if (!st.baseline_matrix_baseline) return { error: "Pick a baseline first." };
      if (!(st.baseline_matrix_days || []).length) return { ok: true, nothing: true };
      const n = row ? (st.baseline_matrix_days || []).length : date ? 2 : 4;
      const label = row ? `Rebuild ${row} — all days vs baseline`
        : date ? `Rebuild all reports — ${date} vs baseline`
        : scope === "all" ? "Rebuild all vs-baseline comparisons"
          : "Refresh stale vs-baseline comparisons";
      return mockEnqueue("compare", row ? "row" : date ? "column" : scope, label,
                         { which: "baseline", total: n });
    },
    open_baseline_cell_comparison: async (rk, d) => {
      push({ t: "log", text: `(mock) open vs-baseline comparison: ${d} ${rk}.xlsx` });
      return { ok: true };
    },
    open_baseline_comparisons_folder: async () => {
      push({ t: "log", text: "(mock) open vs-baseline comparisons folder" });
      return { ok: true };
    },
    pick_batch_dest: async () => {
      st.batch_dest = "C:\\Users\\you\\Desktop\\All Reports";
      pushState(); return { dest: st.batch_dest };
    },
    skip_route: async () => push({ t: "log", text: "Skip requested — will move on once the current wait ends." }),
    cancel_run: async () => {
      push({ t: "log", text: "Cancel requested…" });
      setTimeout(() => {
        if (timer) { clearInterval(timer); timer = null; }
        push({ t: "log", text: "Cancelled." }, { t: "run_ended" });
        st.task = null; st.fast_run = false;
        if (st.batch) {
          st.batch_resume = { reports: [], total: st.batch.total,
                              pending: Math.max(1, st.batch.total - st.batch.done) };
          st.batch = null;
        }
        st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Idle";
        pushState();
      }, 700);
    },
    start_login: async () => {
      st.task = "login"; st.login_phase = "starting";
      st.auth_dot = "busy"; st.auth_text = "Signing in…";
      pushState();
      push({ t: "log", text: "Starting sign-in…" });
      setTimeout(() => {
        st.login_phase = "open";
        st.auth_text = "Waiting — finish sign-in in the browser";
        pushState();
        push({ t: "log", text: "Browser opened. Complete sign-in (SSO + MFA), then click ‘I've finished logging in’." });
      }, 900);
    },
    finish_login: async () => {
      st.login_phase = "saving"; st.auth_text = "Saving session…";
      pushState();
      setTimeout(() => {
        st.task = null; st.login_phase = null;
        st.authed = true; st.login_label = "Re-login";
        st.auth_dot = "ok"; st.auth_text = "Session ready";
        st.logins.file = { valid: true, age_h: 0.1 };
        pushState();
        push({ t: "log", text: "Session saved." });
      }, 1100);
    },
    cancel_login: async () => {
      st.login_phase = "cancelling"; pushState();
      setTimeout(() => {
        st.task = null; st.login_phase = null;
        st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Idle";
        pushState();
        push({ t: "log", text: "Cancelled." });
      }, 600);
    },
    consolidate_info: async (key, day) => {
      // Only "cons:tsn_highway_log" reads from a dropped-in input folder (those
      // district PDFs come from outside the app) — so it carries an input_note and
      // the day picker is hidden. The others read this app's own exports, day-aware
      // like the Excel one. Keyed by the stable consolidation-op key now (P3).
      const dropped = {
        "cons:tsn_highway_log": {
          note: "Drop the TSN district Highway Log PDFs into the input folder first.",
          dir: "C:\\Tools\\TSMIS Exporter\\input\\tsn_highway_log",
          out: "tsn_highway_log_consolidated.xlsx" },
      }[key];
      if (dropped) return {
        dest_dir: "C:\\Tools\\TSMIS Exporter\\output",
        out_path: "C:\\Tools\\TSMIS Exporter\\output\\" + dropped.out,
        exists: false,
        input_note: dropped.note,
        input_dir: dropped.dir,
      };
      return {
        dest_dir: `C:\\Tools\\TSMIS Exporter\\output\\${day || "(legacy)"}\\consolidated`,
        out_path: `C:\\Tools\\TSMIS Exporter\\output\\${day || "(legacy)"}\\consolidated\\${consByKey(key).label.replace(/[:\s]+/g, "_")}.xlsx`,
        exists: key === "cons:ramp_summary" && day === "2026-06-10",
      };
    },
    open_consolidate_input: async () => push({ t: "log", text: "(mock) would open the input folder" }),
    pick_compare_file: async (side) => ({
      path: side === "TSMIS"
        ? "C:\\Users\\you\\Downloads\\tsmis_highway_log_route 1.xlsx"
        : "C:\\Users\\you\\Downloads\\tsn_highway_log_route 1.xlsx",
    }),
    pick_compare_folder: async () => ({
      path: "D:\\Archive\\2026-05-02 ssor-prod",
    }),
    start_compare_env: async (_key, dirA, dirB, wantFormulas, wantValues,
                              _confirmed = false) => {
      if (!wantFormulas && !wantValues) {
        return { error: "Tick at least one output (values and/or live formulas)." };
      }
      if (wantFormulas && wantValues && !_confirmed) {
        const token = `mock-compare-${Date.now()}-${Math.random()}`;
        const path = "C:\\Tools\\TSMIS Exporter\\output\\Environment Comparison (values).xlsx";
        mockCompareOverwrite = {
          token,
          launch: () => mockApi.start_compare_env(
            _key, dirA, dirB, wantFormulas, wantValues, true),
        };
        return {
          confirm_required: true, confirm_token: token, path,
          message: `The automatically created values workbook already exists:\n\n${path}\n\nOverwrite this exact file? The formulas workbook remains the file selected in the Save dialog.`,
        };
      }
      st.task = "compare";
      st.auth_dot = "busy"; st.auth_text = "Comparing…";
      pushState();
      push({ t: "log", text: `Starting comparison: ${dirA} vs ${dirB}` },
           { t: "run_started", mode: "consolidate", label: "Comparing — environments…" });
      setTimeout(() => {
        const match = Math.random() < 0.5;   // exercise both verdict paths
        if (match) {
          push({ t: "log", text: "SSOR-PROD rows: 48,112   ARS-PROD rows: 48,112   union: 48,112 locations across 280 routes" },
               { t: "log", text: "✓ EVERYTHING MATCHES — all 48,112 locations are identical in both environments." },
               { t: "run_ended" },
               { t: "modal", kind: "info", title: "Everything matches",
                 message: "✓ EVERYTHING MATCHES — all 48,112 locations are identical in both environments.\n\nThe saved workbook has the full breakdown and self-checks." });
        } else {
          push({ t: "log", text: "SSOR-PROD rows: 48,112   ARS-PROD rows: 48,090   union: 48,201 locations across 280 routes" },
               { t: "log", text: "✗ DIFFERENCES FOUND — 1,204 differing cell(s) on 312 matched row(s); 89 row(s) only in SSOR-PROD, 22 only in ARS-PROD." },
               { t: "log", text: "Routes only in SSOR-PROD (missing from ARS-PROD) (1): 254" },
               { t: "run_ended" },
               { t: "modal", kind: "warning", title: "Differences found",
                 message: "✗ DIFFERENCES FOUND — 1,204 differing cell(s) on 312 matched row(s).\n\nOpen the saved workbook for the cell-by-cell breakdown (Summary → Comparison → Only-in sheets)." });
        }
        st.task = null;
        st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 2400);
      return { ok: true };
    },
    start_compare: async (_key, _t, _n, wantFormulas, wantValues,
                          _confirmed = false) => {
      if (!wantFormulas && !wantValues) {
        return { error: "Tick at least one output (values and/or live formulas)." };
      }
      if (wantFormulas && wantValues && !_confirmed) {
        const token = `mock-compare-${Date.now()}-${Math.random()}`;
        const path = "C:\\Users\\you\\Downloads\\TSMIS_vs_TSN_Route1_Comparison (values).xlsx";
        mockCompareOverwrite = {
          token,
          launch: () => mockApi.start_compare(
            _key, _t, _n, wantFormulas, wantValues, true),
        };
        return {
          confirm_required: true, confirm_token: token, path,
          message: `The automatically created values workbook already exists:\n\n${path}\n\nOverwrite this exact file? The formulas workbook remains the file selected in the Save dialog.`,
        };
      }
      const kinds = wantFormulas && wantValues ? "values + live formulas"
        : wantFormulas ? "live formulas" : "values";
      st.task = "compare";
      st.auth_dot = "busy"; st.auth_text = "Comparing Highway Logs…";
      pushState();
      push({ t: "log", text: `Starting comparison: TSMIS vs TSN Highway Log (${kinds})` },
           { t: "run_started", mode: "consolidate", label: "Comparing Highway Logs…" });
      setTimeout(() => {
        push({ t: "log", text: "TSMIS rows: 317   TSN rows: 368   union: 386 locations" },
             { t: "log", text: "Matched rows with differences: 221 (971 differing cells); 78 fully identical" },
             { t: "log", text: "Routes only in TSMIS (missing from TSN) (2): 254, 259" });
        if (wantFormulas) push({ t: "log", text: "Live-formulas file: TSMIS_vs_TSN_Route1_Comparison.xlsx" });
        if (wantValues) push({ t: "log", text: "Values file: TSMIS_vs_TSN_Route1_Comparison" + (wantFormulas ? " (values)" : "") + ".xlsx" });
        push({ t: "run_ended" });
        st.task = null;
        st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 2400);
      return { ok: true };
    },
    confirm_compare_overwrite: async (confirmToken, accepted) => {
      const pending = mockCompareOverwrite;
      if (!pending || confirmToken !== pending.token) {
        return { error: "That comparison confirmation is no longer valid. Start the comparison again." };
      }
      mockCompareOverwrite = null;
      if (accepted !== true) return { cancelled: true };
      return pending.launch();
    },
    decline_overwrite: async () => push({ t: "log", text: "Consolidation cancelled (kept existing file)." }),
    start_consolidate: async (key, day) => {
      st.task = "consolidate";
      st.auth_dot = "busy"; st.auth_text = `Consolidating ${consByKey(key).label}…`;
      pushState();
      push({ t: "log", text: `Starting consolidation: ${consByKey(key).label}` + (day ? `   ·   ${day}` : "") },
           { t: "run_started", mode: "consolidate", label: `Consolidating ${consByKey(key).label}…` });
      setTimeout(() => {
        push({ t: "log", text: `Consolidated 31 file(s) -> Output: consolidated\\workbook.xlsx` }, { t: "run_ended" });
        st.task = null;
        st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 2600);
      return { ok: true };
    },
    save_run_report: async () => {
      push({ t: "log", text: "Run report saved: C:\\Users\\you\\Desktop\\run_report.csv" });
      return { saved: true };
    },
    open_output_folder: async () => push({ t: "log", text: "(mock) would open the output folder" }),
    open_logs_folder: async () => push({ t: "log", text: "(mock) would open the logs folder" }),
    open_consolidated_folder: async () => push({ t: "log", text: "(mock) would open the consolidated folder" }),
    check_updates: async () => {
      if (st.update.phase === "available") {
        push({ t: "log", text: "An update is already waiting — see the title bar." });
      } else if (st.update.phase === "staged") {
        push({ t: "log", text: "An update is already downloaded — click ‘Restart to update’ in the title bar to install it." });
      } else {
        push({ t: "log", text: "Checking for updates…" });
        setTimeout(() => push({ t: "log", text: "You're on the latest version (v0.25.2 preview)." }), 600);
      }
      return { ok: true };
    },
    update_start: async () => {
      st.update = { phase: "downloading", progress: 0, version: "9.9.9", url: "#", can_apply: true };
      push({ t: "log", text: "Downloading update v9.9.9 (148 MB)…" });
      pushState();
      const t2 = setInterval(() => {
        st.update.progress = Math.min(100, (st.update.progress || 0) + 6);
        if (st.update.progress >= 100) {
          clearInterval(t2);
          st.update = { phase: "staged", version: "9.9.9", url: "#", can_apply: true };
          push({ t: "log", text: "Update v9.9.9 is downloaded and ready — click ‘Restart to update’ when you're done working (the app closes, updates itself, and reopens)." });
        }
        pushState();
      }, 130);
      return { ok: true };
    },
    update_apply: async () => {
      st.update = { ...st.update, phase: "applying" };
      push({ t: "log", text: "Restarting to finish the update — (mock) the app would close, update itself, and reopen." });
      pushState();
      return { ok: true };
    },
    open_release_page: async () => push({ t: "log", text: "(mock) would open the GitHub releases page" }),
    revert_to_previous: async () => {
      // The real revert lands on a version STRICTLY LOWER than the current build.
      st.update = { phase: "downloading", progress: 0, version: "0.14.1", url: "#", can_apply: true, revert: true };
      push({ t: "log", text: "Reverting to the previous version — finding it and downloading…" });
      pushState();
      const tr = setInterval(() => {
        st.update.progress = Math.min(100, (st.update.progress || 0) + 8);
        if (st.update.progress >= 100) {
          clearInterval(tr);
          st.update = { phase: "staged", version: "0.14.1", url: "#", can_apply: true, revert: true };
          push({ t: "log", text: "Previous version v0.14.1 is downloaded and ready — click ‘Restart to revert’ in the title bar." });
        }
        pushState();
      }, 130);
      return { ok: true };
    },
    get_compare_folders: async () => ({ folders: (st.days || []) }),
    pause_or_resume: async () => {
      st.paused = !st.paused;
      push({ t: "log", text: st.paused
        ? "Paused — finishing the current route(s), then holding. Click Resume to continue."
        : "Resumed." });
      pushState();
      return { ok: true };
    },
  };
  return mockApi;
}


// mock.js owns the mock boot (app.js auto-boots only in production).
boot(makeMockApi());
