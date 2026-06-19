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

// System-check status as a shape+colour icon (not colour alone): ✓ ok, ✗ bad,
// ! warn, spinner while checking — readable for colour-blind users.
const CHECK_ICON = { ok: "i-check", bad: "i-x", warn: "i-warn", busy: "i-loader", unknown: "i-loader" };
function setCheckIcon(el, status) {
  const ic = el.querySelector(".check-ic");
  if (!ic) return;
  ic.querySelector("use").setAttribute("href", "#" + (CHECK_ICON[status] || "i-loader"));
  ic.setAttribute("class", "ic check-ic ci-" + (status || "unknown"));
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

// Run a theme change behind a brief .theme-anim window so light<->dark eases
// (a slower, deliberate colour cross-fade) instead of snapping. Scoped in time
// so ordinary hovers stay snappy — the CSS only transitions while the class is on.
const THEME_FADE_MS = 500;
function withThemeTransition(fn) {
  const el = document.documentElement;
  el.classList.add("theme-anim");
  fn();
  window.clearTimeout(withThemeTransition._t);
  withThemeTransition._t = window.setTimeout(
    () => el.classList.remove("theme-anim"), THEME_FADE_MS + 60);
}

window.matchMedia("(prefers-color-scheme: dark)")
  .addEventListener("change", () => withThemeTransition(applyTheme));

// Theme toggle button (replaces the labeled dropdown): shows the current
// preference as an icon and cycles System -> Light -> Dark on click.
const THEME_ICONS = { auto: "i-monitor", light: "i-sun", dark: "i-moon" };
function renderThemeButton() {
  const btn = $("btnTheme");
  if (!btn) return;
  const pref = themePref();
  btn.querySelector("use").setAttribute("href", "#" + (THEME_ICONS[pref] || THEME_ICONS.auto));
  const word = pref === "auto" ? "System" : pref[0].toUpperCase() + pref.slice(1);
  btn.title = `Theme: ${word} — click to switch`;
}

// Lightweight title-bar popovers (sign-in detail, system checks): one open at a
// time, closing on outside-click or Esc. The trigger is a .status-chip; the
// panel is a sibling .popover inside the same .popover-host.
function closeAllPopovers() {
  document.querySelectorAll(".popover").forEach((p) => p.classList.add("hidden"));
  document.querySelectorAll(".status-chip").forEach((b) => b.setAttribute("aria-expanded", "false"));
}
function attachPopover(host) {
  const btn = host.querySelector(".status-chip");
  const pop = host.querySelector(".popover");
  if (!btn || !pop) return;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    const willOpen = pop.classList.contains("hidden");
    closeAllPopovers();
    if (willOpen) { pop.classList.remove("hidden"); btn.setAttribute("aria-expanded", "true"); }
  });
  pop.addEventListener("click", (e) => e.stopPropagation());   // clicks inside keep it open
}
document.addEventListener("click", closeAllPopovers);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeAllPopovers(); });

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
  // An all-empty run summary ("saved 0 ... empty N") is NOT a success — don't
  // paint it green just because it contains the word "saved".
  const savedZero = /\bsaved:?\s+0\b/i.test(text);
  if (text.startsWith("✓")) line.classList.add("ok");
  else if (text.startsWith("✗")) line.classList.add("err");
  else if (upper.includes("FAIL") || upper.includes("ERROR")) line.classList.add("err");
  else if ((text.includes("saved") && !savedZero) || text.includes("Output file") || text.includes("Output:")) line.classList.add("ok");
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

// A report-type checkbox row (Export tab + Everything tab share this). `off`
// marks an app-wide-disabled report: shown but greyed (.option-static) and
// unpickable (disabled input + dataset.off so the lock-sweep leaves it alone).
function makeReportRow(rep, checked, off, onChange) {
  const row = document.createElement("label");
  row.className = "option-row" + (checked ? " checked" : "") + (off ? " option-static" : "");
  const cb = document.createElement("input");
  // dataset.idx is the STABLE index into EXPORT_REPORTS (rep.idx), not the row
  // position — kept stable even though disabled rows are shown, not filtered.
  cb.type = "checkbox"; cb.checked = !!checked; cb.dataset.idx = rep.idx;
  if (off) { cb.disabled = true; cb.dataset.off = "1"; }
  const box = document.createElement("span");
  box.className = "checkbox"; box.appendChild(icon("i-check"));
  const name = document.createElement("span");
  name.className = "option-name"; name.textContent = rep.label;
  if (off) {
    const note = document.createElement("span");
    note.className = "option-static-note"; note.textContent = " — export-only (unavailable)";
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

// ------------------------------------------------------ one-time build -----
function buildStatic() {
  const init = S.init;
  $("appName").textContent = init.app_name;
  $("appVersion").textContent = "v" + init.version;
  $("appVersion").title = "Check for updates";
  $("outputRoot").textContent = init.output_root;
  document.title = init.app_name;

  // report checkboxes (first ticked by default, same as the old GUI).
  // App-wide-disabled reports (Intersection) are SHOWN but greyed/unpickable —
  // .option-static keeps them dim even when no task is running, and dataset.off
  // keeps the lock-sweep from re-enabling them.
  const list = $("reportList");
  init.reports.forEach((rep, i) => {
    const off = !!rep.disabled;
    const row = makeReportRow(rep, !off && i === 0, off, updateReportCount);
    list.appendChild(row);
  });
  updateReportCount();

  // B3: Export Everything — report-type + environment checklists (all enabled
  // ones ticked; disabled ones shown greyed, never ticked).
  init.reports.forEach((rep) => {
    const off = !!rep.disabled;
    const row = makeReportRow(rep, !off, off, updateBatchCount);
    $("batchReportList").appendChild(row);
  });
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
  init.cons_reports.forEach((rep, i) => {
    const row = document.createElement("label");
    row.className = "option-row" + (i === 0 ? " checked" : "");
    const rb = document.createElement("input");
    rb.type = "radio"; rb.name = "consReport"; rb.checked = i === 0; rb.dataset.idx = i;
    const dot = document.createElement("span"); dot.className = "radio";
    const name = document.createElement("span");
    name.className = "option-name"; name.textContent = rep.label;
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

  const cl2 = $("compareList");
  (init.compare_reports || []).forEach((rep, i) => {
    const row = document.createElement("label");
    row.className = "option-row";
    row.dataset.group = rep.group || "";
    const rb = document.createElement("input");
    rb.type = "radio"; rb.name = "compareReport"; rb.dataset.idx = i;
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
  fill($("selBrowser"), init.channels, init.channel);

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
function currentCompareRep() {
  return (S.init.compare_reports || [])[compareChoice()] || {};
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
  ["selSource", "selEnv", "selBrowser", "routesInput", "btnChooseRoutes", "selDay",
   "btnVerifyEnv", "btnDeleteReports", "btnClearLogin", "btnSupportBundle",
   "btnCheckEnvs"]
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
  const head = $("completionHead"), use = head.querySelector("use");
  if (s.cancelled) {
    head.className = "completion-head warn"; use.setAttribute("href", "#i-warn");
    $("completionTitle").textContent = "Run stopped";
  } else if (failed > 0) {
    head.className = "completion-head warn"; use.setAttribute("href", "#i-warn");
    $("completionTitle").textContent = "Finished with failures";
  } else if (((t.saved || 0) + (t.exists || 0)) === 0 && (t.empty || 0) > 0) {
    // Every route came back empty (no data) — NOT a success. An environment that
    // signs in but returns no data for all routes (outage / permissions /
    // selector drift) must not read as a green "Export complete".
    head.className = "completion-head warn"; use.setAttribute("href", "#i-warn");
    $("completionTitle").textContent = "Finished with no data";
  } else {
    head.className = "completion-head ok"; use.setAttribute("href", "#i-check");
    $("completionTitle").textContent = "Export complete";
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
  if (!card || card.classList.contains("hidden")) return;   // hidden while running
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
    const labels = selectedReportIdxs().map((i) => ((S.init.reports || [])[i] || {}).label).filter(Boolean);
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
  $("reportList").querySelectorAll(".option-row").forEach((row, i) => {
    const label = ((S.init.reports || [])[i] || {}).label;
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
  $("batchReportList").querySelectorAll(".option-row").forEach((row, i) => {
    const label = ((S.init.reports || [])[i] || {}).label;
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
        case "state": S.st = ev.s; renderState(); updateMatrixProgress(); break;
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
        case "run_ended": endRunUi(); if (S.tab === "everything") { renderBatchLibrary(); if (S.everySub === "matrix") renderMatrix(); } break;
        case "matrix_refresh": if (S.tab === "everything" && S.everySub === "matrix") renderMatrix(); break;
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
  // All or none both mean "every route" — keep the box blank (the documented
  // "blank = all" convention) rather than stuffing it with all 283 numbers, so
  // the box and the picker always represent the same selection cleanly.
  const all = (S.init.routes || []).length;
  $("routesInput").value = (picked.length === 0 || picked.length === all) ? "" : picked.join(", ");
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
        .filter((c) => c.checked).map((c) => +c.dataset.idx);
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
  rows.forEach((r, i) => {
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
    btn.onclick = () => startBatch([i]);
    row.append(name, age, btn);
    lib.appendChild(row);
  });
  const meta = $("batchLibMeta");
  if (meta) meta.textContent = `${present.length} of ${rows.length} present`;
}

// ---- environment comparison matrix --------------------------------------
const MX_HI = 50;   // >= this many discrepancies reads as "many" (red); tunable

function updateMatrixProgress() {
  const el = $("matrixProgress");
  if (!el) return;
  const m = S.st && S.st.matrix;
  if (m && m.total) {
    el.hidden = false;
    el.textContent = `Comparing ${m.done}/${m.total}…`;
  } else {
    el.hidden = true;
  }
  // Grey the matrix controls live while ANY task runs (the grid only re-renders
  // at run end, so toggle the existing buttons/selects here on each state push).
  const locked = !!(S.st && S.st.task);
  document.querySelectorAll(
    "#matrixSection .mx-act, #matrixSection .mxch-refresh, #matrixSection .mx-rowmode, "
    + "#matrixSection .mx-linkbtn, #matrixBaseline, #btnMatrixRefreshAll, #btnOpenComparisons, "
    + "#matrixConfig .mx-toggle, #matrixConfig .mc-mode")
    .forEach((c) => { c.disabled = locked; });
  // Cancel is visible + active only while a matrix run is in progress; the
  // "Refresh stale" button then resumes whatever was left when re-clicked.
  const cancel = $("btnMatrixCancel");
  if (cancel) {
    const running = !!(S.st && S.st.task === "matrix");
    cancel.classList.toggle("hidden", !running);
    cancel.disabled = !running;
  }
}

function mxCellContent(cmp, tsnMeta) {
  // Returns {cls, main, sub} for a non-baseline cell from its unified `cmp` state.
  cmp = cmp || {};
  if (cmp.supported === false) return { cls: "mx-na", main: "—", sub: "not available yet" };
  if (cmp.missing_side) {
    if (cmp.missing_side === "tsn") {
      if (tsnMeta && tsnMeta.source_kind === "pdfs")
        return { cls: "mx-missing", main: "consolidate", sub: `${tsnMeta.pdf_count} TSN PDFs` };
      return { cls: "mx-missing", main: "needs TSN", sub: "pick a TSN file" };
    }
    const why = cmp.missing_side === "baseline" ? "baseline not exported"
      : cmp.missing_side === "both" ? "neither exported"
      : cmp.missing_side === "other" ? "other format missing" : "not exported";
    return { cls: "mx-missing", main: "needs export", sub: why };
  }
  if (!cmp.built) return { cls: "mx-stale", main: "compare", sub: "not built yet" };
  if (cmp.stale || cmp.diff_cells == null) {
    return { cls: "mx-stale",
             main: cmp.diff_cells == null ? "re-run" : String(cmp.diff_cells),
             sub: "stale — refresh" };
  }
  const d = cmp.diff_cells || 0, os = cmp.one_sided || 0;
  if (d === 0 && os === 0) return { cls: "mx-match", main: "✓ match", sub: "identical" };
  const cls = (d >= MX_HI || d + os >= MX_HI) ? "mx-diff-hi" : "mx-diff-lo";
  return { cls, main: `${d} diff${d === 1 ? "" : "s"}`,
           sub: os ? `+${os} one-sided` : "" };
}

// A compact icon action button for a matrix cell (export / compare / open). Icons
// (not text) so three actions fit a narrow cell; the title carries the meaning.
function mxActBtn(iconName, title, locked, onClick) {
  const b = document.createElement("button");
  b.className = "mx-act"; b.title = title; b.disabled = locked;
  b.appendChild(icon(iconName));
  b.onclick = onClick;
  return b;
}

function mxColRefreshBtn(title, locked, onClick) {
  const b = document.createElement("button");
  b.className = "mxch-refresh"; b.title = title; b.disabled = locked;
  b.appendChild(icon("i-refresh")); b.onclick = onClick;
  return b;
}

// The vs-TSN file picker shown under a row's name when it's in a TSN mode.
function mxTsnPicker(tm, locked) {
  const wrap = document.createElement("div"); wrap.className = "mx-tsnpick";
  const state = document.createElement("div"); state.className = "mxtp-state";
  if (tm.source_kind === "file" || tm.source_kind === "consolidated")
    state.textContent = "TSN: " + (tm.source_path || "").split(/[\\/]/).pop();
  else if (tm.source_kind === "pdfs") state.textContent = `${tm.pdf_count} TSN PDFs (not consolidated)`;
  else state.textContent = "no TSN file";
  const row = document.createElement("div"); row.className = "mxtp-row";
  const choose = document.createElement("button");
  choose.className = "mx-linkbtn"; choose.textContent = "Choose…"; choose.disabled = locked;
  choose.onclick = async () => {
    const r = await api.pick_matrix_tsn_file(tm.tsn_subdir);
    if (r && r.error) showMessage("error", "Can't pick", r.error);
    if (r && (r.ok || r.path)) await renderMatrix();
  };
  row.appendChild(choose);
  if (tm.source_kind === "pdfs") {
    const cons = document.createElement("button");
    cons.className = "mx-linkbtn"; cons.textContent = "Consolidate"; cons.disabled = locked;
    cons.onclick = async () => {
      const ok = await showConfirm({ title: "Consolidate TSN PDFs?",
        message: `Build one TSN workbook from the ${tm.pdf_count} PDF(s) in:\n\n${tm.input_dir}`,
        confirmLabel: "Consolidate" });
      if (!ok) return;
      const r = await api.consolidate_matrix_tsn(tm.tsn_subdir);
      if (r && r.error) showMessage("error", "Can't consolidate", r.error);
    };
    row.appendChild(cons);
  }
  if (tm.file) {
    const clr = document.createElement("button");
    clr.className = "mx-linkbtn"; clr.textContent = "Clear"; clr.disabled = locked;
    clr.onclick = async () => { await api.set_matrix_tsn_file(tm.tsn_subdir, ""); await renderMatrix(); };
    row.appendChild(clr);
  }
  wrap.append(state, row);
  return wrap;
}

// Config zone (bottom-right): report + environment show/hide toggles + the global
// "set all comparisons to…" control.
function renderMatrixConfig(snap, locked) {
  const mkToggle = (label, isOn, title, onClick) => {
    const b = document.createElement("button");
    b.className = "mx-toggle" + (isOn ? " on" : "");
    b.textContent = label; b.disabled = locked; b.title = title;
    b.onclick = onClick;
    return b;
  };
  const rtog = $("matrixReportToggles");
  if (rtog) {
    rtog.textContent = "";
    const hidden = new Set(snap.hidden || []);
    (snap.all_rows || []).forEach((r) => {
      const isOn = !hidden.has(r.key);
      rtog.appendChild(mkToggle(r.label, isOn, (isOn ? "Hide " : "Show ") + r.label, async () => {
        const res = await api.set_matrix_report(r.key, !isOn);
        if (res && res.error) { showMessage("error", "Can't toggle", res.error); return; }
        await renderMatrix();
      }));
    });
  }
  const etog = $("matrixEnvToggles");
  if (etog) {
    etog.textContent = "";
    const henv = new Set(snap.hidden_envs || []);
    (snap.all_envs || []).forEach((e) => {
      const isOn = !henv.has(e), lbl = snap.env_labels[e] || e;
      etog.appendChild(mkToggle(lbl, isOn, (isOn ? "Hide " : "Show ") + lbl, async () => {
        const res = await api.set_matrix_env(e, !isOn);
        if (res && res.error) { showMessage("error", "Can't toggle", res.error); return; }
        await renderMatrix();
      }));
    });
  }
  document.querySelectorAll("#matrixConfig .mc-mode").forEach((b) => {
    b.disabled = locked;
    b.onclick = async () => {
      const r = await api.set_all_matrix_modes(b.dataset.mode);
      if (r && r.error) { showMessage("error", "Can't apply", r.error); return; }
      await renderMatrix();
    };
  });
}

async function renderMatrix() {
  const grid = $("matrixGrid");
  if (!grid) return;
  let snap;
  try { snap = await api.matrix_info(); } catch (e) { return; }
  if (!snap || !snap.rows) return;
  const envs = snap.envs, locked = !!(S.st && S.st.task);
  // Wider row-label column (it carries the mode dropdown + TSN picker now); the
  // fr units stretch to fill the window, the data rows share the leftover height.
  grid.style.gridTemplateColumns =
    `minmax(190px,1.2fr) repeat(${envs.length}, minmax(116px,1fr))`;
  grid.style.gridTemplateRows = `auto repeat(${snap.rows.length}, minmax(82px,1fr))`;
  grid.textContent = "";

  const corner = document.createElement("div");
  corner.className = "mx-cell mx-corner mx-colhead";
  corner.textContent = "Report \\ Env";
  grid.appendChild(corner);
  envs.forEach((env) => {
    const h = document.createElement("div");
    h.className = "mx-cell mx-colhead" + (env === snap.baseline ? " mx-baseline-col" : "");
    const lab = document.createElement("div");
    lab.textContent = (snap.env_labels[env] || env) + (env === snap.baseline ? " ★" : "");
    h.appendChild(lab);
    h.appendChild(mxColRefreshBtn(`Refresh every comparison in ${snap.env_labels[env] || env}`,
      locked, async () => {
        const r = await api.recompute_matrix("all", null, env);
        if (r && r.nothing) showMessage("info", "Nothing to refresh", "No comparable cells here.");
        else if (r && r.error) showMessage("error", "Can't refresh", r.error);
      }));
    grid.appendChild(h);
  });

  snap.rows.forEach((rk) => {
    const rh = document.createElement("div");
    rh.className = "mx-cell mx-rowhead";
    const top = document.createElement("div"); top.className = "mxrh-top";
    const lbl = document.createElement("span"); lbl.className = "mxrh-label";
    lbl.textContent = snap.row_labels[rk] || rk;
    top.append(lbl, mxColRefreshBtn(`Refresh every comparison in ${snap.row_labels[rk]}`,
      locked, async () => {
        const r = await api.recompute_matrix("all", rk, null);
        if (r && r.nothing) showMessage("info", "Nothing to refresh", "No comparable cells here.");
        else if (r && r.error) showMessage("error", "Can't refresh", r.error);
      }));
    rh.appendChild(top);
    // per-row comparison-mode dropdown (only when the row has >1 mode)
    const modes = (snap.row_modes && snap.row_modes[rk]) || [];
    if (modes.length > 1) {
      const ms = document.createElement("select");
      ms.className = "mx-rowmode"; ms.disabled = locked;
      modes.forEach((m) => {
        const o = document.createElement("option");
        o.value = m.id; o.textContent = m.label + (m.supported ? "" : " (soon)");
        o.disabled = !m.supported;
        if (m.id === snap.modes[rk]) o.selected = true;
        ms.appendChild(o);
      });
      ms.onchange = async () => {
        const r = await api.set_matrix_row_mode(rk, ms.value);
        if (r && r.error) showMessage("error", "Can't switch", r.error);
        await renderMatrix();
      };
      rh.appendChild(ms);
    }
    const tm = snap.tsn_meta && snap.tsn_meta[rk];
    if (tm && tm.supported) rh.appendChild(mxTsnPicker(tm, locked));
    grid.appendChild(rh);

    envs.forEach((env) => {
      const c = snap.cells[rk][env], cmp = c.cmp;
      const cell = document.createElement("div");
      cell.className = "mx-cell" + (env === snap.baseline ? " mx-baseline-col" : "");
      const main = document.createElement("div"); main.className = "mx-num";
      const sub = document.createElement("div"); sub.className = "mx-sub";
      const expWhen = c.export.present ? fmtAge(c.export.age_seconds) : "never exported";
      if (cmp === null) {                 // env-mode baseline column
        main.textContent = "baseline"; sub.textContent = expWhen;
      } else {
        const v = mxCellContent(cmp, tm);
        cell.classList.add(v.cls); main.textContent = v.main; sub.textContent = v.sub;
      }
      cell.title = `${snap.row_labels[rk]} — ${snap.env_labels[env] || env}\nExported: ${expWhen}`;
      cell.append(main, sub);

      const acts = document.createElement("div"); acts.className = "mx-actions";
      acts.appendChild(mxActBtn("i-refresh", "Re-export this report for this environment (live)",
        locked, async () => {
          const r = await api.refresh_cell_export(rk, env);
          if (r && r.error) showMessage("error", "Can't refresh", r.error);
        }));
      const supported = cmp && cmp.supported !== false;
      if (cmp !== null && supported) {
        acts.appendChild(mxActBtn("i-compare", "Rebuild this comparison", locked, async () => {
          const r = await api.refresh_cell_comparison(rk, env);
          if (r && r.error) showMessage("error", "Can't compare", r.error);
        }));
        if (cmp.built) {
          const ob = mxActBtn("i-external", "Open this comparison workbook (values copy)",
            locked, async () => {
              const r = await api.open_cell_comparison(rk, env);
              if (r && r.error) showMessage("error", "Can't open", r.error);
            });
          ob.classList.add("mx-open"); acts.appendChild(ob);
        }
      }
      cell.appendChild(acts);
      grid.appendChild(cell);
    });
  });

  const sel = $("matrixBaseline");
  if (sel) {
    sel.textContent = "";
    snap.all_envs.forEach((env) => {
      const o = document.createElement("option");
      o.value = env; o.textContent = snap.env_labels[env] || env;
      if (env === snap.baseline) o.selected = true;
      sel.appendChild(o);
    });
    sel.disabled = locked;
    sel.onchange = async () => {
      const nb = sel.value;
      const ok = await showConfirm({
        title: "Switch baseline?",
        message: `Compare every environment against ${snap.env_labels[nb] || nb}?\n\n`
          + "This recomputes the cross-environment comparisons against the new baseline.",
        confirmLabel: "Switch & recompute",
      });
      if (!ok) { sel.value = snap.baseline; return; }
      const r = await api.set_matrix_baseline(nb);
      if (r && r.error) { showMessage("error", "Can't switch", r.error); sel.value = snap.baseline; return; }
      await renderMatrix();
      await api.recompute_matrix("all");
    };
  }
  const btn = $("btnMatrixRefreshAll");
  if (btn) btn.onclick = async () => {
    const r = await api.recompute_matrix("stale");
    if (r && r.nothing) showMessage("info", "Up to date", "Every comparison is current.");
    else if (r && r.error) showMessage("error", "Can't refresh", r.error);
  };
  const openFolderBtn = $("btnOpenComparisons");
  if (openFolderBtn) openFolderBtn.onclick = async () => {
    const r = await api.open_comparisons_folder();
    if (r && r.error) showMessage("error", "Can't open", r.error);
  };
  const cancelBtn = $("btnMatrixCancel");
  if (cancelBtn) cancelBtn.onclick = () => api.cancel_run();

  renderMatrixConfig(snap, locked);
  updateMatrixProgress();
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

// Switch the Compare sub-tab: highlight the button, show only that group's
// comparison-type rows, and keep exactly one VISIBLE row selected. Radios share a
// name, so seating a new pick natively drops the now-hidden previous one;
// renderCompareKind then swaps in the matching files/folders inputs.
function selectCompareGroup(groupId) {
  document.querySelectorAll("#compareSubtabs .subtab").forEach((b) => {
    const on = b.dataset.group === groupId;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", String(on));
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
  if (custom) sel.value = custom;
  else if (prev && options.includes(prev)) sel.value = prev;
  else if (preferred) sel.value = preferred;
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
  setToggle("setEnvCheckSignin", v.env_check_after_signin);
  setToggle("setEnvCheckStart", v.env_check_after_start);
  setToggle("setNotifyFinish", v.notify_on_finish);

  const meta = s.meta || {};
  // "Revert to previous version" only makes sense on a writable installed copy
  // (a read-only / dev install can't self-swap).
  $("btnRevert").classList.toggle("hidden", meta.update_support !== "ok");
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
    // Show each target's REAL path under its label, so the exact folders being
    // deleted (especially the user-chosen Export Everything store) are visible —
    // never just a friendly label that hides the location.
    list.textContent = prev.targets.length
      ? prev.targets.map((t, i) =>
          (prev.paths && prev.paths[i]) ? `${t}\n    ${prev.paths[i]}` : t).join("\n")
      : "";
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
  // Pass back the single-use token from the latest preview — start_reset
  // requires it (server-side confirmation that this preview was shown).
  const res = await api.start_reset(includeInput, prev.token);
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
    document.body.classList.toggle("matrix-wide", sub === "matrix");
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
      document.body.classList.remove("matrix-wide");   // leaving Everything restores the layout
    }
    updateActivityCards();
  };
  Object.entries(TABS).forEach(([key, t]) => { $(t.btn).onclick = () => setTab(key); });
  $("subEveryExport").onclick = () => setEverySub("export");
  $("subEveryMatrix").onclick = () => setEverySub("matrix");

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
  document.body.addEventListener("change", renderPreflight);
  document.body.addEventListener("input", renderPreflight);

  $("selBrowser").onchange = () => api.set_browser($("selBrowser").value);
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

window.addEventListener("pywebviewready", () => {
  if (bridgeReady()) boot(window.pywebview.api);   // else the poll catches it
});
if (WANT_MOCK) {
  boot(makeMockApi());
} else {
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
    { label: "Highway Log (PDF)", fmt: "PDF" },
    { label: "Intersection Summary", fmt: "Excel" },
    { label: "Intersection Detail", fmt: "Excel" },
  ];
  // The Consolidate radios index into THIS list (matches reports.CONSOLIDATE_REPORTS,
  // 6 rows) — NOT the 7-row export REPORTS above. consolidate_info/start_consolidate
  // must use this so the preview's labels/out_paths mirror the real bridge.
  const CONS_REPORTS = [
    { label: "TSAR: Ramp Summary" },
    { label: "TSAR: Ramp Detail" },
    { label: "Highway Sequence Listing" },
    { label: "TSMIS Highway Log (Excel)" },
    { label: "TSMIS Highway Log (PDF)" },
    { label: "TSN Highway Log (PDF)" },
  ];
  const st = {
    task: null, fast_run: false,
    authed: false, device_ok: false,
    logins: { file: { valid: false, age_h: null },
              device: { ok: false, primed: true } },
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
    matrix: null,
    matrix_baseline: "ssor-prod",
    matrix_hidden: [],
    matrix_hidden_envs: [],
    matrix_modes: {},            // row_key -> mode id
    matrix_tsn_files: {},        // subdir -> picked file path
    mock_tsn_pdfs: true,         // TSN folder starts with PDFs (not consolidated)
  };
  const mockSettings = {
    report_timeout_min: 6, fast_timeout_min: 10, retry_timeout_min: 15,
    county_timeout_s: 60, fast_workers: 3, debug_logging: false, ui_devtools: false,
    env_check_after_signin: true, env_check_after_start: false, notify_on_finish: true,
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
        version: "0.14.2 (preview)", build: "portable app",
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
      { id: "env", label: "Cross-environment", kind: "env", supported: false },
      { id: "tsn", label: "vs TSN", kind: "tsn", supported: true },
      { id: "vs_excel", label: "vs TSMIS Excel", kind: "self", supported: true }];
    return [
      { id: "env", label: "Cross-environment", kind: "env", supported: true },
      { id: "tsn", label: "vs TSN", kind: "tsn", supported: false }];
  }
  function mockCmp(s) {
    if (s === "needtsn") return { supported: true, built: false, stale: true,
      reason: "missing", missing_side: "tsn", verdict: null, diff_cells: null, one_sided: null };
    if (s === "missing") return { supported: true, built: false, stale: true,
      reason: "missing", missing_side: "cell", verdict: null, diff_cells: null, one_sided: null };
    if (s === "notbuilt") return { supported: true, built: false, stale: true,
      reason: "missing", missing_side: null, verdict: null, diff_cells: null, one_sided: null };
    if (s === "stale") return { supported: true, built: true, stale: true,
      reason: "cell_newer", missing_side: null, verdict: "diff", diff_cells: 18, one_sided: 2 };
    return { supported: true, built: true, stale: false, reason: "fresh", missing_side: null,
             verdict: (s[0] === 0 && s[1] === 0) ? "match" : "diff", diff_cells: s[0], one_sided: s[1] };
  }
  function mockMatrixSnapshot(baseline) {
    const allEnvs = ["ssor-prod", "ssor-test", "ssor-dev", "ars-prod", "ars-test", "ars-dev"];
    const henv = st.matrix_hidden_envs || [];
    const envs = allEnvs.filter((e) => henv.indexOf(e) < 0);
    const allRows = [
      { key: "ramp_summary", label: "TSAR: Ramp Summary", tsn_capable: false },
      { key: "ramp_detail", label: "TSAR: Ramp Detail", tsn_capable: false },
      { key: "highway_sequence", label: "Highway Sequence Listing", tsn_capable: false },
      { key: "highway_log", label: "Highway Log (Excel)", tsn_capable: true },
      { key: "highway_log_pdf", label: "Highway Log (PDF)", tsn_capable: true },
    ];
    const rowLabels = {}; allRows.forEach((r) => { rowLabels[r.key] = r.label; });
    const hidden = st.matrix_hidden || [];
    const rows = allRows.map((r) => r.key).filter((k) => hidden.indexOf(k) < 0);
    const envLabels = {};
    allEnvs.forEach((e) => { const [s, v] = e.split("-");
      envLabels[e] = `${s.toUpperCase()} / ${v[0].toUpperCase()}${v.slice(1)}`; });
    // env-mode samples (vs the baseline column).
    const envSample = {
      ramp_summary: { "ssor-test": [42, 0], "ssor-dev": [42, 0], "ars-prod": [0, 0], "ars-test": [48, 0], "ars-dev": "stale" },
      ramp_detail: { "ssor-test": [25, 10], "ssor-dev": [25, 10], "ars-prod": [0, 0], "ars-test": [31, 10], "ars-dev": "missing" },
      highway_sequence: { "ssor-test": [25, 12], "ssor-dev": [23, 12], "ars-prod": [2, 0], "ars-test": [560, 156], "ars-dev": [102, 44] },
      highway_log: { "ssor-test": [7, 1], "ssor-dev": [7, 1], "ars-prod": [0, 0], "ars-test": [88, 12], "ars-dev": "stale" },
    };
    const cells = {}, modes = {}, rowModes = {}, tsnMeta = {};
    rows.forEach((rk) => {
      const avail = mockMatrixModes(rk);
      let selId = (st.matrix_modes || {})[rk] || "env";
      if (!avail.some((m) => m.id === selId)) selId = "env";
      const mode = avail.find((m) => m.id === selId) || avail[0];
      modes[rk] = mode.id; rowModes[rk] = avail;
      const tsnSub = "highway_log";                 // both HL rows share the TSN folder
      const tsnFile = (st.matrix_tsn_files || {})[tsnSub];
      const srcKind = tsnFile ? "file" : (st.mock_tsn_pdfs ? "pdfs" : "consolidated");
      if (mode.kind === "tsn") {
        tsnMeta[rk] = { supported: mode.supported, fmt: rk === "highway_log_pdf" ? "pdf" : "excel",
          source_kind: srcKind, pdf_count: srcKind === "pdfs" ? 12 : undefined,
          source_path: tsnFile || "…\\_tsn_input\\highway_log\\tsn_highway_log_consolidated.xlsx",
          tsn_subdir: tsnSub, file: tsnFile || null,
          input_dir: "C:\\Tools\\TSMIS Exporter\\output\\All Reports (current)\\_tsn_input\\highway_log" };
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
                : env === "ars-prod" ? [0, 0] : env === "ars-dev" ? "stale" : [73, 9]);
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
  function mockMatrixRun(mode, label, total) {
    st.task = "matrix";
    if (total) st.matrix = { phase: "comparing", row: null, cell: null, done: 0, total };
    pushState();
    push({ t: "run_started", mode, label, workers: 1 }, { t: "log", text: label });
    setTimeout(() => {
      st.task = null; st.matrix = null; pushState();
      push({ t: "run_ended" }, { t: "matrix_refresh" });
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
             { t: "log", text: `Done. ${total} routes handled — saved ${counts.saved}, already had ${counts.exists}, empty ${counts.empty}, skipped ${counts.skipped}, failed ${counts.failed}.` });
        if (autoConsolidate) {
          reports.filter((i) => i < 4).forEach((i) =>
            push({ t: "log", text: `Auto-consolidating ${REPORTS[i].label}… done.` }));
        }
        push({ t: "run_ended" });
        st.task = null; st.fast_run = false; st.can_save_report = true;
        const failedRoutes = routes.slice(0, counts.failed);
        st.last_summary = {
          reports: reports.map((i, n) => ({ label: REPORTS[i].label, ...counts,
            failed_routes: n === 0 ? failedRoutes : [] })),
          totals: { ...counts }, failed_total: counts.failed, cancelled: false,
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
      push({ t: "progress", p: { done, total, route, report: REPORTS[reports[0]].label, report_i: 1, report_n: reports.length, ...counts } });
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
    const reps = reports.map((r) => REPORTS[r]);
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

  return {
    get_initial_state: async () => ({
      app_name: "TSMIS Exporter", version: "0.14.2 (preview)",
      output_root: "C:\\Tools\\TSMIS Exporter\\output",
      log_dir: "C:\\Tools\\TSMIS Exporter\\data\\logs",
      // Mirror the real gate: ALL reports, each carrying its STABLE index into
      // the full registry, with Intersection flagged disabled (shown greyed).
      reports: REPORTS.map((r, i) => ({ idx: i, ...r,
                                        disabled: /^Intersection/.test(r.label) })),
      cons_reports: [
        { label: "TSAR: Ramp Summary", fmt: "PDF" },
        { label: "TSAR: Ramp Detail", fmt: "Excel" },
        { label: "Highway Sequence Listing", fmt: "Excel" },
        { label: "TSMIS Highway Log (Excel)", fmt: "Excel" },
        { label: "TSMIS Highway Log (PDF)", fmt: "PDF" },
        { label: "TSN Highway Log (PDF)", fmt: "PDF" },
      ],
      compare_groups: [
        { id: "env", label: "Cross-environment" },
        { id: "highway_log", label: "Highway Log" },
      ],
      compare_reports: [
        { label: "TSAR: Ramp Summary — between environments", kind: "folders", group: "env" },
        { label: "TSAR: Ramp Detail — between environments", kind: "folders", group: "env" },
        { label: "Highway Sequence Listing — between environments", kind: "folders", group: "env" },
        { label: "Highway Log — between environments", kind: "folders", group: "highway_log" },
        { label: "Highway Log — TSMIS vs TSN", kind: "files", group: "highway_log",
          file_a_label: "TSMIS", file_b_label: "TSN" },
        { label: "Highway Log — TSMIS (PDF) vs TSN (PDF)", kind: "files", group: "highway_log",
          file_a_label: "TSMIS (PDF)", file_b_label: "TSN (PDF)" },
        { label: "Highway Log — TSMIS (PDF) vs TSMIS (Excel)", kind: "files", group: "highway_log",
          file_a_label: "TSMIS (PDF)", file_b_label: "TSMIS (Excel)" },
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
    get_settings: async () => ({ values: { ...mockSettings }, defaults: { ...mockSettings }, meta: { update_support: "ok" } }),
    set_setting: async (key, value) => {
      const numeric = typeof mockSettings[key] === "number";
      const boolish = typeof mockSettings[key] === "boolean";
      mockSettings[key] = numeric ? Math.max(1, parseInt(value, 10) || mockSettings[key])
                        : boolish ? !!value : value;
      push({ t: "log", text: `(mock) setting ${key} = ${mockSettings[key]}` });
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
    save_support_bundle: async () => {
      push({ t: "log", text: "Support bundle saved (12 files): C:\\Users\\you\\Desktop\\tsmis_support.zip" });
      return { saved: true };
    },
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
      runMockExport([0], ROUTES.slice(0, Math.max(2, s.failed_total)), false, 1, false);
      return { ok: true };
    },
    open_run_folder: async () => { push({ t: "log", text: "(mock) opened run folder" }); return { ok: true }; },
    resume_batch: async () => {
      const r = st.batch_resume || { pending: 1, reports: [] };
      st.batch_resume = null;
      const reps = (r.reports && r.reports.length) ? r.reports : [0, 1, 2, 3];
      const envs = Array.from({ length: r.pending || 1 }, (_, i) => `env-${i + 1}`);
      runMockBatch(reps, envs, false, 1, true);
      return { ok: true };
    },
    discard_batch: async () => { st.batch_resume = null; pushState(); return { ok: true }; },
    report_library_info: async () => ({
      dest: st.batch_dest || "C:\\Tools\\TSMIS Exporter\\output\\All Reports (current)",
      // One row per ENABLED export report — matches the real report_library_info
      // (Intersection is app-wide disabled, so it's absent here too).
      reports: [
        { label: "TSAR: Ramp Summary", subdir: "ramp_summary", present: true, mtime: 0, age_seconds: 2 * 3600 },
        { label: "TSAR: Ramp Detail", subdir: "ramp_detail", present: true, mtime: 0, age_seconds: 2 * 3600 },
        { label: "Highway Sequence Listing", subdir: "highway_sequence", present: true, mtime: 0, age_seconds: 3 * 3600 },
        { label: "Highway Log", subdir: "highway_log", present: true, mtime: 0, age_seconds: 6 * 86400 },
        { label: "Highway Log (PDF)", subdir: "highway_log_pdf", present: true, mtime: 0, age_seconds: 6 * 86400 },
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
      const next = {};
      ["highway_log", "highway_log_pdf"].forEach((rk) => { if (mode === "tsn") next[rk] = "tsn"; });
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
      if (st.task) return { error: "A task is already running." };
      st.mock_tsn_pdfs = false;               // pretend the PDFs are now consolidated
      mockMatrixRun("consolidate", `Consolidating TSN ${subdir} PDFs…`, 1);
      return { ok: true };
    },
    set_matrix_baseline: async (b) => {
      st.matrix_baseline = b;
      push({ t: "log", text: `Matrix baseline set to ${b}.` });
      pushState();
      return { baseline: b, recompute_pending: 5 };
    },
    refresh_cell_export: async (rk, env) => {
      if (st.task) return { error: "A task is already running." };
      mockMatrixRun("export", `Refreshing ${rk} — ${env}…`);
      return { ok: true };
    },
    refresh_cell_comparison: async (rk, env) => {
      if (st.task) return { error: "A task is already running." };
      mockMatrixRun("consolidate", `Comparing ${rk} — ${env}…`, 1);
      return { ok: true };
    },
    recompute_matrix: async (scope, row, env) => {
      if (st.task) return { error: "A task is already running." };
      const n = row ? 5 : env ? 4 : scope === "all" ? 18 : 6;
      mockMatrixRun("consolidate", `Rebuilding ${n} comparison(s)…`, n);
      return { ok: true, count: n };
    },
    open_cell_comparison: async (rk, env) => {
      push({ t: "log", text: `(mock) open comparison workbook: ${env}_${rk}.xlsx` });
      return { ok: true };
    },
    open_comparisons_folder: async () => {
      push({ t: "log", text: "(mock) open comparisons folder" });
      return { ok: true };
    },
    set_batch_dest: async (p) => {
      st.batch_dest = p || "C:\\Tools\\TSMIS Exporter\\output\\All Reports (current)";
      pushState(); return { dest: st.batch_dest };
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
    consolidate_info: async (idx, day) => {
      // Only index 5 (TSN Highway Log) reads from a dropped-in input folder (those
      // district PDFs come from outside the app) — so it carries an input_note and
      // the day picker is hidden. Index 4 (TSMIS Highway Log PDF) reads this app's
      // own "Highway Log (PDF)" export, day-aware like the Excel one.
      const dropped = {
        5: { note: "Drop the TSN district Highway Log PDFs into the input folder first.",
             dir: "C:\\Tools\\TSMIS Exporter\\input\\tsn_highway_log",
             out: "tsn_highway_log_consolidated.xlsx" },
      }[idx];
      if (dropped) return {
        dest_dir: "C:\\Tools\\TSMIS Exporter\\output",
        out_path: "C:\\Tools\\TSMIS Exporter\\output\\" + dropped.out,
        exists: false,
        input_note: dropped.note,
        input_dir: dropped.dir,
      };
      return {
        dest_dir: `C:\\Tools\\TSMIS Exporter\\output\\${day || "(legacy)"}\\consolidated`,
        out_path: `C:\\Tools\\TSMIS Exporter\\output\\${day || "(legacy)"}\\consolidated\\${CONS_REPORTS[idx].label.replace(/[:\s]+/g, "_")}.xlsx`,
        exists: idx === 0 && day === "2026-06-10",
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
      st.auth_dot = "busy"; st.auth_text = `Consolidating ${CONS_REPORTS[idx].label}…`;
      pushState();
      push({ t: "log", text: `Starting consolidation: ${CONS_REPORTS[idx].label}` + (day ? `   ·   ${day}` : "") },
           { t: "run_started", mode: "consolidate", label: `Consolidating ${CONS_REPORTS[idx].label}…` });
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
}
