// ArcGIS tab module (v0.29.0, split like the other ui-*.js — same global scope).
// Four sub-tabs, in the order the work flows:
//   LAYERS (v0.46.0, first) — the app's own copy of the 40 TSMIS layers and the
//                       in-app refresh that replaced the manual export: ArcGIS
//                       Pro's status + a quick check, every layer with its rows /
//                       export time / the builds that read it, and Refresh all /
//                       Refresh selected (a matrix-queue job; each finished layer
//                       is swapped in while the next one exports).
//   ARCGIS REPORTS (v0.47.0) — every report rendered from those layers, one
//                       ArcGIS build per report, refreshed in place. Lives in
//                       ui-arcgis-reports.js.
//   REPORTS VS ARCGIS — every export EDITION (Excel and PDF rows) diffed against
//                       its report's ArcGIS build, as a by-day MATRIX (columns =
//                       exported days). The row picks the build up by itself; its
//                       header says what that build is as of and whether it came
//                       from the layers in the library now. Both sides are TSMIS,
//                       so they should agree; the build's as-of date sits beside
//                       the export day in the Notes.
//   CLEAN ROAD VS TSN — the CA HIGHWAYS build (as-of date + Build button) and
//                       the ArcGIS-vs-TSN comparison launcher (formulas/values
//                       checkboxes ride the same start flow as the classic
//                       Compare tab, including the overwrite confirmation).

let AG = null;                 // the last arcgis_status payload (Clean Road)
let AGM = null;                // the last arcgis_matrix_info payload
let AGL = null;                // the last arcgis_layers_info payload (Layers)
let agSub = "layers";          // which sub-tab is showing
let _agRenderSeq = 0;
let _aglRenderSeq = 0;
const aglSelected = new Set(); // layer names ticked for "Refresh selected"
let _aglSeen = null;           // the refresh progress the table last showed

// Read by applyMatrixWide (ui-compare.js): the matrix sub-tab goes full-width
// with its own config corner, like the other four matrices.
function arcgisMatrixActive() {
  return S.tab === "arcgis" && agSub === "reports";
}

// ---- Clean Road vs TSN ----------------------------------------------------- //
async function renderArcgis() {
  let st;
  try {
    st = await api.arcgis_status();
  } catch (e) {
    $("agHwyBuilt").textContent = "Status unavailable: " + e;
    return;
  }
  if (!st || st.error) {
    $("agHwyBuilt").textContent = (st && st.error) || "Status unavailable.";
    return;
  }
  AG = st;
  const hwy = st.highway || {};
  const built = hwy.built || {};
  $("agHwyMeta").textContent = built.exists
    ? `built${built.asof ? " as of " + built.asof : ""}`
    : "not built yet";
  $("agHwyBuilt").textContent = built.exists
    ? `Built workbook: ${built.path}`
      + (built.completion && built.completion !== "complete"
         ? `   ·   last build was ${built.completion}` : "")
    : "No built workbook yet — Build reads the staged layers and writes the "
      + "74-column THY-shaped workbook (with its per-column Provenance sheet).";
  const asof = $("agAsof");
  if (!asof.value && hwy.default_asof) asof.placeholder = hwy.default_asof + " (from the TSN extract)";
  $("btnAgBuild").disabled = !hwy.layers_ok;
  const compareBlockers = [];
  if (!built.exists) compareBlockers.push("build the workbook first");
  if (!hwy.tsn_raw) compareBlockers.push("stage the TSN CA HIGHWAYS extract in the TSN library (Settings → TSN reports)");
  $("btnAgCompare").disabled = compareBlockers.length > 0;
  $("agCompareHint").textContent = compareBlockers.length
    ? "To compare: " + compareBlockers.join("; ") + "."
    : "Compares the built workbook against the TSN extract; every column is "
      + "indexed back to its source layer in the Notes.";
  if (!hwy.layers_ok) {
    $("agCompareHint").textContent =
      `Missing highway layers: ${hwy.missing.join(", ")}`;
  }
  syncArcgisLock();      // final authority on the Build/Compare/Cancel button states
}

// M2-E: the Clean Road build/compare hold the single task lock, so a running one
// must disable Build+Compare and surface a Cancel button. Called on every state
// push (so the Cancel appears/disappears live) and at the end of renderArcgis;
// reads the cached `AG` status so it never needs an API call. The matrix sub-tab
// re-syncs its own lock-sensitive controls through updateArcgisMatrixProgress.
function syncArcgisLock() {
  const cancel = $("btnAgCancel");
  if (!cancel) return;
  const locked = !!(S.st && S.st.task);
  cancel.classList.toggle("hidden", !locked);
  cancel.disabled = !locked;
  const hwy = (AG && AG.highway) || {};
  const built = hwy.built || {};
  const build = $("btnAgBuild");
  if (build) build.disabled = locked || !hwy.layers_ok;
  const compare = $("btnAgCompare");
  if (compare) {
    const canCompare = !!(built.exists && hwy.tsn_raw && hwy.layers_ok);
    compare.disabled = locked || !canCompare;
  }
  if (agSub === "reports") updateArcgisMatrixProgress();
  if (agSub === "layers") updateArcgisLayersProgress();
  if (agSub === "builds") updateArcgisBuildsProgress();
}

// The tab's one entry point: render whichever sub-tab is showing (and apply
// the full-width matrix layout when it is the matrix).
function renderArcgisTab() {
  if (typeof applyMatrixWide === "function") applyMatrixWide();
  if (agSub === "layers") renderArcgisLayers();
  else if (agSub === "builds") renderArcgisBuilds();
  else if (agSub === "reports") renderArcgisMatrix();
  else renderArcgis();
}

// ---- sub-tabs ------------------------------------------------------------ //
const AG_SUBS = { layers: ["subAgLayers", "agLayers"], builds: ["subAgBuilds", "agBuilds"],
                  reports: ["subAgReports", "agReports"], cleanroad: ["subAgCleanRoad", "agCleanRoad"] };

function setArcgisSub(which) {
  agSub = AG_SUBS[which] ? which : "layers";
  Object.entries(AG_SUBS).forEach(([key, [btn, pane]]) => {
    const is = key === agSub;
    const b = $(btn), p = $(pane);
    if (b) { b.classList.toggle("active", is); b.setAttribute("aria-selected", String(is)); }
    if (p) p.classList.toggle("hidden", !is);
  });
  renderArcgisTab();
}

// ---- "Layers": the layer library + the in-app refresh (v0.46.0) ----------- //
function aglJobRunning() {
  const cur = S.st && S.st.matrix_current;
  return !!(cur && (cur.kind === "arcgis_refresh" || cur.kind === "arcgis_probe"));
}

function aglWhen(iso) {                // "2026-10-02T14:05:33" -> "2026-10-02 14:05"
  return iso ? String(iso).replace("T", " ").slice(0, 16) : "";
}

function aglSize(n) {
  if (typeof n !== "number" || !Number.isFinite(n)) return "";
  return n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`;
}

function aglProgressText(m) {
  if (m.phase === "probe") return "Checking ArcGIS Pro…";
  const at = Math.min((m.done || 0) + (m.row ? 1 : 0), m.total || 0);
  const el = typeof m.elapsed_s === "number" && m.elapsed_s >= 1 ? ` · ${fmtDur(m.elapsed_s)} elapsed` : "";
  return `Refreshing ${at} of ${m.total}${m.row ? " — " + m.row : ""}${el}`;
}

async function renderArcgisLayers() {
  const table = $("agLayersTable");
  if (!table) return;
  const seq = ++_aglRenderSeq;
  let info;
  try { info = await api.arcgis_layers_info(); } catch (e) {
    $("agLayersHint").textContent = "Status unavailable: " + e;
    return;
  }
  if (seq !== _aglRenderSeq || !info) return;   // a newer render started
  if (info.error) { $("agLayersHint").textContent = info.error; return; }
  AGL = info;
  const names = new Set((info.layers || []).map((l) => l.name));
  [...aglSelected].forEach((n) => { if (!names.has(n)) aglSelected.delete(n); });
  renderArcgisPro(info);
  renderArcgisLayerLibrary(info);
  renderArcgisLayerTable(info);
  updateArcgisLayersProgress();
}

function renderArcgisPro(info) {
  const pro = info.pro || {}, probe = info.last_probe;
  $("agProMeta").textContent = pro.found ? (pro.how === "chosen" ? "chosen python.exe" : "found") : "not found";
  let hint;
  if (pro.found) {
    hint = `The refresh runs in ArcGIS Pro's own Python: ${pro.python}`
      + (pro.how === "chosen" ? " (chosen by you)." : " (found automatically).");
    if (pro.chosen_missing) hint += " The python.exe chosen earlier is gone, so the one found automatically is used.";
  } else {
    hint = "ArcGIS Pro wasn't found on this PC. The refresh runs in ArcGIS Pro's own Python, "
      + "so it needs ArcGIS Pro installed and signed in. If it's installed somewhere unusual, "
      + "choose its python.exe (…\\bin\\Python\\envs\\arcgispro-py3\\python.exe).";
  }
  $("agProHint").textContent = hint;
  const chk = $("agProCheck");
  chk.className = "hint";
  if (!probe) {
    chk.textContent = pro.found ? "Not checked yet — Check ArcGIS Pro reads one small layer end to end (about a minute)." : "";
  } else {
    let t = `Last check ${aglWhen(probe.when)}: ${probe.message || (probe.ok ? "OK" : "failed")}`;
    const f = probe.facts || {};
    if (probe.ok) {
      if (f.portal) t += ` Signed in to ${f.portal}.`;
      if (probe.library_match === false) {
        const d = probe.library_diff || {};
        t += " Its columns differ from the library's copy"
          + ((d.added || []).length ? ` (new: ${d.added.join(", ")})` : "")
          + ((d.missing || []).length ? ` (gone: ${d.missing.join(", ")})` : "") + ".";
      }
      if (probe.dialect === "codes") t += " It writes domain codes rather than labels — the builds read both.";
    }
    chk.textContent = t;
    chk.classList.add(probe.ok ? "agl-ok" : "agl-err");
  }
  $("btnAgProAuto").classList.toggle("hidden", !pro.chosen);
}

function renderArcgisLayerLibrary(info) {
  const layers = info.layers || [];
  const stamps = layers.filter((l) => l.present && l.exported_at).map((l) => l.exported_at).sort();
  const meta = `${info.present || 0}/${info.expected || 0} layers` + (info.size ? ` · ${aglSize(info.size)}` : "");
  $("agLayersMeta").textContent = meta;
  let hint;
  if (!info.present) {
    hint = "No layers yet. Refresh all layers exports every TSMIS layer with ArcGIS Pro into this library.";
  } else {
    const oldest = aglWhen(stamps[0]), newest = aglWhen(stamps[stamps.length - 1]);
    hint = !stamps.length ? "The layers' export time is unknown."
      : (oldest.slice(0, 10) === newest.slice(0, 10) ? `Layers exported ${oldest}.`
        : `Layers exported between ${oldest} and ${newest} — a build reads as of its oldest layer.`);
  }
  hint += ` Refresh exports from ${info.service} with ArcGIS Pro and swaps each layer in as it `
    + "finishes; the ArcGIS reports built from the old layers then read out of date — "
    + "refresh them on ArcGIS reports.";
  $("agLayersHint").textContent = hint;
  const foot = [];
  const run = info.last_run;
  if (run && run.status && run.status !== "running") {
    foot.push(`Last refresh ${aglWhen(run.finished || run.started)}: ${String(run.message || run.status).split("\n")[0]}`);
  }
  if (info.present && !info.index_present) foot.push("00_INDEX.xlsx is missing — refresh the layers to write it.");
  if ((info.unknown || []).length) foot.push(`Not library layers (ignored): ${info.unknown.join(", ")}`);
  if (info.backup) foot.push("The files the last refresh replaced are kept in the _previous folder until the next refresh.");
  $("agLayersFoot").textContent = foot.join("  ·  ");
}

function aglStatus(l, m) {
  if (m && m.phase === "layers" && m.row === l.name && aglJobRunning())
    return { text: "exporting…", cls: "warn" };
  const last = l.last;
  if (!l.present && (!last || last.status !== "failed"))
    return { text: "missing — refresh it", cls: "warn" };
  if (!last) return { text: "", cls: "" };
  if (last.status === "exported") {
    const secs = typeof last.seconds === "number" ? ` in ${fmtDur(last.seconds) || "1s"}` : "";
    return { text: `refreshed${secs}` + (last.message ? ` · ${last.message}` : ""), cls: "ok" };
  }
  if (last.status === "failed") return { text: `failed: ${last.message || "see the log"}`, cls: "err" };
  if (last.status === "cancelled") return { text: "cancelled before it exported", cls: "warn" };
  if (last.status === "queued" || last.status === "exporting")
    return aglJobRunning() ? { text: "waiting…", cls: "" } : { text: "not finished — refresh it again", cls: "warn" };
  return { text: last.status, cls: "" };
}

function renderArcgisLayerTable(info) {
  const table = $("agLayersTable");
  const layers = info.layers || [];
  const locked = !!(S.st && S.st.task);
  const m = S.st && S.st.matrix;
  table.textContent = "";
  const cellDiv = (cls, text, title) => {
    const d = document.createElement("div");
    if (cls) d.className = cls;
    if (text != null) d.textContent = text;
    if (title) d.title = title;
    return d;
  };
  const head = document.createElement("div");
  head.className = "agl-row agl-head";
  const allBox = document.createElement("input");
  allBox.type = "checkbox";
  allBox.className = "agl-box";
  allBox.title = "Select every layer";
  allBox.checked = layers.length > 0 && layers.every((l) => aglSelected.has(l.name));
  allBox.disabled = locked;
  allBox.onchange = () => {
    layers.forEach((l) => (allBox.checked ? aglSelected.add(l.name) : aglSelected.delete(l.name)));
    renderArcgisLayerTable(AGL);
    updateArcgisLayersProgress();
  };
  const hc = cellDiv("agl-check");
  hc.appendChild(allBox);
  head.append(hc, cellDiv("", "Layer · read by"), cellDiv("num", "Rows"),
    cellDiv("", "Exported"), cellDiv("num", "Size"), cellDiv("", "Last refresh"));
  table.appendChild(head);
  layers.forEach((l) => {
    const row = document.createElement("div");
    const st = aglStatus(l, m);
    row.className = "agl-row" + (l.present ? "" : " missing")
      + (m && m.phase === "layers" && m.row === l.name && aglJobRunning() ? " active" : "");
    const box = document.createElement("input");
    box.type = "checkbox";
    box.className = "agl-box";
    box.checked = aglSelected.has(l.name);
    box.disabled = locked;
    box.title = `Select ${l.name}`;
    box.onchange = () => {
      if (box.checked) aglSelected.add(l.name); else aglSelected.delete(l.name);
      allBox.checked = layers.every((x) => aglSelected.has(x.name));
      updateArcgisLayersProgress();
    };
    const cc = cellDiv("agl-check");
    cc.appendChild(box);
    const users = (l.used_by || []).join(", ");
    const layer = cellDiv("agl-layer");
    layer.append(
      cellDiv("agl-name", l.name, l.file ? `${l.file}${l.source ? "\n" + l.source : ""}` : "not in the library"),
      cellDiv("agl-users", users || "not read by a build yet"));
    row.append(
      cc, layer,
      cellDiv("num", Number.isFinite(Number(l.rows)) && l.present ? Number(l.rows).toLocaleString() : ""),
      cellDiv("agl-when", aglWhen(l.exported_at), l.exported_by || ""),
      cellDiv("num", aglSize(l.size)),
      cellDiv("agl-status" + (st.cls ? " " + st.cls : ""), st.text, st.text));
    table.appendChild(row);
  });
}

// Called on every state push while the Layers sub-tab shows (no API call):
// the live progress line, the Cancel button, the lock-sensitive controls, and
// a table re-read whenever a layer finishes or the exporting layer changes.
function updateArcgisLayersProgress() {
  const locked = !!(S.st && S.st.task);
  const running = aglJobRunning();
  const m = (S.st && S.st.matrix) || null;
  const prog = $("agLayersProgress");
  if (prog) {
    const show = running && m && (m.phase === "layers" || m.phase === "probe");
    prog.hidden = !show;
    if (show) prog.textContent = aglProgressText(m);
  }
  const cancel = $("btnAgLayersCancel");
  if (cancel) { cancel.classList.toggle("hidden", !running); cancel.disabled = !running; }
  const all = $("btnAgRefreshAll"), sel = $("btnAgRefreshSel");
  if (all) all.disabled = locked;
  if (sel) {
    sel.disabled = locked || aglSelected.size === 0;
    sel.lastChild.textContent = aglSelected.size ? `Refresh selected (${aglSelected.size})` : "Refresh selected";
  }
  ["btnAgProCheck", "btnAgProChoose", "btnAgProAuto"].forEach((id) => {
    const b = $(id);
    if (b) b.disabled = locked;
  });
  document.querySelectorAll("#agLayersTable .agl-box").forEach((b) => { b.disabled = locked; });
  const seen = running && m ? `${m.phase}:${m.done}:${m.row || ""}` : "idle";
  if (AGL && seen !== _aglSeen) {
    const first = _aglSeen === null;
    _aglSeen = seen;
    if (!first) renderArcgisLayers();
  }
}

async function aglRefresh(names) {
  const r = await api.refresh_arcgis_layers(names);
  if (r && r.error) { showMessage("error", "Can't refresh", r.error); return false; }
  return true;
}

// ---- "Reports vs ArcGIS": the ArcGIS-side card -------------------------- //
// Which ArcGIS build each report's rows are compared with right now — a chip
// per report that has a build, warning-coloured when it is missing or from
// older layers. Clicking one opens the ArcGIS reports sub-tab.
function renderArcgisLibrary(lib) {
  const drop = lib.drop || {};
  const builds = Object.values(lib.builds || {}).filter((b) => b.available);
  const built = builds.filter((b) => b.built);
  $("agLibMeta").textContent = `${built.length} of ${builds.length} ArcGIS report${builds.length === 1 ? "" : "s"} built`
    + (drop.exported ? ` · layers exported ${drop.exported}` : "");
  const stale = built.filter((b) => b.stale).length;
  $("agLibHint").textContent = !lib.staged
    ? "No layers yet — refresh them on the Layers tab, then build the ArcGIS reports."
    : stale
      ? `${stale} ArcGIS report${stale > 1 ? "s were" : " was"} built from older layers — refresh `
        + `${stale > 1 ? "them" : "it"} on ArcGIS reports, then rebuild the stale comparisons.`
      : "Every row — Excel and PDF alike — is compared with the newest ArcGIS build of its "
        + "report, picked up automatically.";
  const chips = $("agLibIssues");
  chips.textContent = "";
  builds.forEach((b) => {
    const line = agBuildLine(b);
    const chip = document.createElement("button");
    chip.className = "agb-chip" + (line.cls ? " " + line.cls : "");
    chip.textContent = `${b.label} — ${line.text}`;
    chip.title = line.text + (b.path ? `\n${b.path}` : "") + "\nOpen ArcGIS reports";
    chip.onclick = () => setArcgisSub("builds");
    chips.appendChild(chip);
  });
}

// A report's ArcGIS build as a short line: {text, cls}. Warning colour when it
// is missing, from older layers or its outcome is unknown; success when current.
function agBuildLine(b) {
  if (!b || !b.available) return { text: "no ArcGIS build yet", cls: "" };
  if (!b.built) {
    const missing = (b.missing_layers || []).length;
    return { text: missing ? `not built · ${missing} layer${missing > 1 ? "s" : ""} missing` : "not built yet",
             cls: "warn" };
  }
  const asof = b.asof ? `as of ${b.asof}` : "as-of unknown";
  if (b.stale_reason === "outcome_untrusted") return { text: `${asof} · outcome unknown — refresh it`, cls: "warn" };
  if (b.stale_reason === "drop_changed") return { text: `${asof} · from older layers — refresh it`, cls: "warn" };
  return { text: `${asof} · current layers`, cls: "ok" };
}

// A matrix row header's second line: what the row is compared with.
function agRowSideLine(rk, b, supported) {
  if (!supported) {
    if (!b || !b.available) return { text: "no ArcGIS build yet", cls: "" };
    const ed = (b.editions || []).find((e) => e.key === rk);
    return { text: b.comparable && ed && !ed.comparable ? "edition not consolidated yet"
                                                        : "comparison not wired yet", cls: "" };
  }
  if (!b || !b.built) return { text: "no ArcGIS build yet — build it", cls: "warn" };
  const asof = b.asof ? `vs ArcGIS as of ${b.asof}` : "vs ArcGIS (as-of unknown)";
  if (b.stale_reason === "outcome_untrusted") return { text: "ArcGIS build outcome unknown", cls: "warn" };
  if (b.stale_reason === "drop_changed") return { text: `${asof} · older layers`, cls: "warn" };
  return { text: asof, cls: "ok" };
}

async function agBuildReport(rk) {
  const r = await api.build_arcgis_report(rk, "");
  if (r && r.error) showMessage("error", "Can't build", r.error);
}

// ---- "Reports vs ArcGIS": the matrix -------------------------------------- //
function syncArcgisMatrixFormulas() {
  syncFormulasToggle("agMatrixFormulas", "arcgis_matrix_formulas");
}

async function renderArcgisMatrix() {
  const grid = $("agMatrixGrid");
  if (!grid) return;
  const seq = ++_agRenderSeq;
  let snap;
  try { snap = await api.arcgis_matrix_info(); } catch (e) {
    $("agLibHint").textContent = "Status unavailable: " + e;
    return;
  }
  if (seq !== _agRenderSeq) return;      // a newer render started; drop this one
  if (!snap) return;
  if (snap.error) { $("agLibHint").textContent = snap.error; return; }
  AGM = snap;
  const days = snap.days || [], locked = !!(S.st && S.st.task);
  const lib = snap.library || {};
  const builds = lib.builds || {};
  renderArcgisLibrary(lib);

  const srcSel = $("agMatrixSource");
  if (srcSel) {
    srcSel.textContent = "";
    (snap.sources || []).forEach((s) => {
      const o = document.createElement("option");
      o.value = s.key; o.textContent = s.label;
      if (s.key === snap.source) o.selected = true;
      srcSel.appendChild(o);
    });
    srcSel.disabled = locked;
    srcSel.onchange = async () => {
      const r = await api.set_arcgis_matrix_source(srcSel.value);
      if (r && r.error) showMessage("error", "Can't set source", r.error);
      await renderArcgisMatrix();
    };
  }

  const addSel = $("agMatrixAddDay"), addBtn = $("btnAgAddDay");
  const avail = (snap.available_days || []).filter((d) => !days.includes(d));
  if (addSel) {
    addSel.textContent = "";
    if (!avail.length) {
      const o = document.createElement("option");
      o.value = ""; o.textContent = days.length ? "— no more exported days —" : "— no exported days —";
      addSel.appendChild(o);
    } else {
      avail.forEach((d) => {
        const o = document.createElement("option"); o.value = d; o.textContent = mxDayOptionText(d, snap);
        addSel.appendChild(o);
      });
    }
    addSel.disabled = locked || !avail.length;
  }
  if (addBtn) {
    addBtn.disabled = locked || !avail.length;
    addBtn.onclick = () => mxBusyClick(addBtn, async () => {
      const d = $("agMatrixAddDay").value;
      if (!d) return;
      const r = await api.add_arcgis_matrix_day(d);
      if (r && r.error) showMessage("error", "Can't add day", r.error);
      await renderArcgisMatrix();
    });
  }

  const rtog = $("agMatrixReportToggles");
  if (rtog) {
    rtog.textContent = "";
    const hidden = new Set(snap.hidden || []);
    (snap.all_rows || []).forEach((r) => {
      const isOn = !hidden.has(r.key);
      rtog.appendChild(mxToggleChip(r.label, isOn,
        (isOn ? "Hide " : "Show ") + r.label + (r.supported ? "" : " (not available yet)"), locked,
        (next) => api.set_arcgis_matrix_report(r.key, next), renderArcgisMatrix));
    });
  }

  grid.textContent = "";
  if (!days.length) {
    grid.style.gridTemplateColumns = ""; grid.style.gridTemplateRows = "";
    const empty = document.createElement("div");
    empty.className = "dm-empty";
    empty.textContent = "Add an export day from Matrix options to compare each export — "
      + "Excel and PDF — against its report's ArcGIS build. The builds live on ArcGIS reports.";
    grid.appendChild(empty);
    wireArcgisMatrixFooter();
    updateArcgisMatrixProgress();
    return;
  }
  grid.style.gridTemplateColumns = `minmax(230px,1.3fr) repeat(${days.length}, minmax(120px,1fr))`;
  // Rows that cannot compare yet stay listed (the whole report set is visible)
  // but compact, so the live rows keep the room.
  const rowSupported = snap.row_supported || {};
  grid.style.gridTemplateRows = ["auto"].concat(snap.rows.map((rk) =>
    rowSupported[rk] ? "minmax(50px,1fr)" : "minmax(34px,auto)")).join(" ");

  const corner = document.createElement("div");
  corner.className = "mx-cell mx-corner mx-colhead";
  corner.textContent = "Report \\ Day";
  grid.appendChild(corner);
  days.forEach((d) => {
    const h = document.createElement("div");
    h.className = "mx-cell mx-colhead";
    const lab = document.createElement("div"); lab.className = "dnd-handle";
    lab.textContent = d;
    h.appendChild(lab);
    const btns = document.createElement("span"); btns.className = "mxch-btns";
    btns.append(
      mxHeadBtn("i-compare", `Rebuild every report for ${d} (vs the layer builds)`, "mxch-rebuild",
        async () => {
          const r = await api.rebuild_arcgis_matrix("all", null, d);
          if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells in this day — build the ArcGIS reports first (ArcGIS reports).");
          else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
        }),
      mxHeadBtn("i-trash", `Remove the ${d} column`, "mxch-rm", async () => {
        await api.remove_arcgis_matrix_day(d); await renderArcgisMatrix();
      }));
    h.appendChild(btns);
    dndAttach(h, h, d, "ag-day", "x", () => days.slice(), async (order) => {
      const r = await api.set_arcgis_matrix_day_order(order);
      if (r && r.error) showMessage("error", "Can't reorder", r.error);
      else await renderArcgisMatrix();
    });
    grid.appendChild(h);
  });

  const families = snap.row_family || {};
  snap.rows.forEach((rk) => {
    const rlabel = snap.row_labels[rk] || rk;
    const b = builds[families[rk] || rk] || {};      // the report's ArcGIS build
    const supported = !!rowSupported[rk];
    const rh = document.createElement("div");
    rh.className = "mx-cell mx-rowhead" + (supported ? "" : " agm-off");
    rh.dataset.rk = rk; rh.dataset.label = rlabel;
    const top = document.createElement("div"); top.className = "mxrh-top";
    const lbl = document.createElement("span"); lbl.className = "mxrh-label";
    lbl.textContent = rlabel;
    top.appendChild(lbl);
    if (supported) {
      top.appendChild(mxHeadBtn("i-compare", `Rebuild ${rlabel} for every day (vs its ArcGIS build)`,
        "mxch-rebuild", async () => {
          const r = await api.rebuild_arcgis_matrix("all", rk, null);
          if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells in this row — build the report on ArcGIS reports and add an exported day.");
          else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
        }));
    }
    rh.appendChild(top);
    // What the row is compared with: its report's ONE ArcGIS build, picked up
    // by itself (built and refreshed on ArcGIS reports) — or why it can't be yet.
    const line = agRowSideLine(rk, b, supported);
    const bl = document.createElement("div");
    bl.className = "mxrh-build" + (line.cls ? " " + line.cls : "");
    const bt = document.createElement("span"); bt.className = "mxrh-buildtext";
    const meta = (snap.all_rows || []).find((r) => r.key === rk);
    bt.textContent = line.text;
    bt.title = line.text + (b.path ? `\n${b.path}` : "") + (meta && meta.why ? `\n${meta.why}` : "");
    bl.appendChild(bt);
    if (b.built) {
      bl.appendChild(mxHeadBtn("i-external", `Open the ${b.label || rlabel} ArcGIS build`, "mxch-open", async () => {
        const r = await api.open_arcgis_report(rk);
        if (r && r.error) showMessage("error", "Can't open", r.error);
      }));
    }
    rh.appendChild(bl);
    dndAttach(rh, top, rk, "ag-row", "y", () => snap.rows.slice(), async (order) => {
      const r = await api.set_arcgis_matrix_row_order(order);
      if (r && r.error) showMessage("error", "Can't reorder", r.error);
      else await renderArcgisMatrix();
    });
    grid.appendChild(rh);
    days.forEach((d) => {
      const c = snap.cells[rk][d], cmp = c.cmp || {};
      const cell = document.createElement("div"); cell.className = "mx-cell";
      const main = document.createElement("div"); main.className = "mx-num";
      const sub = document.createElement("div"); sub.className = "mx-sub";
      let v = mxCellContent(cmp);
      // Neither the build nor the export is there: say both, in this matrix's words.
      if (cmp.missing_side === "both" && !cmp.last_attempt)
        v = { cls: "mx-missing", main: "needs ArcGIS", sub: "no ArcGIS build · not exported" };
      cell.classList.add(v.cls); main.textContent = v.main; sub.textContent = v.sub;
      if (v.warn) cell.classList.add(v.warn);
      const ed = c.export || {};
      const edWhen = ed.present
        ? `${fmtAge(ed.age_seconds)}${ed.subdir ? " (" + ed.subdir + ")" : ""}`
        : "not exported";
      cell.title = `${rlabel} — ${d} vs its ArcGIS build\nExport: ${edWhen}`
        + (b.built ? `\nArcGIS build: ${agBuildLine(b).text}` : "")
        + (v.title ? `\n⚠ ${v.title}` : "");
      cell.append(main, sub);
      const acts = document.createElement("div"); acts.className = "mx-actions";
      if (supported && b.available && !b.built) {
        acts.appendChild(mxActBtn("i-layers", `Build the ${b.label || rlabel} ArcGIS report`,
          locked, () => agBuildReport(rk)));
      }
      if (cmp.supported && !cmp.missing_side) {
        acts.appendChild(mxActBtn("i-compare", "Build / rebuild this comparison",
          false, async () => {
            const r = await api.build_arcgis_matrix_cell(rk, d);
            if (r && r.error) showMessage("error", "Can't build", r.error);
          }));
      }
      if (cmp.built) {
        const ob = mxActBtn("i-external", "Open this comparison workbook (values copy)",
          false, async () => {
            const r = await api.open_arcgis_cell_comparison(rk, d);
            if (r && r.error) showMessage("error", "Can't open", r.error);
          });
        ob.classList.add("mx-open"); acts.appendChild(ob);
      }
      cell.appendChild(acts);
      grid.appendChild(cell);
    });
  });

  wireArcgisMatrixFooter();
  updateArcgisMatrixProgress();
}

function wireArcgisMatrixFooter() {
  const ba = $("btnAgMxBuildAll");
  if (ba) ba.onclick = async () => {
    const r = await api.rebuild_arcgis_matrix("all");
    if (r && r.nothing) showMessage("info", "Nothing to compare", "Build the ArcGIS reports (ArcGIS reports) and add an exported day first.");
    else if (r && r.error) showMessage("error", "Can't compare", r.error);
  };
  const rb = $("btnAgMxRebuildAll");
  if (rb) rb.onclick = async () => {
    const r = await api.rebuild_arcgis_matrix("stale");
    if (r && r.nothing) showMessage("info", "Up to date", "Every Reports-vs-ArcGIS comparison is current.");
    else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
  };
  const of = $("btnAgMxOpenComparisons");
  if (of) of.onclick = async () => {
    const r = await api.open_arcgis_comparisons_folder();
    if (r && r.error) showMessage("error", "Can't open", r.error);
  };
  const cb = $("btnAgMxCancel");
  if (cb) cb.onclick = () => api.cancel_run();
}

function updateArcgisMatrixProgress() {
  const el = $("agMatrixProgress");
  if (el) {
    const m = S.st && S.st.matrix;
    if (m && m.total) {
      el.hidden = false;
      el.textContent = m.phase === "building" ? agbProgressText(m)
        : (m.phase === "layers" || m.phase === "probe") ? aglProgressText(m)
        : mxProgressText(m);
    } else el.hidden = true;
  }
  const locked = !!(S.st && S.st.task);
  document.querySelectorAll(
    "#agMatrixSource, #agMatrixReportToggles .mx-toggle, #agMatrixGrid .mxrh-top .mxch-rebuild")
    .forEach((c) => { c.disabled = locked; });
  const addSel = $("agMatrixAddDay"), addBtn = $("btnAgAddDay");
  const noAvail = !addSel || !addSel.querySelector('option[value]:not([value=""])');
  if (addSel) addSel.disabled = locked || noAvail;
  if (addBtn) addBtn.disabled = locked || noAvail;
  const cancel = $("btnAgMxCancel");
  if (cancel) {
    const running = !!(S.st && S.st.task === "matrix");
    cancel.classList.toggle("hidden", !running);
    cancel.disabled = !running;
  }
  renderQueuePanel("agQueueGroup", "agQueue", "agQueueCount");
  syncArcgisMatrixFormulas();
}

function bindArcgis() {
  $("subAgLayers").onclick = () => setArcgisSub("layers");
  $("subAgCleanRoad").onclick = () => setArcgisSub("cleanroad");
  $("subAgReports").onclick = () => setArcgisSub("reports");
  bindArcgisBuilds();
  $("btnAgGoBuilds").onclick = () => setArcgisSub("builds");
  $("btnAgRefreshAll").onclick = async () => {
    const n = (AGL && AGL.expected) || 40;
    const ok = await showConfirm({
      title: `Refresh all ${n} layers?`,
      message: "ArcGIS Pro exports every TSMIS layer from the service and the app swaps each one "
        + "in as it finishes. The whole library takes about an hour and a half — County Code "
        + "and City alone take over an hour of it. The ArcGIS reports built from the current "
        + "layers read out of date afterwards; refresh them on ArcGIS reports.",
      confirmLabel: "Refresh",
    });
    if (ok) await aglRefresh([]);
  };
  $("btnAgRefreshSel").onclick = async () => {
    if (!aglSelected.size) return;
    if (await aglRefresh([...aglSelected])) { aglSelected.clear(); renderArcgisLayers(); }
  };
  $("btnAgProCheck").onclick = async () => {
    const r = await api.check_arcgis_pro();
    if (r && r.error) showMessage("error", "Can't check ArcGIS Pro", r.error);
  };
  $("btnAgProChoose").onclick = async () => {
    const r = await api.choose_arcgis_python();
    if (r && r.error) showMessage("error", "Not ArcGIS Pro's Python", r.error);
    if (r && !r.cancelled) renderArcgisLayers();
  };
  $("btnAgProAuto").onclick = async () => {
    await api.clear_arcgis_python();
    renderArcgisLayers();
  };
  $("btnAgLayersOpen").onclick = () => api.open_arcgis_layers_folder();
  $("btnAgLayersCancel").onclick = () => api.cancel_run();
  $("btnAgOpenOut").onclick = () => api.open_arcgis_output_folder();
  $("btnAgCancel").onclick = () => api.cancel_run();
  $("btnAgBuild").onclick = async () => {
    const r = await api.start_arcgis_build($("agAsof").value.trim());
    if (r && r.error) showMessage("error", "Can't build", r.error);
  };
  $("btnAgCompare").onclick = async () => {
    const r = await api.start_arcgis_compare(
      $("agWantFormulas").checked, $("agWantValues").checked);
    if (!r) return;
    if (r.error) { showMessage("error", "Can't compare", r.error); return; }
    // The derived values twin already exists: same confirmation flow as the
    // classic Compare tab (token-bound, single-use).
    if (r.confirm_required) {
      const ok = await showConfirm({
        title: "Overwrite the values workbook?",
        message: r.message,
        confirmLabel: "Overwrite",
      });
      const cr = await api.confirm_compare_overwrite(r.confirm_token, !!ok);
      if (cr && cr.error) showMessage("error", "Can't compare", cr.error);
    }
  };
}
