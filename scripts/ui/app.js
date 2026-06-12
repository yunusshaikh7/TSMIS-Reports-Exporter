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
  workers: 0,          // browser-status rows currently shown (export runs)
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
  // Comparison verdict lines lead with ✓/✗ and win outright.
  const scrubbed = text.replace(/\bfailed:?\s+0\b/gi, "");
  const upper = scrubbed.toUpperCase();
  if (text.startsWith("✓")) line.classList.add("ok");
  else if (text.startsWith("✗")) line.classList.add("err");
  else if (upper.includes("FAIL") || upper.includes("ERROR")) line.classList.add("err");
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
  $("appVersion").title = "Check for updates";
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

  // comparison-type radios ({label, kind} rows; kind decides files vs folders)
  const cl2 = $("compareList");
  (init.compare_reports || []).forEach((rep, i) => {
    const row = document.createElement("label");
    row.className = "option-row" + (i === 0 ? " checked" : "");
    const rb = document.createElement("input");
    rb.type = "radio"; rb.name = "compareReport"; rb.checked = i === 0; rb.dataset.idx = i;
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
  ["selSource", "selEnv", "selBrowser", "routesInput", "btnChooseRoutes", "selDay",
   "btnVerifyEnv", "btnDeleteReports", "btnClearLogin", "btnSupportBundle",
   "btnCheckEnvs"]
    .forEach((id) => { $(id).disabled = locked; });
  Object.keys(SETTING_INPUTS).forEach((id) => { $(id).disabled = locked; });
  ["setDebugLog", "setDevtools"].forEach((id) => {
    $(id).disabled = locked;
    $(id).closest(".option-row").classList.toggle("disabled", locked);
  });
  $("setSiteUrls").querySelectorAll("input").forEach((i) => { i.disabled = locked; });
  $("btnChromiumDownload").disabled = locked;
  $("btnChromiumDelete").disabled = locked;
  $("btnChromiumCancel").classList.toggle("hidden", st.task !== "chromium");
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
}

// ----------------------------------- environment access (scan results) -----
// Python owns the verdicts (state.env_access, keyed "src-env", from the
// Settings "Check all environments" scan); this renders them twice: a status
// chip on each Settings address row, and the title-bar aggregate.
const ENV_ACCESS_BADGE = {
  ok:          { dot: "ok",   text: "OK" },
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
    const onlyLimited = entries.every((e) => e.status === "ok" || e.status === "reports_off");
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
      label = `Downloading… ${up.progress || 0}%`;
      disabled = true;
      break;
    case "staged":
      label = "Restart to update";
      disabled = locked;
      title = locked ? "Finish or cancel the running task first"
                     : `Install v${up.version} — the app closes and reopens by itself`;
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
      title: "Restart and update?",
      message: `The app will close, install v${up.version} (takes a few seconds), and reopen by itself.\n\nYour reports, login and settings stay where they are.`,
      confirmLabel: "Restart now",
    });
    if (!ok) return;
    const res = await api.update_apply();
    if (res && res.error) showMessage("error", "Could not update", res.error);
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

function startRunUi(mode, label, workers) {
  S.runMode = mode;
  buildWorkerStrip(mode === "export" ? (workers || 1) : 0);
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
  buildWorkerStrip(0);
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
        case "settings":
          S.init.settings = ev.s;
          fillSettings();
          break;
        case "log": appendLog(ev.text); sawLog = true; break;
        case "progress": if (S.runMode === "export") renderProgress(ev.p); break;
        case "wstatus": updateWorkerStatus(ev.w, ev.text); break;
        case "preview": showPreviewEvent(ev); break;
        case "run_started": startRunUi(ev.mode, ev.label, ev.workers); break;
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

// ---- comparisons (files kind = TSMIS vs TSN; folders kind = env vs env) ----
const CMP = { tsmis: null, tsn: null };

function compareKind() {
  const rep = (S.init.compare_reports || [])[compareChoice()];
  return (rep && rep.kind) || "files";
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

function fillCompareDirSelect(sel, custom, preferred) {
  const days = (S.st && S.st.days) || [];
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
  if (custom) sel.value = custom;
  else if (prev && options.includes(prev)) sel.value = prev;
  else if (preferred) sel.value = preferred;
}

function renderCompareDirs() {
  const days = (S.st && S.st.days) || [];
  // sensible defaults: baseline = newest ssor-prod run, other side = the
  // newest folder that differs from the baseline
  const baseline = days.find((d) => /ssor-prod$/.test(d)) || days[0] || "";
  fillCompareDirSelect($("cmpDirA"), CMP_DIRS.a, baseline);
  const other = days.find((d) => d !== $("cmpDirA").value) || days[0] || "";
  fillCompareDirSelect($("cmpDirB"), CMP_DIRS.b, other);
  syncCompareButton();
}

function renderCompareKind() {
  const folders = compareKind() === "folders";
  $("cmpFilesSection").classList.toggle("hidden", folders);
  $("cmpFoldersSection").classList.toggle("hidden", !folders);
  if (folders) renderCompareDirs();
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
    renderCompareDirs();
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

function fillSettings() {
  const s = S.init.settings || {};
  const v = s.values || {};
  Object.entries(SETTING_INPUTS).forEach(([id, key]) => {
    if (v[key] != null) $(id).value = v[key];
  });
  const setToggle = (id, on) => {
    $(id).checked = !!on;
    $(id).closest(".option-row").classList.toggle("checked", !!on);
  };
  setToggle("setDebugLog", v.debug_logging);
  setToggle("setDevtools", v.ui_devtools);

  const meta = s.meta || {};
  const paths = $("setPaths");
  paths.textContent = "";
  [["Data folder", meta.data_root], ["Output folder", meta.output_root],
   ["Log file", meta.log_file], ["Failure shots", meta.failures_dir]]
    .forEach(([label, value]) => {
      const line = document.createElement("div");
      line.className = "path-line";
      const l = document.createElement("span");
      l.className = "path-label"; l.textContent = label;
      const p = document.createElement("span");
      p.className = "path"; p.textContent = value || "—"; p.title = value || "";
      line.append(l, p);
      paths.appendChild(line);
    });

  renderSiteUrls(s.site_urls || []);
  renderChromium(s.chromium || {});

  const about = $("setAbout");
  about.textContent = "";
  [["Version", `v${meta.version || S.init.version}`],
   ["Build", `${meta.build || "?"} · ${meta.variant || "?"}`],
   ["Sign-in", meta.auth_state || "?"],
   ["Settings file", "config.json in the data folder (safe to delete — defaults return)"]]
    .forEach(([label, value]) => {
      const line = document.createElement("div");
      const l = document.createElement("span");
      l.className = "muted"; l.textContent = label + ":";
      line.append(l, Object.assign(document.createElement("span"), { textContent: value }));
      about.appendChild(line);
    });
}

// ---- Settings: per-environment site addresses ----
function renderSiteUrls(rows) {
  const box = $("setSiteUrls");
  box.textContent = "";
  rows.forEach((row) => {
    const line = document.createElement("div");
    line.className = "url-row";
    const label = document.createElement("span");
    label.className = "url-label"; label.textContent = row.label;
    const input = document.createElement("input");
    input.className = "input" + (row.custom ? " custom" : "");
    input.value = row.url;
    input.placeholder = row.default;
    input.title = "Default: " + row.default;
    input.spellcheck = false;
    const chip = document.createElement("span");
    chip.className = "url-custom-chip" + (row.custom ? " on" : "");
    chip.textContent = "custom";
    input.addEventListener("change", async () => {
      const res = await api.set_site_url(row.source, row.environment, input.value.trim());
      if (res && res.error) showMessage("error", "Address not saved", res.error);
      if (res && res.site_urls) {
        S.init.settings.site_urls = res.site_urls;
        renderSiteUrls(res.site_urls);
      }
    });
    // Access-scan verdict slot; renderEnvAccess() fills it from state.
    const stat = document.createElement("span");
    stat.className = "url-status";
    stat.dataset.envstat = row.key;
    const statDot = document.createElement("span");
    statDot.className = "dot dot-unknown";
    const statText = document.createElement("span");
    statText.textContent = "Not checked";
    stat.append(statDot, statText);
    line.append(label, input, chip, stat);
    box.appendChild(line);
  });
  renderEnvAccess();
}

// ---- Settings: Built-in Chromium ----
function renderChromium(c) {
  const state = $("chromiumState");
  let text;
  if (c.bundled) {
    text = "Ships with this app (the “with-browser” download) — nothing to manage.";
  } else if (c.downloaded) {
    text = `Downloaded (${c.downloaded_mb} MB)` + (c.active
      ? " and available in the Browser dropdown."
      : " — restart the app to use it.");
  } else {
    text = "Not installed — exports use the PC's Microsoft Edge / Google Chrome.";
  }
  state.textContent = text;
  state.title = c.dir || "";
  $("btnChromiumDownload").classList.toggle("hidden", !!(c.bundled || c.downloaded));
  $("btnChromiumDelete").classList.toggle("hidden", !c.downloaded);
  const downloading = S.st && S.st.task === "chromium";
  $("btnChromiumCancel").classList.toggle("hidden", !downloading);
}

async function downloadChromium() {
  const ok = await showConfirm({
    title: "Download the Built-in Chromium?",
    message: "About 170 MB will be downloaded into the app's data folder "
      + "(data\\ms-playwright).\n\nAfter it finishes, restart the app and "
      + "“Built-in Chromium” appears in the Browser dropdown.",
    confirmLabel: "Download",
  });
  if (!ok) return;
  const res = await api.download_chromium();
  if (res && res.error) showMessage("error", "Could not start", res.error);
  else renderChromium((S.init.settings || {}).chromium || {});
}

async function deleteChromium() {
  const ok = await showConfirm({
    title: "Remove the downloaded browser?",
    message: "The downloaded Built-in Chromium will be deleted from the app's "
      + "data folder. Exports go back to the PC's Edge / Chrome (restart to "
      + "finish the switch if it's currently selected).",
    confirmLabel: "Remove",
    danger: true,
  });
  if (!ok) return;
  const res = await api.delete_chromium();
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

async function onSettingInput(id) {
  const key = SETTING_INPUTS[id];
  const res = await api.set_setting(key, $(id).value);
  if (res && res.error) { showMessage("error", "Could not save the setting", res.error); return; }
  if (res && res.values) {
    S.init.settings.values = res.values;
    $(id).value = res.values[key];          // reflect clamping
    if (key === "fast_workers" && !(S.st && S.st.task)) {
      $("fastWorkers").value = res.values[key];   // reseed the Export pane default
    }
  }
}

async function onSettingToggle(id, key) {
  const cb = $(id);
  cb.closest(".option-row").classList.toggle("checked", cb.checked);
  const res = await api.set_setting(key, cb.checked);
  if (res && res.values) S.init.settings.values = res.values;
}

async function deleteAllReports() {
  let includeInput = false;
  let prev = await api.reset_preview(false);
  if (prev.error) { showMessage("error", "Could not check the output folder", prev.error); return; }

  const m = buildModal({ title: "Delete all reports?", iconName: "i-warn", headClass: "error", wide: true });
  const body = document.createElement("div");
  body.className = "modal-body";
  const summary = document.createElement("p");
  const list = document.createElement("div");
  list.className = "mono";
  list.style.cssText = "max-height:180px; overflow-y:auto; margin:8px 0; padding:8px 10px;"
    + "border:1px solid var(--border); border-radius:6px; font-size:12px; line-height:1.6;"
    + "white-space:pre-wrap;";
  const render = () => {
    summary.textContent = prev.targets.length
      ? `This permanently deletes ${prev.files.toLocaleString()} file(s) (${prev.mb} MB):`
      : "Nothing to delete — no generated reports were found.";
    list.textContent = prev.targets.length ? prev.targets.join("\n") : "";
    list.style.display = prev.targets.length ? "" : "none";
  };
  render();
  const keep = document.createElement("p");
  keep.textContent = "Logs, your saved login and these settings are always kept.";
  const inputRow = document.createElement("label");
  inputRow.style.cssText = "display:flex; align-items:center; gap:8px; margin-top:8px; cursor:pointer;";
  const inputCb = document.createElement("input");
  inputCb.type = "checkbox";
  inputRow.appendChild(inputCb);
  inputRow.appendChild(Object.assign(document.createElement("span"),
    { textContent: "Also delete the TSN input PDFs (input\\tsn_highway_log)" }));
  inputCb.onchange = async () => {
    includeInput = inputCb.checked;
    prev = await api.reset_preview(includeInput);
    render();
  };
  body.append(summary, list, keep, inputRow);
  m.appendChild(body);
  const actions = document.createElement("div");
  actions.className = "modal-actions";
  const cancel = document.createElement("button");
  cancel.className = "btn btn-subtle"; cancel.textContent = "Cancel";
  cancel.onclick = () => closeModal(false);
  const ok = document.createElement("button");
  ok.className = "btn btn-danger"; ok.textContent = "Delete everything";
  ok.disabled = !prev.targets.length;
  ok.onclick = () => closeModal(true);
  actions.append(cancel, ok);
  m.appendChild(actions);
  const confirmed = await openModal(m);
  if (!confirmed) return;
  const res = await api.start_reset(includeInput);
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

async function verifyEnvironment() {
  const res = await api.verify_environment();
  if (res && res.error) { showMessage("info", "Can't check right now", res.error); return; }
  const src = $("selSource").selectedOptions[0]?.textContent || "";
  const env = $("selEnv").selectedOptions[0]?.textContent || "";
  openPreviewModal(0, `Verify environment — ${src} / ${env}`,
    "Opening TSMIS in the background and signing in — this can take 15–60 seconds…");
}

function bindEvents() {
  // tabs
  const TABS = {
    export: { btn: "tabExport", pane: "paneExport", title: "Export reports",
              sub: "Select reports and routes, then run the batch export." },
    consolidate: { btn: "tabConsolidate", pane: "paneConsolidate", title: "Consolidate output",
                   sub: "Merge per-route files into a single workbook." },
    compare: { btn: "tabCompare", pane: "paneCompare", title: "Compare reports",
               sub: "Build a discrepancy workbook from two report sources." },
    settings: { btn: "tabSettings", pane: "paneSettings", title: "Settings",
                sub: "Reliability, debugging and storage options." },
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
  $("btnUpdate").onclick = onUpdateClick;
  $("appVersion").onclick = () => api.check_updates();

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

  // settings tab
  Object.keys(SETTING_INPUTS).forEach((id) => {
    $(id).addEventListener("change", () => onSettingInput(id));
  });
  $("setDebugLog").addEventListener("change", () => onSettingToggle("setDebugLog", "debug_logging"));
  $("setDevtools").addEventListener("change", () => onSettingToggle("setDevtools", "ui_devtools"));
  $("btnSupportBundle").onclick = async () => {
    const res = await api.save_support_bundle();
    if (res && res.error) showMessage("error", "Could not save the bundle", res.error);
  };
  $("btnOpenFailures").onclick = () => api.open_failures_folder();
  $("btnCheckUpdates2").onclick = () => api.check_updates();
  $("btnCheckEnvs").onclick = async () => {
    const res = await api.check_environments();
    if (res && res.error) showMessage("info", "Can't check right now", res.error);
  };
  $("btnCheckEnvsCancel").onclick = () => api.cancel_run();
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
    days: ["2026-06-11 ssor-prod", "2026-06-11 ars-prod", "2026-06-08 ssor-dev", "2026-06-02"],
    can_save_report: false,
    update: { phase: "idle" },
    env_access: {},
  };
  const mockSettings = {
    report_timeout_min: 6, fast_timeout_min: 10, retry_timeout_min: 15,
    county_timeout_s: 60, fast_workers: 3, debug_logging: false, ui_devtools: false,
  };
  const mockUrlOverrides = {};
  const mockChromium = { bundled: false, downloaded: false, downloaded_mb: 0,
                         active: false, dir: "C:\\Tools\\TSMIS Exporter\\data\\ms-playwright" };
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
      meta: {
        version: "0.10.0 (preview)", build: "portable app",
        variant: "system browser",
        data_root: "C:\\Tools\\TSMIS Exporter",
        output_root: "C:\\Tools\\TSMIS Exporter\\output",
        log_file: "C:\\Tools\\TSMIS Exporter\\data\\logs\\tsmis.log",
        failures_dir: "C:\\Tools\\TSMIS Exporter\\data\\failures",
        auth_state: "none", max_workers: 30,
      },
    };
  }
  let timer = null;
  const push = (...evs) => dispatch(evs);
  const pushState = () => push({ t: "state", s: JSON.parse(JSON.stringify(st)) });

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

  function runMockExport(reports, routes, fast, workers) {
    st.task = "export"; st.fast_run = fast;
    st.auth_dot = "busy";
    st.auth_text = reports.length > 1 ? `Exporting ${reports.length} report(s)…`
                                      : `Exporting ${REPORTS[reports[0]].label}…`;
    pushState();
    const names = reports.map((i) => REPORTS[i].label).join(", ");
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
      const w = 1 + (tick % nWorkers);
      push({ t: "wstatus", w, text: `[${String(done).padStart(3)}/${total}] Route ${route}: working… (${(Math.random() * 60 + 3).toFixed(0)}s)` });
      if (status === "saved") push({ t: "log", text: `Route ${route}: saved (${(Math.random() * 3 + 0.4).toFixed(1)} MB, ${(Math.random() * 40 + 8).toFixed(0)}s)` });
      if (status === "failed") push({ t: "log", text: `Route ${route}: FAILED — TSMIS site error (see failures folder)` });
      push({ t: "progress", p: { done, total, route, report: REPORTS[reports[0]].label, report_i: 1, report_n: reports.length, ...counts } });
    }, fast ? 120 : 350);
  }

  return {
    get_initial_state: async () => ({
      app_name: "TSMIS Exporter", version: "0.10.0 (preview)",
      output_root: "C:\\Tools\\TSMIS Exporter\\output",
      log_dir: "C:\\Tools\\TSMIS Exporter\\data\\logs",
      reports: REPORTS,
      cons_reports: REPORTS.map((r) => r.label).concat(["TSN Highway Log"]),
      compare_reports: [
        { label: "Highway Log — TSMIS vs TSN", kind: "files" },
        { label: "TSAR: Ramp Summary — between environments", kind: "folders" },
        { label: "TSAR: Ramp Detail — between environments", kind: "folders" },
        { label: "Highway Sequence Listing — between environments", kind: "folders" },
        { label: "Highway Log — between environments", kind: "folders" },
      ],
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
        mockChromium.downloaded = true; mockChromium.downloaded_mb = 471;
        push({ t: "log", text: "Built-in Chromium downloaded. Restart the app to see it in the Browser dropdown (browsers are probed at startup)." },
             { t: "settings", s: mockSettingsPayload() },
             { t: "run_ended" },
             { t: "modal", kind: "info", title: "Built-in Chromium downloaded",
               message: "The browser is in place. Restart the app and it will appear in the Browser dropdown as 'Built-in Chromium'." });
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
    get_settings: async () => ({ values: { ...mockSettings }, defaults: { ...mockSettings }, meta: {} }),
    set_setting: async (key, value) => {
      const numeric = typeof mockSettings[key] === "number";
      mockSettings[key] = numeric ? Math.max(1, parseInt(value, 10) || mockSettings[key]) : !!value;
      push({ t: "log", text: `(mock) setting ${key} = ${mockSettings[key]}` });
      return { ok: true, values: { ...mockSettings } };
    },
    reset_preview: async (includeInput) => ({
      targets: ["export run folder '2026-06-11 ssor-prod'", "export run folder '2026-06-11 ars-prod'",
                "output folder 'consolidated'", "output folder 'run_reports'", "failure screenshots"]
        .concat(includeInput ? ["TSN input PDFs"] : []),
      files: includeInput ? 1480 : 1398, mb: includeInput ? 612.4 : 540.1,
    }),
    start_reset: async () => {
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
    save_support_bundle: async () => {
      push({ t: "log", text: "Support bundle saved (12 files): C:\\Users\\you\\Desktop\\tsmis_support.zip" });
      return { saved: true };
    },
    clear_saved_login: async () => {
      st.authed = false; st.auth_dot = "bad"; st.auth_text = "No saved login — click Log in";
      push({ t: "log", text: "Saved login deleted — click 'Log in' to sign in again." });
      pushState();
      return { ok: true, removed: true };
    },
    open_failures_folder: async () => push({ t: "log", text: "(mock) would open the failures folder" }),
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
    pick_compare_folder: async () => ({
      path: "D:\\Archive\\2026-05-02 ssor-prod",
    }),
    start_compare_env: async (_idx, dirA, dirB, wantFormulas, wantValues) => {
      if (!wantFormulas && !wantValues) {
        return { error: "Tick at least one output (values and/or live formulas)." };
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
    start_compare: async (_idx, _t, _n, wantFormulas, wantValues) => {
      if (!wantFormulas && !wantValues) {
        return { error: "Tick at least one output (values and/or live formulas)." };
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
    check_updates: async () => {
      if (st.update.phase === "available") {
        push({ t: "log", text: "An update is already waiting — see the title bar." });
      } else if (st.update.phase === "staged") {
        push({ t: "log", text: "An update is already downloaded — click ‘Restart to update’ in the title bar to install it." });
      } else {
        push({ t: "log", text: "Checking for updates…" });
        setTimeout(() => push({ t: "log", text: "You're on the latest version (v0.8.0 preview)." }), 600);
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
  };
}
