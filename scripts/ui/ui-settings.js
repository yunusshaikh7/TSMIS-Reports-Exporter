/* TSMIS UI — the Settings pane renderers (P9b split from app.js).
 * Classic <script> (NO ES module), loaded BEFORE app.js: fillSettings .. verify-
 * Environment + the TSN-library / Chromium / export-browser renderers. SETTING_INPUTS
 * stays in app.js (the lock-sweep + bindEvents read it); these functions reference it
 * (and $, S, api, the ui-dom helpers) at call time. Behavior-neutral move. */
"use strict";

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
  renderExportBrowser(s.export_browser || {});
  renderTsnLibrary(s.tsn_library || []);

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
      ? " and available as an export browser (pick it under Export browser below)."
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

// ---- Settings: Export browser (Built-in Chromium vs Google Chrome) ----
// The real CHOICE only exists when BOTH are available; otherwise just say what's
// in use. Microsoft Edge is the implicit one-click path, never an option here.
function renderExportBrowser(eb) {
  const box = $("setExportBrowser"), info = $("exportBrowserInfo");
  if (!box) return;
  box.textContent = "";
  const labels = eb.labels || { chromium: "Built-in Chromium", chrome: "Google Chrome" };
  const hasChoice = !!(eb.chromium_present && eb.chrome_ok);
  if (hasChoice) {                       // both installed → a real pick
    box.classList.remove("hidden");
    [["auto", "Automatic — Google Chrome when installed"],
     ["chrome", labels.chrome], ["chromium", labels.chromium]].forEach(([val, text]) => {
      const lab = document.createElement("label"); lab.className = "set-radio";
      const r = document.createElement("input");
      r.type = "radio"; r.name = "exportBrowser"; r.value = val;
      r.checked = (eb.value || "auto") === val;
      r.onchange = async () => {
        const res = await api.set_export_browser(val);
        if (res && res.error) showMessage("error", "Can't set export browser", res.error);
      };
      lab.append(r, document.createTextNode(" " + text));
      box.appendChild(lab);
    });
    info.textContent = "";
  } else {                               // no real choice → just say what's used
    box.classList.add("hidden");
    info.textContent = eb.chromium_present
      ? `Exports use the ${labels.chromium} (no Google Chrome installed). `
        + "Install Chrome for a choice."
      : eb.chrome_ok
        ? `Exports use ${labels.chrome} (no Built-in Chromium present). `
          + "Download the Built-in Chromium above for a choice."
        : "No Chrome/Chromium is available — exports use Microsoft Edge. Install "
          + "Google Chrome, or download the Built-in Chromium above, for faster exports.";
  }
}

// ---- Settings: canonical TSN library (v0.17.0) ----
const TSN_RAW_KIND_LABEL = {
  district_pdfs: "district PDFs", statewide_pdf: "statewide PDF",
  statewide_xlsx: "statewide workbook",
};

function renderTsnLibrary(reports) {
  const box = $("setTsnLibrary");
  if (!box) return;
  box.textContent = "";
  const rebuilding = S.st && S.st.task === "consolidate";
  // "Rebuild all out of date" targets exactly the rows the per-report Rebuild
  // would: raw imported, consolidated missing or superseded. Nothing to do (or a
  // task already holding the slot) disables it rather than reporting an error.
  const stale = (reports || []).filter((r) => r.raw_present && !r.current);
  const all = $("setTsnRebuildStale");
  if (all) {
    all.disabled = !!rebuilding || stale.length === 0;
    all.textContent = stale.length
      ? `Rebuild all out of date (${stale.length})`
      : "All up to date";
    all.title = stale.length
      ? `Rebuild: ${stale.map((r) => r.label).join(", ")}`
      : "Every imported TSN report's consolidated workbook is current.";
    // Assigned (not addEventListener): this renderer re-runs on every panel
    // refresh, and assignment replaces the handler instead of stacking copies.
    all.onclick = () => rebuildStaleTsnLibraries();
  }
  // Folder location: WHERE the TSN files live on disk (each report has a
  // <root>\<report>\raw + \consolidated subfolder), with an Open-folder button.
  const root = (S.init.settings || {}).tsn_library_root;
  if (root) {
    const loc = document.createElement("div");
    loc.className = "tsn-loc";
    const lbl = document.createElement("span");
    lbl.className = "tsn-loc-label"; lbl.textContent = "Folder";
    const path = document.createElement("span");
    path.className = "tsn-loc-path mono"; path.textContent = root; path.title = root;
    const open = document.createElement("button");
    open.className = "btn btn-subtle btn-small"; open.textContent = "Open folder";
    open.title = "Open the TSN library folder (each report keeps its raw + "
      + "consolidated files in a <report> subfolder)";
    open.addEventListener("click", () => api.open_tsn_library_folder());
    loc.append(lbl, path, open);
    box.appendChild(loc);
  }
  reports.forEach((r) => {
    const row = document.createElement("div");
    row.className = "tsn-row";

    const dot = document.createElement("span");
    // Green = consolidated current; amber = missing/stale OR raw not imported.
    dot.className = "tsn-dot " + (r.current ? "ok" : (r.raw_present ? "warn" : "none"));
    dot.title = r.current ? "Consolidated workbook is current"
      : r.raw_present ? "Consolidated workbook is missing or older than the raw — rebuild it"
      : "No raw TSN file imported yet";

    const name = document.createElement("span");
    name.className = "tsn-name";
    name.textContent = r.label;
    if (r.raw_dir) name.title = "Raw files for this report go in:\n" + r.raw_dir;

    const status = document.createElement("span");
    status.className = "tsn-status muted";
    const kind = TSN_RAW_KIND_LABEL[r.raw_kind] || r.raw_kind;
    if (!r.raw_present) {
      status.textContent = `no raw imported (${kind})`;
    } else {
      const raw = `${r.raw_count} raw ${kind}`;
      const cons = r.consolidated_present
        ? (r.current ? "consolidated current" : "consolidated STALE")
        : "not yet built";
      status.textContent = `${raw} · ${cons}`;
    }

    // Second asset: the TSN prints the evidence images crop from. Reports that
    // build from the SAME district prints need no separate drop, so they are
    // reported as covered by the raw rather than as a second requirement.
    const eviState = !r.evidence_supported ? "none"
      : r.evidence_pdfs ? "ok" : "warn";
    if (r.evidence_supported) {
      const evi = document.createElement("span");
      evi.className = "tsn-evidence muted " + eviState;
      if (r.evidence_in_raw) {
        evi.textContent = r.evidence_pdfs
          ? `evidence prints: ${r.evidence_pdfs} (same as raw)`
          : "evidence prints: none (uses this report's raw)";
      } else {
        evi.textContent = r.evidence_pdfs
          ? `evidence prints: ${r.evidence_pdfs}`
          : "evidence prints: MISSING";
      }
      evi.title = r.evidence_in_raw
        ? "Evidence images crop from the same raw TSN prints this report builds "
          + "from — no separate drop needed.\n" + (r.evidence_dir || "")
        : (r.evidence_pdfs
            ? "Evidence images can render for this report.\nPrints: " + (r.evidence_dir || "")
            : "No TSN prints for this report yet — evidence images cannot render "
              + "until they are dropped in:\n" + (r.evidence_dir || ""));
      status.append(document.createElement("br"), evi);
    }

    const actions = document.createElement("span");
    actions.className = "tsn-actions";
    const imp = document.createElement("button");
    imp.className = "btn btn-subtle btn-small";
    imp.textContent = "Import raw…";
    imp.disabled = !!rebuilding;
    imp.addEventListener("click", () => importTsnRaw(r.report));
    const reb = document.createElement("button");
    reb.className = "btn btn-standard btn-small";
    reb.textContent = "Rebuild";
    reb.disabled = !!rebuilding || !r.raw_present;
    reb.addEventListener("click", () => rebuildTsnLibrary(r.report));
    actions.append(imp, reb);

    row.append(dot, name, status, actions);
    box.appendChild(row);
  });
}

async function importTsnRaw(report) {
  const res = await api.import_tsn_raw(report);
  if (res && res.error) { showMessage("error", "Import failed", res.error); return; }
  if (res && res.cancelled) return;
  if (res && res.reports) {
    S.init.settings.tsn_library = res.reports;
    renderTsnLibrary(res.reports);
  }
}

async function rebuildTsnLibrary(report) {
  const res = await api.rebuild_tsn_library(report);
  if (res && res.error) { showMessage("error", "Can't rebuild", res.error); return; }
  // The rebuild runs on the shared task slot; refresh the panel once it finishes
  // (see the "state" handler, which clears _tsnRebuildPending when task goes idle).
  S._tsnRebuildPending = true;
  renderTsnLibrary(S.init.settings.tsn_library || []);   // reflect the busy/disabled state
}

async function rebuildStaleTsnLibraries() {
  const res = await api.rebuild_stale_tsn_libraries();
  if (res && res.error) { showMessage("error", "Can't rebuild", res.error); return; }
  // Same shared task slot as the per-report Rebuild: the panel refreshes when the
  // "state" handler sees the task go idle and clears _tsnRebuildPending.
  S._tsnRebuildPending = true;
  renderTsnLibrary(S.init.settings.tsn_library || []);
}

async function refreshTsnLibrary() {
  const res = await api.tsn_library_status();
  if (res && res.reports) {
    S.init.settings = S.init.settings || {};
    S.init.settings.tsn_library = res.reports;
    renderTsnLibrary(res.reports);
  }
}

async function downloadChromium() {
  const ok = await showConfirm({
    title: "Download the Built-in Chromium?",
    message: "About 170 MB will be downloaded into the app's data folder "
      + "(data\\ms-playwright).\n\nAfter it finishes, restart the app, then pick "
      + "“Built-in Chromium” under Settings ▸ Export browser.",
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
