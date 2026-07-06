// Export-tab module (S5 / FE-01, split from app.js — same global scope; loaded
// before app.js like the other ui-*.js files). Owns: the screenshot-preview
// modal + per-browser worker strip, the pre-flight summary card, and the
// Export-tab user actions (fast toggle, routes input, start).
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
