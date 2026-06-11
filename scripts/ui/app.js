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
  progress: null,      // latest export progress payload
  runMode: null,       // "export" | "consolidate" while the bar is live
  elapsedStart: null,
  elapsedTimer: null,
  logPinned: true,
  logLines: 0,
};
const LOG_MAX_LINES = 3000;

let api = null;        // real pywebview api or the mock

// ------------------------------------------------------------- utilities ---
function fmtElapsed(ms) {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const mm = String(m).padStart(2, "0"), ss = String(sec).padStart(2, "0");
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

function setDot(elm, state) {
  elm.className = "dot dot-" + (state || "unknown");
}

// ------------------------------------------------------------- theme -------
// Preference: auto | light | dark (persisted). html[data-theme] always holds
// the EFFECTIVE light/dark; "auto" follows the OS live via matchMedia.
const THEME_KEY = "tsmis-theme";

function themePref() {
  try { return localStorage.getItem(THEME_KEY) || "auto"; } catch (_) { return "auto"; }
}

function applyTheme() {
  const pref = themePref();
  const dark = pref === "dark" || (pref !== "light"
    && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", applyTheme);

function icon(name, cls) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "ic" + (cls ? " " + cls : ""));
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", "#" + name);
  svg.appendChild(use);
  return svg;
}

// ------------------------------------------------------------ log pane -----
function appendLog(text) {
  $("logPlaceholder")?.remove();
  const body = $("logBody");
  const line = document.createElement("div");
  line.className = "log-line";
  // Colorize like the old GUI, but don't paint a SUCCESS summary red just
  // because it says "failed 0": strip zero-count mentions before testing.
  const scrubbed = text.replace(/\bfailed:?\s+0\b/gi, "");
  const upper = scrubbed.toUpperCase();
  if (upper.includes("FAIL") || upper.includes("ERROR")) line.classList.add("err");
  else if (text.includes("saved") || text.includes("Output file") || text.includes("Output:")) line.classList.add("ok");
  line.textContent = text === "" ? " " : text;
  body.appendChild(line);
  if (++S.logLines > LOG_MAX_LINES) { body.firstChild.remove(); S.logLines--; }
  // NOTE: no scroll here — dispatch() scrolls ONCE per event batch (a batch
  // can carry hundreds of lines; per-line scrollTop forces a reflow each).
}

function scrollLogToEnd() {
  if (S.logPinned) {
    const body = $("logBody");
    body.scrollTop = body.scrollHeight;
  }
}

function clearLog() {
  const body = $("logBody");
  body.textContent = "";
  S.logLines = 0;
  const ph = document.createElement("div");
  ph.className = "log-placeholder"; ph.id = "logPlaceholder";
  ph.textContent = "Log cleared — new activity will appear here.";
  body.appendChild(ph);
  api.ui_event("log_cleared");
}

// Full-window failure surface for "the UI cannot work at all" states (bridge
// never arrived, initial state failed). Plain DOM, no dependencies.
function showFatal(title, detail) {
  let el = $("fatalBanner");
  if (!el) {
    el = document.createElement("div");
    el.id = "fatalBanner";
    el.className = "fatal-banner";
    document.body.appendChild(el);
  }
  el.textContent = "";
  const h = document.createElement("div");
  h.className = "fatal-title";
  h.appendChild(icon("i-warn"));
  h.appendChild(Object.assign(document.createElement("span"), { textContent: title }));
  const d = document.createElement("div");
  d.className = "fatal-detail mono";
  d.textContent = detail;
  el.append(h, d);
}

function hideFatal() {
  $("fatalBanner")?.remove();
}

// --------------------------------------------------------------- modals ----
// One overlay; builders return Promises. Esc = dismiss (null / false).
let modalResolve = null;

function closeModal(value) {
  $("modalOverlay").classList.add("hidden");
  $("modalOverlay").textContent = "";
  const r = modalResolve; modalResolve = null;
  if (r) r(value);
}

function openModal(node) {
  // A new modal (e.g. an error pushed by the engine) may replace one that is
  // still open — resolve the old promise as "dismissed" so whatever awaits it
  // doesn't hang forever.
  if (modalResolve) {
    const prev = modalResolve;
    modalResolve = null;
    prev(null);
  }
  const ov = $("modalOverlay");
  ov.textContent = "";
  ov.appendChild(node);
  ov.classList.remove("hidden");
  return new Promise((resolve) => { modalResolve = resolve; });
}

function buildModal({ title, iconName, headClass, wide }) {
  const m = document.createElement("div");
  m.className = "modal" + (wide ? " modal-wide" : "");
  const head = document.createElement("div");
  head.className = "modal-head" + (headClass ? " " + headClass : "");
  if (iconName) head.appendChild(icon(iconName));
  head.appendChild(Object.assign(document.createElement("span"), { textContent: title }));
  m.appendChild(head);
  return m;
}

function showMessage(kind, title, message) {
  // kind: "info" | "warning" | "error"
  const m = buildModal({
    title,
    iconName: kind === "info" ? "i-shield" : "i-warn",
    headClass: kind,
  });
  const body = document.createElement("div");
  body.className = "modal-body";
  body.textContent = message;
  m.appendChild(body);
  const actions = document.createElement("div");
  actions.className = "modal-actions";
  const ok = document.createElement("button");
  ok.className = "btn btn-accent"; ok.textContent = "OK";
  ok.onclick = () => closeModal(true);
  actions.appendChild(ok);
  m.appendChild(actions);
  const p = openModal(m);
  ok.focus();
  return p;
}

function showConfirm({ title, message, confirmLabel, cancelLabel, danger }) {
  const m = buildModal({ title, iconName: "i-warn", headClass: danger ? "error" : "warning" });
  const body = document.createElement("div");
  body.className = "modal-body";
  // Render \n\n as paragraphs, lone mono lines (paths) stay readable.
  message.split("\n\n").forEach((part) => {
    const p = document.createElement("p");
    p.style.margin = "6px 0";
    if (/^[A-Za-z]:\\|^\\\\/.test(part.trim())) p.className = "mono";
    p.textContent = part;
    body.appendChild(p);
  });
  m.appendChild(body);
  const actions = document.createElement("div");
  actions.className = "modal-actions";
  const cancel = document.createElement("button");
  cancel.className = "btn btn-subtle"; cancel.textContent = cancelLabel || "Cancel";
  cancel.onclick = () => closeModal(false);
  const ok = document.createElement("button");
  ok.className = "btn btn-accent"; ok.textContent = confirmLabel || "Continue";
  ok.onclick = () => closeModal(true);
  actions.append(cancel, ok);
  m.appendChild(actions);
  const p = openModal(m);
  ok.focus();
  return p;
}

function showRoutePicker(current) {
  const routes = S.init.routes;
  const chosen = new Set(current);
  const m = buildModal({ title: "Choose routes", iconName: "i-folder-open", wide: true });

  const search = document.createElement("div");
  search.className = "picker-search";
  search.appendChild(icon("i-search"));
  const sin = document.createElement("input");
  sin.className = "input"; sin.placeholder = "Filter routes…"; sin.spellcheck = false;
  search.appendChild(sin);
  m.appendChild(search);

  const grid = document.createElement("div");
  grid.className = "picker-grid";
  const cells = new Map();
  routes.forEach((r) => {
    const c = document.createElement("div");
    c.className = "route-cell" + (chosen.has(r) ? " on" : "");
    c.textContent = r;
    c.onclick = () => {
      if (chosen.has(r)) { chosen.delete(r); c.classList.remove("on"); }
      else { chosen.add(r); c.classList.add("on"); }
      meta.textContent = metaText();
    };
    cells.set(r, c);
    grid.appendChild(c);
  });
  m.appendChild(grid);

  const meta = document.createElement("div");
  meta.className = "picker-meta";
  const metaText = () => chosen.size
    ? `${chosen.size} of ${routes.length} routes selected.`
    : `No routes selected — that means ALL ${routes.length} routes.`;
  meta.textContent = metaText();
  m.appendChild(meta);

  sin.oninput = () => {
    const q = sin.value.trim().toLowerCase();
    cells.forEach((c, r) => { c.style.display = r.toLowerCase().includes(q) ? "" : "none"; });
  };

  const actions = document.createElement("div");
  actions.className = "modal-actions";
  const selAll = document.createElement("button");
  selAll.className = "btn btn-subtle"; selAll.textContent = "Select all";
  selAll.onclick = () => { routes.forEach((r) => chosen.add(r)); cells.forEach((c) => c.classList.add("on")); meta.textContent = metaText(); };
  const clear = document.createElement("button");
  clear.className = "btn btn-subtle"; clear.textContent = "Clear";
  clear.onclick = () => { chosen.clear(); cells.forEach((c) => c.classList.remove("on")); meta.textContent = metaText(); };
  const cancel = document.createElement("button");
  cancel.className = "btn btn-subtle"; cancel.textContent = "Cancel";
  cancel.onclick = () => closeModal(null);
  const ok = document.createElement("button");
  ok.className = "btn btn-accent"; ok.textContent = "OK";
  ok.onclick = () => closeModal(routes.filter((r) => chosen.has(r)));
  actions.append(selAll, clear, Object.assign(document.createElement("span"), { className: "spacer" }), cancel, ok);
  m.appendChild(actions);

  const p = openModal(m);
  sin.focus();
  return p;   // resolves: array of routes, or null (cancelled)
}

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

// ------------------------------------------------------ one-time build -----
function buildStatic() {
  const init = S.init;
  $("appName").textContent = init.app_name;
  $("appVersion").textContent = "v" + init.version;
  $("outputRoot").textContent = init.output_root;
  document.title = init.app_name;

  // report checkboxes (first ticked by default, same as the old GUI)
  const list = $("reportList");
  init.reports.forEach((rep, i) => {
    const row = document.createElement("label");
    row.className = "option-row" + (i === 0 ? " checked" : "");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = i === 0; cb.dataset.idx = i;
    const box = document.createElement("span");
    box.className = "checkbox"; box.appendChild(icon("i-check"));
    const name = document.createElement("span");
    name.className = "option-name"; name.textContent = rep.label;
    const chip = document.createElement("span");
    chip.className = "chip " + (rep.fmt === "PDF" ? "chip-pdf" : "chip-excel");
    chip.textContent = rep.fmt;
    row.append(cb, box, name, chip);
    cb.addEventListener("change", () => {
      row.classList.toggle("checked", cb.checked);
      updateReportCount();
    });
    list.appendChild(row);
  });
  updateReportCount();

  // consolidate radios
  const cl = $("consList");
  init.cons_reports.forEach((label, i) => {
    const row = document.createElement("label");
    row.className = "option-row" + (i === 0 ? " checked" : "");
    const rb = document.createElement("input");
    rb.type = "radio"; rb.name = "consReport"; rb.checked = i === 0; rb.dataset.idx = i;
    const dot = document.createElement("span"); dot.className = "radio";
    const name = document.createElement("span");
    name.className = "option-name"; name.textContent = label;
    const rep = init.reports.find((r) => r.label === label);
    row.append(rb, dot, name);
    if (rep) {
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

  // comparison-type radios (one entry today; the registry grows)
  const cl2 = $("compareList");
  (init.compare_reports || []).forEach((label, i) => {
    const row = document.createElement("label");
    row.className = "option-row" + (i === 0 ? " checked" : "");
    const rb = document.createElement("input");
    rb.type = "radio"; rb.name = "compareReport"; rb.checked = i === 0; rb.dataset.idx = i;
    const dot = document.createElement("span"); dot.className = "radio";
    const name = document.createElement("span");
    name.className = "option-name"; name.textContent = "TSMIS vs TSN — " + label;
    row.append(rb, dot, name);
    rb.addEventListener("change", () => {
      cl2.querySelectorAll(".option-row").forEach((r) => r.classList.remove("checked"));
      row.classList.add("checked");
    });
    cl2.appendChild(row);
  });

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
  fill($("selBrowser"), init.channels, init.channel);

  // readiness dots: one per browser channel + output + tools
  const strip = $("checkStrip");
  const items = init.channels.map((c) => ({ key: "browser_" + c.id, label: c.short }))
    .concat([{ key: "output", label: "Output" }, { key: "tools", label: "Tools" }]);
  items.forEach(({ key, label }) => {
    const it = document.createElement("span");
    it.className = "check-item"; it.id = "check_" + key;
    const dot = document.createElement("span"); dot.className = "dot dot-unknown";
    it.append(dot, Object.assign(document.createElement("span"), { textContent: label }));
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
function selectedReportIdxs() {
  return [...$("reportList").querySelectorAll("input")].filter((c) => c.checked).map((c) => +c.dataset.idx);
}
function consChoice() {
  const r = $("consList").querySelector("input:checked");
  return r ? +r.dataset.idx : 0;
}
function compareChoice() {
  const r = $("compareList").querySelector("input:checked");
  return r ? +r.dataset.idx : 0;
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
    setDot(it.querySelector(".dot"), c.status);
    it.title = c.text;
  });
  $("btnRecheck").disabled = st.checks_running || st.task != null;

  // config inputs lock while any task runs
  const locked = st.task != null;
  ["selSource", "selEnv", "selBrowser", "routesInput", "btnChooseRoutes", "selDay"]
    .forEach((id) => { $(id).disabled = locked; });
  $("reportList").querySelectorAll("input").forEach((c) => { c.disabled = locked; });
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
    ? "Faster, but heavier on your PC; 3–4 recommended. Per-route Skip is off in fast mode."
    : "Fast mode needs a saved login — automatic sign-in runs one browser at a time. Log in first to enable it.";

  // action buttons
  $("btnStartExport").disabled = locked;
  $("btnStartCons").disabled = locked;
  $("btnSkip").disabled = !(st.task === "export" && !st.fast_run);
  $("btnCancelExport").disabled = st.task !== "export";
  $("btnCancelCons").disabled = st.task !== "consolidate";
  $("btnSaveReport").disabled = locked || !st.can_save_report;
  ["btnPickTsmis", "btnPickTsn", "btnOpenConsInput"].forEach((id) => { $(id).disabled = locked; });
  $("compareList").querySelectorAll("input").forEach((c) => { c.disabled = locked; });
  $("compareList").querySelectorAll(".option-row").forEach((r) => r.classList.toggle("disabled", locked));
  $("btnCancelCompare").disabled = st.task !== "compare";
  syncCompareButton();

  renderDays(st.days || []);
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
}

let consDestSeq = 0;
async function refreshConsDest() {
  const seq = ++consDestSeq;
  const info = await api.consolidate_info(consChoice(), selectedDay());
  if (seq !== consDestSeq) return;          // a newer request superseded this one
  $("consDest").textContent = info.dest_dir;
  $("consDest").title = info.dest_dir;
  // Reports with user-supplied inputs (TSN PDFs) say where the files go.
  const row = $("consInputRow");
  if (info.input_note) {
    $("consInputNote").textContent = info.input_note;
    $("consInputDir").textContent = info.input_dir;
    $("consInputDir").title = info.input_dir;
    row.classList.remove("hidden");
  } else {
    row.classList.add("hidden");
  }
}

// progress -------------------------------------------------------------
function renderProgress(p) {
  S.progress = p;
  const pct = p.total ? Math.round((p.done / p.total) * 100) : 0;
  $("progressPct").textContent = pct + "%";
  $("progressFill").style.width = pct + "%";
  let head = "";
  if (p.report_n > 1) head = `[${p.report_i}/${p.report_n}] ${p.report}  ·  `;
  else if (p.report) head = `${p.report}  ·  `;
  $("progressText").textContent = `${head}Route ${p.route}   ·   ${p.done}/${p.total}`;
  const counts = { cSaved: p.saved, cExists: p.exists, cEmpty: p.empty, cSkipped: p.skipped, cFailed: p.failed };
  Object.entries(counts).forEach(([id, v]) => {
    $(id).textContent = v;
    $(id).closest(".count-chip").classList.toggle("lit", v > 0);
  });
}

function startRunUi(mode, label) {
  S.runMode = mode;
  S.elapsedStart = Date.now();
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
  document.querySelector(".progress-card").classList.remove("running");
  $("progressIcon").querySelector("use").setAttribute("href", "#i-shield");
  $("progressIcon").classList.remove("spin");
  $("progressBar").classList.remove("indeterminate");
  $("progressPct").classList.remove("hidden");
  $("progressPct").textContent = "0%";
  $("progressFill").style.width = "0%";
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
        case "state": S.st = ev.s; renderState(); break;
        case "log": appendLog(ev.text); sawLog = true; break;
        case "progress": if (S.runMode === "export") renderProgress(ev.p); break;
        case "run_started": startRunUi(ev.mode, ev.label); break;
        case "run_ended": endRunUi(); break;
        case "modal": showMessage(ev.kind, ev.title, ev.message); break;
        default: break;
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
  $("routesInput").value = picked.join(", ");
  onRoutesInput();
}

async function startExport() {
  const reports = selectedReportIdxs();
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
  const res = await api.start_export(reports, raw, fast, workers);
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

async function startConsolidate() {
  const idx = consChoice();
  const day = selectedDay();
  const info = await api.consolidate_info(idx, day);
  if (info.exists) {
    const ok = await showConfirm({
      title: "Overwrite?",
      message: `A consolidated workbook already exists:\n\n${info.out_path}\n\nOverwrite it?`,
      confirmLabel: "Overwrite",
      danger: true,
    });
    if (!ok) { api.decline_overwrite(); return; }
  }
  const res = await api.start_consolidate(idx, day);
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

async function saveRunReport() {
  const res = await api.save_run_report();
  if (res && res.error) showMessage("error", "Could not save report", res.error);
}

// ---- TSMIS vs TSN comparison ----
const CMP = { tsmis: null, tsn: null };

function renderCompareFiles() {
  for (const [side, id] of [["tsmis", "cmpTsmisPath"], ["tsn", "cmpTsnPath"]]) {
    const el = $(id);
    el.textContent = CMP[side] || "— not selected —";
    el.title = CMP[side] || "";
    el.classList.toggle("unset", !CMP[side]);
  }
  syncCompareButton();
}

function syncCompareButton() {
  const locked = S.st && S.st.task != null;
  $("btnStartCompare").disabled = locked || !(CMP.tsmis && CMP.tsn);
}

async function pickCompareFile(side) {
  const res = await api.pick_compare_file(side.toUpperCase());
  if (res && res.path) {
    CMP[side] = res.path;
    renderCompareFiles();
  }
}

async function startCompare() {
  const res = await api.start_compare(compareChoice(), CMP.tsmis, CMP.tsn);
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

function bindEvents() {
  // tabs
  const TABS = {
    export: { btn: "tabExport", pane: "paneExport", title: "Export reports",
              sub: "Select reports and routes, then run the batch export." },
    consolidate: { btn: "tabConsolidate", pane: "paneConsolidate", title: "Consolidate output",
                   sub: "Merge per-route files into a single workbook." },
    compare: { btn: "tabCompare", pane: "paneCompare", title: "Compare TSMIS vs TSN",
               sub: "Pick a TSMIS and a TSN highway log, then build a discrepancy workbook." },
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
  };
  Object.entries(TABS).forEach(([key, t]) => { $(t.btn).onclick = () => setTab(key); });

  $("selTheme").value = themePref();
  $("selTheme").onchange = () => {
    try { localStorage.setItem(THEME_KEY, $("selTheme").value); } catch (_) { /* keep for session */ }
    applyTheme();
    api.ui_event("theme:" + $("selTheme").value);
  };

  $("selBrowser").onchange = () => api.set_browser($("selBrowser").value);
  $("selSource").onchange = () => api.set_site($("selSource").value, $("selEnv").value);
  $("selEnv").onchange = () => api.set_site($("selSource").value, $("selEnv").value);
  $("btnRecheck").onclick = () => api.start_checks();

  $("btnLogin").onclick = () => {
    if (S.st && S.st.login_phase === "open") api.finish_login();
    else api.start_login();
  };
  $("btnLoginCancel").onclick = () => api.cancel_login();

  $("routesInput").addEventListener("input", onRoutesInput);
  $("btnChooseRoutes").onclick = chooseRoutes;
  $("fastMode").addEventListener("change", syncFastVisual);

  $("btnStartExport").onclick = startExport;
  $("btnSkip").onclick = () => api.skip_route();
  $("btnCancelExport").onclick = () => api.cancel_run();
  $("btnSaveReport").onclick = saveRunReport;

  $("selDay").onchange = refreshConsDest;
  $("btnStartCons").onclick = startConsolidate;
  $("btnCancelCons").onclick = () => api.cancel_run();
  $("btnOpenConsFolder").onclick = () => api.open_consolidated_folder(consChoice(), selectedDay());
  $("btnOpenConsInput").onclick = () => api.open_consolidate_input(consChoice());

  $("btnPickTsmis").onclick = () => pickCompareFile("tsmis");
  $("btnPickTsn").onclick = () => pickCompareFile("tsn");
  $("btnStartCompare").onclick = startCompare;
  $("btnCancelCompare").onclick = () => api.cancel_run();
  renderCompareFiles();

  $("btnOpenOutput").onclick = () => api.open_output_folder();
  $("btnOpenLogs").onclick = () => api.open_logs_folder();
  $("btnClearLog").onclick = clearLog;

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
  let init = null;
  try {
    init = await api.get_initial_state();
  } catch (e) {
    init = { error: String(e) };
  }
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

window.addEventListener("pywebviewready", () => boot(window.pywebview.api));
if (WANT_MOCK) {
  boot(makeMockApi());
} else {
  // The ready event may have fired before this script attached its listener;
  // re-check periodically instead of guessing one magic delay.
  const poll = setInterval(() => {
    if (booted) { clearInterval(poll); return; }
    if (window.pywebview && window.pywebview.api) { clearInterval(poll); boot(window.pywebview.api); }
  }, 150);
  setTimeout(() => {
    if (!booted) {
      showFatal("The app's interface couldn't connect to its engine",
                "The page loaded but the pywebview bridge never arrived. Close the app and try again; "
                + "details are in the log file. (For a browser-only design preview, open index.html#mock.)");
    }
  }, 8000);
}

// ============================ mock API (browser preview) ====================
// Lets the UI run in a plain browser: simulated checks, login, exports and
// consolidation. Never loaded by the real app (pywebview wins the race above).
function makeMockApi() {
  const ROUTES = [];
  for (let i = 1; i <= 280; i++) {
    ROUTES.push(String(i).padStart(3, "0"));
    if (i === 5) ROUTES.push("005S");
    if (i === 14) ROUTES.push("014U");
    if (i === 101) ROUTES.push("101U");
  }
  const REPORTS = [
    { label: "TSAR: Ramp Summary", fmt: "PDF" },
    { label: "TSAR: Ramp Detail", fmt: "Excel" },
    { label: "Highway Sequence Listing", fmt: "Excel" },
    { label: "Highway Log", fmt: "Excel" },
  ];
  const st = {
    task: null, fast_run: false,
    authed: false, device_ok: false,
    auth_dot: "bad", auth_text: "No saved login — click Log in",
    login_phase: null, login_label: "Log in",
    checks: {
      browser_msedge: { status: "busy", text: "Microsoft Edge: checking…" },
      browser_chrome: { status: "busy", text: "Google Chrome: checking…" },
      output: { status: "busy", text: "Output folder: checking…" },
      tools: { status: "busy", text: "Report tools: checking…" },
    },
    checks_running: true,
    days: ["2026-06-10", "2026-06-08", "2026-06-02"],
    can_save_report: false,
  };
  let timer = null;
  const push = (...evs) => dispatch(evs);
  const pushState = () => push({ t: "state", s: JSON.parse(JSON.stringify(st)) });

  function finishChecks() {
    st.checks.output = { status: "ok", text: "Output folder: writable" };
    st.checks.tools = { status: "ok", text: "Report tools (PDF/Excel): ready" };
    st.checks.browser_msedge = { status: "ok", text: "Microsoft Edge: ready" };
    st.checks.browser_chrome = { status: "bad", text: "Google Chrome: not installed" };
    st.checks_running = false;
    pushState();
  }

  function runMockExport(reports, routes, fast, workers) {
    st.task = "export"; st.fast_run = fast;
    st.auth_dot = "busy";
    st.auth_text = reports.length > 1 ? `Exporting ${reports.length} report(s)…`
                                      : `Exporting ${REPORTS[reports[0]].label}…`;
    pushState();
    const names = reports.map((i) => REPORTS[i].label).join(", ");
    let msg = `Starting export: ${names}`;
    if (routes.length !== ROUTES.length) msg += `   ·   ${routes.length} routes`;
    if (fast) msg += `   ·   FAST MODE (${workers} browsers)`;
    push({ t: "log", text: msg }, { t: "run_started", mode: "export", label: "Working…" });

    const total = routes.length;
    let done = 0;
    const counts = { saved: 0, empty: 0, skipped: 0, failed: 0, exists: 0 };
    timer = setInterval(() => {
      if (done >= total) {
        clearInterval(timer); timer = null;
        push({ t: "log", text: "" },
             { t: "log", text: `Done. ${total} routes handled — saved ${counts.saved}, already had ${counts.exists}, empty ${counts.empty}, skipped ${counts.skipped}, failed ${counts.failed}.` },
             { t: "run_ended" });
        st.task = null; st.fast_run = false; st.can_save_report = true;
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
      if (status === "saved") push({ t: "log", text: `Route ${route}: saved (${(Math.random() * 3 + 0.4).toFixed(1)} MB, ${(Math.random() * 40 + 8).toFixed(0)}s)` });
      if (status === "failed") push({ t: "log", text: `Route ${route}: FAILED — TSMIS site error (see failures folder)` });
      push({ t: "progress", p: { done, total, route, report: REPORTS[reports[0]].label, report_i: 1, report_n: reports.length, ...counts } });
    }, fast ? 120 : 350);
  }

  return {
    get_initial_state: async () => ({
      app_name: "TSMIS Exporter", version: "0.8.0 (preview)",
      output_root: "C:\\Tools\\TSMIS Exporter\\output",
      log_dir: "C:\\Tools\\TSMIS Exporter\\data\\logs",
      reports: REPORTS,
      cons_reports: REPORTS.map((r) => r.label).concat(["TSN Highway Log"]),
      compare_reports: ["Highway Log"],
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
      state: JSON.parse(JSON.stringify(st)),
    }),
    ui_ready: async () => { setTimeout(finishChecks, 900); },
    ui_event: async () => {},
    log_js_error: async (m) => console.error("js error:", m),
    set_browser: async (ch) => push({ t: "log", text: `Browser set to ${ch} (the other is still used as a fallback if needed).` }),
    set_site: async (src, env) => push({ t: "log", text: `Site set to ${src.toUpperCase()} / ${env} (used by the next sign-in or export).` }),
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
    start_export: async (reports, routesText, fast, workers) => {
      // Mock keeps runs short: a typed subset caps at 24 routes, "all" at 32.
      const routes = routesText ? ROUTES.slice(0, 24) : ROUTES.slice(0, 32);
      runMockExport(reports, routes, fast, workers);
      return { ok: true };
    },
    skip_route: async () => push({ t: "log", text: "Skip requested — will move on once the current wait ends." }),
    cancel_run: async () => {
      push({ t: "log", text: "Cancel requested…" });
      setTimeout(() => {
        if (timer) { clearInterval(timer); timer = null; }
        push({ t: "log", text: "Cancelled." }, { t: "run_ended" });
        st.task = null; st.fast_run = false;
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
    consolidate_info: async (idx, day) => (idx === 4 ? {
      dest_dir: "C:\\Tools\\TSMIS Exporter\\output",
      out_path: "C:\\Tools\\TSMIS Exporter\\output\\tsn_highway_log_consolidated.xlsx",
      exists: false,
      input_note: "Drop the TSN district Highway Log PDFs into the input folder first.",
      input_dir: "C:\\Tools\\TSMIS Exporter\\input\\tsn_highway_log",
    } : {
      dest_dir: `C:\\Tools\\TSMIS Exporter\\output\\${day || "(legacy)"}\\consolidated`,
      out_path: `C:\\Tools\\TSMIS Exporter\\output\\${day || "(legacy)"}\\consolidated\\${REPORTS[idx].label.replace(/[:\s]+/g, "_")}.xlsx`,
      exists: idx === 0 && day === "2026-06-10",
    }),
    open_consolidate_input: async () => push({ t: "log", text: "(mock) would open the TSN input folder" }),
    pick_compare_file: async (side) => ({
      path: side === "TSMIS"
        ? "C:\\Users\\you\\Downloads\\tsmis_highway_log_route 1.xlsx"
        : "C:\\Users\\you\\Downloads\\tsn_highway_log_route 1.xlsx",
    }),
    start_compare: async (_idx) => {
      st.task = "compare";
      st.auth_dot = "busy"; st.auth_text = "Comparing Highway Logs…";
      pushState();
      push({ t: "log", text: "Starting comparison: TSMIS vs TSN Highway Log" },
           { t: "run_started", mode: "consolidate", label: "Comparing Highway Logs…" });
      setTimeout(() => {
        push({ t: "log", text: "TSMIS rows: 317   TSN rows: 368   union: 386 locations" },
             { t: "log", text: "Matched rows with differences: 221 (971 differing cells); 78 fully identical" },
             { t: "log", text: "Routes only in TSMIS (missing from TSN) (2): 254, 259" },
             { t: "log", text: "Output: TSMIS_vs_TSN_Route1_Comparison.xlsx" },
             { t: "run_ended" });
        st.task = null;
        st.auth_dot = st.authed ? "ok" : "bad"; st.auth_text = "Done";
        pushState();
      }, 2400);
      return { ok: true };
    },
    decline_overwrite: async () => push({ t: "log", text: "Consolidation cancelled (kept existing file)." }),
    start_consolidate: async (idx, day) => {
      st.task = "consolidate";
      st.auth_dot = "busy"; st.auth_text = `Consolidating ${REPORTS[idx].label}…`;
      pushState();
      push({ t: "log", text: `Starting consolidation: ${REPORTS[idx].label}` + (day ? `   ·   ${day}` : "") },
           { t: "run_started", mode: "consolidate", label: `Consolidating ${REPORTS[idx].label}…` });
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
  };
}
