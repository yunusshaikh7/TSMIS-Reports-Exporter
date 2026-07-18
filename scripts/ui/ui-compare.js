// Compare-tab module (S5 / FE-01, split from app.js — same global scope).
// Owns: the comparison-type groups/sub-tabs (incl. the by-day matrix group +
// body.matrix-wide), the file/folder pickers, and start_compare.
// ---- comparisons (files kind = TSMIS vs TSN; folders kind = env vs env) ----
const CMP = { tsmis: null, tsn: null };

function compareKind() {
  // Resolve by KEY (P3) — compareChoice() returns a `cmp:*` key, so the old
  // array[index] lookup always read undefined and defaulted every comparison to
  // "files", routing folder compares to the file path. currentCompareRep() finds
  // the row by key.
  return currentCompareRep().kind || "files";
}

// Switch the Compare sub-tab: highlight the button, show only that group's
// comparison-type rows, and keep exactly one VISIBLE row selected. Radios share a
// name, so seating a new pick natively drops the now-hidden previous one;
// renderCompareKind then swaps in the matching files/folders inputs.
const DAY_MATRIX_GROUP = "tsn_by_day";
const BASELINE_MATRIX_GROUP = "baseline_by_day";

// Full-width "matrix" layout is shared by the Everything comparison matrix and the
// Compare-tab day matrices. Compute it from the active tab/sub-tab in ONE place so
// every entry point (tab switch, Everything sub-tab, compare-group switch) stays in
// sync. body.matrix-wide drives the shared layout (grid fills the screen, activity
// log shrinks); body.mw-day / body.mw-bl additionally pick that matrix's config corner.
function applyMatrixWide() {
  const every = S.tab === "everything" && S.everySub === "matrix";
  const day = S.tab === "compare" && S.compareGroup === DAY_MATRIX_GROUP;
  const bl = S.tab === "compare" && S.compareGroup === BASELINE_MATRIX_GROUP;
  document.body.classList.toggle("matrix-wide", every || day || bl);
  document.body.classList.toggle("mw-day", day);
  document.body.classList.toggle("mw-bl", bl);
}

function selectCompareGroup(groupId) {
  S.compareGroup = groupId;
  document.querySelectorAll("#compareSubtabs .subtab").forEach((b) => {
    const on = b.dataset.group === groupId;
    b.classList.toggle("active", on);
    b.setAttribute("aria-selected", String(on));
  });
  // The day matrices swap the whole classic picker out for their grid and go
  // full-width (same treatment as the Everything matrix).
  const dayMode = groupId === DAY_MATRIX_GROUP;
  const blMode = groupId === BASELINE_MATRIX_GROUP;
  $("compareClassic")?.classList.toggle("hidden", dayMode || blMode);
  $("dayMatrixSection")?.classList.toggle("hidden", !dayMode);
  $("baselineMatrixSection")?.classList.toggle("hidden", !blMode);
  applyMatrixWide();
  if (dayMode) { renderDayMatrix(); return; }
  if (blMode) { renderBaselineMatrix(); return; }
  // family headers (W2) filter with their sub-tab, like the rows
  $("compareList").querySelectorAll(".option-group").forEach((h) => {
    h.classList.toggle("hidden", h.dataset.group !== groupId);
  });
  const rows = [...$("compareList").querySelectorAll(".option-row")];
  let firstVisible = null, checkedVisible = false;
  rows.forEach((r) => {
    const on = r.dataset.group === groupId;
    r.classList.toggle("hidden", !on);
    if (on) {
      firstVisible = firstVisible || r;
      if (r.querySelector("input").checked) checkedVisible = true;
    }
  });
  if (!checkedVisible && firstVisible) {
    rows.forEach((r) => r.classList.remove("checked"));
    firstVisible.querySelector("input").checked = true;
    firstVisible.classList.add("checked");
  }
  renderCompareKind();
}

function renderCompareFiles() {
  for (const [side, id] of [["tsmis", "cmpTsmisPath"], ["tsn", "cmpTsnPath"]]) {
    const el = $(id);
    el.textContent = CMP[side] || "— not selected —";
    el.title = CMP[side] || "";
    el.classList.toggle("unset", !CMP[side]);
  }
  syncCompareButton();
}

// Folder dropdowns: the known run folders (newest first) plus any custom
// path picked via Browse… (kept as an extra option per side).
const CMP_DIRS = { a: null, b: null };   // custom absolute paths from Browse…

function fillCompareDirSelect(sel, custom, preferred, days) {
  days = days || [];
  const prev = sel.value;
  sel.textContent = "";
  if (custom) {
    const o = document.createElement("option");
    o.value = custom; o.textContent = custom;
    sel.appendChild(o);
  }
  days.forEach((d) => {
    const o = document.createElement("option");
    o.value = d; o.textContent = d;
    sel.appendChild(o);
  });
  if (!days.length && !custom) {
    const o = document.createElement("option");
    o.value = ""; o.textContent = "— no export folders yet —";
    sel.appendChild(o);
  }
  const options = [...sel.options].map((o) => o.value);
  // The user's CURRENT selection survives every re-render; the Browse… path is
  // just an extra OPTION, not an override (it used to win here on every state
  // re-render, silently stomping a later dropdown pick — the comparison then
  // ran against the stale custom folder). Browse takes effect via
  // pickCompareFolder setting the value explicitly, once.
  if (prev && options.includes(prev)) sel.value = prev;
  else if (preferred && options.includes(preferred)) sel.value = preferred;
  else if (custom) sel.value = custom;
}

// CMP-AUD-072: folder discovery is async AND per-recipe. Without sequencing, a
// slow get_compare_folders response for a since-abandoned recipe arrives last and
// stomps the current recipe's folder lists (rapid A->B->A), so the wrong day
// choices can be launched through the newer adapter. Snapshot a generation token
// AND the recipe key (mirrors refreshConsDest's consDestSeq guard), discard any
// non-latest / recipe-changed response, and hold Start disabled while a discovery
// is unresolved so nothing launches against a stale/empty list.
let compareDirsSeq = 0;
let compareDirsLoading = false;

async function renderCompareDirs() {
  // A2: only offer run folders that actually contain the chosen report. Python
  // owns the membership test (api.get_compare_folders); fall back to all known
  // folders on any hiccup so the dropdowns are never empty by mistake.
  const seq = ++compareDirsSeq;
  const key = compareChoice();          // the recipe THIS discovery is for
  compareDirsLoading = true;
  syncCompareButton();                  // Start off while options load
  let days = (S.st && S.st.days) || [];
  try {
    const res = await api.get_compare_folders(key);
    if (seq !== compareDirsSeq) return;         // a newer discovery superseded this
    if (res && Array.isArray(res.folders)) days = res.folders;
  } catch (e) {
    if (seq !== compareDirsSeq) return;         // stale failure — the newer render owns the UI
    /* keep the unfiltered list */
  }
  if (key !== compareChoice()) return;          // recipe changed under us (belt + suspenders)
  compareDirsLoading = false;
  // sensible defaults: baseline = newest ssor-prod run, other side = the
  // newest folder that differs from the baseline
  const baseline = days.find((d) => /ssor-prod$/.test(d)) || days[0] || "";
  fillCompareDirSelect($("cmpDirA"), CMP_DIRS.a, baseline, days);
  const other = days.find((d) => d !== $("cmpDirA").value) || days[0] || "";
  fillCompareDirSelect($("cmpDirB"), CMP_DIRS.b, other, days);
  syncCompareButton();
}

function renderCompareKind() {
  const folders = compareKind() === "folders";
  $("cmpFilesSection").classList.toggle("hidden", folders);
  $("cmpFoldersSection").classList.toggle("hidden", !folders);
  if (folders) {
    renderCompareDirs();
  } else {
    // Label the two file pickers from the selected comparison so a
    // PDF-vs-Excel comparison doesn't say "TSN" for a TSMIS Excel file.
    const rep = currentCompareRep();
    const a = rep.file_a_label || "TSMIS", b = rep.file_b_label || "TSN";
    $("cmpTsmisLabel").textContent = a + " file";
    $("cmpTsnLabel").textContent = b + " file";
    // CMP-AUD-074: the per-side shape is registry-owned (report_catalog input
    // profiles) — only the 3 Highway Log recipes accept a per-route file, and the
    // 2 Summary-vs-TSN recipes take a raw statewide TSN PDF on the TSN side. Fall
    // back to the consolidated shape if the payload predates the profile.
    const consolidated = "a consolidated workbook (all routes)";
    const shapeA = rep.file_a_shape || consolidated;
    const shapeB = rep.file_b_shape || consolidated;
    $("cmpFilesHint").textContent = (shapeA === shapeB)
      ? `Pick the ${a} file and the ${b} file — each ${shapeA}.`
      : `Pick the ${a} file: ${shapeA}. And the ${b} file: ${shapeB}.`;
  }
  syncCompareButton();
}

function syncCompareButton() {
  const locked = S.st && S.st.task != null;
  const anyOut = $("cmpWantValues").checked || $("cmpWantFormulas").checked;
  // CMP-AUD-072: while a folder discovery is unresolved the run-folder options
  // aren't trustworthy yet, so a folder comparison is NOT ready (Start disabled).
  const loading = compareKind() === "folders" && compareDirsLoading;
  const ready = compareKind() === "folders"
    ? (!loading && $("cmpDirA").value && $("cmpDirB").value
       && $("cmpDirA").value !== $("cmpDirB").value)
    : (CMP.tsmis && CMP.tsn);
  $("btnStartCompare").disabled = locked || !ready || !anyOut;
  // A disabled primary button always says WHY (hover) — never a mystery grey.
  $("btnStartCompare").title = locked
    ? "Another task is running — it finishes (or you cancel it) first."
    : !anyOut ? "Tick at least one output format above first."
    : loading ? "Finding the run folders for this report…"
    : !ready ? (compareKind() === "folders"
        ? "Pick two different run folders above first."
        : "Pick both input files above first.")
    : "";
  $("cmpOutHint").textContent = anyOut
    ? "Pick one or both. With both, the values copy is saved next to the other as “… (values).xlsx”."
    : "Tick at least one output to enable the comparison.";
  renderPreflight();
}

async function pickCompareFile(side) {
  // CMP-AUD-073: pass the selected recipe key so the native dialog offers the
  // extensions this recipe/side actually accepts (a raw TSN PDF for the two
  // Summary-vs-TSN recipes' TSN side; Excel elsewhere).
  const res = await api.pick_compare_file(side.toUpperCase(), compareChoice());
  if (res && res.path) {
    CMP[side] = res.path;
    renderCompareFiles();
  }
}

async function pickCompareFolder(side) {
  const res = await api.pick_compare_folder(side.toUpperCase());
  if (res && res.path) {
    CMP_DIRS[side] = res.path;
    await renderCompareDirs();
    // Browsing IS an explicit selection (once) — later dropdown picks stick.
    $(side === "a" ? "cmpDirA" : "cmpDirB").value = res.path;
    syncCompareButton();
  }
}

async function startCompare() {
  let res;
  if (compareKind() === "folders") {
    res = await api.start_compare_env(compareChoice(),
                                      $("cmpDirA").value, $("cmpDirB").value,
                                      $("cmpWantFormulas").checked,
                                      $("cmpWantValues").checked);
  } else {
    res = await api.start_compare(compareChoice(), CMP.tsmis, CMP.tsn,
                                  $("cmpWantFormulas").checked,
                                  $("cmpWantValues").checked);
  }
  if (res && res.confirm_required) {
    const accepted = await showConfirm({
      title: "Overwrite the values workbook?",
      message: res.message ||
        `The automatically created values workbook already exists:\n\n${res.path}\n\nOverwrite this exact file?`,
      confirmLabel: "Overwrite values copy",
      cancelLabel: "Keep existing file",
      danger: true,
    });
    // The follow-up carries only the opaque token + decision. Inputs, output,
    // and mode remain bound to the operation retained by the Python bridge.
    res = await api.confirm_compare_overwrite(res.confirm_token, accepted);
  }
  if (res && res.error) showMessage("error", "Could not start", res.error);
}
