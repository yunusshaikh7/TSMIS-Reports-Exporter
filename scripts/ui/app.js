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

// ------------------------------------------------- screenshot previews -----
// One modal for both flavors: a worker's on-demand page screenshot during an
// export, and the idle "Verify environment" check (worker 0). Python answers
// with a {t:"preview"} event; until it arrives the modal shows a wait note.
let preview = null;   // {worker, body, note, timer} while the modal is open

function openPreviewModal(worker, title, waitText) {
  const m = buildModal({ title, iconName: "i-camera" });
  m.classList.add("modal-preview");
  const body = document.createElement("div");
  body.className = "preview-body";
  const wait = document.createElement("div");
  wait.className = "preview-wait";
  wait.appendChild(icon("i-loader"));
  wait.appendChild(Object.assign(document.createElement("span"), { textContent: waitText }));
  body.appendChild(wait);
  m.appendChild(body);
  const note = document.createElement("div");
  note.className = "preview-note";
  m.appendChild(note);
  const actions = document.createElement("div");
  actions.className = "modal-actions";
  const refresh = document.createElement("button");
  refresh.className = "btn btn-subtle";
  refresh.appendChild(icon("i-refresh"));
  refresh.appendChild(Object.assign(document.createElement("span"), { textContent: "Take another" }));
  refresh.onclick = () => { if (worker > 0) { requestPreview(worker, true); } };
  if (worker > 0) actions.appendChild(refresh);
  const close = document.createElement("button");
  close.className = "btn btn-accent"; close.textContent = "Close";
  close.onclick = () => closeModal(true);
  actions.appendChild(close);
  m.appendChild(actions);

  preview = { worker, body, note, timer: null };
  if (worker > 0) {
    preview.timer = setTimeout(() => {
      if (preview && preview.worker === worker) {
        note.textContent = "Still waiting — the browser may be mid-download; "
          + "the screenshot arrives at its next safe moment.";
      }
    }, 30000);
  }
  openModal(m).then(() => {
    if (preview) { clearTimeout(preview.timer); preview = null; }
  });
  close.focus();
}

function showPreviewEvent(ev) {
  // Screenshot (or failure note) arrived. Fill the open modal; if the user
  // already closed it, drop the image silently (they can click again).
  if (!preview || preview.worker !== ev.w) return;
  clearTimeout(preview.timer);
  preview.body.textContent = "";
  if (ev.env_info) {
    const v = ev.env_info;
    const banner = document.createElement("div");
    let cls = "unknown";
    let text = "The page didn't report which data source / environment it loaded — check the screenshot's own label.";
    if (v.env) {
      const got = `${(v.src || "?").toUpperCase()} · ${(v.env || "?").toUpperCase()}`;
      if (v.matches) { cls = "ok"; text = `The page is running ${got} — matches your selection (${v.wanted}).`; }
      else { cls = "bad"; text = `The page is running ${got}, but ${v.wanted} is selected!`; }
    } else if (v.ok === false) {
      cls = "bad"; text = "Sign-in didn't complete — the screenshot shows where it stopped.";
    }
    banner.className = "env-verdict " + cls;
    banner.textContent = text;
    preview.body.appendChild(banner);
  }
  if (ev.url) {
    // The page's address at capture time — an address bar over the screenshot.
    const addr = document.createElement("div");
    addr.className = "preview-url";
    addr.textContent = ev.url;
    preview.body.appendChild(addr);
  }
  if (ev.img) {
    const img = document.createElement("img");
    img.className = "preview-img";
    img.src = "data:image/jpeg;base64," + ev.img;
    img.alt = "Browser screenshot";
    preview.body.appendChild(img);
    preview.note.textContent = (ev.note ? ev.note + " — " : "")
      + "taken " + new Date().toLocaleTimeString();
  } else {
    const fail = document.createElement("div");
    fail.className = "preview-wait";
    fail.textContent = ev.note || "No screenshot was captured.";
    preview.body.appendChild(fail);
  }
}

function requestPreview(worker, isRefresh) {
  api.request_preview(worker).then((res) => {
    if (res && res.error) {
      closeModal(null);
      showMessage("info", "No screenshot available", res.error);
    }
  });
  if (!isRefresh) {
    openPreviewModal(worker, `Browser ${worker} — live screenshot`,
      "Asking the browser for a screenshot… it answers at its next safe moment (usually under 5 s).");
  } else if (preview) {
    preview.note.textContent = "Taking another…";
  }
}

// ------------------------------------------------ worker status rows -------
function buildWorkerStrip(n) {
  const strip = $("workerStrip");
  strip.textContent = "";
  S.workers = n;
  for (let w = 1; w <= n; w++) {
    const row = document.createElement("div");
    row.className = "worker-row";
    const name = document.createElement("span");
    name.className = "w-name";
    name.textContent = n > 1 ? `Browser ${w}` : "Browser";
    const status = document.createElement("span");
    status.className = "w-status"; status.id = `workerStatus_${w}`;
    status.textContent = "starting…";
    const btn = document.createElement("button");
    btn.className = "btn btn-subtle btn-small w-shot";
    btn.title = "Show a live screenshot of this browser's page (auth state, environment label, report progress)";
    btn.appendChild(icon("i-camera"));
    btn.appendChild(Object.assign(document.createElement("span"), { textContent: "Preview" }));
    btn.onclick = () => requestPreview(w, false);
    row.append(name, status, btn);
    strip.appendChild(row);
  }
  strip.classList.toggle("hidden", n < 1);
}

function updateWorkerStatus(w, text) {
  const el = $(`workerStatus_${w}`);
  if (el) { el.textContent = text; el.title = text; }
}

// ARIA tabs arrow-key pattern (FE-04): Left/Right move + activate within any
// role=tablist (the main tab bar + the Everything sub-tabs). Tabs are real
// buttons, so Enter/Space/Tab already work; this adds the expected arrows.
document.addEventListener("keydown", (e) => {
  if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
  const bar = e.target.closest && e.target.closest('[role="tablist"]');
  if (!bar) return;
  const tabs = [...bar.querySelectorAll('[role="tab"]:not(:disabled)')];
  const i = tabs.indexOf(e.target);
  if (i < 0) return;
  e.preventDefault();
  const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
  next.focus();
  next.click();
});

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && modalResolve) closeModal(null);
  // Block page reloads: WebView2 honors F5/Ctrl+R, and reloading mid-run
  // resets the live progress/log view while the engine keeps working.
  if (e.key === "F5" || ((e.ctrlKey || e.metaKey) && (e.key === "r" || e.key === "R"))) {
    e.preventDefault();
  }
});

// No browser context menu (it carries Reload). Text selection + Ctrl+C still
// work for copying log lines and paths.
document.addEventListener("contextmenu", (e) => e.preventDefault());

// A report-type checkbox row (Export tab + Everything tab share this). `off`
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
  // The "TSN by day" matrix is a manual day-picking sub-tab (not a registry
  // comparison group), appended after the generated ones.
  const dayTab = document.createElement("button");
  dayTab.className = "subtab"; dayTab.dataset.group = DAY_MATRIX_GROUP;
  dayTab.setAttribute("role", "tab"); dayTab.setAttribute("aria-selected", "false");
  dayTab.textContent = "vs TSN Matrix";
  dayTab.addEventListener("click", () => selectCompareGroup(DAY_MATRIX_GROUP));
  subStrip.appendChild(dayTab);

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
  ["selSource", "selEnv", "routesInput", "btnChooseRoutes", "selDay",
   "btnVerifyEnv", "btnDeleteReports", "btnClearLogin", "btnSupportBundle",
   "btnValidate", "btnCheckEnvs"]
    .forEach((id) => { $(id).disabled = locked; });
  Object.keys(SETTING_INPUTS).forEach((id) => { $(id).disabled = locked; });
  ["setDebugLog", "setDevtools", "setEnvCheckSignin", "setEnvCheckStart", "setNotifyFinish"].forEach((id) => {
    $(id).disabled = locked;
    $(id).closest(".option-row").classList.toggle("disabled", locked);
  });
  $("setSiteUrls").querySelectorAll("input").forEach((i) => { i.disabled = locked; });
  $("btnChromiumDownload").disabled = locked;
  $("btnChromiumDelete").disabled = locked;
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
  $("btnStartExport").disabled = locked;
  $("btnStartCons").disabled = locked;
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
  $("btnStartBatch").disabled = locked;
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
  $("btnPickBatchDest").disabled = locked;
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

// Pre-flight summary for the activity column: a plain-words "about to do X"
// mirror of the active tab's pending action — the report/scope, the resolved
// SSOR/ARS × environment target (answering the recurring "am I on the right
// site?" worry), and where the file lands. Shown while idle; the progress card
// replaces it on run. Built from live form state so it tracks every change.
function pfTodayRunFolder() {
  const d = new Date(), p = (n) => String(n).padStart(2, "0");
  const date = `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  return `${date} ${$("selSource").value}-${$("selEnv").value}`;
}
function pfRoutesSummary() {
  const raw = $("routesInput").value.trim();
  const total = (S.init.routes || []).length;
  if (!raw) return `All ${total} routes`;
  const parts = raw.split(/[,\s]+/).filter(Boolean);
  return `${parts.length} route${parts.length === 1 ? "" : "s"}: ${raw}`;
}
function renderPreflight() {
  const card = $("preflightCard");
  // Bail when hidden DIRECTLY (while running) or via an ANCESTOR (matrix mode
  // hides the whole tab; offsetParent is null anywhere under display:none) —
  // the class check alone kept recomputing the table invisibly (FE-08).
  if (!card || card.classList.contains("hidden")
      || card.offsetParent === null) return;
  const tab = S.tab || "export";
  const rows = $("preflightRows");
  const targetEl = $("preflightTarget");
  rows.textContent = "";
  targetEl.classList.add("hidden");
  const srcLabel = (id) => (((S.init || {}).sources || []).find((s) => s.id === id) || {}).label || id;
  const envLabel = (id) => (((S.init || {}).envs || []).find((e) => e.id === id) || {}).label || id;

  const addRow = (label, value, opts) => {
    opts = opts || {};
    const r = document.createElement("div"); r.className = "pf-row";
    const l = document.createElement("span"); l.className = "pf-label"; l.textContent = label;
    const v = document.createElement("span");
    v.className = "pf-value" + (opts.path ? " path" : "") + (opts.warn ? " pf-warn" : "");
    v.textContent = value;
    if (opts.title) v.title = value;
    r.append(l, v); rows.appendChild(r);
  };
  const showTarget = () => {
    const src = $("selSource").value, env = $("selEnv").value;
    targetEl.classList.remove("hidden");
    targetEl.querySelector(".pf-target-text").textContent = `${srcLabel(src)} · ${envLabel(env)}`;
    const acc = (S.st && S.st.env_access) || {};
    const e = acc[`${src}-${env}`];
    const badge = e && (ENV_ACCESS_BADGE[e.status] || ENV_ACCESS_BADGE.error);
    setDot($("preflightTargetDot"), badge ? badge.dot : "unknown");
  };

  if (tab === "export") {
    $("preflightTitle").textContent = "Ready to export";
    showTarget();
    const labels = selectedReportKeys().map((k) => reportByKey(k).label).filter(Boolean);
    if (!labels.length) addRow("Reports", "Nothing selected — pick a report on the left", { warn: true });
    else addRow("Reports", labels.length === 1 ? labels[0] : `${labels.length} reports`, { title: true });
    addRow("Routes", pfRoutesSummary());
    addRow("Saves to", `output\\${pfTodayRunFolder()}\\`, { path: true, title: true });
    if ($("fastMode").checked) addRow("Mode", `Fast — ${$("fastWorkers").value} browsers at once`);
  } else if (tab === "everything") {
    $("preflightTitle").textContent = "Ready to refresh";
    const reps = $("batchReportList").querySelectorAll("input:checked").length;
    const envs = $("batchEnvList").querySelectorAll("input:checked").length;
    addRow("Reports", `${reps} report type${reps === 1 ? "" : "s"}`, { warn: reps === 0 });
    addRow("Targets", `${envs} environment${envs === 1 ? "" : "s"}`, { warn: envs === 0 });
    addRow("Saves to", $("batchDest").textContent || "—", { path: true, title: true });
  } else if (tab === "consolidate") {
    $("preflightTitle").textContent = "Ready to consolidate";
    const r = $("consList").querySelector(".option-row.checked .option-name");
    addRow("Report", r ? r.textContent : "—", { title: true });
    // Dropped-input reports (TSN / TSMIS Highway Log PDF) read from their input
    // folder, not a dated export run, so the "From" is that folder, not a day.
    if (S.consDropped) addRow("From", S.consInputDir || "input folder", { path: true, title: true });
    else addRow("From", $("selDay").value || "Newest run");
    addRow("Saves to", $("consDest").textContent || "—", { path: true, title: true });
  } else if (tab === "compare") {
    $("preflightTitle").textContent = "Ready to compare";
    const t = $("compareList").querySelector(".option-row.checked .option-name");
    addRow("Type", t ? t.textContent : "—", { title: true });
    if (compareKind() === "folders") {
      addRow("Baseline", $("cmpDirA").value || "— not picked —", { title: true, warn: !$("cmpDirA").value });
      addRow("Compare", $("cmpDirB").value || "— not picked —", { title: true, warn: !$("cmpDirB").value });
    } else {
      const rep = currentCompareRep();
      addRow(rep.file_a_label || "TSMIS", CMP.tsmis || "— not picked —", { path: !!CMP.tsmis, title: true, warn: !CMP.tsmis });
      addRow(rep.file_b_label || "TSN", CMP.tsn || "— not picked —", { path: !!CMP.tsn, title: true, warn: !CMP.tsn });
    }
    const outs = [];
    if ($("cmpWantValues").checked) outs.push("Values");
    if ($("cmpWantFormulas").checked) outs.push("Live formulas");
    addRow("Output", outs.join(" + ") || "Pick at least one", { warn: !outs.length });
  } else {
    $("preflightTitle").textContent = "Nothing queued";
    const note = document.createElement("div");
    note.className = "pf-value";
    note.textContent = "Adjust settings on the left — exports run from the other tabs.";
    rows.appendChild(note);
  }
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
    row.title = off
      ? `The last environment check found this report ${state === "greyed"
          ? "greyed out" : "missing"} on ${active.label} — the export may fail.`
      : "";
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
    row.title = hits.length
      ? "The last environment check found this report unavailable on:\n"
        + hits.join("\n") + "\nThe export may fail there."
      : "";
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
          break;
        case "matrix_refresh":
          if (S.tab === "everything" && S.everySub === "matrix") renderMatrix();
          if (S.tab === "compare" && S.compareGroup === DAY_MATRIX_GROUP) renderDayMatrix();
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
function syncFastVisual() {
  const on = $("fastMode").checked;
  $("fastZap").classList.toggle("on", on);
  $("fastWorkers").disabled = !on || $("fastMode").disabled;
}

let routesDebounce = null;
function onRoutesInput() {
  clearTimeout(routesDebounce);
  routesDebounce = setTimeout(async () => {
    const raw = $("routesInput").value.trim();
    const hint = $("routesHint");
    if (!raw) {
      hint.textContent = "Leave blank to export all routes.";
      hint.classList.remove("hint-error");
      return;
    }
    const res = await api.parse_routes_preview(raw);
    hint.textContent = res.ok ? `${res.count} route(s) selected.` : res.error;
    hint.classList.toggle("hint-error", !res.ok);
  }, 200);
}

async function chooseRoutes() {
  const raw = $("routesInput").value.trim();
  let current = [];
  if (raw) {
    const res = await api.parse_routes_preview(raw);
    if (res.ok) current = res.routes;
  }
  const picked = await showRoutePicker(current);
  if (picked == null) return;
  // All or none both mean "every route" — keep the box blank (the documented
  // "blank = all" convention) rather than stuffing it with all 283 numbers, so
  // the box and the picker always represent the same selection cleanly.
  const all = (S.init.routes || []).length;
  $("routesInput").value = (picked.length === 0 || picked.length === all) ? "" : picked.join(", ");
  onRoutesInput();
}

async function startExport() {
  const reports = selectedReportKeys();
  if (!reports.length) {
    showMessage("info", "Pick a report", "Tick at least one report to export.");
    return;
  }
  const raw = $("routesInput").value.trim();
  if (raw) {
    const res = await api.parse_routes_preview(raw);
    if (!res.ok) {
      showMessage("error", "Check routes", res.error + "\n\nExample: 5, 99, 101");
      return;
    }
  }
  const st = S.st;
  if (!st.authed && !st.device_ok) {
    const go = await showConfirm({
      title: "No saved login",
      message: "There's no saved login yet.\n\nStart the export anyway? On Caltrans PCs it can sign in "
        + "automatically using Microsoft Edge and this PC's Windows account.\n\n"
        + "(If automatic sign-in isn't available, the export will stop and ask you to log in.)",
      confirmLabel: "Start anyway",
    });
    if (!go) return;
  }
  const fast = $("fastMode").checked;
  const workers = fast ? parseInt($("fastWorkers").value, 10) || S.init.fast.default : 1;
  const autoConsolidate = $("autoConsolidate").checked;
  const res = await api.start_export(reports, raw, fast, workers, autoConsolidate);
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

// ---- Export Everything (B3) ----
function updateBatchCount() {
  const r = [...$("batchReportList").querySelectorAll("input")].filter((c) => c.checked).length;
  const e = [...$("batchEnvList").querySelectorAll("input")].filter((c) => c.checked).length;
  const el = $("batchReportCount");
  if (el) el.textContent = `${r} report type(s) × ${e} env(s)`;
}

function renderBatchResume(resume) {
  const el = $("batchResume");
  if (!el) return;
  if (!resume || !resume.pending) { el.hidden = true; el.textContent = ""; return; }
  el.hidden = false; el.textContent = "";
  const msg = document.createElement("p");
  msg.className = "hint";
  msg.textContent = `An unfinished Export Everything batch has ${resume.pending} of ${resume.total} environment(s) left.`;
  const row = document.createElement("div");
  row.className = "actions-row";
  const locked = !!(S.st && S.st.task);
  const rb = document.createElement("button");
  rb.className = "btn btn-accent"; rb.textContent = "Resume batch";
  rb.disabled = locked; rb.onclick = () => api.resume_batch();
  const db = document.createElement("button");
  db.className = "btn btn-subtle"; db.textContent = "Discard";
  db.disabled = locked; db.onclick = () => api.discard_batch();
  row.append(rb, db);
  el.append(msg, row);
}

async function startBatch(onlyReports) {
  const reports = (onlyReports && onlyReports.length) ? onlyReports
    : [...$("batchReportList").querySelectorAll("input")]
        .filter((c) => c.checked).map((c) => c.dataset.key);
  if (!reports.length) {
    showMessage("info", "Pick a report type", "Tick at least one report type."); return;
  }
  const envs = [...$("batchEnvList").querySelectorAll("input")]
    .filter((c) => c.checked).map((c) => c.dataset.key);
  if (!envs.length) {
    showMessage("info", "Pick an environment", "Tick at least one environment."); return;
  }
  const st = S.st;
  if (!st.authed && !st.device_ok) {
    const go = await showConfirm({
      title: "No saved login",
      message: "There's no saved login yet.\n\nStart anyway? On Caltrans PCs it can sign in "
        + "automatically using Microsoft Edge and this PC's Windows account.",
      confirmLabel: "Start anyway",
    });
    if (!go) return;
  }
  const fast = $("batchFast").checked;
  const workers = fast ? parseInt($("batchWorkers").value, 10) || S.init.fast.default : 1;
  const auto = $("batchAutoConsolidate").checked;
  const res = await api.start_batch_export(reports, envs, fast, workers, auto);
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

function fmtAge(s) {
  if (s == null) return "";
  const d = Math.floor(s / 86400), h = Math.floor(s / 3600), m = Math.floor(s / 60);
  if (d >= 1) return `${d} day${d > 1 ? "s" : ""} ago`;
  if (h >= 1) return `${h} hour${h > 1 ? "s" : ""} ago`;
  if (m >= 1) return `${m} min ago`;
  return "just now";
}

function setBatchDest(dest) {
  const el = $("batchDest");
  if (el && dest) { el.textContent = dest; el.title = dest; }
  renderPreflight();
}

async function renderBatchLibrary() {
  let info;
  try { info = await api.report_library_info(); } catch (e) { return; }
  if (!info) return;
  setBatchDest(info.dest);
  const lib = $("batchLibrary");
  if (!lib) return;
  const rows = info.reports || [];
  const present = rows.filter((r) => r.present);
  const freshest = present.length ? Math.min(...present.map((r) => r.age_seconds)) : 0;
  const locked = !!(S.st && S.st.task);
  lib.textContent = "";
  rows.forEach((r) => {
    const row = document.createElement("div");
    row.className = "lib-row" + (r.present ? "" : " missing");
    const name = document.createElement("span");
    name.className = "lib-name"; name.textContent = r.label;
    const age = document.createElement("span");
    age.className = "lib-age";
    if (!r.present) {
      age.textContent = "never exported";
    } else {
      const stale = (r.age_seconds - freshest) > 2 * 86400 && r.age_seconds > 86400;
      age.textContent = fmtAge(r.age_seconds) + (stale ? " · stale" : "");
      if (stale) row.classList.add("stale");
    }
    const btn = document.createElement("button");
    btn.className = "btn btn-subtle btn-small";
    btn.textContent = r.present ? "Refresh" : "Export";
    btn.disabled = locked;
    btn.onclick = () => startBatch([r.subdir]);   // export-op key = subdir (P3)
    row.append(name, age, btn);
    lib.appendChild(row);
  });
  const meta = $("batchLibMeta");
  if (meta) meta.textContent = `${present.length} of ${rows.length} present`;
}

async function startConsolidate() {
  const key = consChoice();
  const day = selectedDay();
  const info = await api.consolidate_info(key, day);
  if (info.exists) {
    const ok = await showConfirm({
      title: "Overwrite?",
      message: `A consolidated workbook already exists:\n\n${info.out_path}\n\nOverwrite it?`,
      confirmLabel: "Overwrite",
      danger: true,
    });
    if (!ok) { api.decline_overwrite(); return; }
  }
  const res = await api.start_consolidate(key, day);
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

async function saveRunReport() {
  const res = await api.save_run_report();
  if (res && res.error) showMessage("error", "Could not save report", res.error);
}

// ---- comparisons (files kind = TSMIS vs TSN; folders kind = env vs env) ----
const CMP = { tsmis: null, tsn: null };

function compareKind() {
  // Resolve by KEY (P3) — compareChoice() returns a `cmp:*` key, so the old
  // array[index] lookup always read undefined and defaulted every comparison to
  // "files", routing folder compares to the file path. currentCompareRep() finds
  // the row by key.
  return currentCompareRep().kind || "files";
}

// Switch the Compare sub-tab: highlight the button, show only that group's
// comparison-type rows, and keep exactly one VISIBLE row selected. Radios share a
// name, so seating a new pick natively drops the now-hidden previous one;
// renderCompareKind then swaps in the matching files/folders inputs.
const DAY_MATRIX_GROUP = "tsn_by_day";

// Full-width "matrix" layout is shared by the Everything comparison matrix and the
// Compare-tab by-day matrix. Compute it from the active tab/sub-tab in ONE place so
// every entry point (tab switch, Everything sub-tab, compare-group switch) stays in
// sync. body.matrix-wide drives the shared layout (grid fills the screen, activity
// log shrinks); body.mw-day additionally picks the by-day config corner.
function applyMatrixWide() {
  const every = S.tab === "everything" && S.everySub === "matrix";
  const day = S.tab === "compare" && S.compareGroup === DAY_MATRIX_GROUP;
  document.body.classList.toggle("matrix-wide", every || day);
  document.body.classList.toggle("mw-day", day);
}

function selectCompareGroup(groupId) {
  S.compareGroup = groupId;
  document.querySelectorAll("#compareSubtabs .subtab").forEach((b) => {
    const on = b.dataset.group === groupId;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", String(on));
  });
  // The TSN-by-day matrix swaps the whole classic picker out for the grid and goes
  // full-width (same treatment as the Everything matrix).
  const dayMode = groupId === DAY_MATRIX_GROUP;
  $("compareClassic")?.classList.toggle("hidden", dayMode);
  $("dayMatrixSection")?.classList.toggle("hidden", !dayMode);
  applyMatrixWide();
  if (dayMode) { renderDayMatrix(); return; }
  // family headers (W2) filter with their sub-tab, like the rows
  $("compareList").querySelectorAll(".option-group").forEach((h) => {
    h.classList.toggle("hidden", h.dataset.group !== groupId);
  });
  const rows = [...$("compareList").querySelectorAll(".option-row")];
  let firstVisible = null, checkedVisible = false;
  rows.forEach((r) => {
    const on = r.dataset.group === groupId;
    r.classList.toggle("hidden", !on);
    if (on) {
      firstVisible = firstVisible || r;
      if (r.querySelector("input").checked) checkedVisible = true;
    }
  });
  if (!checkedVisible && firstVisible) {
    rows.forEach((r) => r.classList.remove("checked"));
    firstVisible.querySelector("input").checked = true;
    firstVisible.classList.add("checked");
  }
  renderCompareKind();
}

function renderCompareFiles() {
  for (const [side, id] of [["tsmis", "cmpTsmisPath"], ["tsn", "cmpTsnPath"]]) {
    const el = $(id);
    el.textContent = CMP[side] || "— not selected —";
    el.title = CMP[side] || "";
    el.classList.toggle("unset", !CMP[side]);
  }
  syncCompareButton();
}

// Folder dropdowns: the known run folders (newest first) plus any custom
// path picked via Browse… (kept as an extra option per side).
const CMP_DIRS = { a: null, b: null };   // custom absolute paths from Browse…

function fillCompareDirSelect(sel, custom, preferred, days) {
  days = days || [];
  const prev = sel.value;
  sel.textContent = "";
  if (custom) {
    const o = document.createElement("option");
    o.value = custom; o.textContent = custom;
    sel.appendChild(o);
  }
  days.forEach((d) => {
    const o = document.createElement("option");
    o.value = d; o.textContent = d;
    sel.appendChild(o);
  });
  if (!days.length && !custom) {
    const o = document.createElement("option");
    o.value = ""; o.textContent = "— no export folders yet —";
    sel.appendChild(o);
  }
  const options = [...sel.options].map((o) => o.value);
  // The user's CURRENT selection survives every re-render; the Browse… path is
  // just an extra OPTION, not an override (it used to win here on every state
  // re-render, silently stomping a later dropdown pick — the comparison then
  // ran against the stale custom folder). Browse takes effect via
  // pickCompareFolder setting the value explicitly, once.
  if (prev && options.includes(prev)) sel.value = prev;
  else if (preferred && options.includes(preferred)) sel.value = preferred;
  else if (custom) sel.value = custom;
}

async function renderCompareDirs() {
  // A2: only offer run folders that actually contain the chosen report. Python
  // owns the membership test (api.get_compare_folders); fall back to all known
  // folders on any hiccup so the dropdowns are never empty by mistake.
  let days = (S.st && S.st.days) || [];
  try {
    const res = await api.get_compare_folders(compareChoice());
    if (res && Array.isArray(res.folders)) days = res.folders;
  } catch (e) { /* keep the unfiltered list */ }
  // sensible defaults: baseline = newest ssor-prod run, other side = the
  // newest folder that differs from the baseline
  const baseline = days.find((d) => /ssor-prod$/.test(d)) || days[0] || "";
  fillCompareDirSelect($("cmpDirA"), CMP_DIRS.a, baseline, days);
  const other = days.find((d) => d !== $("cmpDirA").value) || days[0] || "";
  fillCompareDirSelect($("cmpDirB"), CMP_DIRS.b, other, days);
  syncCompareButton();
}

function renderCompareKind() {
  const folders = compareKind() === "folders";
  $("cmpFilesSection").classList.toggle("hidden", folders);
  $("cmpFoldersSection").classList.toggle("hidden", !folders);
  if (folders) {
    renderCompareDirs();
  } else {
    // Label the two file pickers from the selected comparison so a
    // PDF-vs-Excel comparison doesn't say "TSN" for a TSMIS Excel file.
    const rep = currentCompareRep();
    const a = rep.file_a_label || "TSMIS", b = rep.file_b_label || "TSN";
    $("cmpTsmisLabel").textContent = a + " file";
    $("cmpTsnLabel").textContent = b + " file";
    $("cmpFilesHint").textContent =
      `Pick the ${a} file and the ${b} file — either two per-route workbooks `
      + `(one route each) or two consolidated workbooks (all routes).`;
  }
  syncCompareButton();
}

function syncCompareButton() {
  const locked = S.st && S.st.task != null;
  const anyOut = $("cmpWantValues").checked || $("cmpWantFormulas").checked;
  const ready = compareKind() === "folders"
    ? ($("cmpDirA").value && $("cmpDirB").value
       && $("cmpDirA").value !== $("cmpDirB").value)
    : (CMP.tsmis && CMP.tsn);
  $("btnStartCompare").disabled = locked || !ready || !anyOut;
  $("cmpOutHint").textContent = anyOut
    ? "Pick one or both. With both, the values copy is saved next to the other as “… (values).xlsx”."
    : "Tick at least one output to enable the comparison.";
  renderPreflight();
}

async function pickCompareFile(side) {
  const res = await api.pick_compare_file(side.toUpperCase());
  if (res && res.path) {
    CMP[side] = res.path;
    renderCompareFiles();
  }
}

async function pickCompareFolder(side) {
  const res = await api.pick_compare_folder(side.toUpperCase());
  if (res && res.path) {
    CMP_DIRS[side] = res.path;
    await renderCompareDirs();
    // Browsing IS an explicit selection (once) — later dropdown picks stick.
    $(side === "a" ? "cmpDirA" : "cmpDirB").value = res.path;
    syncCompareButton();
  }
}

async function startCompare() {
  let res;
  if (compareKind() === "folders") {
    res = await api.start_compare_env(compareChoice(),
                                      $("cmpDirA").value, $("cmpDirB").value,
                                      $("cmpWantFormulas").checked,
                                      $("cmpWantValues").checked);
  } else {
    res = await api.start_compare(compareChoice(), CMP.tsmis, CMP.tsn,
                                  $("cmpWantFormulas").checked,
                                  $("cmpWantValues").checked);
  }
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

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
      // Compare re-enters its last sub-tab; the by-day one re-applies full-width.
      if (tab === "compare" && S.compareGroup === DAY_MATRIX_GROUP) renderDayMatrix();
      applyMatrixWide();   // clears matrix-wide unless the by-day matrix is active
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
  // The by-day matrix shares the same queue (Clear / Stop-all act on it too).
  $("btnDayQueueClear")?.addEventListener("click", () => api.matrix_queue_clear());
  $("btnDayQueueStopAll")?.addEventListener("click", () => api.matrix_stop_all());

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
