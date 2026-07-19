/* TSMIS Reports Exporter — frontend logic.
 *
 * Talks to Python through the pywebview js_api bridge (gui_api.GuiApi):
 *   JS -> Python : api.<method>(...) (all return Promises)
 *   Python -> JS : window.__tsmis.dispatch([{t: "state"|"log"|"progress"|
 *                  "run_started"|"run_ended"|"modal", ...}, ...])
 *
 * Python owns app state (auth, task, checks, days, …) and pushes full
 * snapshots; this file owns only presentation + form fields. Log lines are
 * never invented here — anything worth showing goes through Python so the
 * tsmis.ui file-log mirror stays complete.
 *
 * Opened in a plain browser (no pywebview), a built-in mock API drives the
 * same UI with simulated runs, so layout and flows can be previewed without
 * launching the real app.
 */
"use strict";

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- state ----
const S = {
  init: null,          // immutable initial payload from Python
  st: null,            // latest state snapshot from Python
  tab: "export",
  everySub: "export",  // Everything sub-tab: "export" | "matrix"
  compareGroup: null,  // active Compare sub-tab id (incl. "tsn_by_day")
  progress: null,      // latest export progress payload
  runMode: null,       // "export" | "consolidate" while the bar is live
  workers: 0,          // browser-status rows currently shown (export runs)
  elapsedStart: null,
  elapsedTimer: null,
  logPinned: true,
  logLines: 0,
};
const LOG_MAX_LINES = 3000;

let api = null;        // real pywebview api or the mock

// marks an app-wide-disabled report: shown but greyed (.option-static) and
// unpickable (disabled input + dataset.off so the lock-sweep leaves it alone).
function makeReportRow(rep, checked, off, onChange) {
  const row = document.createElement("label");
  row.className = "option-row" + (checked ? " checked" : "") + (off ? " option-static" : "")
    + (rep.group ? " option-indent" : "");
  const cb = document.createElement("input");
  // dataset.key is the STABLE export-op key (rep.key), not the row position — so
  // selection no longer depends on registry order (P3), even though disabled rows
  // are shown rather than filtered.
  cb.type = "checkbox"; cb.checked = !!checked; cb.dataset.key = rep.key;
  if (off) { cb.disabled = true; cb.dataset.off = "1"; }
  const box = document.createElement("span");
  box.className = "checkbox"; box.appendChild(icon("i-check"));
  const name = document.createElement("span");
  // Grouped reports show the short leaf label (e.g. "Detail") under their family
  // header; flat top-level reports show the full label. (P-D)
  name.className = "option-name"; name.textContent = rep.short || rep.label;
  if (off) {
    const note = document.createElement("span");
    note.className = "option-static-note"; note.textContent = " — not yet available";
    name.appendChild(note);
  }
  const chip = document.createElement("span");
  chip.className = "chip " + (rep.fmt === "PDF" ? "chip-pdf" : "chip-excel");
  chip.textContent = rep.fmt;
  row.append(cb, box, name, chip);
  // Print editions (the *_pdf keys) explain themselves on hover; the
  // env-availability sync APPENDS its warning to this base title (never
  // replaces it). Ramp Summary is fmt PDF but not a print edition.
  if (/_pdf$/.test(rep.key)) {
    row.dataset.baseTitle =
      "The same on-site report as its Excel sibling, saved via the site's own "
      + "Print layout (print-accurate). Ticking both editions generates the "
      + "report once per route and saves both files.";
    row.title = row.dataset.baseTitle;
  }
  cb.addEventListener("change", () => {
    row.classList.toggle("checked", cb.checked);
    onChange();
  });
  return row;
}

// Fill a report checklist from init.reports — already in PICKER order (the flat
// top-level reports first in the TSMIS site's order, then each family contiguously).
// Emit a family header (.option-group) whenever the group changes; flat reports get
// none. `checkedFor(rep)` decides the initial tick; `onChange` fires on toggle. (P-D)
function fillReportList(container, checkedFor, onChange) {
  let lastGroup = null;
  (S.init.reports || []).forEach((rep) => {
    const g = rep.group || null;
    if (g && g !== lastGroup) {
      const head = document.createElement("div");
      head.className = "option-group"; head.textContent = g;
      container.appendChild(head);
    }
    lastGroup = g;
    container.appendChild(makeReportRow(rep, checkedFor(rep), !!rep.disabled, onChange));
  });
}

// ------------------------------------------------------ one-time build -----
function buildStatic() {
  const init = S.init;
  $("appName").textContent = init.app_name;
  $("appVersion").textContent = "v" + init.version;
  $("appVersion").title = "Check for updates";
  $("outputRoot").textContent = init.output_root;
  document.title = init.app_name;

  // report checkboxes — grouped by family (P-D): flat reports first, then each
  // family (Ramp / Intersection / Highway) under a header, mirroring the TSMIS
  // site's grouped dropdown. App-wide-disabled reports (rep.disabled) are SHOWN
  // but greyed/unpickable (.option-static + dataset.off). The first ENABLED report
  // is ticked by default — the same default report as the old flat list.
  const firstKey = (init.reports.find((r) => !r.disabled) || {}).key;
  fillReportList($("reportList"),
                 (rep) => !rep.disabled && rep.key === firstKey,
                 updateReportCount);
  updateReportCount();

  // B3: Export Everything — same grouping; every enabled report ticked, disabled greyed.
  fillReportList($("batchReportList"), (rep) => !rep.disabled, updateBatchCount);
  (init.sources || []).forEach((s) => (init.envs || []).forEach((e) => {
    const row = document.createElement("label");
    row.className = "option-row checked";
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = true; cb.dataset.key = `${s.id}-${e.id}`;
    const box = document.createElement("span");
    box.className = "checkbox"; box.appendChild(icon("i-check"));
    const name = document.createElement("span");
    name.className = "option-name"; name.textContent = `${s.label} / ${e.label}`;
    row.append(cb, box, name);
    cb.addEventListener("change", () => {
      row.classList.toggle("checked", cb.checked);
      updateBatchCount();
      renderBatchAccess();      // selection moved -> re-flag error-prone reports
    });
    $("batchEnvList").appendChild(row);
  }));
  updateBatchCount();
  if (S.init.batch_dest) setBatchDest(S.init.batch_dest);

  // consolidate radios. Each cons_reports entry is {label, fmt} where fmt is the
  // INPUT file format (PDF or Excel) — shown as a badge so the PDF-input
  // consolidators (TSN / TSMIS Highway Log PDF) are labeled like the rest.
  const cl = $("consList");
  let consLastGroup = null;
  init.cons_reports.forEach((rep, i) => {
    // W2: same family organization as the Export picker — a header when the
    // group changes, indented short-labeled leaves under it.
    const g = rep.group || null;
    if (g && g !== consLastGroup) {
      const head = document.createElement("div");
      head.className = "option-group"; head.textContent = g;
      cl.appendChild(head);
    }
    consLastGroup = g;
    const row = document.createElement("label");
    row.className = "option-row" + (i === 0 ? " checked" : "")
      + (g ? " option-indent" : "");
    const rb = document.createElement("input");
    rb.type = "radio"; rb.name = "consReport"; rb.checked = i === 0; rb.dataset.key = rep.key;
    const dot = document.createElement("span"); dot.className = "radio";
    const name = document.createElement("span");
    name.className = "option-name"; name.textContent = rep.short || rep.label;
    row.append(rb, dot, name);
    if (rep.fmt) {
      const chip = document.createElement("span");
      chip.className = "chip " + (rep.fmt === "PDF" ? "chip-pdf" : "chip-excel");
      chip.textContent = rep.fmt;
      row.appendChild(chip);
    }
    rb.addEventListener("change", () => {
      cl.querySelectorAll(".option-row").forEach((r) => r.classList.remove("checked"));
      row.classList.add("checked");
      refreshConsDest();
    });
    cl.appendChild(row);
  });

  // Comparison-type SUB-TABS + radios. Each registry row carries a `group` (its
  // sub-tab — Cross-environment or Highway Log); the sub-tab strip is generated
  // from init.compare_groups, and the radio list shows only the active sub-tab's
  // reports (selectCompareGroup).
  const subStrip = $("compareSubtabs");
  subStrip.textContent = "";
  (init.compare_groups || []).forEach((g, gi) => {
    const b = document.createElement("button");
    b.className = "subtab" + (gi === 0 ? " active" : "");
    b.dataset.group = g.id;
    b.setAttribute("role", "tab");
    b.setAttribute("aria-selected", String(gi === 0));
    b.textContent = g.label;
    b.addEventListener("click", () => selectCompareGroup(g.id));
    subStrip.appendChild(b);
  });
  // The "TSN by day" + "vs Baseline" matrices are manual day-picking sub-tabs
  // (not registry comparison groups), appended after the generated ones.
  const dayTab = document.createElement("button");
  dayTab.className = "subtab"; dayTab.dataset.group = DAY_MATRIX_GROUP;
  dayTab.setAttribute("role", "tab"); dayTab.setAttribute("aria-selected", "false");
  dayTab.textContent = "vs TSN Matrix";
  dayTab.addEventListener("click", () => selectCompareGroup(DAY_MATRIX_GROUP));
  subStrip.appendChild(dayTab);
  const blTab = document.createElement("button");
  blTab.className = "subtab"; blTab.dataset.group = BASELINE_MATRIX_GROUP;
  blTab.setAttribute("role", "tab"); blTab.setAttribute("aria-selected", "false");
  blTab.textContent = "vs Baseline Matrix";
  blTab.addEventListener("click", () => selectCompareGroup(BASELINE_MATRIX_GROUP));
  subStrip.appendChild(blTab);

  const cl2 = $("compareList");
  // W2: family headers inside each comparison-type sub-tab; tracked PER SUB-TAB
  // (the payload interleaves a family's env/tsn flavors, so consecutive-row
  // tracking would emit duplicate headers). The header carries the SUB-TAB's
  // dataset.group so selectCompareGroup filters it with its rows.
  const cmpLastFamilyByGroup = {};
  (init.compare_reports || []).forEach((rep, i) => {
    const sub = rep.group || "";
    if (rep.family_group && cmpLastFamilyByGroup[sub] !== rep.family_group) {
      const head = document.createElement("div");
      head.className = "option-group";
      head.dataset.group = sub;
      head.textContent = rep.family_group;
      cl2.appendChild(head);
    }
    cmpLastFamilyByGroup[sub] = rep.family_group || null;
    const row = document.createElement("label");
    row.className = "option-row" + (rep.family_group ? " option-indent" : "");
    row.dataset.group = rep.group || "";
    const rb = document.createElement("input");
    rb.type = "radio"; rb.name = "compareReport"; rb.dataset.key = rep.key;
    const dot = document.createElement("span"); dot.className = "radio";
    const name = document.createElement("span");
    name.className = "option-name"; name.textContent = rep.label;
    row.append(rb, dot, name);
    rb.addEventListener("change", () => {
      cl2.querySelectorAll(".option-row").forEach((r) => r.classList.remove("checked"));
      row.classList.add("checked");
      renderCompareKind();
    });
    cl2.appendChild(row);
  });
  // Default sub-tab = the first group; also seats the initial radio selection.
  const groups0 = init.compare_groups || [];
  if (groups0.length) selectCompareGroup(groups0[0].id);

  // titlebar selects
  const fill = (sel, items, currentId) => {
    items.forEach(({ id, label }) => {
      const o = document.createElement("option");
      o.value = id; o.textContent = label;
      if (id === currentId) o.selected = true;
      sel.appendChild(o);
    });
  };
  fill($("selSource"), init.sources, init.site.source);
  fill($("selEnv"), init.envs, init.site.environment);
  // (The browser picker moved to Settings ▸ Export browser; the title bar now
  //  shows a read-only indicator instead — see renderState / st.export_browser.)

  // readiness dots: one per browser channel + output + tools
  const strip = $("checkStrip");
  const items = init.channels.map((c) => ({ key: "browser_" + c.id, label: c.short }))
    .concat([{ key: "output", label: "Output" }, { key: "tools", label: "Tools" }]);
  items.forEach(({ key, label }) => {
    const it = document.createElement("span");
    it.className = "check-item"; it.id = "check_" + key;
    const ic = icon("i-loader", "check-ic ci-unknown");   // shape + colour status cue
    it.append(ic, Object.assign(document.createElement("span"), { textContent: label }));
    it.title = label + ": checking…";
    strip.appendChild(it);
  });

  $("fastWorkers").value = init.fast.default;
  $("fastWorkers").min = 2;
  $("fastWorkers").max = init.fast.max;
}

function updateReportCount() {
  const n = [...$("reportList").querySelectorAll("input")].filter((c) => c.checked).length;
  $("reportCount").textContent = `${n} selected`;
}

// ------------------------------------------------------------- renders -----
// Selection travels by stable KEY now (P3), so a registry re-order never changes
// what a tick resolves to. reportByKey maps an export-op key back to its payload.
function reportByKey(key) {
  return (S.init.reports || []).find((r) => r.key === key) || {};
}
function selectedReportKeys() {
  return [...$("reportList").querySelectorAll("input")].filter((c) => c.checked).map((c) => c.dataset.key);
}
function consChoice() {
  const r = $("consList").querySelector("input:checked");
  return r ? r.dataset.key : null;
}
function compareChoice() {
  const r = $("compareList").querySelector("input:checked");
  return r ? r.dataset.key : null;
}
function currentCompareRep() {
  return (S.init.compare_reports || []).find((r) => r.key === compareChoice()) || {};
}
function selectedDay() {
  return $("selDay").value || null;   // "" = legacy "(older exports)"
}

function renderState() {
  const st = S.st;
  if (!st) return;

  // auth status + login button
  setDot($("authDot"), st.auth_dot);
  $("authText").textContent = st.auth_text;

  // the two sign-in paths, separately (saved file vs Edge one-click)
  const lg = st.logins || {};
  const file = lg.file || {};
  setDot($("loginFile").querySelector(".dot"), file.valid ? "ok" : "unknown");
  $("loginFile").title = file.valid
    ? "Saved login file: valid" + (file.age_h != null ? ` (saved ${file.age_h} h ago)` : "")
      + ". Captured via Chrome / Built-in Chromium; used by exports and required for fast mode."
    : "No saved login file. Sign in (Chrome / Built-in Chromium) to save one — required for fast mode.";
  const dev = lg.device || {};
  setDot($("loginEdge").querySelector(".dot"),
         dev.ok ? "ok" : dev.primed ? "warn" : "unknown");
  $("loginEdge").title = dev.ok
    ? "Edge one-click sign-in: working (proven this session). Exports can sign themselves in without a saved file."
    : dev.primed
      ? "Edge one-click sign-in: set up (the Edge sign-in profile exists) — it's verified the first time something signs in this session."
      : "Edge one-click sign-in: not set up. Sign in once with Microsoft Edge to enable hands-free sign-in on this PC.";

  // Export-browser indicator: what will actually do the exporting right now.
  const eb = st.export_browser || {};
  setDot($("exportBrowserDot"), eb.dot || "unknown");
  $("exportBrowserText").textContent = eb.cls_label || "—";
  $("exportBrowserInd").title = eb.normal
    ? `Normal export: ${eb.normal}\nFast mode: ${eb.fast}`
      + "\nMicrosoft Edge is used for one-click sign-in and as a fallback."
      + "\nChange it under Settings ▸ Export browser."
    : "";

  const bl = $("btnLogin"), blc = $("btnLoginCancel");
  const phase = st.login_phase;
  const labels = { starting: "Signing in…", saving: "Saving…", cancelling: "Cancelling…" };
  if (phase === "open") {
    $("btnLoginLabel").textContent = "I've finished logging in";
    bl.disabled = false;
    blc.classList.remove("hidden");
  } else {
    $("btnLoginLabel").textContent = labels[phase] || st.login_label;
    bl.disabled = phase != null || st.task != null;
    blc.classList.add("hidden");
  }

  // readiness checks
  Object.entries(st.checks || {}).forEach(([key, c]) => {
    const it = $("check_" + key);
    if (!it) return;
    setCheckIcon(it, c.status);
    it.title = c.text;
  });
  $("btnRecheck").disabled = st.checks_running || st.task != null;

  // aggregate readiness -> the title-bar "Ready" chip (per-item detail in its
  // popover). "Ready" needs only ONE working browser (Edge alone is fine — a
  // missing Chrome isn't a problem) plus output + report tools; busy while any
  // check is pending; otherwise "Check setup" (something blocking failed).
  const ckEntries = Object.entries(st.checks || {});
  let rdot = "unknown", rtext = "Checking…";
  if (ckEntries.length) {
    const browsers = ckEntries.filter(([k]) => k.startsWith("browser_")).map(([, c]) => c.status);
    const others = ckEntries.filter(([k]) => !k.startsWith("browser_")).map(([, c]) => c.status);
    const anyPending = st.checks_running
      || ckEntries.some(([, c]) => c.status === "busy" || c.status === "unknown");
    const browserOk = browsers.length === 0 || browsers.some((s) => s === "ok");
    const othersOk = others.every((s) => s === "ok");
    if (anyPending) { rdot = "busy"; rtext = "Checking…"; }
    else if (browserOk && othersOk) { rdot = "ok"; rtext = "Ready"; }
    else { rdot = "bad"; rtext = "Check setup"; }
  }
  setDot($("readyDot"), rdot);
  $("readyText").textContent = rtext;

  // config inputs lock while any task runs
  const locked = st.task != null;
  // Every [data-lock-when-busy] control disables while any task runs (S5:
  // the hand-kept ID lists became ONE attribute sweep — tag new controls in
  // the HTML instead of extending an array here).
  document.querySelectorAll("[data-lock-when-busy]").forEach((el) => { el.disabled = locked; });
  Object.keys(SETTING_INPUTS).forEach((id) => { $(id).disabled = locked; });
  ["setDebugLog", "setDevtools", "setEnvCheckSignin", "setEnvCheckStart", "setNotifyFinish"].forEach((id) => {
    $(id).disabled = locked;
    $(id).closest(".option-row").classList.toggle("disabled", locked);
  });
  $("setSiteUrls").querySelectorAll("input").forEach((i) => { i.disabled = locked; });
  $("btnChromiumCancel").classList.toggle("hidden", st.task !== "chromium");
  $("btnValidateCancel").classList.toggle("hidden", st.task !== "validate");
  // dataset.off rows (app-wide-disabled reports) stay disabled regardless of lock.
  $("reportList").querySelectorAll("input").forEach((c) => { c.disabled = locked || c.dataset.off === "1"; });
  $("reportList").querySelectorAll(".option-row").forEach((r) => r.classList.toggle("disabled", locked));
  $("consList").querySelectorAll("input").forEach((c) => { c.disabled = locked; });
  $("consList").querySelectorAll(".option-row").forEach((r) => r.classList.toggle("disabled", locked));

  // fast mode: needs a saved login (device sign-in runs one browser at a time)
  const fastAllowed = st.authed && !locked;
  const fastCb = $("fastMode");
  if (!st.authed && fastCb.checked) { fastCb.checked = false; syncFastVisual(); }
  fastCb.disabled = !fastAllowed;
  fastCb.closest(".fast-toggle").classList.toggle("disabled", !fastAllowed);
  $("fastWorkers").disabled = !fastAllowed || !fastCb.checked;
  $("fastHint").textContent = st.authed
    ? "Faster, but heavier on your PC; 3–4 recommended. Per-route Skip is off in fast mode. "
      + "Runs in the Built-in Chromium / Google Chrome (not Microsoft Edge)."
    : "Fast mode needs a saved login — automatic sign-in runs one browser at a time. Log in first to enable it.";

  // action buttons
  $("btnSkip").disabled = !(st.task === "export" && !st.fast_run);
  // B1: Pause works in fast mode too (every browser parks between routes),
  // unlike Skip. The button toggles label + icon from the Python-owned state.
  $("btnPause").disabled = st.task !== "export";
  const pauseUse = $("btnPause").querySelector("use");
  if (pauseUse) pauseUse.setAttribute("href", st.paused ? "#i-play" : "#i-pause");
  $("btnPauseLabel").textContent = st.paused ? "Resume" : "Pause";
  $("btnCancelExport").disabled = st.task !== "export";
  $("btnCancelCons").disabled = st.task !== "consolidate";
  $("btnSaveReport").disabled = locked || !st.can_save_report;

  // B3: Export Everything pane
  $("btnPauseBatch").disabled = st.task !== "batch";
  const pbUse = $("btnPauseBatch").querySelector("use");
  if (pbUse) pbUse.setAttribute("href", st.paused ? "#i-play" : "#i-pause");
  $("btnPauseBatchLabel").textContent = st.paused ? "Resume" : "Pause";
  $("btnCancelBatch").disabled = st.task !== "batch";
  // Lock AND grey the whole Everything pane while any task runs (incl. env
  // check), matching the Export/Consolidate/Compare panes: option rows dim via
  // .option-row.disabled, fast toggles via .fast-toggle.disabled. The Saved-
  // reports Refresh buttons are re-synced here too — renderBatchLibrary only
  // re-runs on tab-switch/run-end, so without this they'd stay clickable.
  ["batchReportList", "batchEnvList"].forEach((id) => {
    $(id).querySelectorAll("input").forEach((c) => { c.disabled = locked || c.dataset.off === "1"; });
    $(id).querySelectorAll(".option-row").forEach((r) => r.classList.toggle("disabled", locked));
  });
  $("batchLibrary").querySelectorAll("button").forEach((b) => { b.disabled = locked; });
  $("batchFast").disabled = locked;
  $("batchFast").closest(".fast-toggle").classList.toggle("disabled", locked);
  $("batchWorkers").disabled = locked || !$("batchFast").checked;
  $("batchAutoConsolidate").disabled = locked;
  $("batchAutoConsolidate").closest(".fast-toggle").classList.toggle("disabled", locked);
  renderBatchResume(st.batch_resume);
  const bp = $("batchProgress");
  if (st.batch && st.batch.total) {
    bp.hidden = false;
    bp.textContent = `Environment ${(st.batch.done || 0) + 1} of ${st.batch.total}: ${st.batch.label || ""}`;
  } else { bp.hidden = true; }
  ["btnPickTsmis", "btnPickTsn", "btnPickDirA", "btnPickDirB",
   "cmpDirA", "cmpDirB", "btnOpenConsInput"].forEach((id) => { $(id).disabled = locked; });
  ["compareList", "cmpOutList"].forEach((id) => {
    $(id).querySelectorAll("input").forEach((c) => { c.disabled = locked; });
    $(id).querySelectorAll(".option-row").forEach((r) => r.classList.toggle("disabled", locked));
  });
  $("btnCancelCompare").disabled = st.task !== "compare";
  // CMP-AUD-079: keep the running comparison's Cancel reachable — lock the Compare
  // sub-tab strip while a Compare-tab comparison is live, so the user can't
  // navigate away from the section that owns its Cancel control.
  const subtabsLocked = compareSubtabsShouldLock(st);
  document.querySelectorAll("#compareSubtabs .subtab").forEach((b) => {
    b.disabled = subtabsLocked;
    b.title = subtabsLocked
      ? "Finish or cancel the running comparison before switching sub-tabs" : "";
  });
  syncCompareButton();

  $("btnCheckEnvsCancel").classList.toggle("hidden", st.task !== "envscan");

  renderUpdate(st.update);
  renderDays(st.days || []);
  renderEnvAccess();

  // Right-column lifecycle: pre-flight while idle, progress while running, a
  // persistent completion summary after an export finishes.
  updateActivityCards();
}

// Pick which activity-column card is visible: progress while a task runs; on
// the Export tab a finished run keeps its completion summary; otherwise the
// per-tab pre-flight.
function updateActivityCards() {
  const st = S.st;
  if (!st) return;
  const idle = st.task == null;
  const showCompletion = idle && !!st.last_summary && S.tab === "export";
  $("progressCard").classList.toggle("hidden", idle);
  $("completionCard").classList.toggle("hidden", !showCompletion);
  $("preflightCard").classList.toggle("hidden", !(idle && !showCompletion));
  // A batch's "which environment" update arrives as a state push between the
  // per-route "progress" events, so refresh just the headline + stepper here —
  // NOT the bar (it only advances on a real route outcome; re-running the full
  // renderProgress with the previous env's 100% progress would overshoot the
  // bar a whole environment, then snap back). Without this the headline would
  // lag a whole environment during sign-in/preflight at each env boundary.
  if (!idle && S.runMode === "batch") syncBatchHeadline();
  renderPreflight();
  renderCompletion();
}

// The persistent post-run summary: totals as count chips, the failed routes,
// and Open-folder / Retry-failed / Save-report actions.
function renderCompletion() {
  const card = $("completionCard");
  if (!card || card.classList.contains("hidden")) return;
  const s = S.st && S.st.last_summary;
  if (!s) return;
  const t = s.totals || {};
  const failed = s.failed_total || 0;
  // P1: branch on the PRODUCER-owned completion (default-derived from the counts
  // when a payload predates it, for intra-version safety). A skipped-only run is
  // now partial too — incomplete coverage never reads as a green "complete". An
  // env that signs in but returns no data for every route is "no data", not a
  // success.
  const completion = s.completion || (
    s.cancelled ? "cancelled"
      : failed > 0 ? "partial"
        : ((t.saved || 0) + (t.exists || 0)) === 0 && (t.empty || 0) > 0 ? "no_data"
          : "complete");
  // A partial/failed/cancelled store refresh keeps last-good (artifact); note it.
  const keptLastGood = s.artifact === "previous_preserved" ? " — kept last-good" : "";
  const head = $("completionHead"), use = head.querySelector("use");
  if (completion === "complete") {
    head.className = "completion-head ok"; use.setAttribute("href", "#i-check");
    $("completionTitle").textContent = "Export complete";
  } else {
    head.className = "completion-head warn"; use.setAttribute("href", "#i-warn");
    $("completionTitle").textContent = (
      completion === "cancelled" ? "Run stopped"
        : completion === "no_data" ? "Finished with no data"
          : failed > 0 ? "Finished with failures"
            : "Finished — incomplete") + keptLastGood;   // partial (skipped-only)
  }
  const chips = $("completionChips");
  chips.textContent = "";
  [["saved", "saved", "cc-saved"], ["exists", "already had", "cc-exists"],
   ["empty", "empty", "cc-empty"], ["skipped", "skipped", "cc-skipped"],
   ["failed", "failed", "cc-failed"]].forEach(([k, label, cls]) => {
    const v = t[k] || 0;
    const chip = document.createElement("span");
    chip.className = "count-chip " + cls + (v > 0 ? " lit" : "");
    chip.append(document.createTextNode(label + " "));
    const b = document.createElement("b"); b.textContent = v; chip.append(b);
    chips.append(chip);
  });
  const fr = $("completionFailed");
  const routes = [...new Set((s.reports || []).flatMap((r) => r.failed_routes || []))];
  if (routes.length) { fr.textContent = "Failed routes: " + routes.join(", "); fr.classList.remove("hidden"); }
  else fr.classList.add("hidden");
  $("btnRetryFailed").disabled = !(failed > 0) || (S.st.task != null);
  $("btnOpenRunFolder").disabled = !s.run_folder;
}
// ----------------------------------- environment access (scan results) -----
// Python owns the verdicts (state.env_access, keyed "src-env", from the
// Settings "Check all environments" scan); this renders them twice: a status
// chip on each Settings address row, and the title-bar aggregate.
const ENV_ACCESS_BADGE = {
  ok:          { dot: "ok",   text: "OK" },
  unverified:  { dot: "warn", text: "Couldn't verify" },
  reports_off: { dot: "warn", text: "Reports limited" },
  no_reports:  { dot: "bad",  text: "No report data" },
  denied:      { dot: "bad",  text: "Access denied" },
  no_signin:   { dot: "bad",  text: "Sign-in failed" },
  wrong_site:  { dot: "bad",  text: "Wrong site" },
  unreachable: { dot: "bad",  text: "Unreachable" },
  error:       { dot: "bad",  text: "Check failed" },
  checking:    { dot: "busy", text: "Checking…" },
};

function renderEnvAccess() {
  const acc = (S.st && S.st.env_access) || {};
  document.querySelectorAll("[data-envstat]").forEach((el) => {
    const e = acc[el.dataset.envstat];
    const badge = e && (ENV_ACCESS_BADGE[e.status] || ENV_ACCESS_BADGE.error);
    setDot(el.querySelector(".dot"), badge ? badge.dot : "unknown");
    el.lastElementChild.textContent = badge ? badge.text : "Not checked";
    el.classList.toggle("env-bad", !!badge && badge.dot === "bad");
    el.classList.toggle("env-warn", !!badge && badge.dot === "warn");
    if (e) {
      let tip = e.detail + (e.url ? "\n" + e.url : "");
      const reps = Object.entries(e.reports || {}).map(([lbl, state]) =>
        `${lbl}: ${state === "ok" ? "OK" : state === "greyed" ? "greyed out" : "missing"}`);
      if (reps.length) tip += "\n" + reps.join("\n");
      if (e.checked_at) tip += `\nChecked ${e.checked_at}`;
      el.title = tip;
    } else {
      el.title = "Not checked yet — click “Check all environments”.";
    }
  });
  const entries = Object.values(acc);
  const total = (((S.init || {}).sources || []).length || 2)
              * (((S.init || {}).envs || []).length || 3);
  const dot = $("envAccessDot"), txt = $("envAccessText"), btn = $("btnEnvAccess");
  if (!entries.length) {
    setDot(dot, "unknown");
    txt.textContent = "Env access";
    btn.title = "Sign-in + report access across all six environments — run "
      + "the check from Settings ▸ TSMIS site addresses";
  } else if (entries.some((e) => e.status === "checking")) {
    setDot(dot, "busy");
    const done = entries.filter((e) => e.status !== "checking").length;
    txt.textContent = `Checking ${done}/${total}…`;
    btn.title = "Environment check running — verdicts land next to each address in Settings";
  } else {
    const ok = entries.filter((e) => e.status === "ok").length;
    const onlyLimited = entries.every((e) =>
      e.status === "ok" || e.status === "reports_off" || e.status === "unverified");
    setDot(dot, ok === total ? "ok" : onlyLimited ? "warn" : "bad");
    txt.textContent = `Envs ${ok}/${total}`;
    const lines = entries.filter((e) => e.status !== "ok")
      .map((e) => `${e.label}: ${(ENV_ACCESS_BADGE[e.status] || ENV_ACCESS_BADGE.error).text}`);
    if (entries.length < total) lines.push(`${total - entries.length} not checked`);
    btn.title = lines.length ? lines.join("\n")
      : "Sign-in and report data verified on every environment";
  }
  const last = entries.map((e) => e.checked_at).filter(Boolean).sort().pop();
  $("envScanStamp").textContent = last ? `Last checked ${last}`
                                       : "Not checked yet this session.";

  // Export tab: flag report types the ACTIVE site's scan found unavailable
  // (warning only — the site may have changed since; the run will tell).
  const active = acc[`${$("selSource").value}-${$("selEnv").value}`];
  const reps = (active && active.reports) || {};
  $("reportList").querySelectorAll(".option-row").forEach((row) => {
    const label = reportByKey(row.querySelector("input").dataset.key).label;
    const state = label && reps[label];
    const off = state && state !== "ok";
    row.classList.toggle("report-off", !!off);
    const warn = off
      ? `The last environment check found this report ${state === "greyed"
          ? "greyed out" : "missing"} on ${active.label} — the export may fail.`
      : "";
    // Compose with the row's static base title (the *_pdf print-edition
    // explainer) rather than clobbering it.
    row.title = [row.dataset.baseTitle, warn].filter(Boolean).join("\n\n");
  });
  renderBatchAccess();
}

// Everything tab: colour-code reports and environments the env-access scan
// flagged, same convention as the Export tab. Each environment row maps 1:1 to
// a scan verdict (amber = limited, red = will fail outright); a report-type row
// is flagged amber when it's greyed/missing in any of the SELECTED environments
// (so the warning tracks what this batch will actually export). Cleared when no
// scan has run. Re-run from renderEnvAccess (state pushes) and on env-checkbox
// changes (selection moves which envs a report is judged against).
function renderBatchAccess() {
  const acc = (S.st && S.st.env_access) || {};
  const selectedKeys = [];
  $("batchEnvList").querySelectorAll(".option-row").forEach((row) => {
    const cb = row.querySelector("input");
    if (cb.checked) selectedKeys.push(cb.dataset.key);
    const e = acc[cb.dataset.key];
    const badge = e && e.status !== "checking"
      && (ENV_ACCESS_BADGE[e.status] || ENV_ACCESS_BADGE.error);
    const bad = !!badge && badge.dot === "bad";
    const warn = !!badge && badge.dot === "warn";
    row.classList.toggle("env-error", bad);
    row.classList.toggle("report-off", warn);
    row.title = badge
      ? `Last environment check: ${badge.text} on ${e.label}.`
        + (bad ? " Exporting this environment will fail until it's fixed."
               : warn ? " Some report types may be unavailable here." : "")
      : "";
  });
  $("batchReportList").querySelectorAll(".option-row").forEach((row) => {
    const label = reportByKey(row.querySelector("input").dataset.key).label;
    const hits = [];                          // envs where this report is unavailable
    selectedKeys.forEach((key) => {
      const e = acc[key];
      const state = e && e.reports && e.reports[label];
      if (state && state !== "ok") {
        hits.push(`${e.label} (${state === "greyed" ? "greyed out" : "missing"})`);
      }
    });
    row.classList.toggle("report-off", hits.length > 0);
    const warn = hits.length
      ? "The last environment check found this report unavailable on:\n"
        + hits.join("\n") + "\nThe export may fail there."
      : "";
    row.title = [row.dataset.baseTitle, warn].filter(Boolean).join("\n\n");
  });
}

// One-click update pill (title bar). Python owns the whole update state; this
// only decides the pill's label/visibility for the current phase.
function renderUpdate(up) {
  const b = $("btnUpdate");
  up = up || { phase: "idle" };
  const locked = S.st && S.st.task != null;
  let show = true, label = "", disabled = false, title = "";
  switch (up.phase) {
    case "available":
      if (up.can_apply) {
        label = `Update to v${up.version}`;
        title = "Download and install the new version";
      } else {
        label = `v${up.version} available`;
        title = "Open the download page (this app folder is read-only, so the app can't update itself)";
      }
      break;
    case "downloading":
      label = `${up.revert ? "Reverting" : "Downloading"}… ${up.progress || 0}%`;
      disabled = true;
      break;
    case "staged":
      label = up.revert ? "Restart to revert" : "Restart to update";
      disabled = locked;
      title = locked ? "Finish or cancel the running task first"
                     : `${up.revert ? "Reinstall" : "Install"} v${up.version} — `
                       + "the app closes and reopens by itself";
      break;
    case "applying":
      label = "Restarting…";
      disabled = true;
      break;
    default:
      show = false;
  }
  b.classList.toggle("hidden", !show);
  b.textContent = label;
  b.disabled = disabled;
  b.title = title;
}

async function onUpdateClick() {
  const up = (S.st && S.st.update) || {};
  if (up.phase === "available" && !up.can_apply) { api.open_release_page(); return; }
  if (up.phase === "available") {
    const res = await api.update_start();
    if (res && res.error) showMessage("error", "Could not start the update", res.error);
    return;
  }
  if (up.phase === "staged") {
    const ok = await showConfirm({
      title: up.revert ? "Restart and revert?" : "Restart and update?",
      message: `The app will close, ${up.revert ? "reinstall" : "install"} v${up.version} `
        + "(takes a few seconds), and reopen by itself.\n\n"
        + "Your reports, login and settings stay where they are.",
      confirmLabel: "Restart now",
    });
    if (!ok) return;
    const res = await api.update_apply();
    if (res && res.error) showMessage("error", up.revert ? "Could not revert" : "Could not update", res.error);
  }
}

const LEGACY_DAY_LABEL = "(older exports)";
let lastDaysKey = null;

function renderDays(days) {
  const key = days.join("|");
  if (key === lastDaysKey) return;
  lastDaysKey = key;
  const sel = $("selDay");
  const prev = sel.value;
  sel.textContent = "";
  const values = days.length ? days : [""];
  values.forEach((d) => {
    const o = document.createElement("option");
    o.value = d; o.textContent = d || LEGACY_DAY_LABEL;
    sel.appendChild(o);
  });
  sel.value = [...sel.options].some((o) => o.value === prev) ? prev : values[0];
  refreshConsDest();
  if (compareKind() === "folders") renderCompareDirs();
}

let consDestSeq = 0;
async function refreshConsDest() {
  const seq = ++consDestSeq;
  const info = await api.consolidate_info(consChoice(), selectedDay());
  if (seq !== consDestSeq) return;          // a newer request superseded this one
  $("consDest").textContent = info.dest_dir;
  $("consDest").title = info.dest_dir;
  // The one dropped-input report (TSN Highway Log (PDF), whose district PDFs come
  // from OUTSIDE the app) reads a fixed input folder, not a dated export run — so
  // it advertises where the files go AND the "Export day" picker is meaningless for
  // it (signalled by info.input_note). Every other report — including TSMIS Highway
  // Log (PDF), which reads the app's own dated export — keeps the picker.
  const dropped = !!info.input_note;
  S.consDropped = dropped;
  S.consInputDir = dropped ? info.input_dir : null;
  $("consDaySection").classList.toggle("hidden", dropped);   // hide the day picker
  const row = $("consInputRow");
  if (dropped) {
    $("consInputNote").textContent = info.input_note;
    $("consInputDir").textContent = info.input_dir;
    $("consInputDir").title = info.input_dir;
    row.classList.remove("hidden");
  } else {
    row.classList.add("hidden");
  }
  renderPreflight();
}

// progress -------------------------------------------------------------
function renderProgress(p) {
  S.progress = p;
  // The counter restarted (a new report, or the engine's end-of-run retry pass
  // re-counting the failed routes) — drop the stale rate so the ETA can't carry
  // a huge value across the reset.
  if (p.done === 0 && p.total > 0) S.etaSmoothed = null;
  // Overall fraction drives the bar so it stays monotonic: multi-report runs
  // reset `done` per report, and a batch runs many environments — fold those in.
  const within = p.total > 0 ? p.done / p.total : 0;
  const withinRun = ((p.report_i || 1) - 1 + within) / (p.report_n || 1);
  const b = S.st && S.st.batch;
  const overall = (S.runMode === "batch" && b && b.total)
    ? Math.min(1, (b.done + withinRun) / b.total)
    : withinRun;
  const isBatch = S.runMode === "batch" && b && b.total;
  const pct = Math.round(Math.max(0, Math.min(1, overall)) * 100);
  $("progressPct").textContent = pct + "%";
  $("progressFill").style.width = pct + "%";
  updateEta(overall);

  // Two-level readout so "what's running" and "where in progress" are both
  // obvious: the PRIMARY line is the highest level (the environment for a batch,
  // the report for a single/multi export); the SECONDARY line is the finer
  // detail (report + route for a batch, route for an export).
  const reportPart = (p.report_n > 1)
    ? `Report ${p.report_i} of ${p.report_n} · ${p.report || "…"}`
    : (p.report || "");
  const routePart = (p.route && p.route !== "—")
    ? `Route ${p.route} · ${p.done}/${p.total} routes`
    : (p.total ? `${p.done}/${p.total} routes` : "Starting…");
  let primary, secondary;
  if (isBatch) {
    primary = `Environment ${(b.done || 0) + 1} of ${b.total} · ${b.label || ""}`;
    secondary = [reportPart, routePart].filter(Boolean).join("   ·   ");
  } else {
    primary = reportPart || "Exporting";
    secondary = routePart;
  }
  $("progressText").textContent = primary;
  const sub = $("progressSub");
  if (sub) { sub.textContent = secondary; sub.classList.toggle("hidden", !secondary); }
  renderBatchSteps(isBatch ? (b.steps || []) : null);

  const counts = { cSaved: p.saved, cExists: p.exists, cEmpty: p.empty, cSkipped: p.skipped, cFailed: p.failed };
  Object.entries(counts).forEach(([id, v]) => {
    $(id).textContent = v;
    $(id).closest(".count-chip").classList.toggle("lit", v > 0);
  });
}

// Refresh ONLY the batch headline + env stepper from the latest batch state
// (called on state pushes between progress events). Deliberately leaves the bar,
// %, and route detail alone — those move on real per-route progress. When the
// environment changes, neutralize the route line to "Preparing…" so it doesn't
// keep showing the previous environment's last route during the new one's
// sign-in/preflight.
function syncBatchHeadline() {
  const b = S.st && S.st.batch;
  if (!b || !b.total) return;
  $("progressText").textContent =
    `Environment ${(b.done || 0) + 1} of ${b.total} · ${b.label || ""}`;
  renderBatchSteps(b.steps || []);
  const key = `${b.src || ""}-${b.env || ""}`;
  if (key !== S.curEnvKey) {
    S.curEnvKey = key;
    const sub = $("progressSub");
    if (sub) { sub.textContent = `Preparing ${b.label || "next environment"}…`; sub.classList.remove("hidden"); }
  }
}

// Export Everything: a pill per environment showing the whole batch's position —
// done (✓), running now (spinner, highlighted), or still pending. Labels are
// compacted (e.g. "SSOR·Prod") so all six fit. Hidden for single exports.
function renderBatchSteps(steps) {
  const el = $("progressSteps");
  if (!el) return;
  // Rebuild only when the steps actually change (env boundaries) — renderProgress
  // calls this on EVERY route event, and recreating the running pill's spinner
  // each time would restart its CSS spin animation (a visible stutter).
  const sig = (steps && steps.length) ? steps.map((s) => `${s.key}:${s.state}`).join("|") : "";
  if (sig === S.stepsSig) return;
  S.stepsSig = sig;
  if (!sig) { el.classList.add("hidden"); el.textContent = ""; return; }
  el.classList.remove("hidden");
  el.textContent = "";
  steps.forEach((s) => {
    const state = s.state || "pending";
    const pill = document.createElement("span");
    pill.className = "pstep " + state;
    pill.title = `${s.label} — ${state === "done" ? "done"
                  : state === "running" ? "running now" : "pending"}`;
    if (state === "running") { const i = icon("i-loader"); i.classList.add("spin"); pill.appendChild(i); }
    else if (state === "done") pill.appendChild(icon("i-check"));
    const t = document.createElement("span");
    t.textContent = (s.label || s.key || "").replace(" / ", "·");
    pill.appendChild(t);
    el.appendChild(pill);
  });
}

// Time-remaining from overall progress + client elapsed, smoothed with an EMA
// (the early/parallel route rate is noisy). Hidden until there's enough real
// progress, near the very end, or while paused (wall-clock elapsed inflates it).
function updateEta(overall) {
  const eta = $("progressEta");
  if (!eta) return;
  const paused = S.st && S.st.paused;
  if (overall < 0.03 || overall >= 0.999 || paused || !S.elapsedStart) {
    eta.classList.add("hidden");
    return;
  }
  const elapsed = Date.now() - S.elapsedStart;
  const raw = elapsed * (1 - overall) / overall;
  S.etaSmoothed = S.etaSmoothed == null ? raw : 0.3 * raw + 0.7 * S.etaSmoothed;
  eta.textContent = "~" + fmtElapsed(S.etaSmoothed) + " left";
  eta.classList.remove("hidden");
}

function startRunUi(mode, label, workers) {
  S.runMode = mode;
  S.curEnvKey = null;                   // batch: forces the first env's "Preparing…"
  S.stepsSig = null;                    // force the stepper to rebuild for this run
  buildWorkerStrip(mode === "export" || mode === "batch" ? (workers || 1) : 0);
  S.elapsedStart = Date.now();
  S.etaSmoothed = null;
  $("progressEta").classList.add("hidden");
  $("progressElapsed").classList.remove("hidden");
  $("progressElapsed").textContent = "00:00";
  if (S.elapsedTimer) clearInterval(S.elapsedTimer);
  S.elapsedTimer = setInterval(() => {
    $("progressElapsed").textContent = fmtElapsed(Date.now() - S.elapsedStart);
  }, 1000);

  document.querySelector(".progress-card").classList.add("running");
  $("progressIcon").querySelector("use").setAttribute("href", "#i-loader");
  $("progressIcon").classList.add("spin");
  $("progressFill").style.width = "0%";
  if (mode === "consolidate") {
    $("progressBar").classList.add("indeterminate");
    $("progressPct").classList.add("hidden");
    $("countChips").classList.add("hidden");
    $("progressSub").classList.add("hidden");
    $("progressSteps").classList.add("hidden");
    $("progressText").textContent = label || "Working…";
  } else {
    $("progressBar").classList.remove("indeterminate");
    $("progressPct").classList.remove("hidden");
    $("progressPct").textContent = "0%";
    $("countChips").classList.remove("hidden");
    renderProgress({ done: 0, total: 0, route: "—", report: "", report_i: 1, report_n: 1,
                     saved: 0, empty: 0, skipped: 0, failed: 0, exists: 0 });
    $("progressText").textContent = label || "Working…";
  }
}

function endRunUi() {
  if (S.elapsedTimer) { clearInterval(S.elapsedTimer); S.elapsedTimer = null; }
  if (S.elapsedStart) $("progressElapsed").textContent = fmtElapsed(Date.now() - S.elapsedStart);
  S.elapsedStart = null;
  S.runMode = null;
  S.curEnvKey = null;
  S.stepsSig = null;
  buildWorkerStrip(0);
  document.querySelector(".progress-card").classList.remove("running");
  $("progressIcon").querySelector("use").setAttribute("href", "#i-shield");
  $("progressIcon").classList.remove("spin");
  $("progressBar").classList.remove("indeterminate");
  $("progressPct").classList.remove("hidden");
  $("progressPct").textContent = "0%";
  $("progressFill").style.width = "0%";
  $("progressEta").classList.add("hidden");
  $("progressSub").classList.add("hidden");
  $("progressSteps").classList.add("hidden");
  $("progressText").textContent = "Idle — ready to export";
}

// ------------------------------------------------------- event dispatch ----
// Python pushes batches of events through here (see gui_api._sender). Each
// event is isolated: one bad payload must not take down the rest of the
// batch, and the log pane scrolls once per batch, not once per line.
function dispatch(events) {
  let sawLog = false;
  for (const ev of events) {
    try {
      switch (ev.t) {
        case "state":
          S.st = ev.s; renderState(); updateMatrixProgress(); updateDayMatrixProgress();
          updateBaselineMatrixProgress();
          // env_access can change on a push (background active-env check / scan) —
          // re-overlay the matrix warnings without a full rebuild when one is visible.
          if ((S.tab === "everything" && S.everySub === "matrix")
              || (S.tab === "compare" && S.compareGroup === DAY_MATRIX_GROUP)) applyMatrixEnvFlags();
          // A TSN-library rebuild finished (task slot freed) → refresh its panel.
          if (S._tsnRebuildPending && (!S.st || S.st.task !== "consolidate")) {
            S._tsnRebuildPending = false; refreshTsnLibrary();
          }
          break;
        case "settings":
          S.init.settings = ev.s;
          fillSettings();
          break;
        case "log": appendLog(ev.text); sawLog = true; break;
        case "progress":
          if (S.runMode === "export" || S.runMode === "batch") renderProgress(ev.p);
          break;
        case "wstatus": updateWorkerStatus(ev.w, ev.text); break;
        case "preview": showPreviewEvent(ev); break;
        case "run_started": startRunUi(ev.mode, ev.label, ev.workers); break;
        case "run_ended":
          endRunUi();
          if (S.tab === "everything") { renderBatchLibrary(); if (S.everySub === "matrix") renderMatrix(); }
          if (S.tab === "compare" && S.compareGroup === DAY_MATRIX_GROUP) renderDayMatrix();
          if (S.tab === "compare" && S.compareGroup === BASELINE_MATRIX_GROUP) renderBaselineMatrix();
          break;
        case "matrix_refresh":
          if (S.tab === "everything" && S.everySub === "matrix") renderMatrix();
          if (S.tab === "compare" && S.compareGroup === DAY_MATRIX_GROUP) renderDayMatrix();
          if (S.tab === "compare" && S.compareGroup === BASELINE_MATRIX_GROUP) renderBaselineMatrix();
          break;
        case "modal": showMessage(ev.kind, ev.title, ev.message); break;
        default:
          // No silent drop: the backend posted an event type app.js has no
          // case for (bridge protocol drift). Surface it in devtools instead
          // of letting it vanish; the known kinds above are unaffected.
          console.warn("dispatch: unhandled event type", ev.t, ev);
          break;
      }
    } catch (e) {
      console.error("dispatch failed for", ev, e);
      try { api && api.log_js_error(`dispatch(${ev && ev.t}): ${e}`); } catch (_) { /* best-effort */ }
    }
  }
  if (sawLog) scrollLogToEnd();
}

// --------------------------------------------------------- user actions ----
// ---- Settings tab ----
const SETTING_INPUTS = {
  setReportTimeout: "report_timeout_min",
  setFastTimeout: "fast_timeout_min",
  setRetryTimeout: "retry_timeout_min",
  setCountyTimeout: "county_timeout_s",
  setFastWorkers: "fast_workers",
};

function bindEvents() {
  // tabs
  const TABS = {
    export: { btn: "tabExport", pane: "paneExport", title: "Export reports",
              sub: "Select reports and routes, then run the batch export." },
    consolidate: { btn: "tabConsolidate", pane: "paneConsolidate", title: "Consolidate output",
                   sub: "Merge per-route files into a single workbook." },
    compare: { btn: "tabCompare", pane: "paneCompare", title: "Compare reports",
               sub: "Build a discrepancy workbook from two report sources." },
    everything: { btn: "tabEverything", pane: "paneEverything", title: "Export everything",
                  sub: "Export selected report types across selected environments." },
    settings: { btn: "tabSettings", pane: "paneSettings", title: "Settings",
                sub: "Reliability, debugging and storage options." },
  };
  // Everything has two sub-tabs: the batch refresh/export controls and the
  // comparison matrix. The matrix one goes full-width — body.matrix-wide makes
  // the stylesheet shrink the activity column to a slim log so the grid fills
  // the screen, transitioning cleanly. Only active while ON the Everything tab.
  const setEverySub = (sub) => {
    S.everySub = sub;
    $("subEveryExport").classList.toggle("active", sub === "export");
    $("subEveryExport").setAttribute("aria-selected", String(sub === "export"));
    $("subEveryMatrix").classList.toggle("active", sub === "matrix");
    $("subEveryMatrix").setAttribute("aria-selected", String(sub === "matrix"));
    $("everyExport").classList.toggle("hidden", sub !== "export");
    $("everyMatrix").classList.toggle("hidden", sub !== "matrix");
    applyMatrixWide();
    if (sub === "matrix") renderMatrix();
    updateActivityCards();
  };
  const setTab = (tab) => {
    S.tab = tab;
    Object.entries(TABS).forEach(([key, t]) => {
      $(t.btn).classList.toggle("active", key === tab);
      $(t.btn).setAttribute("aria-selected", String(key === tab));
      $(t.pane).classList.toggle("hidden", key !== tab);
    });
    $("panelTitle").textContent = TABS[tab].title;
    $("panelSub").textContent = TABS[tab].sub;
    if (tab === "everything") {
      renderBatchLibrary();
      setEverySub(S.everySub || "export");   // re-applies matrix-wide if on the matrix sub-tab
    } else {
      // Compare re-enters its last sub-tab; a matrix one re-applies full-width.
      if (tab === "compare" && S.compareGroup === DAY_MATRIX_GROUP) renderDayMatrix();
      if (tab === "compare" && S.compareGroup === BASELINE_MATRIX_GROUP) renderBaselineMatrix();
      applyMatrixWide();   // clears matrix-wide unless a day matrix is active
    }
    updateActivityCards();
  };
  Object.entries(TABS).forEach(([key, t]) => { $(t.btn).onclick = () => setTab(key); });
  $("subEveryExport").onclick = () => setEverySub("export");
  $("subEveryMatrix").onclick = () => setEverySub("matrix");

  // Matrix fast-mode toggle + queue Clear / Stop-all (stay live mid-run).
  $("matrixFast")?.addEventListener("change", async (e) => {
    const r = await api.set_matrix_fast(e.target.checked);
    if (r && r.error) { showMessage("error", "Can't set fast mode", r.error); syncMatrixFast(); }
  });
  // Fast-mode browser count — the shared `fast_workers` knob, editable from the
  // matrix corner (same value the Export pane + Settings tab use).
  $("matrixWorkers")?.addEventListener("change", async (e) => {
    const res = await api.set_setting("fast_workers", e.target.value);
    if (res && res.error) { showMessage("error", "Can't set browser count", res.error); syncMatrixFast(); return; }
    if (res && res.values) {
      S.init.settings.values = res.values;
      const n = res.values.fast_workers;
      e.target.value = n;                                    // reflect clamping
      if (!(S.st && S.st.task)) {                            // keep the other mirrors in sync
        ["fastWorkers", "setFastWorkers"].forEach((id) => { const el = $(id); if (el) el.value = n; });
      }
    }
  });
  // Live-formulas toggles — each matrix has its OWN persisted setting.
  $("matrixFormulas")?.addEventListener("change", async (e) => {
    const r = await api.set_matrix_formulas(e.target.checked);
    if (r && r.error) showMessage("error", "Can't set formulas option", r.error);
    syncMatrixFormulas();
  });
  $("dayMatrixFormulas")?.addEventListener("change", async (e) => {
    const r = await api.set_day_matrix_formulas(e.target.checked);
    if (r && r.error) showMessage("error", "Can't set formulas option", r.error);
    syncDayMatrixFormulas();
  });
  $("baselineMatrixFormulas")?.addEventListener("change", async (e) => {
    const r = await api.set_baseline_matrix_formulas(e.target.checked);
    if (r && r.error) showMessage("error", "Can't set formulas option", r.error);
    syncBaselineMatrixFormulas();
  });
  // Evidence images — ONE shared persisted setting, surfaced on both matrix
  // pages (the checkboxes/counts are mirrors, resynced from each state push).
  for (const [cbId, countId, resync] of [
    ["matrixEvidence", "matrixEvidenceCount", () => syncMatrixEvidence()],
    ["dayMatrixEvidence", "dayMatrixEvidenceCount", () => syncDayMatrixEvidence()],
  ]) {
    $(cbId)?.addEventListener("change", async (e) => {
      const r = await api.set_evidence_images(e.target.checked);
      if (r && r.error) showMessage("error", "Can't set evidence option", r.error);
      resync();
    });
    $(countId)?.addEventListener("change", async (e) => {
      const r = await api.set_evidence_examples(e.target.value | 0);
      if (r && r.error) { showMessage("error", "Can't set evidence option", r.error); return; }
      if (r && r.examples) e.target.value = r.examples;      // reflect clamping
    });
  }
  // By-day Export-speed controls — the SAME shared fast knob the Everything matrix /
  // Export pane / Settings use (set_matrix_fast + the one fast_workers count).
  $("dayMatrixFast")?.addEventListener("change", async (e) => {
    const r = await api.set_matrix_fast(e.target.checked);
    if (r && r.error) { showMessage("error", "Can't set fast mode", r.error); syncDayMatrixFast(); }
  });
  $("dayMatrixWorkers")?.addEventListener("change", async (e) => {
    const res = await api.set_setting("fast_workers", e.target.value);
    if (res && res.error) { showMessage("error", "Can't set browser count", res.error); syncDayMatrixFast(); return; }
    if (res && res.values) {
      S.init.settings.values = res.values;
      const n = res.values.fast_workers;
      e.target.value = n;                                    // reflect clamping
      if (!(S.st && S.st.task)) {
        ["fastWorkers", "setFastWorkers", "matrixWorkers"].forEach((id) => { const el = $(id); if (el) el.value = n; });
      }
    }
  });
  $("btnQueueClear")?.addEventListener("click", () => api.matrix_queue_clear());
  $("btnQueueStopAll")?.addEventListener("click", () => api.matrix_stop_all());
  // The day matrices share the same queue (Clear / Stop-all act on it too).
  $("btnDayQueueClear")?.addEventListener("click", () => api.matrix_queue_clear());
  $("btnDayQueueStopAll")?.addEventListener("click", () => api.matrix_stop_all());
  $("btnBaselineQueueClear")?.addEventListener("click", () => api.matrix_queue_clear());
  $("btnBaselineQueueStopAll")?.addEventListener("click", () => api.matrix_stop_all());

  renderThemeButton();
  $("btnTheme").onclick = () => {
    const order = ["auto", "light", "dark"];
    const next = order[(order.indexOf(themePref()) + 1) % order.length];
    try { localStorage.setItem(THEME_KEY, next); } catch (_) { /* keep for session */ }
    withThemeTransition(() => { applyTheme(); renderThemeButton(); });
    api.ui_event("theme:" + next);
  };
  document.querySelectorAll(".popover-host").forEach(attachPopover);
  // keep the pre-flight summary live as the user edits any control
  // Debounced (FE-08): these fire on EVERY keystroke/toggle anywhere in the
  // body; the preflight table itself only needs the settled value (the routes
  // input already debounces its own handler at 200 ms).
  let preflightTimer = null;
  const debouncedPreflight = () => {
    clearTimeout(preflightTimer);
    preflightTimer = setTimeout(renderPreflight, 150);
  };
  document.body.addEventListener("change", debouncedPreflight);
  document.body.addEventListener("input", debouncedPreflight);

  $("selSource").onchange = () => {
    api.set_site($("selSource").value, $("selEnv").value);
    renderEnvAccess();          // re-aim the Export tab's availability flags
  };
  $("selEnv").onchange = () => {
    api.set_site($("selSource").value, $("selEnv").value);
    renderEnvAccess();
  };
  $("btnRecheck").onclick = () => api.start_checks();

  $("btnLogin").onclick = () => {
    if (S.st && S.st.login_phase === "open") api.finish_login();
    else api.start_login();
  };
  $("btnLoginCancel").onclick = () => api.cancel_login();
  $("btnUpdate").onclick = onUpdateClick;
  $("appVersion").onclick = () => api.check_updates();

  $("routesInput").addEventListener("input", onRoutesInput);
  $("btnChooseRoutes").onclick = chooseRoutes;
  $("fastMode").addEventListener("change", syncFastVisual);

  $("btnStartExport").onclick = startExport;
  $("btnSkip").onclick = () => api.skip_route();
  $("btnPause").onclick = () => api.pause_or_resume();
  $("btnCancelExport").onclick = () => api.cancel_run();
  $("btnStartBatch").onclick = () => startBatch();
  $("btnPauseBatch").onclick = () => api.pause_or_resume();
  $("btnCancelBatch").onclick = () => api.cancel_run();
  $("btnPickBatchDest").onclick = async () => {
    const r = await api.pick_batch_dest();
    if (r && r.dest) { setBatchDest(r.dest); renderBatchLibrary(); }
  };
  $("batchFast").onchange = () => { renderState(); };
  $("btnSaveReport").onclick = saveRunReport;
  $("btnSaveReportDone").onclick = saveRunReport;
  $("btnOpenRunFolder").onclick = () => api.open_run_folder();
  $("btnRetryFailed").onclick = async () => {
    const res = await api.retry_failed();
    if (res && res.error) showMessage("info", "Nothing to retry", res.error);
  };

  $("selDay").onchange = refreshConsDest;
  $("btnStartCons").onclick = startConsolidate;
  $("btnCancelCons").onclick = () => api.cancel_run();
  $("btnOpenConsFolder").onclick = () => api.open_consolidated_folder(consChoice(), selectedDay());
  $("btnOpenConsInput").onclick = () => api.open_consolidate_input(consChoice());

  // settings tab
  Object.keys(SETTING_INPUTS).forEach((id) => {
    $(id).addEventListener("change", () => onSettingInput(id));
  });
  $("setDebugLog").addEventListener("change", () => onSettingToggle("setDebugLog", "debug_logging"));
  $("setDevtools").addEventListener("change", () => onSettingToggle("setDevtools", "ui_devtools"));
  $("setEnvCheckSignin").addEventListener("change", () => onSettingToggle("setEnvCheckSignin", "env_check_after_signin"));
  $("setEnvCheckStart").addEventListener("change", () => onSettingToggle("setEnvCheckStart", "env_check_after_start"));
  $("setNotifyFinish").addEventListener("change", () => onSettingToggle("setNotifyFinish", "notify_on_finish"));
  $("btnValidate").onclick = async () => {
    // Disclose the side effect: validation re-runs each sample vs-TSN comparison
    // against the live store, refreshing those matrix cells (and rebuilding a
    // stale TSN library) — so the mutation is expected, not hidden.
    const ok = await showConfirm({
      title: "Validate & package results?",
      message: "This re-runs each sample report's comparison against TSN using the "
        + "reports already on this PC, then saves everything a maintainer needs into "
        + "one file.\n\nIt refreshes those comparison cells in the matrix and can take "
        + "several minutes. You can cancel it while it runs.",
      confirmLabel: "Validate",
    });
    if (!ok) return;
    const res = await api.run_validation();
    if (res && res.error) showMessage("error", "Can't validate right now", res.error);
    // Progress + the completion modal arrive via run_started/log/validate_done.
  };
  $("btnSupportBundle").onclick = async () => {
    const res = await api.save_support_bundle();
    if (res && res.error) showMessage("error", "Could not save the bundle", res.error);
  };
  $("btnSiteCapture")?.addEventListener("click", async () => {
    const res = await api.capture_site_source();
    if (res && res.error) showMessage("error", "Can't capture right now", res.error);
    // Progress + the saved-folder summary arrive via run_started/log events.
  });
  $("btnOpenFailures").onclick = () => api.open_failures_folder();
  $("btnCheckUpdates2").onclick = () => api.check_updates();
  $("btnRevert").onclick = async () => {
    const ok = await showConfirm({
      title: "Revert to the previous version?",
      message: "This downloads the release just before this one and restarts into it.\n\n"
        + "Your reports, login and settings are kept, and you can update again afterwards.",
      confirmLabel: "Revert",
    });
    if (!ok) return;
    const res = await api.revert_to_previous();
    if (res && res.error) showMessage("error", "Couldn't revert", res.error);
  };
  $("btnCheckEnvs").onclick = async () => {
    const res = await api.check_environments();
    if (res && res.error) showMessage("info", "Can't check right now", res.error);
  };
  $("btnCheckEnvsCancel").onclick = () => api.cancel_run();
  const applySitePreset = async (preset, confirmMsg) => {
    if (confirmMsg && !await showConfirm({ title: "Switch all site addresses?",
        message: confirmMsg, confirmLabel: "Switch all" })) return;
    const res = await api.apply_site_preset(preset);
    if (res && res.error) showMessage("error", "Couldn't switch", res.error);
    if (res && res.site_urls) { S.init.settings.site_urls = res.site_urls; renderSiteUrls(res.site_urls); }
  };
  $("btnSiteDev").onclick = () => applySitePreset("dev",
    "Point all six TSMIS addresses at the development site (tsmis-dev.dot.ca.gov)? "
    + "Intersection reports are available there. Used by the next sign-in / export.");
  $("btnSiteProd").onclick = () => applySitePreset("prod",
    "Clear every site-address override and go back to the built-in production addresses?");
  $("btnEnvAccess").onclick = () => {
    $("tabSettings").click();
    $("setSiteUrls").scrollIntoView({ behavior: "smooth", block: "center" });
  };
  $("btnOpenOutput2").onclick = () => api.open_output_folder();
  $("btnClearLogin").onclick = async () => {
    const ok = await showConfirm({
      title: "Forget the saved login?",
      message: "The saved session file will be deleted; the next export will need "
        + "a fresh sign-in (or automatic device sign-in, where available).",
      confirmLabel: "Forget login",
    });
    if (ok) api.clear_saved_login();
  };
  $("btnDeleteReports").onclick = deleteAllReports;
  $("btnVerifyEnv").onclick = verifyEnvironment;
  $("btnChromiumDownload").onclick = downloadChromium;
  $("btnChromiumDelete").onclick = deleteChromium;
  $("btnChromiumCancel").onclick = () => api.cancel_run();
  $("btnValidateCancel").onclick = () => api.cancel_run();

  $("btnPickTsmis").onclick = () => pickCompareFile("tsmis");
  $("btnPickTsn").onclick = () => pickCompareFile("tsn");
  $("btnPickDirA").onclick = () => pickCompareFolder("a");
  $("btnPickDirB").onclick = () => pickCompareFolder("b");
  $("cmpDirA").onchange = syncCompareButton;
  $("cmpDirB").onchange = syncCompareButton;
  ["cmpWantValues", "cmpWantFormulas"].forEach((id) => {
    const cb = $(id);
    cb.addEventListener("change", () => {
      cb.closest(".option-row").classList.toggle("checked", cb.checked);
      syncCompareButton();
      api.ui_event(`compare_out:${id}=${cb.checked}`);
    });
  });
  $("btnStartCompare").onclick = startCompare;
  $("btnCancelCompare").onclick = () => api.cancel_run();
  renderCompareFiles();
  renderCompareKind();

  $("btnOpenOutput").onclick = () => api.open_output_folder();
  $("btnOpenLogs").onclick = () => api.open_logs_folder();
  $("btnClearLog").onclick = clearLog;
  $("btnLogFailures").onclick = () => {
    const on = $("logBody").classList.toggle("filter-failures");
    $("btnLogFailures").classList.toggle("active", on);
    $("btnLogFailures").setAttribute("aria-pressed", String(on));
    if (on) scrollLogToEnd();
  };
  $("btnCopyLog").onclick = async () => {
    const text = [...$("logBody").querySelectorAll(".log-line")].map((l) => l.textContent).join("\n");
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      const b = $("btnCopyLog"); b.textContent = "Copied";
      setTimeout(() => { b.textContent = "Copy"; }, 1200);
    } catch (_) { /* clipboard can be blocked; nothing else to do */ }
  };

  const logBody = $("logBody");
  logBody.addEventListener("scroll", () => {
    S.logPinned = logBody.scrollHeight - logBody.scrollTop - logBody.clientHeight < 30;
  });

  window.addEventListener("error", (e) => {
    try { api && api.log_js_error(String(e.message || e.error)); } catch (_) { /* best-effort */ }
  });
}

// ----------------------------------------------------------- bootstrap -----
let booted = false;
async function boot(realApi) {
  if (booted) return;
  booted = true;
  api = realApi;
  // The first call can race a cold WebView2: pywebview's api OBJECT appears
  // before its method stubs are injected into it, so the call right after an
  // update (the coldest start — Windows is still scanning the new files)
  // could throw "get_initial_state is not a function" and a one-shot boot
  // died on it (field failure, v0.10.2 update). Retry patiently, re-grabbing
  // the bridge object each round, before declaring the engine dead.
  let init = null;
  let lastErr = null;
  for (let attempt = 1; attempt <= 6; attempt++) {
    try {
      init = await api.get_initial_state();
      lastErr = null;
      break;
    } catch (e) {
      lastErr = e;
      if (!WANT_MOCK && window.pywebview && window.pywebview.api) {
        api = window.pywebview.api;       // stubs may have landed by now
      }
      await new Promise((r) => setTimeout(r, Math.min(1000 * attempt, 3000)));
    }
  }
  if (lastErr) init = { error: String(lastErr) };
  if (!init || init.error) {
    // The bridge answered but the engine is broken — building a half-dead UI
    // would only hide it. Fail loudly; the log file has the traceback.
    showFatal("The app couldn't load its settings",
              (init && init.error) || "No response from the app engine. Details are in the log file.");
    try { api.log_js_error("boot aborted: get_initial_state failed"); } catch (_) { /* mock/broken bridge */ }
    return;
  }
  hideFatal();
  S.init = init;
  buildStatic();
  fillSettings();
  bindEvents();
  S.st = S.init.state;
  renderState();
  refreshConsDest();
  window.__tsmis = {
    dispatch,
    // hooks for the packaged self-test (build/full_smoke.py)
    test_state: () => JSON.stringify({ init: !!S.init, task: S.st && S.st.task, lines: S.logLines }),
  };
  await api.ui_ready();
}

// The mock preview must be OPT-IN (open index.html#mock in a browser). It must
// never race the real bridge: on a cold/slow WebView2 the pywebview object can
// appear later than any fixed timeout, and silently booting the mock inside
// the real app would show convincing fake exports.
const WANT_MOCK = /[?#&]mock\b/.test(location.search + location.hash);

// The bridge is only usable once its method STUBS are injected — the bare
// api object shows up a beat earlier on a cold WebView2 (boot() also retries,
// as the second line of defense).
const bridgeReady = () =>
  !!(window.pywebview && window.pywebview.api
     && typeof window.pywebview.api.get_initial_state === "function");

// In production (no #mock) app.js owns EVERY real-bridge boot path -- the
// pywebviewready listener AND the poll backstop -- so they ALL live inside this
// !WANT_MOCK gate. For #mock, mock.js -- loaded as a classic <script> AFTER this
// file -- owns the boot (it defines the mock api, then boots the UI against it), so
// under #mock app.js registers NO bridge boot: the preview can never race the real
// bridge and the mock code never ships into the production boot path (P9-R01).
if (!WANT_MOCK) {
  window.addEventListener("pywebviewready", () => {
    if (bridgeReady()) boot(window.pywebview.api);   // else the poll catches it
  });
  // The ready event may have fired before this script attached its listener;
  // re-check periodically instead of guessing one magic delay.
  const poll = setInterval(() => {
    if (booted) { clearInterval(poll); return; }
    if (bridgeReady()) { clearInterval(poll); boot(window.pywebview.api); }
  }, 150);
  // Cold starts (especially the FIRST launch after an update, while Windows
  // scans the fresh files) can outlast any reasonable timeout — reassure
  // first, declare failure only much later. The poll keeps running either
  // way, and a late bridge still boots + clears the banner.
  setTimeout(() => {
    if (!booted) {
      showFatal("Still starting…",
                "The interface is waiting for the app engine. The first launch after an "
                + "update can take noticeably longer while Windows checks the new files — "
                + "this screen goes away by itself when the app is ready.");
    }
  }, 8000);
  setTimeout(() => {
    if (!booted) {
      showFatal("The app's interface couldn't connect to its engine",
                "The page loaded but the pywebview bridge never arrived. Close the app and try again; "
                + "details are in the log file. (For a browser-only design preview, open index.html#mock.)");
    }
  }, 60000);
}
