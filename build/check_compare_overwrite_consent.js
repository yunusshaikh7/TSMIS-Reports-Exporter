/* Classic comparison mode="both" overwrite-consent contract.
 * Pure Node: source-wires the real UI and executes the #mock bridge in a VM.
 * Run from the repo root: node build/check_compare_overwrite_consent.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.join(__dirname, "..");
const ui = fs.readFileSync(path.join(ROOT, "scripts", "ui", "ui-compare.js"), "utf8");
const mockSource = fs.readFileSync(path.join(ROOT, "scripts", "ui", "mock.js"), "utf8");
const failures = [];

function check(name, condition) {
  console.log(`  [${condition ? "OK " : "FAIL"}] ${name}`);
  if (!condition) failures.push(name);
}

console.log("classic compare overwrite UI wiring:");
check("confirmation modal is driven by confirm_required",
      /if\s*\(res\s*&&\s*res\.confirm_required\)/.test(ui) && /showConfirm\s*\(\{/.test(ui));
check("modal names the exact server-returned path/message",
      /res\.message/.test(ui) && /res\.path/.test(ui) && /Overwrite this exact file/.test(ui));
check("follow-up sends only token and boolean decision",
      /api\.confirm_compare_overwrite\(res\.confirm_token,\s*accepted\)/.test(ui));

let mockApi = null;
const context = {
  window: { CONTRACT: {} },
  dispatch: () => {},
  boot: (api) => { mockApi = api; },
  setTimeout: () => 1,
  clearTimeout: () => {},
  setInterval: () => 1,
  clearInterval: () => {},
  console,
};
vm.createContext(context);
vm.runInContext(mockSource, context, { filename: "mock.js" });

(async () => {
  console.log("#mock single-use confirmation behavior:");
  check("mock exposes the production confirmation endpoint",
        mockApi && typeof mockApi.confirm_compare_overwrite === "function");

  let preview = await mockApi.start_compare("cmp:test", "a.xlsx", "b.xlsx", true, true);
  check("both-mode mock returns a path-naming confirmation",
        preview.confirm_required === true && Boolean(preview.confirm_token)
        && preview.message.includes(preview.path));
  const token = preview.confirm_token;
  let result = await mockApi.confirm_compare_overwrite("stale-token", true);
  check("mismatched token is refused", Boolean(result.error));
  result = await mockApi.confirm_compare_overwrite(token, false);
  check("decline cancels without launch", result.cancelled === true);
  result = await mockApi.confirm_compare_overwrite(token, true);
  check("declined token cannot be replayed", Boolean(result.error));

  preview = await mockApi.start_compare("cmp:test", "a.xlsx", "b.xlsx", true, true);
  result = await mockApi.confirm_compare_overwrite(preview.confirm_token, true);
  check("accept launches the parked mock operation", result.ok === true);
  result = await mockApi.confirm_compare_overwrite(preview.confirm_token, true);
  check("accepted token cannot be replayed", Boolean(result.error));

  preview = await mockApi.start_compare_env(
    "cmp:env", "env-a", "env-b", true, true);
  check("folder comparison mock uses the same consent flow",
        preview.confirm_required === true && preview.path.includes("(values).xlsx"));
  await mockApi.confirm_compare_overwrite(preview.confirm_token, false);

  console.log();
  if (failures.length) {
    console.error(`FAILED: ${failures.length} check(s): ${failures.join(", ")}`);
    process.exitCode = 1;
  } else {
    console.log("ALL CLASSIC COMPARE OVERWRITE-CONSENT CHECKS PASSED");
  }
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
