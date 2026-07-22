// ArcGIS tab module (v0.29.0, split like the other ui-*.js — same global scope).
// Owns: the layer-library status card, the CA HIGHWAYS build (as-of date +
// Build button), and the ArcGIS-vs-TSN comparison launcher (formulas/values
// checkboxes ride the same start flow as the classic Compare tab, including
// the derived-values overwrite confirmation).

let AG = null;                 // the last arcgis_status payload

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
}

function bindArcgis() {
  $("btnAgOpenLayers").onclick = () => api.open_arcgis_layers_folder();
  $("btnAgOpenOut").onclick = () => api.open_arcgis_output_folder();
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
