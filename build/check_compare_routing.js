// P3-B03 routing guard: the Compare tab must resolve a row's KIND by its stable
// `cmp:*` key (P3), not by array-indexing compare_reports with that string. The
// regression: compareKind() did `compare_reports[compareChoice()]` -> undefined ->
// defaulted every comparison to "files", so a FOLDER comparison got file inputs and
// routed to api.start_compare instead of api.start_compare_env. A row-presence check
// can't catch this — the routing itself must be exercised. Extracts the four
// self-contained functions from scripts/ui/app.js and runs them in a vm sandbox.
//
// Run from the repo root:  node build/check_compare_routing.js
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const appjs = fs.readFileSync(
  path.join(__dirname, "..", "scripts", "ui", "app.js"), "utf8")
  // S5: the compare cluster moved to ui-compare.js (same global scope) — the
  // extracted-function sandbox reads both.
  + fs.readFileSync(path.join(__dirname, "..", "scripts", "ui", "ui-compare.js"), "utf8");

function extract(re, label) {
  const m = appjs.match(re);
  if (!m) { console.error(`FAIL: could not extract ${label} from app.js`); process.exit(1); }
  return m[0];
}
const srcs = [
  extract(/function compareChoice\(\) \{[\s\S]*?\n\}/, "compareChoice"),
  extract(/function currentCompareRep\(\) \{[\s\S]*?\n\}/, "currentCompareRep"),
  extract(/function compareKind\(\) \{[\s\S]*?\n\}/, "compareKind"),
  extract(/async function startCompare\(\) \{[\s\S]*?\n\}/, "startCompare"),
].join("\n");

const fails = [];
function check(name, cond) {
  console.log(`  [${cond ? "OK " : "FAIL"}] ${name}`);
  if (!cond) fails.push(name);
}

const sandbox = {
  // Two rows mirroring the registry contract: a folders-kind cross-env compare and
  // a files-kind vs-TSN compare, each keyed by its stable cmp:* key.
  S: { init: { compare_reports: [
        { key: "cmp:ramp_summary:env", kind: "folders" },
        { key: "cmp:highway_log:tsn", kind: "files" },
      ] }, st: { task: null } },
  CMP: { tsmis: "T.xlsx", tsn: "N.xlsx" },
  __checked: null,        // the selected radio's dataset.key
  __apiCalls: [],
};
sandbox.$ = (id) => {
  if (id === "compareList") {
    return { querySelector: () => (sandbox.__checked == null
              ? null : { dataset: { key: sandbox.__checked } }) };
  }
  // cmpDirA/cmpDirB (distinct values) + the want-output checkboxes for startCompare.
  return { value: id === "cmpDirB" ? "2026 ars-prod" : "2026 ssor-prod", checked: true };
};
sandbox.api = {
  start_compare_env: async (...a) => { sandbox.__apiCalls.push(["start_compare_env", a[0]]); return { ok: true }; },
  start_compare: async (...a) => { sandbox.__apiCalls.push(["start_compare", a[0]]); return { ok: true }; },
};
sandbox.showMessage = () => {};
vm.createContext(sandbox);
vm.runInContext(srcs +
  "\nglobalThis.compareKind = compareKind;" +
  "\nglobalThis.startCompare = startCompare;", sandbox);

(async () => {
  // --- a FOLDERS-kind selection must resolve "folders" and route to start_compare_env
  sandbox.__checked = "cmp:ramp_summary:env";
  check("folders-kind key -> compareKind() === 'folders' (drives folder controls)",
        sandbox.compareKind() === "folders");
  sandbox.__apiCalls = [];
  await sandbox.startCompare();
  check("folders-kind key routes to api.start_compare_env with the key",
        sandbox.__apiCalls.length === 1
        && sandbox.__apiCalls[0][0] === "start_compare_env"
        && sandbox.__apiCalls[0][1] === "cmp:ramp_summary:env");

  // --- a FILES-kind selection must resolve "files" and route to start_compare
  sandbox.__checked = "cmp:highway_log:tsn";
  check("files-kind key -> compareKind() === 'files' (drives file controls)",
        sandbox.compareKind() === "files");
  sandbox.__apiCalls = [];
  await sandbox.startCompare();
  check("files-kind key routes to api.start_compare with the key",
        sandbox.__apiCalls.length === 1
        && sandbox.__apiCalls[0][0] === "start_compare"
        && sandbox.__apiCalls[0][1] === "cmp:highway_log:tsn");

  // --- no selection falls back to the safe default
  sandbox.__checked = null;
  check("no selection -> compareKind() defaults to 'files'",
        sandbox.compareKind() === "files");

  if (fails.length) {
    console.log(`\nFAILED: ${fails.length} check(s): ${fails.join(", ")}`);
    process.exit(1);
  }
  console.log("\nALL COMPARE-ROUTING CHECKS PASSED");
})();
