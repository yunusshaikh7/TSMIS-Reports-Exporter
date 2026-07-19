// CMP-AUD-079: switching Compare sub-tabs can hide EVERY Cancel control. The
// classic comparison's only Cancel (btnCancelCompare) lives in the classic
// section, and the day/baseline matrix grids show their Cancel only for
// task==="matrix"; so navigating to a different sub-tab during a live run can
// leave no usable cancellation control. The fix locks the Compare sub-tab strip
// while a COMPARE-TAB comparison is live (classic compare, or a day/baseline
// matrix comparison), keeping the user on the section that owns the run's Cancel.
//
// This extracts the real `compareSubtabsShouldLock` predicate from
// scripts/ui/ui-compare.js and drives it through every task/which state. Red→green:
// pre-fix the predicate does not exist (extraction fails) — and the lock never
// fired — so idle/classic/matrix states could all strand a run with no Cancel.
//
// Run from the repo root:  node build/check_compare_cancel_visibility.js
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const src = fs.readFileSync(
  path.join(__dirname, "..", "scripts", "ui", "ui-compare.js"), "utf8");

function extract(re, label) {
  const m = src.match(re);
  if (!m) { console.error(`FAIL: could not extract ${label}`); process.exit(1); }
  return m[0];
}
const code = extract(
  /function compareSubtabsShouldLock\(st\) \{[\s\S]*?\n\}/,
  "compareSubtabsShouldLock");

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(code + "\nthis.compareSubtabsShouldLock = compareSubtabsShouldLock;",
                sandbox);
const lock = sandbox.compareSubtabsShouldLock;

const fails = [];
function check(name, cond) {
  console.log(`  [${cond ? "OK " : "FAIL"}] ${name}`);
  if (!cond) fails.push(name);
}

console.log("CMP-AUD-079: the Compare sub-tab strip locks exactly while a Compare-tab run is live:");
// Idle / non-comparison tasks never lock the strip.
check("idle (no task) does NOT lock", lock({ task: null }) === false);
check("null state does NOT lock", lock(null) === false);
check("an export run does NOT lock the Compare strip", lock({ task: "export" }) === false);
check("a consolidate run does NOT lock", lock({ task: "consolidate" }) === false);
check("a batch run does NOT lock", lock({ task: "batch" }) === false);

// A classic comparison: its only Cancel is in the classic section -> must lock.
check("a classic comparison LOCKS the strip", lock({ task: "compare" }) === true);

// Compare-tab matrix comparisons (day / baseline) own their Cancel in their own
// grid section -> the strip must lock so the user can't navigate away from it.
check("a by-day matrix comparison LOCKS",
      lock({ task: "matrix", matrix_current: { which: "day" } }) === true);
check("a vs-baseline matrix comparison LOCKS",
      lock({ task: "matrix", matrix_current: { which: "baseline" } }) === true);

// An EVERYTHING-tab matrix run is a different tab (its own Cancel) -> never locks
// this strip; and a matrix task with no current job can't be a Compare-tab run.
check("an Everything (env) matrix run does NOT lock the Compare strip",
      lock({ task: "matrix", matrix_current: { which: "env" } }) === false);
check("a matrix task with no current job does NOT lock",
      lock({ task: "matrix", matrix_current: null }) === false);

console.log("");
if (fails.length) {
  console.log(`FAILED: ${fails.length} check(s): ${JSON.stringify(fails)}`);
  process.exit(1);
}
console.log("ALL COMPARE-CANCEL-VISIBILITY CHECKS PASSED");
