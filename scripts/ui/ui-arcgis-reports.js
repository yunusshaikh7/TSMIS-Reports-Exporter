// ArcGIS ▸ ArcGIS reports (v0.47.0) — split from ui-arcgis.js, same global scope.
// Every TSMIS report rendered from the layer library, one ArcGIS build per
// report (the `arcgis_reports` registry; the reports with no build yet are
// listed greyed, so the whole set is visible). Refresh all / refresh one
// rebuilds them from the current layers as ONE matrix-queue job, report after
// report; each row says what its build is as of, whether it came from the
// layers in the library now, and which export editions Reports vs ArcGIS
// compares against it.

let AGB = null;                 // the last arcgis_reports_info payload
let _agbRenderSeq = 0;
let _agbSeen = null;            // the build progress the table last showed

function agbJobRunning() {
  const cur = S.st && S.st.matrix_current;
  return !!(cur && cur.kind === "arcgis_build");
}

function agbProgressText(m) {
  const at = Math.min((m.done || 0) + 1, m.total || 1);
  const el = typeof m.elapsed_s === "number" && m.elapsed_s >= 1 ? ` · ${fmtDur(m.elapsed_s)} elapsed` : "";
  return (m.total > 1 ? `Refreshing ${at} of ${m.total}` : "Refreshing")
    + (m.row ? ` — ${m.row}` : "") + el;
}

// One report's build as a status line: {text, cls}. `m` is the live progress.
function agbStatus(b, m) {
  if (!b.available) return { text: "not available yet", cls: "" };
  if (agbJobRunning() && m && m.phase === "building") {
    if (m.row === b.label) return { text: "building…", cls: "warn" };
    if (AGB && (AGB.running_rows || []).includes(b.key)) {
      const idx = AGB.running_rows.indexOf(b.key);
      if (idx > (m.done || 0)) return { text: "waiting…", cls: "" };
    }
  }
  const tried = b.last_attempt;
  const failed = tried && (tried.status === "error" || tried.status === "cancelled");
  const when = tried && tried.at ? ` ${agbWhen(tried.at)}` : "";
  if (failed && tried.status === "error") {
    const why = tried.reason || "see the log";
    return { text: `last refresh failed${when}: ${why.length > 70 ? why.slice(0, 68) + "…" : why}`,
             title: `Last refresh failed${when}: ${why}`, cls: "err" };
  }
  if (failed) return { text: `last refresh cancelled${when}`, cls: "warn" };
  if (!b.built) {
    const missing = (b.missing_layers || []).length;
    return missing
      ? { text: `${missing} layer${missing > 1 ? "s" : ""} missing — refresh them on Layers`, cls: "warn" }
      : { text: "not built yet", cls: "" };
  }
  if (b.stale_reason === "outcome_untrusted") return { text: "outcome unknown — refresh it", cls: "warn" };
  if (b.stale_reason === "drop_changed")
    return { text: `built from older layers${b.drop_exported ? " (" + b.drop_exported + ")" : ""} — refresh it`,
             cls: "warn" };
  return { text: "current" + (b.completion === "partial" ? " · partial (its notes sheet says why)" : ""),
           cls: "ok" };
}

function agbWhen(epochS) {            // epoch seconds -> "2026-10-05 14:05"
  const d = new Date(Number(epochS) * 1000);
  if (!Number.isFinite(d.getTime())) return "";
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

// What Reports vs ArcGIS does with a report's build, as one short line.
function agbComparedWith(b) {
  if (!b.available) return "build coming later";
  const eds = (b.editions || []).filter((e) => e.comparable);
  if (!eds.length) return "built here · comparison not wired yet";
  return "compared with " + eds.map((e) => e.label).join(" · ");
}

async function renderArcgisBuilds() {
  const table = $("agBuildsTable");
  if (!table) return;
  const seq = ++_agbRenderSeq;
  let info;
  try { info = await api.arcgis_reports_info(); } catch (e) {
    $("agBuildsHint").textContent = "Status unavailable: " + e;
    return;
  }
  if (seq !== _agbRenderSeq || !info) return;    // a newer render started
  if (info.error) { $("agBuildsHint").textContent = info.error; return; }
  AGB = info;
  const reports = info.reports || [];
  const stale = reports.filter((b) => b.built && b.stale).length;
  $("agBuildsMeta").textContent = `${info.built || 0} built · ${info.buildable || 0} of ${reports.length} can be built`;
  const drop = info.drop || {};
  let hint = drop.exported
    ? `Builds from the layers exported ${aglWhen(drop.exported_at) || drop.exported}`
      + (drop.mixed && drop.newest_at ? ` to ${aglWhen(drop.newest_at)}` : "") + ", as of that date unless you set one."
    : "Builds from the layer library, as of the layers' export date unless you set one.";
  if (!info.staged) hint = "No layers yet — refresh them on the Layers tab first.";
  hint += " Reports vs ArcGIS compares every export of a report — Excel and PDF — against its build here.";
  if (stale) hint += ` ${stale} report${stale > 1 ? "s were" : " was"} built from older layers — refresh ${stale > 1 ? "them" : "it"}.`;
  $("agBuildsHint").textContent = hint;
  const asof = $("agBuildsAsof");
  if (asof && !asof.value) asof.placeholder = drop.exported ? `${drop.exported} (the layers' date)` : "YYYY-MM-DD";
  $("agBuildsFoot").textContent = `Builds are saved in ${info.reports_root} (Clean Road: Highway keeps its own `
    + "CA HIGHWAYS folder). A refresh replaces the build in place.";
  renderArcgisBuildsTable(info);
  updateArcgisBuildsProgress();
}

function renderArcgisBuildsTable(info) {
  const table = $("agBuildsTable");
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
  head.append(cellDiv("", "Report · compared on Reports vs ArcGIS"), cellDiv("", "As of · built"),
    cellDiv("num", "Rows"), cellDiv("", "Status"), cellDiv("", ""));
  table.appendChild(head);
  (info.reports || []).forEach((b) => {
    const st = agbStatus(b, m);
    const row = document.createElement("div");
    row.className = "agl-row" + (b.available ? "" : " agb-off")
      + (st.text === "building…" ? " active" : "");
    const name = cellDiv("agl-layer");
    const layers = (b.layers || []).length;
    name.append(
      cellDiv("agl-name", b.label, b.path ? `${b.path}${layers ? `\nreads ${layers} layers` : ""}` : (b.why || "")),
      cellDiv("agl-users", agbComparedWith(b), b.why || ""));
    const acts = cellDiv("agb-acts");
    if (b.available) {
      const rb = document.createElement("button");
      rb.className = "btn btn-subtle btn-small agb-refresh";
      rb.innerHTML = '<svg class="ic"><use href="#i-refresh"/></svg>';
      rb.appendChild(document.createTextNode(b.built ? "Refresh" : "Build"));
      rb.title = (b.built ? "Rebuild " : "Build ") + b.label + " from the current layers";
      rb.dataset.blocked = (b.missing_layers || []).length ? "1" : "";   // layers missing
      rb.disabled = locked || rb.dataset.blocked === "1";
      rb.onclick = () => agbRefresh([b.key]);
      acts.appendChild(rb);
    }
    if (b.built) {
      const ob = document.createElement("button");
      ob.className = "btn btn-subtle btn-small agb-open";
      ob.innerHTML = '<svg class="ic"><use href="#i-external"/></svg>';
      ob.title = `Open the ${b.label} ArcGIS report`;
      ob.onclick = async () => {
        const r = await api.open_arcgis_report(b.key);
        if (r && r.error) showMessage("error", "Can't open", r.error);
      };
      acts.appendChild(ob);
    }
    const rows = Number(b.rows);
    const asof = cellDiv("agb-asof-cell");
    if (b.built) {
      const built = b.mtime ? agbWhen(b.mtime) : "";
      asof.append(cellDiv("agl-when", b.asof || "?", "Reconstructed as of this date"),
                  cellDiv("agl-users", built ? "built " + built.slice(5) : "", built ? "Built " + built : ""));
    }
    row.append(
      name, asof,
      cellDiv("num", b.built && Number.isFinite(rows) && rows > 0 ? rows.toLocaleString() : ""),
      cellDiv("agl-status" + (st.cls ? " " + st.cls : ""), st.text, st.title || st.text),
      acts);
    table.appendChild(row);
  });
}

// Called on every state push while the ArcGIS reports sub-tab shows (no API
// call): the progress line, Cancel, the lock-sensitive controls, and a table
// re-read whenever the report being built changes.
function updateArcgisBuildsProgress() {
  const locked = !!(S.st && S.st.task);
  const running = agbJobRunning();
  const m = (S.st && S.st.matrix) || null;
  const prog = $("agBuildsProgress");
  if (prog) {
    const show = running && m && m.phase === "building";
    prog.hidden = !show;
    if (show) prog.textContent = agbProgressText(m);
  }
  const cancel = $("btnAgBuildsCancel");
  if (cancel) { cancel.classList.toggle("hidden", !running); cancel.disabled = !running; }
  const all = $("btnAgBuildsAll");
  if (all) all.disabled = locked || !(AGB && AGB.buildable);
  document.querySelectorAll("#agBuildsTable .agb-refresh").forEach((b) => {
    b.disabled = locked || b.dataset.blocked === "1";
  });
  const seen = running && m ? `${m.done}:${m.row || ""}` : "idle";
  if (AGB && seen !== _agbSeen) {
    const first = _agbSeen === null;
    _agbSeen = seen;
    if (!first) renderArcgisBuilds();
  }
}

async function agbRefresh(keys) {
  const box = $("agBuildsAsof");
  const r = await api.refresh_arcgis_reports(keys, box ? box.value.trim() : "");
  if (r && r.error) { showMessage("error", "Can't refresh", r.error); return false; }
  return true;
}

function bindArcgisBuilds() {
  $("subAgBuilds").onclick = () => setArcgisSub("builds");
  $("btnAgBuildsAll").onclick = async () => {
    const able = ((AGB && AGB.reports) || []).filter((b) => b.available);
    if (!able.length) return;
    const ok = await showConfirm({
      title: `Refresh all ${able.length} ArcGIS reports?`,
      message: "Each report is rebuilt from the current layers, one after another ("
        + able.map((b) => b.label).join(", ") + ") — Highway Detail alone takes about "
        + "half an hour. Comparisons made against the old builds read stale afterwards; "
        + "rebuild them on Reports vs ArcGIS.",
      confirmLabel: "Refresh",
    });
    if (ok) await agbRefresh([]);
  };
  $("btnAgBuildsCancel").onclick = () => api.cancel_run();
  $("btnAgBuildsOpen").onclick = () => api.open_arcgis_reports_folder();
}
