// CMP-AUD-016: the classic Compare file (CMP) and custom Browse folder (CMP_DIRS)
// selections are GLOBAL. Switching recipes used to keep a stale workbook / custom
// folder selected — with Start still enabled — under a recipe that never accepted
// it (only the deep adapter later rejected it). The fix binds the selections to the
// recipe they were picked under: `syncCompareInputsToRecipe` clears BOTH the file
// paths and the custom Browse folders the moment the recipe key changes, and keeps
// them when it doesn't.
//
// Extracts the real `syncCompareInputsToRecipe` from scripts/ui/ui-compare.js and
// drives it through recipe changes in a vm sandbox. Red→green: pre-fix the function
// does not exist (extraction fails), and stale selections survived a recipe switch.
//
// Run from the repo root:  node build/check_compare_input_recipe_binding.js
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const src = fs.readFileSync(
  path.join(__dirname, "..", "scripts", "ui", "ui-compare.js"), "utf8");

const m = src.match(
  /let compareInputsRecipe = null;\s*\nfunction syncCompareInputsToRecipe\(\) \{[\s\S]*?\n\}/);
if (!m) { console.error("FAIL: could not extract syncCompareInputsToRecipe"); process.exit(1); }

// Sandbox: the module state the function reads/writes + a controllable recipe key.
let currentKey = "cmp:ramp_detail:tsn";
const sandbox = {
  CMP: { tsmis: null, tsn: null },
  CMP_DIRS: { a: null, b: null },
  compareChoice: () => currentKey,
};
vm.createContext(sandbox);
vm.runInContext(m[0] + "\nthis.syncCompareInputsToRecipe = syncCompareInputsToRecipe;",
                sandbox);
const sync = sandbox.syncCompareInputsToRecipe;

const fails = [];
function check(name, cond) {
  console.log(`  [${cond ? "OK " : "FAIL"}] ${name}`);
  if (!cond) fails.push(name);
}

console.log("CMP-AUD-016: file/Browse selections are bound to the recipe:");

// First render seats the recipe (no stale selections to drop).
sync();

// Pick a workbook pair + custom folders under the ramp_detail recipe.
sandbox.CMP.tsmis = "C:/dl/ramp.xlsx";
sandbox.CMP.tsn = "C:/dl/tsn.xlsx";
sandbox.CMP_DIRS.a = "C:/dl/runA";
sandbox.CMP_DIRS.b = "C:/dl/runB";

// Re-render on the SAME recipe -> selections kept (a plain state push mustn't wipe).
let changed = sync();
check("same recipe keeps the file + folder selections (no gratuitous clear)",
      changed === false && sandbox.CMP.tsmis === "C:/dl/ramp.xlsx"
      && sandbox.CMP_DIRS.a === "C:/dl/runA");

// Switch to an INCOMPATIBLE recipe (PDF-vs-Excel) -> everything clears.
currentKey = "cmp:highway_log:pdf_vs_excel";
changed = sync();
check("switching recipes reports a change", changed === true);
check("the stale FILE paths are cleared on a recipe switch",
      sandbox.CMP.tsmis === null && sandbox.CMP.tsn === null);
check("the stale custom Browse FOLDERS are cleared on a recipe switch",
      sandbox.CMP_DIRS.a === null && sandbox.CMP_DIRS.b === null);

// Re-pick under the new recipe, then switch back -> cleared again (bound per recipe).
sandbox.CMP.tsmis = "C:/dl/pdf.xlsx";
currentKey = "cmp:ramp_detail:tsn";
sync();
check("returning to the earlier recipe does NOT resurrect its old selections",
      sandbox.CMP.tsmis === null);

console.log("");
if (fails.length) {
  console.log(`FAILED: ${fails.length} check(s): ${JSON.stringify(fails)}`);
  process.exit(1);
}
console.log("ALL COMPARE-INPUT-RECIPE-BINDING CHECKS PASSED");
