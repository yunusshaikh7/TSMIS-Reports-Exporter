// ArcGIS tab module (v0.29.0, split like the other ui-*.js — same global scope).
// Two sub-tabs; "Reports vs layers" is the main one since 2026-09-02:
//   REPORTS VS LAYERS — every TSMIS report rendered from the layer library and
//                       diffed against our own export of it, as a by-day MATRIX
//                       (rows = the registry's reports, columns = exported days).
//                       ONE layer build per report, like the TSN library: the
//                       library card names the staged drop (export date +
//                       content fingerprint) and each row header says whether
//                       its build is from that drop, with Build / Open buttons.
//                       Both sides are TSMIS, so they should agree; the build's
//                       as-of date sits beside the export day in the Notes.
//   CLEAN ROAD VS TSN — the CA HIGHWAYS build (as-of date + Build button) and
//                       the ArcGIS-vs-TSN comparison launcher (formulas/values
//                       checkboxes ride the same start flow as the classic
//                       Compare tab, including the overwrite confirmation).

let AG = null;                 // the last arcgis_status payload (Clean Road)
let AGM = null;                // the last arcgis_matrix_info payload
let agSub = "reports";         // which sub-tab is showing
let _agRenderSeq = 0;

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
}

// The tab's one entry point: render whichever sub-tab is showing (and apply
// the full-width matrix layout when it is the matrix).
function renderArcgisTab() {
  if (typeof applyMatrixWide === "function") applyMatrixWide();
  if (agSub === "reports") renderArcgisMatrix();
  else renderArcgis();
}

// ---- sub-tabs ------------------------------------------------------------ //
function setArcgisSub(which) {
  agSub = which;
  const on = (id, is) => {
    const el = $(id);
    if (!el) return;
    el.classList.toggle("active", is);
    el.setAttribute("aria-selected", String(is));
  };
  on("subAgCleanRoad", which === "cleanroad");
  on("subAgReports", which === "reports");
  const cr = $("agCleanRoad"), rp = $("agReports");
  if (cr) cr.classList.toggle("hidden", which !== "cleanroad");
  if (rp) rp.classList.toggle("hidden", which !== "reports");
  renderArcgisTab();
}

// ---- "Reports vs layers": the library card ------------------------------- //
function renderArcgisLibrary(lib) {
  const drop = lib.drop || {};
  const staged = lib.staged || 0, expected = lib.expected || 0;
  $("agLibMeta").textContent = drop.exported
    ? `drop exported ${drop.exported} · ${staged}/${expected} layers`
    : `${staged}/${expected} layers staged`;
  const bits = [];
  if (staged && !lib.index_present) bits.push("00_INDEX.xlsx is missing — copy the export's manifest in with the layers.");
  if ((lib.missing || []).length) bits.push(`Missing: ${lib.missing.join(", ")}`);
  if ((lib.unknown || []).length) bits.push(`Not in the manifest (ignored): ${lib.unknown.join(", ")}`);
  const fp = drop.fingerprint ? String(drop.fingerprint) : "";
  let hint;
  if (!staged) {
    hint = "Drop the per-layer .xlsx exports plus the export's 00_INDEX.xlsx manifest in the layers folder.";
  } else {
    hint = drop.exported
      ? `Staged drop exported ${drop.exported_at || drop.exported}`
        + (drop.exported_source === "files" ? " (from the file dates — the manifest carries no timestamp)" : "")
      : "The staged drop's export date is unknown";
    hint += (fp ? ` · fingerprint …${fp.slice(-10)}` : "")
      + ". Every build records the drop it came from; a row built from another drop reads stale.";
  }
  $("agLibHint").textContent = hint;
  const issues = $("agLibIssues");
  issues.innerHTML = "";
  bits.forEach((t) => {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = t;
    issues.appendChild(p);
  });
  const asof = $("agMxAsof");
  if (asof && !asof.value) asof.placeholder = drop.exported ? `${drop.exported} (the drop's export date)` : "YYYY-MM-DD";
}

// One row's build state as a short line: {text, cls}. Warning colour when the
// build is from another drop or its outcome is unknown, success when current.
function agBuildLine(b) {
  if (!b || !b.available) return { text: (b && b.why) || "no build yet", cls: "" };
  if (!b.built) {
    const missing = (b.missing_layers || []).length;
    return { text: missing ? `not built · ${missing} layer${missing > 1 ? "s" : ""} missing` : "not built yet", cls: "" };
  }
  const asof = b.asof ? `as of ${b.asof}` : "as-of unknown";
  const rows = Number.isFinite(Number(b.rows)) && Number(b.rows) > 0
    ? ` · ${Number(b.rows).toLocaleString()} rows` : "";
  if (b.stale_reason === "outcome_untrusted")
    return { text: `built ${asof}${rows} · outcome unknown — rebuild`, cls: "warn" };
  if (b.stale_reason === "drop_changed")
    return { text: `built ${asof}${rows} · from ${b.drop_exported ? "the " + b.drop_exported + " drop" : "an older drop"} — rebuild`,
             cls: "warn" };
  const partial = b.completion === "partial" ? " · partial" : "";
  return { text: `built ${asof}${rows}${partial} · current drop`, cls: "ok" };
}

async function agBuildReport(rk) {
  const box = $("agMxAsof");
  const r = await api.build_arcgis_report(rk, box ? box.value.trim() : "");
  if (r && r.error) showMessage("error", "Can't build", r.error);
}

// ---- "Reports vs layers": the matrix -------------------------------------- //
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
        (isOn ? "Hide " : "Show ") + r.label + (r.supported ? "" : " (no build yet)"), locked,
        (next) => api.set_arcgis_matrix_report(r.key, next), renderArcgisMatrix));
    });
  }

  grid.textContent = "";
  if (!days.length) {
    grid.style.gridTemplateColumns = ""; grid.style.gridTemplateRows = "";
    const empty = document.createElement("div");
    empty.className = "dm-empty";
    empty.textContent = "Add an export day from Matrix options to compare each report's "
      + "layer build against that day's export. Build a report from the layers with "
      + "the ▤ button on its row.";
    grid.appendChild(empty);
    wireArcgisMatrixFooter();
    updateArcgisMatrixProgress();
    return;
  }
  grid.style.gridTemplateColumns = `minmax(230px,1.3fr) repeat(${days.length}, minmax(120px,1fr))`;
  grid.style.gridTemplateRows = `auto repeat(${snap.rows.length}, minmax(50px,1fr))`;

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
          if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells in this day — build the reports from the layers first.");
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

  snap.rows.forEach((rk) => {
    const rlabel = snap.row_labels[rk] || rk;
    const b = builds[rk] || {};
    const supported = !!(snap.row_supported || {})[rk];
    const rh = document.createElement("div"); rh.className = "mx-cell mx-rowhead";
    rh.dataset.rk = rk; rh.dataset.label = rlabel;
    const top = document.createElement("div"); top.className = "mxrh-top";
    const lbl = document.createElement("span"); lbl.className = "mxrh-label";
    lbl.textContent = rlabel;
    top.appendChild(lbl);
    if (supported) {
      top.appendChild(mxHeadBtn("i-compare", `Rebuild ${rlabel} for every day (vs the layer build)`,
        "mxch-rebuild", async () => {
          const r = await api.rebuild_arcgis_matrix("all", rk, null);
          if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells in this row — build the report from the layers and add an exported day.");
          else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
        }));
    }
    rh.appendChild(top);
    // The row's ONE layer build: state line + build / open buttons.
    const line = agBuildLine(b);
    const bl = document.createElement("div");
    bl.className = "mxrh-build" + (line.cls ? " " + line.cls : "");
    const bt = document.createElement("span"); bt.className = "mxrh-buildtext";
    bt.textContent = line.text; bt.title = line.text + (b.path ? `\n${b.path}` : "");
    bl.appendChild(bt);
    if (b.available) {
      const bb = mxHeadBtn("i-layers", b.built ? `Rebuild ${rlabel} from the layers` : `Build ${rlabel} from the layers`,
        "mxch-rebuild", () => agBuildReport(rk));
      bb.disabled = locked;
      bl.appendChild(bb);
    }
    if (b.built) {
      bl.appendChild(mxHeadBtn("i-external", `Open the ${rlabel} layer build`, "mxch-open", async () => {
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
        v = { cls: "mx-missing", main: "needs build", sub: "not built · not exported" };
      cell.classList.add(v.cls); main.textContent = v.main; sub.textContent = v.sub;
      if (v.warn) cell.classList.add(v.warn);
      const ed = c.export || {};
      const edWhen = ed.present
        ? `${fmtAge(ed.age_seconds)}${ed.subdir ? " (" + ed.subdir + ")" : ""}`
        : "not exported";
      cell.title = `${rlabel} — ${d} vs the layer build\nExport: ${edWhen}`
        + (b.built ? `\nLayer build: ${agBuildLine(b).text}` : "")
        + (v.title ? `\n⚠ ${v.title}` : "");
      cell.append(main, sub);
      const acts = document.createElement("div"); acts.className = "mx-actions";
      if (supported && b.available && !b.built) {
        acts.appendChild(mxActBtn("i-layers", `Build ${rlabel} from the layers`,
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
    if (r && r.nothing) showMessage("info", "Nothing to compare", "Build a report from the layers and add an exported day first.");
    else if (r && r.error) showMessage("error", "Can't compare", r.error);
  };
  const rb = $("btnAgMxRebuildAll");
  if (rb) rb.onclick = async () => {
    const r = await api.rebuild_arcgis_matrix("stale");
    if (r && r.nothing) showMessage("info", "Up to date", "Every Reports-vs-layers comparison is current.");
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
      el.textContent = m.phase === "building"
        ? `Building from the layers${m.row ? " — " + m.row : ""}…`
        : mxProgressText(m);
    } else el.hidden = true;
  }
  const locked = !!(S.st && S.st.task);
  document.querySelectorAll(
    "#agMatrixSource, #agMatrixReportToggles .mx-toggle, #agMatrixGrid .mxrh-build .mxch-rebuild")
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
  $("subAgCleanRoad").onclick = () => setArcgisSub("cleanroad");
  $("subAgReports").onclick = () => setArcgisSub("reports");
  $("btnAgRepOpenOut").onclick = () => api.open_arcgis_reports_folder();
  $("btnAgOpenLayers").onclick = () => api.open_arcgis_layers_folder();
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
