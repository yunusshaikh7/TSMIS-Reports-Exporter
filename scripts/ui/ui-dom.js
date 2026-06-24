/* TSMIS UI — DOM / theme / log / modal-dialog primitives (P9b split from app.js).
 * A classic <script> (NO ES module): loaded BEFORE app.js in index.html, so these
 * top-level function declarations + their literal state (CHECK_ICON, THEME_*,
 * modalResolve) share the global lexical scope with app.js. They read app.js's
 * globals ($, S, LOG_MAX_LINES, api) only at call time (from boot()/handlers),
 * which always runs after every app script has loaded. Behavior-neutral move. */
"use strict";

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
