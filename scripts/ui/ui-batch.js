// Export-Everything + Consolidate module (S5 / FE-01, split from app.js — same
// global scope). Owns: the batch report picker count, resume banner, batch
// start/destination/library renders, and the consolidate/run-report actions.
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
        .filter((c) => c.checked).map((c) => c.dataset.key);
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
  rows.forEach((r) => {
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
    btn.onclick = () => startBatch([r.subdir]);   // export-op key = subdir (P3)
    row.append(name, age, btn);
    lib.appendChild(row);
  });
  const meta = $("batchLibMeta");
  if (meta) meta.textContent = `${present.length} of ${rows.length} present`;
}

async function startConsolidate() {
  const key = consChoice();
  const day = selectedDay();
  const info = await api.consolidate_info(key, day);
  if (info.exists) {
    const ok = await showConfirm({
      title: "Overwrite?",
      message: `A consolidated workbook already exists:\n\n${info.out_path}\n\nOverwrite it?`,
      confirmLabel: "Overwrite",
      danger: true,
    });
    if (!ok) { api.decline_overwrite(); return; }
  }
  const res = await api.start_consolidate(key, day);
  if (res && res.error) showMessage("error", "Could not start", res.error);
}

async function saveRunReport() {
  const res = await api.save_run_report();
  if (res && res.error) showMessage("error", "Could not save report", res.error);
}
