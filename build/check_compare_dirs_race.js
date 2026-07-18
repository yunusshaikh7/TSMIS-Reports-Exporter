// CMP-AUD-072 race guard: Compare-tab folder discovery is async AND per-recipe.
// Without sequencing, a SLOW get_compare_folders response for a since-abandoned
// recipe arrives last and stomps the current recipe's folder lists (rapid
// A->B->A), so the wrong day choices can be launched through the newer adapter.
// renderCompareDirs must (1) discard a superseded/recipe-changed response and
// (2) hold Start disabled while a discovery is unresolved.
//
// Extracts the real functions from scripts/ui/{app,ui-compare}.js and drives them
// in a vm sandbox with DEFERRED get_compare_folders promises resolved out of order.
//
// Run from the repo root:  node build/check_compare_dirs_race.js
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const src = fs.readFileSync(path.join(__dirname, "..", "scripts", "ui", "app.js"), "utf8")
  + fs.readFileSync(path.join(__dirname, "..", "scripts", "ui", "ui-compare.js"), "utf8");

function extract(re, label) {
  const m = src.match(re);
  if (!m) { console.error(`FAIL: could not extract ${label}`); process.exit(1); }
  return m[0];
}
const srcs = [
  extract(/function compareChoice\(\) \{[\s\S]*?\n\}/, "compareChoice"),
  extract(/function currentCompareRep\(\) \{[\s\S]*?\n\}/, "currentCompareRep"),
  extract(/function compareKind\(\) \{[\s\S]*?\n\}/, "compareKind"),
  extract(/function syncCompareButton\(\) \{[\s\S]*?\n\}/, "syncCompareButton"),
  extract(/async function renderCompareDirs\(\) \{[\s\S]*?\n\}/, "renderCompareDirs"),
].join("\n");

const fails = [];
function check(name, cond) {
  console.log(`  [${cond ? "OK " : "FAIL"}] ${name}`);
  if (!cond) fails.push(name);
}
const tick = () => new Promise((r) => setTimeout(r, 0));

// --- sandbox ---------------------------------------------------------------
const els = {};
const deferreds = [];              // one per get_compare_folders call, resolved by hand
const sandbox = {
  // module-level state renderCompareDirs owns (declared in ui-compare.js; provided
  // here as context globals so the extracted function can read/write them).
  compareDirsSeq: 0,
  compareDirsLoading: false,
  CMP: { tsmis: null, tsn: null },
  CMP_DIRS: { a: null, b: null },
  S: { init: { compare_reports: [
        { key: "cmp:ramp_summary:env", kind: "folders" },
        { key: "cmp:ramp_detail:env", kind: "folders" },
      ] }, st: { task: null, days: ["seed"] } },
  __checked: null,
  __appliedDays: null,
  renderPreflight: () => {},
  fillCompareDirSelect: (sel, _custom, preferred, days) => {
    sandbox.__appliedDays = days.slice();       // what the UI ended up showing
    sel.value = preferred || days[0] || "";
  },
};
sandbox.$ = (id) => {
  if (id === "compareList") {
    return { querySelector: () => (sandbox.__checked == null
              ? null : { dataset: { key: sandbox.__checked } }) };
  }
  if (!els[id]) {
    els[id] = { value: "", checked: true, disabled: false, title: "",
                classList: { toggle() {}, add() {}, remove() {} } };
  }
  return els[id];
};
sandbox.api = {
  // returns a promise we resolve by hand; tagged with the recipe key it was called for.
  get_compare_folders: (key) => new Promise((resolve) => { deferreds.push({ key, resolve }); }),
};
// Pre-populate the two dir dropdowns with distinct values so that — WITHOUT the
// loading guard — syncCompareButton would compute ready=true (Start enabled) during
// an unresolved discovery. This makes the "Start disabled while loading" check
// genuinely red without the fix, instead of passing on empty-dropdown luck.
const _el = () => ({ value: "", checked: true, disabled: false, title: "",
                     classList: { toggle() {}, add() {}, remove() {} } });
els.cmpDirA = Object.assign(_el(), { value: "PRE-A" });
els.cmpDirB = Object.assign(_el(), { value: "PRE-B" });
vm.createContext(sandbox);
vm.runInContext(srcs +
  "\nglobalThis.renderCompareDirs = renderCompareDirs;" +
  "\nglobalThis.syncCompareButton = syncCompareButton;", sandbox);

(async () => {
  // === the A->B->A race: A slow, B fast, then A's stale response arrives last ===
  sandbox.__checked = "cmp:ramp_summary:env";      // recipe A
  const pA = sandbox.renderCompareDirs();          // seq 1, awaits deferreds[0] (A)
  await tick();
  // Defensive: without the fix the old code never calls syncCompareButton during
  // the await, so btnStartCompare may not exist yet — that IS the defect (Start not
  // held disabled while loading), so treat a missing/enabled button as a clean FAIL.
  check("Start is disabled while the first discovery is unresolved",
        !!els.btnStartCompare && els.btnStartCompare.disabled === true
        && sandbox.compareDirsLoading === true);

  sandbox.__checked = "cmp:ramp_detail:env";       // recipe B (user switched)
  const pB = sandbox.renderCompareDirs();          // seq 2, awaits deferreds[1] (B)
  await tick();

  // Resolve B (the CURRENT recipe) first, then A (the abandoned one) last.
  deferreds[1].resolve({ folders: ["B-2026 ssor-prod", "B-2026 ars-prod"] });
  await pB; await tick();
  const afterB = (sandbox.__appliedDays || []).join(",");

  deferreds[0].resolve({ folders: ["A-2026 ssor-prod", "A-2026 ars-prod"] });
  await pA; await tick();
  const afterA = (sandbox.__appliedDays || []).join(",");

  check("the current recipe B's folders are applied",
        afterB.startsWith("B-"));
  check("the STALE recipe A response is discarded — B's folders still stand",
        afterA.startsWith("B-") && !afterA.includes("A-"));
  check("discovery resolved -> Start no longer force-disabled by loading",
        sandbox.compareDirsLoading === false);

  // === a clean single discovery still applies + enables ===
  sandbox.__appliedDays = null;
  sandbox.__checked = "cmp:ramp_summary:env";
  const p1 = sandbox.renderCompareDirs();          // seq 3
  await tick();
  deferreds[2].resolve({ folders: ["2026 ssor-prod", "2026 ars-prod"] });
  await p1; await tick();
  check("a clean single discovery applies its folders",
        (sandbox.__appliedDays || []).join(",") === "2026 ssor-prod,2026 ars-prod");

  // === a rejected discovery for the current recipe falls back, not crashes ===
  sandbox.__appliedDays = null;
  sandbox.__checked = "cmp:ramp_detail:env";
  const p2 = sandbox.renderCompareDirs();          // seq 4
  await tick();
  deferreds[3].resolve(Promise.reject(new Error("boom")));   // reject the inner promise
  try { await p2; } catch (_e) { /* renderCompareDirs swallows it */ }
  await tick();
  check("a rejected discovery falls back to the seed day list (no crash)",
        (sandbox.__appliedDays || []).join(",") === "seed");

  if (fails.length) {
    console.log(`\nFAILED: ${fails.length} check(s): ${fails.join(", ")}`);
    process.exit(1);
  }
  console.log("\nALL COMPARE-DIRS-RACE CHECKS PASSED");
})();
