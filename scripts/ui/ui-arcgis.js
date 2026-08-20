// ArcGIS tab module (v0.29.0, split like the other ui-*.js — same global scope).
// Two sub-tabs (v0.39.0):
//   CLEAN ROAD    — the layer-library status card, the CA HIGHWAYS build (as-of
//                   date + Build button), and the ArcGIS-vs-TSN comparison
//                   launcher (formulas/values checkboxes ride the same start
//                   flow as the classic Compare tab, including the derived-
//                   values overwrite confirmation).
//   REPORTS       — the same layers rendered as a TSMIS report and diffed
//                   against our own export of it. Because that comparison is
//                   TSMIS vs TSMIS, the card leads with the VINTAGE question:
//                   the build's as-of date beside the export day, and a loud
//                   line when they differ (across a gap the comparison measures
//                   network change, not correctness).

let AG = null;                 // the last arcgis_status payload
let AGR = null;                // the last arcgis_report_status payload
let agSub = "cleanroad";       // which sub-tab is showing

async function renderArcgis() {
  let st;
  try {
    st = await api.arcgis_status();
  } catch (e) {
    $("agLibHint").textContent = "Status unavailable: " + e;
    return;
  }
  if (!st || st.error) {
    $("agLibHint").textContent = (st && st.error) || "Status unavailable.";
    return;
  }
  AG = st;
  $("agLibMeta").textContent = `${st.staged}/${st.expected} layers staged`;
  const bits = [];
  if (!st.index_present) bits.push("00_INDEX.xlsx is missing — copy the export's manifest in with the layers.");
  if (st.missing.length) bits.push(`Missing: ${st.missing.join(", ")}`);
  if (st.unknown.length) bits.push(`Not in the manifest (ignored): ${st.unknown.join(", ")}`);
  $("agLibHint").textContent = bits.length
    ? "One .xlsx per layer, plus the export's 00_INDEX.xlsx manifest."
    : "Complete — every manifest layer is staged, with the INDEX manifest.";
  const issues = $("agLibIssues");
  issues.innerHTML = "";
  bits.forEach((t) => {
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = t;
    issues.appendChild(p);
  });

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

// M2-E: the ArcGIS build/compare hold the single task lock, so a running one must
// disable Build+Compare and surface a Cancel button. Called on every state push (so
// the Cancel appears/disappears live) and at the end of renderArcgis; reads the
// cached `AG` status so it never needs an API call.
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

  // Reports sub-tab — same rule, its own readiness (cached, no API call).
  const rsrc = (AGR && AGR.source) || {}, rbuilt = (AGR && AGR.built) || {};
  const rdays = (AGR && AGR.days) || [];
  const rbuild = $("btnAgRepBuild");
  if (rbuild) rbuild.disabled = locked || !rsrc.exists;
  const rcmp = $("btnAgRepCompare");
  if (rcmp) rcmp.disabled = locked || !(rbuilt.exists && rdays.length);
  const rday = $("agRepDay");
  if (rday) rday.disabled = locked || !rdays.length;
  const rcancel = $("btnAgRepCancel");
  if (rcancel) {
    rcancel.classList.toggle("hidden", !locked);
    rcancel.disabled = !locked;
  }
}

// The tab's one entry point: refresh the clean-road card (it owns the shared
// lock sync) and, when the reports sub-tab is the one showing, its card too.
function renderArcgisTab() {
  renderArcgis();
  if (agSub === "reports") renderArcgisReports();
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
  if (which === "reports") renderArcgisReports();
}

// ---- "Reports vs layers" -------------------------------------------------- //
async function renderArcgisReports() {
  let st;
  try {
    st = await api.arcgis_report_status();
  } catch (e) {
    $("agRepSource").textContent = "Status unavailable: " + e;
    return;
  }
  if (!st || st.error) {
    $("agRepSource").textContent = (st && st.error) || "Status unavailable.";
    return;
  }
  AGR = st;
  const src = st.source || {}, built = st.built || {};

  $("agRepSourceMeta").textContent = src.exists
    ? (src.asof ? "as of " + src.asof : "built") : "not built yet";
  $("agRepSource").textContent = src.exists
    ? `This report's own source table, built from the layers it prints.`
      + `   ·   ${src.path}`
    : "Not built yet — Build makes it from the ArcGIS layers. This report has "
      + "its own build and does not read the Clean Road workbook.";

  $("agRepHdMeta").textContent = built.exists
    ? `${Number(built.rows || 0).toLocaleString()} records`
      + (built.asof ? " · as of " + built.asof : "")
    : "not built yet";
  $("agRepHdBuilt").textContent = built.exists
    ? `Built: ${built.path}`
      + (built.merged_away
         ? `   ·   ${Number(built.merged_away).toLocaleString()} CA HIGHWAYS rows merged `
           + `(they split only on columns Highway Detail doesn't print)` : "")
    : "Not built yet — Build renders the layers as Highway Detail's own 34 columns.";

  // The as-of box defaults to the export day, because a same-date pair is the
  // only kind that measures correctness rather than network change.
  const asofBox = $("agRepAsof");
  if (asofBox && !asofBox.value && built.asof) asofBox.value = built.asof;

  // Export-day picker: only days whose Highway Detail is CONSOLIDATED.
  const sel = $("agRepDay");
  const days = st.days || [];
  const keep = sel.value;
  sel.textContent = "";
  if (!days.length) {
    const o = document.createElement("option");
    o.value = ""; o.textContent = "no consolidated Highway Detail export";
    sel.appendChild(o);
  } else {
    days.forEach((d) => {
      const o = document.createElement("option");
      o.value = d.day; o.textContent = d.day;
      sel.appendChild(o);
    });
    if (days.some((d) => d.day === keep)) sel.value = keep;
  }

  // The vintage line — the first thing that makes this comparison honest.
  const day = sel.value, asof = built.asof || (src.exists ? src.asof : "");
  if (asofBox && !asofBox.value && day) asofBox.value = day;
  const vint = $("agRepVintage");
  if (!day || !asof) {
    vint.textContent = "";
    vint.classList.remove("warn");
  } else if (asof === day) {
    vint.textContent = `Same date on both sides (${asof}) — differences are real `
      + "differences, not network change.";
    vint.classList.remove("warn");
  } else {
    vint.textContent = `⚠ The layers were rebuilt as of ${asof} but this export is `
      + `from ${day}. Across that gap the comparison measures network CHANGE, not `
      + `correctness. To compare like for like, rebuild the Clean Road workbook `
      + `with its as-of date set to ${day}, then build this report again.`;
    vint.classList.add("warn");
  }

  const blockers = [];
  if (!src.exists) blockers.push("build the Clean Road Highway workbook");
  if (!built.exists) blockers.push("build the Highway Detail report from the layers");
  if (!days.length) blockers.push("consolidate a Highway Detail export to compare against");
  $("agRepCompareHint").textContent = blockers.length
    ? "To compare: " + blockers.join("; ") + "."
    : "Compares our layer-built Highway Detail against the TSMIS export of the "
      + "chosen day. Both sides are TSMIS, so they should agree — every column is "
      + "indexed back to its source in the Notes.";
  syncArcgisLock();
}

function bindArcgis() {
  $("subAgCleanRoad").onclick = () => setArcgisSub("cleanroad");
  $("subAgReports").onclick = () => setArcgisSub("reports");
  $("btnAgRepOpenOut").onclick = () => api.open_arcgis_reports_folder();
  $("btnAgRepCancel").onclick = () => api.cancel_run();
  $("agRepDay").onchange = () => renderArcgisReports();
  const asofDayBtn = $("btnAgRepAsofDay");
  if (asofDayBtn) asofDayBtn.onclick = () => {
    const d = $("agRepDay") && $("agRepDay").value;
    if (d) $("agRepAsof").value = d;
  };
  $("btnAgRepBuild").onclick = async () => {
    const box = $("agRepAsof");
    const r = await api.start_arcgis_report_build(box ? box.value.trim() : "");
    if (r && r.error) showMessage("error", "Can't build", r.error);
  };
  $("btnAgRepCompare").onclick = async () => {
    const r = await api.start_arcgis_report_compare(
      $("agRepDay").value, $("agRepWantFormulas").checked,
      $("agRepWantValues").checked);
    if (!r) return;
    if (r.error) { showMessage("error", "Can't compare", r.error); return; }
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
