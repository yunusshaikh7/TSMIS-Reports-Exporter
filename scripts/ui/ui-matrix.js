/* TSMIS UI — the comparison-matrix + by-day-matrix renderers (P9b split from app.js).
 * Classic <script> (NO ES module), loaded BEFORE app.js: the matrix/by-day grid
 * renderers, the shared cell/queue/drag helpers, and MX_HI live here as global
 * declarations sharing scope with app.js (read at call time). Behavior-neutral move,
 * plus the two duplicated sync* render pairs unified behind thin named wrappers. */
"use strict";

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
  // Grey only the SELECTION controls while a task runs (the grid re-renders at
  // run end). The cell/header ACTION triggers stay live — a 2nd click queues —
  // and the queue/fast controls are always editable (excluded here on purpose).
  const locked = !!(S.st && S.st.task);
  document.querySelectorAll(
    "#matrixSection .mx-rowmode, #matrixSection .mx-linkbtn, #matrixBaseline, "
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
  // Pause/Skip apply only to a matrix re-EXPORT run (the worker forwards the
  // pause/skip events to the engine). Skip is meaningless in fast mode.
  const cur = S.st && S.st.matrix_current;
  const exporting = !!(S.st && S.st.task === "matrix" && cur && cur.kind === "export");
  const pause = $("btnMatrixPause");
  if (pause) {
    pause.classList.toggle("hidden", !exporting);
    pause.disabled = !exporting;
    const u = pause.querySelector("use");
    if (u) u.setAttribute("href", S.st && S.st.paused ? "#i-play" : "#i-pause");
    const lbl = $("btnMatrixPauseLabel");
    if (lbl) lbl.textContent = S.st && S.st.paused ? "Resume" : "Pause";
  }
  const skip = $("btnMatrixSkip");
  if (skip) {
    skip.classList.toggle("hidden", !exporting);
    skip.disabled = !exporting || !!(S.st && S.st.fast_run);
  }
  renderMatrixQueue();
  syncMatrixFast();
  syncMatrixFormulas();
  syncMatrixEvidence();
}

// The live job-queue panel (driven from each state push, so reorder/remove/
// clear/stop-all update without a full grid re-render). The SAME queue serves
// both matrices, so it renders into both panels (Everything config zone + the
// Compare by-day section).
function renderMatrixQueue() {
  renderQueuePanel("matrixQueueGroup", "matrixQueue", "matrixQueueCount");
}

function renderQueuePanel(groupId, listId, countId) {
  const group = $(groupId);
  if (!group) return;
  const st = S.st || {};
  const cur = st.matrix_current || null;
  const pending = st.matrix_queue || [];
  const list = $(listId);
  // Clear the list in EVERY path: hiding the group isn't enough to drop a finished
  // job's row (a hidden .mc-group must also be emptied), else it lingers if anything
  // re-shows the group without repopulating it.
  if (list) list.textContent = "";
  if (!cur && !pending.length) { group.hidden = true; return; }
  group.hidden = false;
  const count = $(countId);
  if (count) count.textContent = pending.length ? `(${pending.length} waiting)` : "";
  if (cur) list.appendChild(mxQueueRow(cur, true, 0, 1));
  pending.forEach((job, i) => list.appendChild(mxQueueRow(job, false, i, pending.length)));
}

function mxQueueRow(job, running, idx, total) {
  const row = document.createElement("div");
  row.className = "mx-qrow" + (running ? " is-running" : "");
  const kindIcon = job.kind === "export" ? "i-refresh"
    : job.kind === "compare" ? "i-compare" : "i-layers";
  const ic = icon(running ? "i-loader" : kindIcon, "mx-qicon");
  if (running) ic.classList.add("spin");
  row.appendChild(ic);
  const label = document.createElement("span");
  label.className = "mx-qlabel"; label.textContent = job.label;
  label.title = job.label + (job.fast ? "  ·  fast mode" : "");
  row.appendChild(label);
  if (job.fast) {
    const f = icon("i-zap", "mx-qfast"); f.setAttribute("aria-label", "fast mode");
    row.appendChild(f);
  }
  if (running) {
    const badge = document.createElement("span");
    badge.className = "mx-qbadge"; badge.textContent = "running";
    row.appendChild(badge);
  } else {
    const ctr = document.createElement("span"); ctr.className = "mx-qctrls";
    ctr.append(
      mxQctrl("i-chevron-up", "Move up", idx === 0,
        () => api.matrix_queue_move(job.id, "up")),
      mxQctrl("i-chevron-down", "Move down", idx >= total - 1,
        () => api.matrix_queue_move(job.id, "down")),
      mxQctrl("i-trash", "Remove from queue", false,
        () => api.matrix_queue_remove(job.id), "mx-qrm"));
    row.appendChild(ctr);
  }
  return row;
}

function mxQctrl(iconName, title, disabled, onClick, extra) {
  const b = document.createElement("button");
  b.className = "mx-qbtn" + (extra ? " " + extra : "");
  b.title = title; b.setAttribute("aria-label", title);
  b.disabled = disabled; b.appendChild(icon(iconName));
  b.onclick = onClick;          // a state push re-renders the panel
  return b;
}

// Reflect the persisted matrix fast-mode toggle + browser-count picker (kept
// editable mid-run). The count is the shared `fast_workers` knob, so the spinner,
// the Export pane and the Settings tab all stay on one value.
// Reflect the SHARED fast knob (matrix_fast + the one fast_workers count) on a
// matrix's fast-mode controls. Both matrices read the SAME state — only the element
// ids differ — so one helper drives both, behind thin named wrappers the callers
// still use (P9b renderer-path merge; behavior-neutral).
function syncMatrixFastControls(cbId, rowId, wkId) {
  const cb = $(cbId);
  if (!cb) return;
  const mf = (S.st && S.st.matrix_fast) || { on: false, workers: 0 };
  cb.checked = !!mf.on;
  const row = $(rowId);
  if (row) row.classList.toggle("is-off", !mf.on);
  const wk = $(wkId);
  // Don't stomp the field while the user is mid-edit (focused).
  if (wk && document.activeElement !== wk && mf.workers) wk.value = mf.workers;
}
function syncMatrixFast() {
  syncMatrixFastControls("matrixFast", "matrixWorkersRow", "matrixWorkers");
}
// The by-day matrix's Export-speed controls reflect the SHARED fast knob, so toggling
// fast here / in the Everything matrix / in Settings all stay on one value.
function syncDayMatrixFast() {
  syncMatrixFastControls("dayMatrixFast", "dayMatrixWorkersRow", "dayMatrixWorkers");
}

// Reflect a persisted live-formulas toggle. Each matrix has its OWN setting (Everything
// ← matrix_formulas, by-day ← day_matrix_formulas), so the shared helper is keyed by
// both the checkbox id and the state key (P9b renderer-path merge; behavior-neutral).
function syncFormulasToggle(cbId, stateKey) {
  const cb = $(cbId);
  if (cb) cb.checked = !!(S.st && S.st[stateKey]);
}
function syncMatrixFormulas() {
  syncFormulasToggle("matrixFormulas", "matrix_formulas");
}
function syncDayMatrixFormulas() {
  syncFormulasToggle("dayMatrixFormulas", "day_matrix_formulas");
}

// Reflect the SHARED evidence-images option (one persisted setting surfaced on
// both matrix pages) and spell out PER REPORT what the toggle will actually
// generate: a ✓ line for each report whose TSN prints are in place (images WILL
// render for its vs-TSN cells), a ○ line naming the drop folder for one that
// isn't, and one line naming the reports with no evidence support at all — so
// the toggle is never a mystery switch. The toggle greys out only when NO
// report is ready.
function syncEvidenceControls(cbId, countRowId, countId, hintId, layoutId) {
  const ev = (S.st && S.st.evidence) || {};
  const cb = $(cbId);
  if (cb) {
    cb.checked = !!ev.on;
    cb.disabled = !ev.ready;
  }
  const row = $(countRowId);
  if (row) row.style.display = ev.on && ev.ready ? "" : "none";
  const count = $(countId);
  if (count && document.activeElement !== count) count.value = ev.examples || 2;
  const layoutSel = layoutId && $(layoutId);
  if (layoutSel && document.activeElement !== layoutSel)
    layoutSel.value = ev.layout || "pair";
  const hint = $(hintId);
  if (!hint) return;
  hint.hidden = false;
  if (!ev.deps_ok) {
    hint.textContent = "Evidence images aren't available in this build.";
    return;
  }
  const line = (mark, text, title) => {
    const div = document.createElement("div");
    div.className = "ev-status-line";
    const m = document.createElement("span");
    m.className = `ev-mark ev-mark-${mark}`;
    m.textContent = mark === "ok" ? "✓" : mark === "todo" ? "○" : "—";
    div.appendChild(m);
    div.appendChild(document.createTextNode(" " + text));
    if (title) div.title = title;
    return div;
  };
  const lines = [];
  for (const r of ev.reports || []) {
    if (r.tsn_pdfs) {
      lines.push(line("ok",
        `${r.label} — will generate (${r.tsn_pdfs} TSN print${r.tsn_pdfs === 1 ? "" : "s"})`,
        `TSN prints read from ${r.dir}. Cells whose run lacks the ${r.label} (PDF) ` +
        "export skip with a note (that export is the TSMIS-side image source)."));
    } else {
      lines.push(line("todo",
        `${r.label} — needs its TSN PDFs in ${r.dir}`,
        "Evidence is supported for this report, but its TSN prints aren't there yet."));
    }
  }
  if ((ev.unsupported || []).length) {
    lines.push(line("na", `No evidence support yet: ${ev.unsupported.join(", ")}.`,
      "Evidence images need both sides as PDFs; these reports don't have " +
      "verified PDF sources yet."));
  }
  hint.replaceChildren(...lines);
}
function syncMatrixEvidence() {
  syncEvidenceControls("matrixEvidence", "matrixEvidenceCountRow",
    "matrixEvidenceCount", "matrixEvidenceHint", "matrixEvidenceLayout");
}
function syncDayMatrixEvidence() {
  syncEvidenceControls("dayMatrixEvidence", "dayMatrixEvidenceCountRow",
    "dayMatrixEvidenceCount", "dayMatrixEvidenceHint", "dayMatrixEvidenceLayout");
}

// Whether a row can run the ON-DEMAND per-cell evidence action right now:
// deps in the build, the row has an adapter, and ITS report's TSN prints are
// dropped in (per-report since v0.22.0). Returns the report info (for the
// tooltip) or null.
function evidenceActionInfo(rowKey) {
  const ev = (S.st && S.st.evidence) || {};
  if (!ev.deps_ok || !(ev.rows || []).includes(rowKey)) return null;
  const repKey = (ev.row_reports || {})[rowKey];
  const rep = (ev.reports || []).find((r) => r.key === repKey);
  return rep && rep.tsn_pdfs ? rep : null;
}

// A small camera badge on an evidence-SUPPORTED row's header (both matrices):
// lit when its TSN prints are in place (images will render for its vs-TSN
// comparisons), dimmed with the drop-folder in the tooltip when not. Rows with
// no evidence support get no badge — the toggle's status lines name them.
function evidenceRowBadge(rowKey) {
  const ev = (S.st && S.st.evidence) || {};
  if (!ev.deps_ok || !(ev.rows || []).includes(rowKey)) return null;
  const repKey = (ev.row_reports || {})[rowKey];
  const rep = (ev.reports || []).find((r) => r.key === repKey);
  if (!rep) return null;
  const b = document.createElement("span");
  b.className = "mxrh-evbadge" + (rep.tsn_pdfs ? "" : " mxrh-evbadge-off");
  b.appendChild(icon("i-camera", "ic"));
  b.title = rep.tsn_pdfs
    ? `Evidence images supported — the toggle (or a cell's camera) renders ${rep.label} diffs as highlighted PDF snippets.`
    : `Evidence images supported once ${rep.label}'s TSN PDFs are in ${rep.dir}.`;
  return b;
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
  const d = Number.isFinite(cmp.diff_cells) ? cmp.diff_cells : null;
  const os = Number.isFinite(cmp.one_sided) ? cmp.one_sided : null;
  if (cmp.completion === "partial" && d != null && os != null) {
    const observed = `${d} diff${d === 1 ? "" : "s"}`
      + (os ? ` + ${os} one-sided` : "");
    const retry = cmp.pairing_quality === "capped"
      ? "pairing capped — re-scope"
      : "refresh";
    return { cls: "mx-partial", main: "partial",
             sub: `${observed} observed — ${retry}` };
  }
  if (cmp.stale || cmp.diff_cells == null) {
    return { cls: "mx-stale",
             main: cmp.diff_cells == null ? "re-run" : String(cmp.diff_cells),
             sub: "stale — refresh" };
  }
  if (cmp.completion !== "complete") {
    return { cls: "mx-stale", main: "re-run", sub: "outcome unknown" };
  }
  if (d === 0 && os === 0) {
    return cmp.verdict === "match"
      ? { cls: "mx-match", main: "✓ match", sub: "identical" }
      : { cls: "mx-stale", main: "re-run", sub: "verdict/counts disagree" };
  }
  const base = os ? `+${os} one-sided` : "";
  const cls = (d >= MX_HI || d + os >= MX_HI) ? "mx-diff-hi" : "mx-diff-lo";
  return { cls, main: `${d} diff${d === 1 ? "" : "s"}`,
           sub: base };
}

// A compact icon action button for a matrix cell (export / compare / open). Icons
// (not text) so three actions fit a narrow cell; the title carries the meaning.
function mxActBtn(iconName, title, locked, onClick) {
  const b = document.createElement("button");
  b.className = "mx-act"; b.title = title; b.disabled = locked;
  b.setAttribute("aria-label", title);     // icon-only — needs an accessible name
  b.appendChild(icon(iconName));
  b.onclick = onClick;
  return b;
}

// A matrix HEADER button group (row + column): ↻ live re-export (i-refresh) and
// ⟳ rebuild comparisons (i-compare), mirroring the per-cell action icons. Both
// keep the .mxch-refresh hook for CSS; they enqueue, so they stay live mid-run.
function mxHeadBtn(iconName, title, extra, onClick) {
  const b = document.createElement("button");
  b.className = "mxch-refresh" + (extra ? " " + extra : "");
  b.title = title; b.setAttribute("aria-label", title);
  b.appendChild(icon(iconName)); b.onclick = onClick;
  return b;
}

function mxHeaderBtns(label, onReexport, onRebuild) {
  const grp = document.createElement("span");
  grp.className = "mxch-btns";
  grp.append(
    mxHeadBtn("i-refresh", `Re-export ${label} live from TSMIS`, "mxch-reexport", onReexport),
    mxHeadBtn("i-compare", `Rebuild every comparison in ${label}`, "mxch-rebuild", onRebuild),
  );
  return grp;
}

// Bulk live re-export (a whole row or column) hits TSMIS many times, so confirm
// first. The job is queued and cancellable; single-cell re-export needs no
// confirm.
function confirmBulkReexport(what) {
  return showConfirm({
    title: "Re-export from TSMIS?",
    message: `This re-exports ${what} live from TSMIS. It can take a while and `
      + `runs as a queued job you can reorder or cancel.\n\nStart it?`,
    confirmLabel: "Re-export",
  });
}

// The vs-TSN file picker shown under a row's name when it's in a TSN mode.
// A status-dot chip surfaces the ACTIVE file the engine uses (mono basename,
// truncated, full path on hover) over a compact action row. Every api.* call +
// confirm flow is unchanged; the buttons keep the .mx-linkbtn hook so the
// live-lock sweep still disables them.
function mxTsnPicker(tm, locked, rerender) {
  // The TSN dataset is shared by both matrices, so the picker re-renders whichever
  // grid it sits in (default: the Everything matrix).
  rerender = rerender || renderMatrix;
  const wrap = document.createElement("div"); wrap.className = "mx-tsnpick";

  const hasFile = tm.source_kind === "file" || tm.source_kind === "consolidated";
  const needsCons = tm.source_kind === "pdfs";
  const missingSelection = tm.selection_missing || tm.source_kind === "missing_explicit";

  // Line 1: status dot + truncated monospace filename (full path = tooltip).
  const fileLine = document.createElement("div");
  fileLine.className = "mxtp-file " + (hasFile ? "has-file" : needsCons ? "needs-cons" : "is-empty");
  const dot = document.createElement("span"); dot.className = "mxtp-dot";
  const name = document.createElement("span"); name.className = "mxtp-name";
  if (missingSelection) {
    const picked = tm.selected_path || tm.file || "";
    const reason = tm.selection_reason || "missing";
    name.textContent = reason === "changed" ? "Selected TSN file changed"
      : reason === "legacy_identity" ? "Selected TSN file needs re-pick"
      : reason === "not_workbook" || reason === "unreadable"
        ? "Selected TSN file can't be read"
        : reason === "conflicting_aliases" ? "Conflicting TSN selections"
        : "Selected TSN file is missing";
    name.title = "The explicitly selected TSN workbook is unavailable:\n" + picked
      + "\nRe-pick it, or Clear the selection to use the canonical library.";
  } else if (hasFile) {
    const full = tm.source_path || "";
    name.textContent = full.split(/[\\/]/).pop() || "(file)";
    name.title = "TSN file in use:\n" + (full || name.textContent);
  } else if (needsCons) {
    name.textContent = tm.pdf_count + " TSN PDF" + (tm.pdf_count === 1 ? "" : "s");
    name.title = tm.pdf_count + " TSN PDF(s) in:\n" + (tm.input_dir || "")
      + "\nNot consolidated yet — Consolidate to build one TSN workbook.";
  } else {
    name.textContent = "No TSN file";
    name.title = "Choose a TSN workbook, or drop district PDFs into the TSN input folder and consolidate.";
  }
  fileLine.append(dot, name);
  wrap.appendChild(fileLine);

  // Line 2: compact actions — Consolidate (accent, pdfs only) / Choose / Clear.
  const row = document.createElement("div"); row.className = "mxtp-row";

  if (needsCons) {
    const cons = document.createElement("button");
    cons.type = "button"; cons.className = "mx-linkbtn is-primary"; cons.disabled = locked;
    cons.title = "Build one TSN workbook from the dropped PDFs";
    cons.append(icon("i-grid"), Object.assign(document.createElement("span"),
      { textContent: "Consolidate" }));
    cons.onclick = async () => {
      const ok = await showConfirm({ title: "Consolidate TSN PDFs?",
        message: `Build one TSN workbook from the ${tm.pdf_count} PDF(s) in:\n\n${tm.input_dir}`,
        confirmLabel: "Consolidate" });
      if (!ok) return;
      const r = await api.consolidate_matrix_tsn(tm.tsn_subdir);
      if (r && r.error) showMessage("error", "Can't consolidate", r.error);
      else await rerender();      // reflect the queued job (Choose/Clear do the same)
    };
    row.appendChild(cons);
  }

  const choose = document.createElement("button");
  choose.type = "button"; choose.className = "mx-linkbtn"; choose.disabled = locked;
  choose.title = "Pick a TSN workbook (.xlsx)";
  choose.append(icon("i-folder-open"), Object.assign(document.createElement("span"),
    { textContent: missingSelection ? "Re-pick…" : hasFile ? "Replace…" : "Choose…" }));
  choose.onclick = async () => {
    const r = await api.pick_matrix_tsn_file(tm.tsn_subdir);
    if (r && r.error) showMessage("error", "Can't pick", r.error);
    if (r && (r.ok || r.path)) await rerender();
  };
  row.appendChild(choose);

  if (tm.file) {
    const clr = document.createElement("button");
    clr.type = "button"; clr.className = "mx-linkbtn mxtp-clear"; clr.disabled = locked;
    clr.title = "Clear the picked TSN file"; clr.setAttribute("aria-label", "Clear the picked TSN file");
    clr.appendChild(icon("i-x"));
    clr.onclick = async () => { await api.set_matrix_tsn_file(tm.tsn_subdir, ""); await rerender(); };
    row.appendChild(clr);
  }

  wrap.appendChild(row);
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

// ---- Drag-to-reorder (matrix rows + columns), v0.17.0 Phase 4b ----
// A small drag grip on each row/column header reorders it; the new key order is
// persisted via the bridge and re-rendered (the backend applies the order). The
// order is a display preference only — it never touches exports or comparisons.
let _dnd = null;   // { group, key } while a drag is in flight

function _clearDndOver() {
  document.querySelectorAll(".dnd-before-x,.dnd-after-x,.dnd-before-y,.dnd-after-y")
    .forEach((x) => x.classList.remove("dnd-before-x", "dnd-after-x", "dnd-before-y", "dnd-after-y"));
}

// targetEl = the drop target (the whole header); gripHost = where the grip is
// inserted; axis 'x' (columns) or 'y' (rows); getOrder() = current visible key
// list; commit(newOrder) persists + re-renders.
function dndAttach(targetEl, gripHost, key, group, axis, getOrder, commit) {
  const grip = document.createElement("span");
  grip.className = "dnd-grip"; grip.textContent = "⠿";
  grip.title = "Drag to reorder"; grip.setAttribute("aria-hidden", "true");
  grip.draggable = true;
  grip.addEventListener("dragstart", (e) => {
    _dnd = { group, key }; targetEl.classList.add("dnd-dragging");
    try { e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", key); } catch (_) { /* ignore */ }
  });
  grip.addEventListener("dragend", () => {
    targetEl.classList.remove("dnd-dragging"); _clearDndOver(); _dnd = null;
  });
  const isAfter = (e) => {
    const r = targetEl.getBoundingClientRect();
    return axis === "x" ? (e.clientX > r.left + r.width / 2) : (e.clientY > r.top + r.height / 2);
  };
  targetEl.addEventListener("dragover", (e) => {
    if (!_dnd || _dnd.group !== group || _dnd.key === key) return;
    e.preventDefault();
    try { e.dataTransfer.dropEffect = "move"; } catch (_) { /* ignore */ }
    _clearDndOver();
    targetEl.classList.add((isAfter(e) ? "dnd-after-" : "dnd-before-") + axis);
  });
  targetEl.addEventListener("dragleave", () => {
    targetEl.classList.remove("dnd-before-" + axis, "dnd-after-" + axis);
  });
  targetEl.addEventListener("drop", async (e) => {
    if (!_dnd || _dnd.group !== group || _dnd.key === key) return;
    e.preventDefault();
    const after = isAfter(e), from = _dnd.key;
    _clearDndOver();
    const order = getOrder().filter((k) => k !== from);
    let idx = order.indexOf(key); if (idx < 0) idx = order.length;
    order.splice(after ? idx + 1 : idx, 0, from);
    await commit(order);
  });
  gripHost.prepend(grip);
  targetEl.classList.add("dnd-target");
}

// Overlay the env-access scan verdicts onto BOTH matrices, same amber convention
// as the Export tab (renderEnvAccess): a report greyed/missing on an environment
// "may cause an issue". Cheap class+tooltip toggles over already-rendered DOM
// (cells/headers carry data-rk/data-env/data-label), so it can re-run on every
// state push without rebuilding the grid. Source of truth: S.st.env_access.
function applyMatrixEnvFlags() {
  const acc = (S.st && S.st.env_access) || {};
  const note = (state, envLabel) =>
    `\n⚠ ${state === "greyed" ? "Greyed out" : "Missing"} on ${envLabel}`
    + " at the last environment check — the export may fail.";
  // Everything matrix: report × environment (flag the precise cell + its headers).
  const mg = $("matrixGrid");
  if (mg) {
    const shownEnvs = [...mg.querySelectorAll(".mx-colhead[data-env]")].map((h) => h.dataset.env);
    mg.querySelectorAll(".mx-colhead[data-env]").forEach((h) => {
      const e = acc[h.dataset.env];
      const badge = e && e.status !== "checking" && (ENV_ACCESS_BADGE[e.status] || ENV_ACCESS_BADGE.error);
      const bad = !!badge && badge.dot === "bad", warn = !!badge && badge.dot === "warn";
      h.classList.toggle("mx-env-bad", bad);
      h.classList.toggle("mx-env-warn", warn && !bad);
      h.title = badge && (bad || warn) ? `Last environment check: ${badge.text} on ${e.label}.` : "";
    });
    mg.querySelectorAll(".mx-cell[data-rk][data-env]").forEach((cell) => {
      const e = acc[cell.dataset.env];
      const state = e && e.reports && e.reports[cell.dataset.label];
      const off = !!state && state !== "ok";
      cell.classList.toggle("mx-env-flag", off);
      const base = cell.dataset.baseTitle || "";
      cell.title = off ? base + note(state, e.label) : base;
    });
    mg.querySelectorAll(".mx-rowhead[data-rk]").forEach((rh) => {
      const label = rh.dataset.label;
      const hit = shownEnvs.some((env) => {
        const e = acc[env], st = e && e.reports && e.reports[label];
        return st && st !== "ok";
      });
      rh.classList.toggle("mx-env-flag", hit);
    });
  }
  // By-day matrix: report × day under ONE source environment — flag the row header.
  const dg = $("dayMatrixGrid");
  if (dg) {
    const e = acc[dg.dataset.srcEnv];
    dg.querySelectorAll(".mx-rowhead[data-rk]").forEach((rh) => {
      const st = e && e.reports && e.reports[rh.dataset.label];
      const off = !!st && st !== "ok";
      rh.classList.toggle("mx-env-flag", off);
      rh.title = off ? note(st, e.label).trimStart() : "";
    });
  }
}

// Stale-response guards: renderMatrix/renderDayMatrix fire twice per run end
// (run_ended + matrix_refresh) with no sequencing on the awaits — a slower,
// OLDER snapshot could resolve last and repaint stale over the newer one. Each
// render takes a token; a response whose token is no longer current is dropped.
let _matrixRenderSeq = 0;
let _dayRenderSeq = 0;

async function renderMatrix() {
  const grid = $("matrixGrid");
  if (!grid) return;
  const seq = ++_matrixRenderSeq;
  let snap;
  try { snap = await api.matrix_info(); } catch (e) { return; }
  if (seq !== _matrixRenderSeq) return;   // a newer render started; drop this one
  if (!snap || !snap.rows) return;
  const envs = snap.envs, locked = !!(S.st && S.st.task);
  // All rows or all columns hidden (only reachable via a hand-edited config — the
  // bridge keeps at least one of each): show guidance instead of a blank grid, but
  // still render the config zone so the user can turn something back on.
  if (!snap.rows.length || !envs.length) {
    grid.style.gridTemplateColumns = ""; grid.style.gridTemplateRows = "";
    grid.textContent = "";
    const empty = document.createElement("div");
    empty.className = "dm-empty";
    empty.textContent = (!snap.rows.length ? "All reports" : "All environments")
      + " are hidden — turn one back on under Matrix options.";
    grid.appendChild(empty);
    renderMatrixConfig(snap, locked);
    updateMatrixProgress();
    return;
  }
  // Wider row-label column (it carries the mode dropdown + TSN picker now); the
  // fr units stretch to fill the window, the data rows share the leftover height.
  grid.style.gridTemplateColumns =
    `minmax(190px,1.2fr) repeat(${envs.length}, minmax(116px,1fr))`;
  grid.style.gridTemplateRows = `auto repeat(${snap.rows.length}, minmax(50px,1fr))`;
  grid.textContent = "";

  const corner = document.createElement("div");
  corner.className = "mx-cell mx-corner mx-colhead";
  corner.textContent = "Report \\ Env";
  grid.appendChild(corner);
  envs.forEach((env) => {
    const h = document.createElement("div");
    h.className = "mx-cell mx-colhead" + (env === snap.baseline ? " mx-baseline-col" : "");
    h.dataset.env = env;                 // env-access flag target (applyMatrixEnvFlags)
    const elabel = snap.env_labels[env] || env;
    const lab = document.createElement("div");
    lab.textContent = elabel + (env === snap.baseline ? " ★" : "");
    h.appendChild(lab);
    h.appendChild(mxHeaderBtns(elabel,
      async () => {
        if (!await confirmBulkReexport(`every report for ${elabel}`)) return;
        const r = await api.refresh_column_export(env);
        if (r && r.error) showMessage("error", "Can't re-export", r.error);
      },
      async () => {
        const r = await api.recompute_matrix("all", null, env);
        if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells here.");
        else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
      }));
    dndAttach(h, h, env, "mx-col", "x", () => snap.envs.slice(), async (order) => {
      const r = await api.set_matrix_env_order(order);
      if (r && r.error) showMessage("error", "Can't reorder", r.error);
      else await renderMatrix();
    });
    grid.appendChild(h);
  });

  snap.rows.forEach((rk) => {
    const rh = document.createElement("div");
    rh.className = "mx-cell mx-rowhead";
    const top = document.createElement("div"); top.className = "mxrh-top";
    const lbl = document.createElement("span"); lbl.className = "mxrh-label";
    const rlabel = snap.row_labels[rk] || rk;
    rh.dataset.rk = rk; rh.dataset.label = rlabel;   // env-access flag target
    lbl.textContent = rlabel; lbl.title = rlabel;
    const evb = evidenceRowBadge(rk);
    if (evb) lbl.appendChild(evb);
    top.append(lbl, mxHeaderBtns(rlabel,
      async () => {
        if (!await confirmBulkReexport(`${rlabel} across every environment`)) return;
        const r = await api.refresh_row_export(rk);
        if (r && r.error) showMessage("error", "Can't re-export", r.error);
      },
      async () => {
        const r = await api.recompute_matrix("all", rk, null);
        if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells here.");
        else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
      }));
    rh.appendChild(top);
    // per-row comparison-mode dropdown (only when the row has >1 mode), stacked
    // UNDER the label so the label keeps the full header line (no truncation),
    // with a compact chevron-wrapper select.
    const modes = (snap.row_modes && snap.row_modes[rk]) || [];
    if (modes.length > 1) {
      const fs = document.createElement("div"); fs.className = "mx-fluent-select";
      const ms = document.createElement("select");
      ms.className = "mx-rowmode"; ms.disabled = locked;
      ms.title = "Comparison type for " + rlabel;
      ms.setAttribute("aria-label", ms.title);
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
      fs.append(ms, icon("i-chevron-down", "mx-fs-chev"));
      rh.appendChild(fs);
    }
    const tm = snap.tsn_meta && snap.tsn_meta[rk];
    if (tm && tm.supported) rh.appendChild(mxTsnPicker(tm, locked));
    dndAttach(rh, top, rk, "mx-row", "y", () => snap.rows.slice(), async (order) => {
      const r = await api.set_matrix_row_order(order);
      if (r && r.error) showMessage("error", "Can't reorder", r.error);
      else await renderMatrix();
    });
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
      cell.dataset.rk = rk; cell.dataset.env = env;
      cell.dataset.label = snap.row_labels[rk] || rk;
      cell.dataset.baseTitle = cell.title;             // env flag appends to this base
      cell.append(main, sub);

      // Action triggers stay LIVE during a run — a 2nd click now QUEUES rather
      // than being rejected, so they are never disabled by the lock sweep.
      const acts = document.createElement("div"); acts.className = "mx-actions";
      acts.appendChild(mxActBtn("i-refresh", "Re-export this report for this environment (live)",
        false, async () => {
          const r = await api.refresh_cell_export(rk, env);
          if (r && r.error) showMessage("error", "Can't refresh", r.error);
        }));
      const supported = cmp && cmp.supported !== false;
      if (cmp !== null && supported) {
        acts.appendChild(mxActBtn("i-compare", "Rebuild this comparison", false, async () => {
          const r = await api.refresh_cell_comparison(rk, env);
          if (r && r.error) showMessage("error", "Can't compare", r.error);
        }));
        if (cmp.built) {
          const ob = mxActBtn("i-external", "Open this comparison workbook (values copy)",
            false, async () => {
              const r = await api.open_cell_comparison(rk, env);
              if (r && r.error) showMessage("error", "Can't open", r.error);
            });
          ob.classList.add("mx-open"); acts.appendChild(ob);
          // On-demand evidence images for the EXISTING vs-TSN comparison (no
          // re-compare; works with the Evidence images toggle off). Fresh
          // tsn-mode cells of evidence-capable rows only — a stale cell needs
          // a comparison rebuild first (which regenerates evidence itself
          // when the toggle is on).
          if (snap.modes[rk] === "tsn" && !cmp.stale && evidenceActionInfo(rk)) {
            acts.appendChild(mxActBtn("i-camera",
              "Generate/refresh the evidence images for this comparison (no re-compare)",
              false, async () => {
                const r = await api.matrix_evidence_cell(rk, env);
                if (r && r.error) showMessage("error", "Can't run evidence", r.error);
              }));
          }
        }
      }
      cell.appendChild(acts);
      grid.appendChild(cell);
    });
  });
  applyMatrixEnvFlags();              // overlay env-access warnings on the grid

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
      // CMP-AUD-099: only the cross-environment cells changed their reference side;
      // "stale" scope rebuilds exactly those and leaves fresh vs-TSN / self-check
      // cells (baseline-independent) alone — "all" would needlessly rebuild them.
      await api.recompute_matrix("stale");
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
  const pauseBtn = $("btnMatrixPause");
  if (pauseBtn) pauseBtn.onclick = () => api.pause_or_resume();
  const skipBtn = $("btnMatrixSkip");
  if (skipBtn) skipBtn.onclick = () => api.skip_route();

  renderMatrixConfig(snap, locked);
  updateMatrixProgress();
}

// ---- Compare-tab "TSN by day" matrix --------------------------------------
// A manual day-picking matrix: rows = report types, columns = exported days the
// user adds, each cell = that day's export vs TSN. Reuses the matrix cell vocab
// (mxCellContent / mxActBtn / mxHeadBtn) + the shared queue panel; no live
// re-export and no cross-environment (only ⟳ rebuild + open).
async function renderDayMatrix() {
  const grid = $("dayMatrixGrid");
  if (!grid) return;
  const seq = ++_dayRenderSeq;
  let snap;
  try { snap = await api.day_matrix_info(); } catch (e) { return; }
  if (seq !== _dayRenderSeq) return;      // a newer render started; drop this one
  if (!snap) return;
  const days = snap.days || [], locked = !!(S.st && S.st.task);
  const today = snap.today;          // the one EXPORTABLE column (past = locked)
  grid.dataset.srcEnv = snap.source || "";   // env-access flags key on the source env

  const srcSel = $("dayMatrixSource");
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
      const r = await api.set_day_matrix_source(srcSel.value);
      if (r && r.error) showMessage("error", "Can't set source", r.error);
      await renderDayMatrix();
    };
  }

  const addSel = $("dayMatrixAddDay"), addBtn = $("btnDayAddDay");
  const avail = (snap.available_days || []).filter((d) => !days.includes(d));
  if (addSel) {
    addSel.textContent = "";
    if (!avail.length) {
      const o = document.createElement("option");
      o.value = ""; o.textContent = days.length ? "— no more exported days —" : "— no exported days —";
      addSel.appendChild(o);
    } else {
      avail.forEach((d) => {
        const o = document.createElement("option"); o.value = d; o.textContent = d;
        addSel.appendChild(o);
      });
    }
    addSel.disabled = locked || !avail.length;
  }
  if (addBtn) {
    addBtn.disabled = locked || !avail.length;
    addBtn.onclick = async () => {
      const d = $("dayMatrixAddDay").value;
      if (!d) return;
      const r = await api.add_day_matrix_day(d);
      if (r && r.error) showMessage("error", "Can't add day", r.error);
      await renderDayMatrix();
    };
  }

  // (TSN dataset pickers are PER-ROW now — in each row header, named by its
  //  report — exactly like the Everything matrix; the old single shared picker
  //  in this config corner is gone.)

  // Report show/hide toggles (parity with the Everything matrix's config zone).
  // The " (soon)" suffix below is defensive — every report is wired as of v0.17.0,
  // so it only renders if a future report ships before its by-day comparator does.
  const rtog = $("dayMatrixReportToggles");
  if (rtog) {
    rtog.textContent = "";
    const hidden = new Set(snap.hidden || []);
    (snap.all_rows || []).forEach((r) => {
      const isOn = !hidden.has(r.key);
      const b = document.createElement("button");
      b.className = "mx-toggle" + (isOn ? " on" : "");
      b.textContent = r.label + (r.supported ? "" : " (soon)");
      b.disabled = locked;
      b.title = (isOn ? "Hide " : "Show ") + r.label;
      b.onclick = async () => {
        const res = await api.set_day_matrix_report(r.key, !isOn);
        if (res && res.error) { showMessage("error", "Can't toggle", res.error); return; }
        await renderDayMatrix();
      };
      rtog.appendChild(b);
    });
  }

  grid.textContent = "";
  if (!days.length) {
    grid.style.gridTemplateColumns = ""; grid.style.gridTemplateRows = "";
    const empty = document.createElement("div");
    empty.className = "dm-empty";
    empty.textContent = "Add an export day from Matrix options to compare it against TSN.";
    grid.appendChild(empty);
    wireDayMatrixFooter();
    updateDayMatrixProgress();
    return;
  }
  grid.style.gridTemplateColumns = `minmax(190px,1.1fr) repeat(${days.length}, minmax(120px,1fr))`;
  grid.style.gridTemplateRows = `auto repeat(${snap.rows.length}, minmax(50px,1fr))`;

  const corner = document.createElement("div");
  corner.className = "mx-cell mx-corner mx-colhead";
  corner.textContent = "Report \\ Day";
  grid.appendChild(corner);
  const dayCons = snap.day_consolidated || {};
  days.forEach((d) => {
    const h = document.createElement("div");
    h.className = "mx-cell mx-colhead";
    const lab = document.createElement("div"); lab.textContent = d;
    h.appendChild(lab);
    h.appendChild(dmConsolidatedBadge(d, dayCons[d] || { exists: false, fresh: false, actionable: false }));
    const btns = document.createElement("span"); btns.className = "mxch-btns";
    // Export is offered ONLY for today's column — past days are the immutable
    // record you pulled (re-exporting them would overwrite with today's data).
    if (d === today) {
      btns.appendChild(mxHeadBtn("i-refresh",
        `Export every report for ${d} (today) from TSMIS, then compare vs TSN`,
        "mxch-reexport", async () => {
          const r = await api.export_day_column();
          if (r && r.error) showMessage("error", "Can't export", r.error);
        }));
    }
    btns.append(
      mxHeadBtn("i-compare", `Rebuild every report for ${d}`, "mxch-rebuild", async () => {
        const r = await api.rebuild_day_matrix("all", null, d);
        if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells in this day.");
        else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
      }),
      mxHeadBtn("i-trash", `Remove the ${d} column`, "mxch-rm", async () => {
        await api.remove_day_matrix_day(d); await renderDayMatrix();
      }));
    h.appendChild(btns);
    grid.appendChild(h);
  });

  snap.rows.forEach((rk) => {
    const supported = !!snap.row_supported[rk];
    const rlabel = snap.row_labels[rk] || rk;
    const rh = document.createElement("div"); rh.className = "mx-cell mx-rowhead";
    rh.dataset.rk = rk; rh.dataset.label = rlabel;   // env-access flag target
    const top = document.createElement("div"); top.className = "mxrh-top";
    const lbl = document.createElement("span"); lbl.className = "mxrh-label";
    lbl.textContent = rlabel + (supported ? "" : " (soon)");
    const evb = supported ? evidenceRowBadge(rk) : null;
    if (evb) lbl.appendChild(evb);
    top.appendChild(lbl);
    if (supported) {
      top.appendChild(mxHeadBtn("i-refresh", `Export ${rlabel} for today + compare vs TSN`,
        "mxch-reexport", async () => {
          const r = await api.export_day_row(rk);
          if (r && r.error) showMessage("error", "Can't export", r.error);
        }));
      top.appendChild(mxHeadBtn("i-compare", `Rebuild ${rlabel} for every day`, "mxch-rebuild",
        async () => {
          const r = await api.rebuild_day_matrix("all", rk, null);
          if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells in this row.");
          else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
        }));
    }
    rh.appendChild(top);
    // Per-row TSN dataset picker (named by its row) — replaces the old single
    // shared picker; each report shows + chooses its OWN TSN source.
    const tm = snap.tsn_meta && snap.tsn_meta[rk];
    if (tm && tm.supported) rh.appendChild(mxTsnPicker(tm, locked, renderDayMatrix));
    dndAttach(rh, top, rk, "dm-row", "y", () => snap.rows.slice(), async (order) => {
      const r = await api.set_day_matrix_row_order(order);
      if (r && r.error) showMessage("error", "Can't reorder", r.error);
      else await renderDayMatrix();
    });
    grid.appendChild(rh);
    days.forEach((d) => {
      const c = snap.cells[rk][d], cmp = c.cmp;
      const cell = document.createElement("div"); cell.className = "mx-cell";
      const main = document.createElement("div"); main.className = "mx-num";
      const sub = document.createElement("div"); sub.className = "mx-sub";
      const v = mxCellContent(cmp, tm);
      cell.classList.add(v.cls); main.textContent = v.main; sub.textContent = v.sub;
      const expWhen = c.export.present ? fmtAge(c.export.age_seconds) : "not exported";
      cell.title = `${rlabel} — ${d}\nExported: ${expWhen}`;
      cell.append(main, sub);
      if (supported) {
        const acts = document.createElement("div"); acts.className = "mx-actions";
        // Export action only on TODAY's cell (the primary action when it's not yet
        // pulled); past cells stay export-locked and offer compare/open only.
        if (d === today) {
          acts.appendChild(mxActBtn("i-refresh", "Export this report for today + compare vs TSN",
            false, async () => {
              const r = await api.export_day_cell(rk, d);
              if (r && r.error) showMessage("error", "Can't export", r.error);
            }));
        }
        // The comparison needs the TSMIS export present (W3: an export-less
        // 'today' column now always shows, so don't offer a Build that would
        // just consolidate an empty folder — export first via the action above).
        if (c.export.present) {
          acts.appendChild(mxActBtn("i-compare", "Build / rebuild this comparison vs TSN",
            false, async () => {
              const r = await api.build_day_cell(rk, d);
              if (r && r.error) showMessage("error", "Can't build", r.error);
            }));
        }
        if (cmp && cmp.built) {
          const ob = mxActBtn("i-external", "Open this comparison workbook (values copy)",
            false, async () => {
              const r = await api.open_day_cell_comparison(rk, d);
              if (r && r.error) showMessage("error", "Can't open", r.error);
            });
          ob.classList.add("mx-open"); acts.appendChild(ob);
          // On-demand evidence for the EXISTING comparison (by-day cells are
          // always vs-TSN). Fresh cells of evidence-capable rows only.
          if (!cmp.stale && evidenceActionInfo(rk)) {
            acts.appendChild(mxActBtn("i-camera",
              "Generate/refresh the evidence images for this comparison (no re-compare)",
              false, async () => {
                const r = await api.day_matrix_evidence_cell(rk, d);
                if (r && r.error) showMessage("error", "Can't run evidence", r.error);
              }));
          }
        }
        cell.appendChild(acts);
      }
      grid.appendChild(cell);
    });
  });

  wireDayMatrixFooter();
  updateDayMatrixProgress();
  applyMatrixEnvFlags();              // overlay env-access warnings on the row headers
}

// A small per-day "consolidated workbook" indicator + refresh-consolidated action.
// Reuse means a comparison doesn't re-consolidate the day's export every time; the
// badge shows whether a fresh consolidated exists, and clicking it force-rebuilds
// it (e.g. after the consolidation mechanism changes).
function dmConsolidatedBadge(date, state) {
  const b = document.createElement("button");
  b.appendChild(icon("i-layers"));
  // CMP-AUD-093: when the refresh-consolidated action has no target this day (no
  // visible, TSN-ready, exported cell), the badge is informational only — a click
  // would resolve zero targets and drain. Show a disabled "not applicable" state
  // rather than inviting a no-op.
  if (state.actionable === false) {
    b.className = "dm-cons dm-cons-none";
    b.disabled = true;
    b.title = `No vs-TSN consolidation for ${date} — add a TSN file and an export for a report first.`;
    b.setAttribute("aria-label", b.title);
    return b;
  }
  const cls = !state.exists ? "dm-cons-none" : state.fresh ? "dm-cons-fresh" : "dm-cons-stale";
  b.className = "dm-cons " + cls;
  b.title = !state.exists
    ? `No consolidated workbook for ${date} yet — built on first compare. Click to (re)consolidate now.`
    : state.fresh
      ? `Consolidated workbook ready for ${date} (reused by comparisons). Click to re-consolidate.`
      : `Consolidated for ${date} is stale — a newer export exists. Click to re-consolidate.`;
  b.setAttribute("aria-label", b.title);
  b.onclick = async () => {
    const r = await api.rebuild_day_matrix("all", null, date, true);   // force re-consolidate
    if (r && r.nothing) showMessage("info", "Nothing to consolidate",
      "Add a TSN file and an export for this day first.");
    else if (r && r.error) showMessage("error", "Can't re-consolidate", r.error);
  };
  return b;
}

function wireDayMatrixFooter() {
  const ba = $("btnDayBuildAll");
  if (ba) ba.onclick = async () => {
    const r = await api.rebuild_day_matrix("all");
    if (r && r.nothing) showMessage("info", "Nothing to build", "Add days (and a TSN file) first.");
    else if (r && r.error) showMessage("error", "Can't build", r.error);
  };
  const rb = $("btnDayRebuildAll");
  if (rb) rb.onclick = async () => {
    const r = await api.rebuild_day_matrix("stale");
    if (r && r.nothing) showMessage("info", "Up to date", "Every by-day comparison is current.");
    else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
  };
  const of = $("btnOpenDayComparisons");
  if (of) of.onclick = async () => {
    const r = await api.open_day_comparisons_folder();
    if (r && r.error) showMessage("error", "Can't open", r.error);
  };
  const ex = $("btnDayExportToday");
  if (ex) ex.onclick = async () => {
    const r = await api.export_day_column();
    if (r && r.error) showMessage("error", "Can't export", r.error);
  };
  const cb = $("btnDayCancel");
  if (cb) cb.onclick = () => api.cancel_run();
  const pb = $("btnDayPause");
  if (pb) pb.onclick = () => api.pause_or_resume();
  const sb = $("btnDaySkip");
  if (sb) sb.onclick = () => api.skip_route();
}

function updateDayMatrixProgress() {
  const el = $("dayMatrixProgress");
  if (el) {
    const m = S.st && S.st.matrix;
    if (m && m.total) { el.hidden = false; el.textContent = `Comparing ${m.done}/${m.total}…`; }
    else el.hidden = true;
  }
  const locked = !!(S.st && S.st.task);
  document.querySelectorAll(
    "#dayMatrixSection .mx-linkbtn, #dayMatrixConfig .mx-linkbtn, "
    + "#dayMatrixSource, #dayMatrixReportToggles .mx-toggle")
    .forEach((c) => { c.disabled = locked; });
  // Add-day controls: disable on lock OR when there are no days left to add (the
  // latter is owned by renderDayMatrix). Don't blindly re-enable here — that would
  // override the "no exported days" guard on a plain state push.
  const addSel = $("dayMatrixAddDay"), addBtn = $("btnDayAddDay");
  const noAvail = !addSel || !addSel.querySelector('option[value]:not([value=""])');
  if (addSel) addSel.disabled = locked || noAvail;
  if (addBtn) addBtn.disabled = locked || noAvail;
  const exportBtn = $("btnDayExportToday");
  // CMP-AUD-104: export_day_column ENQUEUES onto the shared matrix queue (a 2nd
  // click queues behind the running job), exactly like the per-cell/row export
  // actions that stay live and the by-day Build/Rebuild-all footer buttons — so it
  // must NOT be lock-disabled while busy, or one queue-capable action would
  // uniquely refuse work its equivalents accept.
  if (exportBtn) exportBtn.disabled = false;
  const cancel = $("btnDayCancel");
  if (cancel) {
    const running = !!(S.st && S.st.task === "matrix");
    cancel.classList.toggle("hidden", !running);
    cancel.disabled = !running;
  }
  // Pause/Skip apply only to a by-day re-EXPORT run (today's column). The worker
  // forwards pause/skip to the engine; Skip is meaningless in fast mode.
  const cur = S.st && S.st.matrix_current;
  const exporting = !!(S.st && S.st.task === "matrix" && cur
                       && cur.kind === "export" && cur.which === "day");
  const pause = $("btnDayPause");
  if (pause) {
    pause.classList.toggle("hidden", !exporting);
    pause.disabled = !exporting;
    const u = pause.querySelector("use");
    if (u) u.setAttribute("href", S.st && S.st.paused ? "#i-play" : "#i-pause");
    const lbl = $("btnDayPauseLabel");
    if (lbl) lbl.textContent = S.st && S.st.paused ? "Resume" : "Pause";
  }
  const skip = $("btnDaySkip");
  if (skip) {
    skip.classList.toggle("hidden", !exporting);
    skip.disabled = !exporting || !!(S.st && S.st.fast_run);
  }
  renderQueuePanel("dayQueueGroup", "dayQueue", "dayQueueCount");
  syncDayMatrixFormulas();
  syncDayMatrixEvidence();
  syncDayMatrixFast();
}

// ---- Compare-tab "vs Baseline" matrix --------------------------------------
// A manual day-picking matrix: rows = report types, columns = exported days the
// user adds, each cell = that day's export vs the picked BASELINE copy of the
// same report (an earlier day's run folder, or the Everything store — same
// source, same format). Reuses the matrix cell vocab (mxCellContent / mxActBtn
// / mxHeadBtn) + the shared queue panel; compare-only — no TSN dataset, no
// live re-export, no evidence.
let _blRenderSeq = 0;

function syncBaselineMatrixFormulas() {
  syncFormulasToggle("baselineMatrixFormulas", "baseline_matrix_formulas");
}

async function renderBaselineMatrix() {
  const grid = $("baselineMatrixGrid");
  if (!grid) return;
  const seq = ++_blRenderSeq;
  let snap;
  try { snap = await api.baseline_matrix_info(); } catch (e) { return; }
  if (seq !== _blRenderSeq) return;       // a newer render started; drop this one
  if (!snap) return;
  const days = snap.days || [], locked = !!(S.st && S.st.task);
  const bl = snap.baseline || {};

  const srcSel = $("baselineMatrixSource");
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
      const r = await api.set_baseline_matrix_source(srcSel.value);
      if (r && r.error) showMessage("error", "Can't set source", r.error);
      await renderBaselineMatrix();
    };
  }

  // The baseline picker: the Everything store + every exported day, each with
  // how many of the matrix reports it covers — the "which days have an old
  // copy" answer, per option; the grid's cells answer it per report.
  const blSel = $("baselineMatrixBaseline");
  if (blSel) {
    blSel.textContent = "";
    const opts = snap.baseline_options || [];
    const none = document.createElement("option");
    none.value = "";
    none.textContent = opts.length ? "— pick a baseline —" : "— no exported days yet —";
    blSel.appendChild(none);
    opts.forEach((o) => {
      const el = document.createElement("option");
      el.value = o.id;
      el.textContent = `${o.label}  (${o.present}/${o.total} reports)`;
      if (o.id === bl.id) el.selected = true;
      blSel.appendChild(el);
    });
    blSel.disabled = locked || !opts.length;
    blSel.onchange = async () => {
      const r = await api.set_baseline_matrix_baseline(blSel.value);
      if (r && r.error) showMessage("error", "Can't set baseline", r.error);
      await renderBaselineMatrix();
    };
  }

  const addSel = $("baselineMatrixAddDay"), addBtn = $("btnBaselineAddDay");
  const avail = (snap.available_days || []).filter((d) => !days.includes(d));
  if (addSel) {
    addSel.textContent = "";
    if (!avail.length) {
      const o = document.createElement("option");
      o.value = ""; o.textContent = days.length ? "— no more exported days —" : "— no exported days —";
      addSel.appendChild(o);
    } else {
      avail.forEach((d) => {
        const o = document.createElement("option"); o.value = d; o.textContent = d;
        addSel.appendChild(o);
      });
    }
    addSel.disabled = locked || !avail.length;
  }
  if (addBtn) {
    addBtn.disabled = locked || !avail.length;
    addBtn.onclick = async () => {
      const d = $("baselineMatrixAddDay").value;
      if (!d) return;
      const r = await api.add_baseline_matrix_day(d);
      if (r && r.error) showMessage("error", "Can't add day", r.error);
      await renderBaselineMatrix();
    };
  }

  const rtog = $("baselineMatrixReportToggles");
  if (rtog) {
    rtog.textContent = "";
    const hidden = new Set(snap.hidden || []);
    (snap.all_rows || []).forEach((r) => {
      const isOn = !hidden.has(r.key);
      const b = document.createElement("button");
      b.className = "mx-toggle" + (isOn ? " on" : "");
      b.textContent = r.label + (r.supported ? "" : " (soon)");
      b.disabled = locked;
      b.title = (isOn ? "Hide " : "Show ") + r.label;
      b.onclick = async () => {
        const res = await api.set_baseline_matrix_report(r.key, !isOn);
        if (res && res.error) { showMessage("error", "Can't toggle", res.error); return; }
        await renderBaselineMatrix();
      };
      rtog.appendChild(b);
    });
  }

  grid.textContent = "";
  if (!days.length) {
    grid.style.gridTemplateColumns = ""; grid.style.gridTemplateRows = "";
    const empty = document.createElement("div");
    empty.className = "dm-empty";
    empty.textContent = "Add an export day from Matrix options, then pick a "
      + "baseline to compare it against.";
    grid.appendChild(empty);
    wireBaselineMatrixFooter();
    updateBaselineMatrixProgress();
    return;
  }
  grid.style.gridTemplateColumns = `minmax(190px,1.1fr) repeat(${days.length}, minmax(120px,1fr))`;
  grid.style.gridTemplateRows = `auto repeat(${snap.rows.length}, minmax(50px,1fr))`;

  const corner = document.createElement("div");
  corner.className = "mx-cell mx-corner mx-colhead";
  corner.textContent = "Report \\ Day";
  grid.appendChild(corner);
  days.forEach((d) => {
    const h = document.createElement("div");
    h.className = "mx-cell mx-colhead" + (d === bl.date ? " mx-baseline-col" : "");
    const lab = document.createElement("div");
    lab.textContent = d + (d === bl.date ? " (baseline)" : "");
    h.appendChild(lab);
    const btns = document.createElement("span"); btns.className = "mxch-btns";
    if (d !== bl.date) {
      btns.appendChild(
        mxHeadBtn("i-compare", `Rebuild every report for ${d} vs the baseline`,
          "mxch-rebuild", async () => {
            const r = await api.rebuild_baseline_matrix("all", null, d);
            if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells in this day.");
            else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
          }));
    }
    btns.appendChild(
      mxHeadBtn("i-trash", `Remove the ${d} column`, "mxch-rm", async () => {
        await api.remove_baseline_matrix_day(d); await renderBaselineMatrix();
      }));
    h.appendChild(btns);
    grid.appendChild(h);
  });

  snap.rows.forEach((rk) => {
    const supported = !!snap.row_supported[rk];
    const rlabel = snap.row_labels[rk] || rk;
    const rh = document.createElement("div"); rh.className = "mx-cell mx-rowhead";
    rh.dataset.rk = rk; rh.dataset.label = rlabel;
    const top = document.createElement("div"); top.className = "mxrh-top";
    const lbl = document.createElement("span"); lbl.className = "mxrh-label";
    lbl.textContent = rlabel + (supported ? "" : " (soon)");
    top.appendChild(lbl);
    if (supported && bl.id) {
      top.appendChild(mxHeadBtn("i-compare", `Rebuild ${rlabel} for every day vs the baseline`,
        "mxch-rebuild", async () => {
          const r = await api.rebuild_baseline_matrix("all", rk, null);
          if (r && r.nothing) showMessage("info", "Nothing to rebuild", "No comparable cells in this row.");
          else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
        }));
    }
    rh.appendChild(top);
    dndAttach(rh, top, rk, "bl-row", "y", () => snap.rows.slice(), async (order) => {
      const r = await api.set_baseline_matrix_row_order(order);
      if (r && r.error) showMessage("error", "Can't reorder", r.error);
      else await renderBaselineMatrix();
    });
    grid.appendChild(rh);
    days.forEach((d) => {
      const c = snap.cells[rk][d], cmp = c.cmp;
      const cell = document.createElement("div"); cell.className = "mx-cell";
      const main = document.createElement("div"); main.className = "mx-num";
      const sub = document.createElement("div"); sub.className = "mx-sub";
      const expWhen = c.export.present ? fmtAge(c.export.age_seconds) : "not exported";
      if (!bl.id) {                        // no baseline picked yet
        cell.classList.add("mx-na"); main.textContent = "—"; sub.textContent = "pick a baseline";
      } else if (cmp && cmp.is_baseline) {  // the baseline's own column
        cell.classList.add("mx-baseline-col");
        main.textContent = "baseline"; sub.textContent = expWhen;
      } else {
        const v = mxCellContent(cmp);
        cell.classList.add(v.cls); main.textContent = v.main; sub.textContent = v.sub;
      }
      cell.title = `${rlabel} — ${d} vs ${bl.label || "baseline"}\nExported: ${expWhen}`;
      cell.append(main, sub);
      if (supported && bl.id && cmp && !cmp.is_baseline) {
        const acts = document.createElement("div"); acts.className = "mx-actions";
        if (!cmp.missing_side) {
          acts.appendChild(mxActBtn("i-compare", "Build / rebuild this comparison vs the baseline",
            false, async () => {
              const r = await api.build_baseline_matrix_cell(rk, d);
              if (r && r.error) showMessage("error", "Can't build", r.error);
            }));
        }
        if (cmp.built) {
          const ob = mxActBtn("i-external", "Open this comparison workbook (values copy)",
            false, async () => {
              const r = await api.open_baseline_cell_comparison(rk, d);
              if (r && r.error) showMessage("error", "Can't open", r.error);
            });
          ob.classList.add("mx-open"); acts.appendChild(ob);
        }
        cell.appendChild(acts);
      }
      grid.appendChild(cell);
    });
  });

  wireBaselineMatrixFooter();
  updateBaselineMatrixProgress();
}

function wireBaselineMatrixFooter() {
  const ba = $("btnBaselineBuildAll");
  if (ba) ba.onclick = async () => {
    const r = await api.rebuild_baseline_matrix("all");
    if (r && r.nothing) showMessage("info", "Nothing to build", "Add days and pick a baseline first.");
    else if (r && r.error) showMessage("error", "Can't build", r.error);
  };
  const rb = $("btnBaselineRebuildAll");
  if (rb) rb.onclick = async () => {
    const r = await api.rebuild_baseline_matrix("stale");
    if (r && r.nothing) showMessage("info", "Up to date", "Every vs-baseline comparison is current.");
    else if (r && r.error) showMessage("error", "Can't rebuild", r.error);
  };
  const of = $("btnOpenBaselineComparisons");
  if (of) of.onclick = async () => {
    const r = await api.open_baseline_comparisons_folder();
    if (r && r.error) showMessage("error", "Can't open", r.error);
  };
  const cb = $("btnBaselineCancel");
  if (cb) cb.onclick = () => api.cancel_run();
}

function updateBaselineMatrixProgress() {
  const el = $("baselineMatrixProgress");
  if (el) {
    const m = S.st && S.st.matrix;
    if (m && m.total) { el.hidden = false; el.textContent = `Comparing ${m.done}/${m.total}…`; }
    else el.hidden = true;
  }
  const locked = !!(S.st && S.st.task);
  document.querySelectorAll(
    "#baselineMatrixSource, #baselineMatrixBaseline, "
    + "#baselineMatrixReportToggles .mx-toggle")
    .forEach((c) => { c.disabled = locked; });
  // Add-day controls: disable on lock OR when there are no days left to add
  // (the latter is owned by renderBaselineMatrix — don't blindly re-enable).
  const addSel = $("baselineMatrixAddDay"), addBtn = $("btnBaselineAddDay");
  const noAvail = !addSel || !addSel.querySelector('option[value]:not([value=""])');
  if (addSel) addSel.disabled = locked || noAvail;
  if (addBtn) addBtn.disabled = locked || noAvail;
  const cancel = $("btnBaselineCancel");
  if (cancel) {
    const running = !!(S.st && S.st.task === "matrix");
    cancel.classList.toggle("hidden", !running);
    cancel.disabled = !running;
  }
  renderQueuePanel("baselineQueueGroup", "baselineQueue", "baselineQueueCount");
  syncBaselineMatrixFormulas();
}
