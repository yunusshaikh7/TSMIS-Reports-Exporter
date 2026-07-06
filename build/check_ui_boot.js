"use strict";
/* P9 deterministic boot check: the #mock extraction keeps app.js + mock.js +
 * contract.js loadable, ordered, and self-consistent (no missing globals / no 404s),
 * for BOTH the production boot (app.js owns it) and the #mock boot (mock.js owns it).
 *
 * Static + offline: each script is COMPILED (not executed -- no DOM needed) to catch
 * syntax errors, then the boot wiring + index.html ordering + the mock's cross-file
 * global references are asserted structurally. Run from the repo root:
 *     node build/check_ui_boot.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const UI = path.join(__dirname, "..", "scripts", "ui");
const failures = [];
const check = (name, cond) => {
  console.log("  [" + (cond ? "OK " : "FAIL") + "] " + name);
  if (!cond) failures.push(name);
};
const read = (f) => fs.readFileSync(path.join(UI, f), "utf-8");

// [open, close] source offsets of the FIRST `if (!WANT_MOCK) { ... }` block, brace-
// matched (nested arrow-function braces included; this block carries no braces inside
// strings/comments). Returns null if absent.
function gateRange(src) {
  const head = src.search(/if\s*\(\s*!WANT_MOCK\s*\)\s*\{/);
  if (head < 0) return null;
  const open = src.indexOf("{", head);
  let depth = 0;
  for (let j = open; j < src.length; j++) {
    if (src[j] === "{") depth++;
    else if (src[j] === "}" && --depth === 0) return [open, j];
  }
  return null;
}

// 1. Syntax: compile each script (does NOT run it, so no DOM/window needed).
for (const f of ["contract.js", "ui-dom.js", "ui-matrix.js", "ui-settings.js", "app.js", "mock.js"]) {
  let ok = true;
  try { new vm.Script(read(f), { filename: f }); }
  catch (e) { ok = false; check(f + " compiles (no syntax error) -> " + e.message, false); }
  if (ok) check(f + " compiles (no syntax error)", true);
}

const app = read("app.js");
const mock = read("mock.js");
const contract = read("contract.js");
const html = read("index.html");
const uiDom = read("ui-dom.js");
const uiMatrix = read("ui-matrix.js");
const uiSettings = read("ui-settings.js");
const uiExport = read("ui-export.js");      // S5: the per-tab splits
const uiBatch = read("ui-batch.js");
const uiCompare = read("ui-compare.js");

// 2. The mock moved OUT of app.js; production boot only.
check("app.js no longer DEFINES makeMockApi (it moved to mock.js)",
      !/function\s+makeMockApi\s*\(/.test(app));
check("app.js never calls boot(makeMockApi()) (mock owns the mock boot)",
      !/boot\(\s*makeMockApi\(\)\s*\)/.test(app));
// EVERY real-bridge boot path (boot(window.pywebview.api), incl. the pywebviewready
// listener AND the poll) must live inside the !WANT_MOCK gate, so under #mock app.js
// registers no bridge boot and mock.js owns it (P9-R01). Brace-match the gate block
// and assert containment -- not merely that an `if (!WANT_MOCK)` exists.
const gate = gateRange(app);
check("app.js has the production-only boot gate (if (!WANT_MOCK) { ... })", gate !== null);
if (gate) {
  const inside = (idx) => idx > gate[0] && idx < gate[1];
  const bridgeBoots = [...app.matchAll(/boot\(\s*window\.pywebview\.api\s*\)/g)].map((m) => m.index);
  check("app.js has at least one real-bridge boot path (production boot exists)",
        bridgeBoots.length >= 1);
  check("EVERY real-bridge boot (boot(window.pywebview.api)) is inside the !WANT_MOCK gate (P9-R01)",
        bridgeBoots.length >= 1 && bridgeBoots.every(inside));
  const readyIdx = app.indexOf('addEventListener("pywebviewready"');
  check("the pywebviewready listener is inside the !WANT_MOCK gate (no ungated bridge boot)",
        readyIdx >= 0 && inside(readyIdx));
}

// 3. mock.js OWNS makeMockApi + the mock boot.
check("mock.js DEFINES makeMockApi", /function\s+makeMockApi\s*\(\)/.test(mock));
check("mock.js owns the mock boot (calls boot(makeMockApi()))",
      /boot\(\s*makeMockApi\(\)\s*\)/.test(mock));

// 4. No missing globals: mock.js reads app.js's top-level bindings (S, boot). Those
//    are classic-script globals, so they MUST be declared at app.js top level (mock.js
//    loads after app.js, sharing the global lexical scope).
check("app.js declares `boot` at top level (mock.js calls it)",
      /(?:^|\n)\s*(?:async\s+)?function\s+boot\s*\(/.test(app));
check("app.js declares `S` at top level (mock.js reads S.init)",
      /(?:^|\n)const\s+S\s*=/.test(app));
check("app.js declares `WANT_MOCK` at top level",
      /(?:^|\n)const\s+WANT_MOCK\s*=/.test(app));
if (/\bS\./.test(mock)) check("mock.js reads the shared `S` (cross-file binding wired)", true);

// 5. contract.js exposes the enum mirror.
check("contract.js sets window.CONTRACT (the bridge-enum mirror)",
      /window\.CONTRACT\s*=/.test(contract));

// 6. index.html: ordering + #mock gating + no 404 (every referenced ui asset exists).
const iContract = html.indexOf('src="contract.js"');
const iApp = html.indexOf('src="app.js"');
const iMockGate = html.indexOf('"mock.js"');  // the conditional src = "mock.js" injection
check("index.html loads contract.js BEFORE app.js",
      iContract >= 0 && iApp >= 0 && iContract < iApp);
check("index.html injects mock.js AFTER app.js",
      iMockGate > iApp);
check("index.html gates the mock load on #mock", html.includes("[?#&]mock"));
for (const f of ["contract.js", "ui-dom.js", "ui-matrix.js", "ui-settings.js", "app.js", "mock.js"])
  check("ui asset exists (no 404): " + f, fs.existsSync(path.join(UI, f)));

// 7. P9b module boundaries: each cohesive cluster moved OUT of app.js into its own
//    classic-script module (loaded before app.js, sharing the global scope). A
//    representative function per module must be DEFINED in that module and GONE from
//    app.js (truly moved, not copied) -- yet still CALLED somewhere (wired). app.js
//    keeps the entry points (boot/bindEvents/buildStatic/S/WANT_MOCK -- locked above).
const MODULES = {
  "ui-dom.js": { src: uiDom, fns: ["setDot", "icon", "appendLog", "buildModal", "showConfirm", "showRoutePicker"] },
  "ui-export.js": { src: uiExport, fns: ["openPreviewModal", "renderPreflight", "startExport"] },
  "ui-batch.js": { src: uiBatch, fns: ["startBatch", "renderBatchLibrary", "startConsolidate"] },
  "ui-compare.js": { src: uiCompare, fns: ["selectCompareGroup", "applyMatrixWide", "startCompare"] },
  "ui-matrix.js": { src: uiMatrix, fns: ["renderMatrix", "renderDayMatrix", "mxCellContent", "renderMatrixConfig", "dndAttach"] },
  "ui-settings.js": { src: uiSettings, fns: ["fillSettings", "renderTsnLibrary", "renderExportBrowser", "verifyEnvironment"] },
};
const allUi = app + uiDom + uiMatrix + uiSettings
            + uiExport + uiBatch + uiCompare;         // all real-UI scripts, one scope
// "wiring intact" = a reference EXISTS BEYOND the declaration: a call `fn(...)` OR a
// handler/value use (`= fn`, `fn,`). The declaration is STRIPPED first, so the check
// can't pass on the declaration alone -- the old `\bfn\s*\(` matched `function fn(`
// itself and was vacuous for handler-bound symbols (P9b-R01).
const refBeyondDecl = (fn) => {
  const noDecl = allUi.replace(new RegExp("(?:async\\s+)?function\\s+" + fn + "\\b", "g"), "");
  return new RegExp("\\b" + fn + "\\b").test(noDecl);
};
for (const [name, { src, fns }] of Object.entries(MODULES)) {
  for (const fn of fns) {
    const def = new RegExp("function\\s+" + fn + "\\s*\\(");
    check(`${fn}: defined in ${name}`, def.test(src));
    check(`${fn}: NO LONGER defined in app.js (truly moved)`, !def.test(app));
    check(`${fn}: referenced beyond its declaration (wiring intact)`, refBeyondDecl(fn));
  }
}
// A moved HANDLER-bound symbol is ASSIGNED, not called, so a call-only check would
// miss it (P9b-R01, Codex's example) -- lock the specific verifyEnvironment wiring.
check("verifyEnvironment is wired to the btnVerifyEnv handler (app.js)",
      /\$\("btnVerifyEnv"\)\.onclick\s*=\s*verifyEnvironment\b/.test(app));
// The two duplicated render pairs were UNIFIED behind one helper each (renderer merge),
// with the four named wrappers preserved so callers are unchanged.
check("ui-matrix.js unifies the fast-controls pair (syncMatrixFastControls helper)",
      /function\s+syncMatrixFastControls\s*\(/.test(uiMatrix));
check("ui-matrix.js unifies the formulas pair (syncFormulasToggle helper)",
      /function\s+syncFormulasToggle\s*\(/.test(uiMatrix));
for (const w of ["syncMatrixFast", "syncDayMatrixFast", "syncMatrixFormulas", "syncDayMatrixFormulas"])
  check(`named wrapper ${w} preserved (callers unchanged)`,
        new RegExp("function\\s+" + w + "\\s*\\(").test(uiMatrix));

// 8. index.html classic-script load order: contract -> ui-dom -> ui-matrix ->
//    ui-settings -> app -> (#mock) mock. A module that loads AFTER app.js would not
//    have its functions defined when app.js's top-level runs, and the shared-scope
//    contract would break.
const order = ["contract.js", "ui-dom.js", "ui-matrix.js", "ui-settings.js", "app.js"]
  .map((f) => html.indexOf(`src="${f}"`));
check("index.html loads contract/ui-dom/ui-matrix/ui-settings/app in order, all present",
      order.every((i) => i >= 0) && order.every((v, i) => i === 0 || order[i - 1] < v));
check("index.html injects mock.js AFTER every ui-* module + app.js",
      iMockGate > order[order.length - 1]);

console.log("");
if (failures.length) {
  console.log("FAILED: " + failures.length + " check(s): " + JSON.stringify(failures));
  process.exit(1);
}
console.log("ALL UI-BOOT CHECKS PASSED");
