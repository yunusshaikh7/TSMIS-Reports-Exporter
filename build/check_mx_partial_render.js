// P1-R01 renderer guard: a matrix cell whose comparison was built from PARTIAL
// consolidation inputs MUST render distinctly from a fully-valid result, so a green
// "✓ match" can never hide that inputs were left out. Extracts the self-contained
// mxCellContent() from scripts/ui/ui-matrix.js (the P9b matrix-renderer module; it
// moved out of app.js) and exercises it in a vm sandbox (it's a browser script, not a
// module, so it can't be `require`d directly).
//
// Run from the repo root:  node build/check_mx_partial_render.js
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const src = fs.readFileSync(
  path.join(__dirname, "..", "scripts", "ui", "ui-matrix.js"), "utf8");
const mxHi = (src.match(/const\s+MX_HI\s*=\s*(\d+)/) || [])[1];
const fnSrc = (src.match(/function mxCellContent\(cmp, tsnMeta\) \{[\s\S]*?\n\}/) || [])[0];
if (!mxHi || !fnSrc) {
  console.error("FAIL: could not extract mxCellContent / MX_HI from ui-matrix.js");
  process.exit(1);
}
const sandbox = { MX_HI: Number(mxHi) };
vm.createContext(sandbox);
vm.runInContext(fnSrc + "\nglobalThis.mxCellContent = mxCellContent;", sandbox);
const mx = sandbox.mxCellContent;

const fails = [];
function check(name, cond) {
  console.log(`  [${cond ? "OK " : "FAIL"}] ${name}`);
  if (!cond) fails.push(name);
}

const base = { built: true, stale: false };
// A fully-valid identical comparison renders the green match.
const full = mx({ ...base, diff_cells: 0, one_sided: 0,
                  completion: "complete", verdict: "match" });
check("complete match -> mx-match / identical",
      full.cls === "mx-match" && full.sub === "identical");
// The SAME zero counts but PARTIAL inputs must NOT read as a valid match.
const part = mx({ ...base, diff_cells: 0, one_sided: 0, completion: "partial" });
check("partial match -> NOT the green mx-match", part.cls !== "mx-match");
check("partial result -> mx-partial with no match/checkmark certification",
      part.cls === "mx-partial" && part.main === "partial"
      && !/[✓]|match/i.test(part.main + part.sub) && /refresh/.test(part.sub));
// A partial WITH diffs is still flagged and keeps observed counts in its detail.
const pd = mx({ ...base, diff_cells: 3, one_sided: 1, completion: "partial" });
check("partial with diffs -> mx-partial, observed count preserved, retryable",
      pd.cls === "mx-partial" && pd.main === "partial"
      && /3 diffs/.test(pd.sub) && /refresh/.test(pd.sub));
const capped = mx({ ...base, diff_cells: 0, one_sided: 0,
                    completion: "partial", pairing_quality: "capped" });
check("capped pairing -> partial with an honest re-scope instruction",
      capped.cls === "mx-partial" && capped.main === "partial"
      && /pairing capped/.test(capped.sub) && /re-scope/.test(capped.sub)
      && !/[✓]|match/i.test(capped.main + capped.sub));
// Missing typed completion can no longer inherit a green legacy default.
const env = mx({ ...base, diff_cells: 0, one_sided: 0 });
check("no completion -> fail-closed re-run", env.cls === "mx-stale"
      && env.main === "re-run" && /unknown/.test(env.sub));
const contradiction = mx({ ...base, diff_cells: 0, one_sided: 0,
                           completion: "complete", verdict: "diff" });
check("complete verdict/count contradiction -> re-run, never green",
      contradiction.cls === "mx-stale" && /disagree/.test(contradiction.sub));

if (fails.length) {
  console.log(`\nFAILED: ${fails.length} check(s): ${fails.join(", ")}`);
  process.exit(1);
}
console.log("\nALL MX-PARTIAL RENDER CHECKS PASSED");
