// The render pipeline's two cost rules, locked.
//
// gui_api._sender drains up to 200 queued events into ONE batch, and there are
// ~92 `_push_state()` call sites, so a batch routinely carries several full
// state snapshots. Painting every one of them draws the same surface repeatedly
// and throws all but the last away (measured ~5 ms per state on the matrix tab;
// a 20-state batch cost 194 ms before this and 21 ms after).
//
// Two properties have to hold, and neither is visible in ordinary use — a
// regression here just makes the app quietly slow again:
//
//   1. dispatch ASSIGNS every state in order (so anything an interleaved handler
//      reads off S.st is unchanged) but PAINTS only the last one;
//   2. paintState repaints only the matrix that is actually on screen — arriving
//      at any matrix tab runs its own full render, so an off-screen one has
//      nothing to lose.
//
// Plus the third leg, which is what made renderState cheap: the ~98 option rows
// grey from ONE `body.busy` class instead of a per-row class written on every
// push, and the functional `disabled` sweeps run only when the lock CHANGES.
//
// Run from the repo root:  node build/check_state_paint_coalescing.js
"use strict";
const fs = require("fs");
const path = require("path");

const uiDir = path.join(__dirname, "..", "scripts", "ui");
const appJs = fs.readFileSync(path.join(uiDir, "app.js"), "utf8");
const appCss = fs.readFileSync(path.join(uiDir, "app.css"), "utf8");

const fails = [];
function check(name, cond, detail) {
  console.log(`  [${cond ? "OK " : "FAIL"}] ${name}`);
  if (!cond) { fails.push(name); if (detail) console.log(`       ${detail}`); }
}

function section(src, header) {
  const i = src.indexOf(header);
  if (i < 0) return "";
  const rest = src.slice(i);
  // to the next top-level `function ` declaration after this one's body
  const next = rest.indexOf("\nfunction ", header.length);
  return next < 0 ? rest : rest.slice(0, next);
}

// ---------------------------------------------------------------- 1. paint ---
console.log("dispatch coalesces states and paints once:");

const dispatchSrc = section(appJs, "function dispatch(events)");
check("dispatch exists", dispatchSrc.length > 0);
check("it finds the LAST state in the batch before looping",
      /lastStateAt\s*=\s*-1/.test(dispatchSrc)
      && /events\[i\]\.t === "state"/.test(dispatchSrc),
      "no pre-scan for the final state event");
check("every state is still ASSIGNED (ordering for interleaved handlers)",
      /case "state":\s*\n\s*S\.st = ev\.s;/.test(dispatchSrc),
      "S.st must be set for EVERY state, not just the painted one");
check("only the last state PAINTS",
      /if \(i === lastStateAt\) paintState\(\);/.test(dispatchSrc));
check("dispatch itself no longer calls renderState directly",
      !/\brenderState\(\)/.test(dispatchSrc),
      "painting belongs to paintState so the coalescing cannot be bypassed");

// The TSN-rebuild watcher keys on a task TRANSITION, so it must NOT be coalesced.
check("the consolidate->idle watcher still runs on EVERY state",
      /_lastTask/.test(dispatchSrc)
      && dispatchSrc.indexOf("_lastTask") > dispatchSrc.indexOf("paintState()"),
      "the task-transition watcher must stay outside the lastStateAt guard");

// ------------------------------------------------------- 2. matrix gating ---
console.log("paintState repaints only the visible matrix:");

const paintSrc = section(appJs, "function paintState()");
check("paintState exists", paintSrc.length > 0);
for (const [fn, guard] of [
  ["updateMatrixProgress", "onEverythingMatrix"],
  ["updateDayMatrixProgress", "DAY_MATRIX_GROUP"],
  ["updateBaselineMatrixProgress", "BASELINE_MATRIX_GROUP"],
  ["updatePveMatrixProgress", "PVE_MATRIX_GROUP"],
]) {
  const line = paintSrc.split("\n").find((l) => l.includes(fn + "()"));
  check(`${fn} is gated on ${guard}`,
        !!line && line.trim().startsWith("if (") && line.includes(guard),
        `line: ${line ? line.trim() : "(absent)"}`);
}

// -------------------------------------------------------- 3. the lock pass ---
console.log("the lock sweep runs on CHANGE, and greying is CSS:");

const lockSrc = section(appJs, "function applyLockState(locked)");
check("applyLockState exists", lockSrc.length > 0);
check("it returns early when the lock state is unchanged",
      /if \(locked === S\._lockApplied\) return;/.test(lockSrc));
check("it records what it applied", /S\._lockApplied = locked;/.test(lockSrc));
check("it flips the single body class",
      /document\.body\.classList\.toggle\("busy", locked\)/.test(lockSrc));

const renderSrc = section(appJs, "function renderState()");
check("renderState delegates the lock pass", /applyLockState\(locked\)/.test(renderSrc));
// Only `.fast-toggle` may still take the class by hand (see below); no line may
// write it onto an option row.
const rowClassWrites = renderSrc.split("\n").filter(
  (l) => /classList\.toggle\("disabled"/.test(l) && !l.includes(".fast-toggle"));
check("renderState writes NO per-row .disabled class",
      rowClassWrites.length === 0,
      `option-row greying must come from body.busy: ${JSON.stringify(rowClassWrites)}`);
check("renderState no longer sweeps the option containers for `disabled`",
      !/\$\("reportList"\)\.querySelectorAll\("input"\)/.test(renderSrc)
      && !/\$\("compareList"\)\.querySelectorAll\("input"\)/.test(renderSrc),
      "those belong to applyLockState now");

check("app.css greys every option row from body.busy",
      /body\.busy \.option-row\s*\{[^}]*opacity/.test(appCss));
check("the standalone .option-row.disabled rule still exists",
      /\.option-row\.disabled,?\s*\n?\s*(body\.busy \.option-row)?\s*\{[^}]*opacity/.test(appCss),
      "rows greyed for their OWN reasons must keep working");
check("body.busy also suppresses the row hover",
      /body\.busy \.option-row:hover/.test(appCss));

// The three .fast-toggle greys stay in JS on purpose: only 3 of the 8 toggles
// dim on lock, so a blanket ancestor rule would catch five that must not.
check("the fast toggles are still greyed individually",
      /\$\("batchFast"\)\.closest\("\.fast-toggle"\)\.classList\.toggle\("disabled", locked\)/
        .test(renderSrc),
      "a blanket body.busy .fast-toggle rule would dim five toggles that must not");
check("no blanket body.busy .fast-toggle rule slipped into the CSS",
      !/body\.busy \.fast-toggle\s*\{/.test(appCss));

console.log();
if (fails.length) {
  console.error(`FAILED: ${fails.length} check(s): ${JSON.stringify(fails)}`);
  process.exit(1);
}
console.log("ALL STATE-PAINT COALESCING CHECKS PASSED");
