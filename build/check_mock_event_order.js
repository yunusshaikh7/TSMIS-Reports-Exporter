// Guard: the #mock preview must emit task-END events in the PRODUCTION order.
//
// v0.18.4's queue-phantom hid because the real bridge ends a task as
//   run_ended -> state -> matrix_refresh   (gui_api._end_task)
// while mock.js pushed state BEFORE run_ended — so the order-sensitive frontend
// bug only reproduced by hand-replaying the real order. This check pins both
// sides as text invariants:
//   * gui_api._end_task keeps `self._emit(payload)` (run_ended) before
//     `self._push_state()`;
//   * in mock.js, wherever a task ends (`st.task = null`), the next state push
//     in that completion block comes AFTER the run_ended push.
//
// Pure Node, no browser. Run:  node build/check_mock_event_order.js
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const failures = [];
const ok = (name) => console.log(`  ok: ${name}`);
const fail = (name, detail) => {
  console.log(`FAIL: ${name}${detail ? "\n      " + detail : ""}`);
  failures.push(name);
};

// ---- production side: _end_task emits run_ended BEFORE the state push -------
const gui = fs.readFileSync(path.join(ROOT, "scripts", "gui_api.py"), "utf8");
const endTask = gui.split(/def _end_task\(/)[1] || "";
const body = endTask.split(/\n    def /)[0];          // up to the next method
const emitIdx = body.indexOf("self._emit(payload)");
const pushIdx = body.indexOf("self._push_state()");
if (emitIdx < 0 || pushIdx < 0) {
  fail("_end_task still emits run_ended then pushes state",
       "could not locate the emit/push pair — did _end_task move? update this check");
} else if (emitIdx < pushIdx) {
  ok("production _end_task order: run_ended -> state");
} else {
  fail("production _end_task order: run_ended -> state",
       "self._push_state() now precedes self._emit(payload)");
}

// ---- mock side: every task-end block orders run_ended before the state push -
const mock = fs.readFileSync(path.join(ROOT, "scripts", "ui", "mock.js"), "utf8");
const lines = mock.split("\n");
const WINDOW = 14;                     // a completion block is a handful of lines
const LOOKBACK = 8;                    // run_ended may fire just BEFORE st.task = null
let blocks = 0, bad = [];
lines.forEach((line, i) => {
  if (!/st\.task\s*=\s*null/.test(line)) return;
  let runEndedAt = -1, stateAt = -1;
  for (let j = Math.max(0, i - LOOKBACK); j < Math.min(lines.length, i + WINDOW); j++) {
    if (runEndedAt < 0 && /run_ended/.test(lines[j])) runEndedAt = j;
  }
  for (let j = i; j < Math.min(lines.length, i + WINDOW); j++) {
    if (stateAt < 0 && (/pushState\(\)/.test(lines[j]) || /\{\s*t:\s*"state"/.test(lines[j]))) stateAt = j;
  }
  if (runEndedAt < 0) return;          // not a run-completion block (e.g. idle reset)
  blocks++;
  if (stateAt >= 0 && stateAt < runEndedAt) {
    bad.push(`mock.js:${i + 1} (state at :${stateAt + 1} before run_ended at :${runEndedAt + 1})`);
  }
});
if (blocks === 0) {
  fail("mock task-end blocks found", "no `st.task = null` + run_ended blocks matched — update this check");
} else if (bad.length) {
  fail(`mock emits run_ended before the state push (${blocks} block(s) scanned)`,
       "inverted: " + bad.join(", "));
} else {
  ok(`mock emits run_ended before the state push (${blocks} block(s) scanned)`);
}

console.log("");
if (failures.length) {
  console.log(`${failures.length} check(s) FAILED`);
  process.exit(1);
}
console.log("all good");
