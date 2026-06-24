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
for (const f of ["contract.js", "app.js", "mock.js"]) {
  let ok = true;
  try { new vm.Script(read(f), { filename: f }); }
  catch (e) { ok = false; check(f + " compiles (no syntax error) -> " + e.message, false); }
  if (ok) check(f + " compiles (no syntax error)", true);
}

const app = read("app.js");
const mock = read("mock.js");
const contract = read("contract.js");
const html = read("index.html");

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
for (const f of ["contract.js", "app.js", "mock.js"])
  check("ui asset exists (no 404): " + f, fs.existsSync(path.join(UI, f)));

console.log("");
if (failures.length) {
  console.log("FAILED: " + failures.length + " check(s): " + JSON.stringify(failures));
  process.exit(1);
}
console.log("ALL UI-BOOT CHECKS PASSED");
