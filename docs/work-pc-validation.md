# Work-PC validation handoff & operational sign-off plan (cuts as v0.18.5)

> **Two-tier release model.** **v0.18.0** is the *offline-validated candidate* — every phase is
> provable from CI/offline before it ships, but anything that needs the live TSMIS site or the
> locked-down Caltrans work PC is **not** yet field-validated. **v0.18.1** was the *field-validated
> close-out* of the overhaul (it fixed two work-PC field bugs). The full **operational sign-off** — the
> §3 checklist below — was **DEFERRED** past v0.18.1; v0.18.2/3/4 then shipped further field-driven
> hotfixes, so the sign-off now cuts as **v0.18.5**. "Enterprise-ready" = that sign-off, never v0.18.0
> (and not yet claimed at v0.18.1–v0.18.4).
>
> This doc is the **handoff**: how to gather evidence on the work PC, the manual fallback, the
> per-item acceptance checklist, and the v0.18.1 plan that consumes the evidence.

> **STATUS — v0.18.1 SHIPPED (2026-06-26).** The close-out release is committed, tagged, and published
> from the branch (commit `e2bfade`; `release.yml` published the 3 zips + `.sha256`). It fixed **two
> work-PC field bugs** found on the v0.18.0 build — **(1)** the Intersection dropdown break on the site's
> new nested report menu (now selected by stable `data-value` + a `cs-submenu` fly-out reveal; prod-safe),
> and **(2)** the matrix queue phantom — plus three layered asks (website-style report grouping, Highway
> Detail/Summary reserved-disabled groundwork, `wait_js` validation) and the Intersection Detail
> "Roadbed"→"Route Suffix" rename. All offline checks + both frozen self-tests passed; `compare_core` is
> untouched. **`main` reconciliation is now DONE** (superseded onto the v0.18.x tree; `main` is at v0.18.4
> after the v0.18.2/3/4 hotfixes). **Still owed (the actual field sign-off → v0.18.5):** the §3 live
> acceptance below, including a live confirmation of the v0.18.1–v0.18.4 field fixes on the work PC. §4 is
> the process (followed for v0.18.1; the template for the v0.18.5 sign-off).

The work PC reality (why this is needed): real users run locked-down Caltrans PCs — no
PowerShell, cmd, admin, temp scripts, or scheduled tasks; only "an unsigned exe from a
user-writable folder." The personal dev PC can't reach the TSMIS intranet, so the live export /
consolidate / compare paths and the IT/DLP behavior can **only** be verified on the work PC.

---

## 1. Gathering evidence — the credential-safe collector

The collector is the shipped exe run with one flag — no admin, no install, **and no cmd or
PowerShell required** (the work PC has none). Two ways to run it:

**A. The no-cmd way (a desktop shortcut — preferred on a locked PC).** In the app folder,
right-click `TSMIS Exporter.exe` → **Create shortcut**. Right-click the new shortcut →
**Properties**, and in **Target** append the flag after the quoted exe path:

```
"…\TSMIS Exporter.exe" --collect-evidence
```

To also include real source files (below), append the evidence folder too:

```
"…\TSMIS Exporter.exe" --collect-evidence --evidence-dir "C:\Users\<you>\Desktop\tsmis_evidence"
```

Click **OK**, then **double-click the shortcut**. (Everything happens with the mouse — no
terminal.)

**B. From a command line (maintainer / dev reproduction only):**

```
TSMIS Exporter.exe --collect-evidence
TSMIS Exporter.exe --collect-evidence --evidence-dir "C:\Users\<you>\Desktop\tsmis_evidence"
```

Either way it writes **one zip** — `tsmis_evidence_<timestamp>.zip` — into the app's data folder
and shows the path in a message box. Send that zip to the TSMIS maintainer.

**The evidence folder (`--evidence-dir`) takes only report/TSN source files.** Put a route's
disagreeing PDF/Excel, or a TSN export the maintainer asks for, in a folder you control. **Only
`.pdf`, `.xlsx`, and `.xls` files are bundled** (under `user_evidence/`, each listed in the
manifest). Anything else you happen to place there — a copied browser cookie store / login DB
(`Cookies`, `Login Data`, …), a saved internal page's `.html`, any other file type — is
**refused, not bundled, and listed in the manifest's REFUSED section** with the reason. So you
cannot accidentally leak a credential or internal page source through this folder.

**What the bundle contains (an allowlist — nothing else is gathered):**

| In the bundle | Why |
|---|---|
| `manifest.txt` | this PC's name in paths, OS / version / build, login **status** (not the login), the allowlisted diagnostic settings, the run-folder list, the 8-report live-verify set, and a listing of **every** file in the zip |
| `self_test.txt` | the offline self-test output — proves the **exact** frozen exe boots and runs every real code path (browser + `page.pdf()` + pdfplumber + openpyxl + the matrix modules + the GUI bridge) on this PC; the failing output, if it fails, **is** the evidence |
| `logs/…` | the rotating diagnostic logs (the "one log upload answers it" contract) |
| `run_reports/…` | recent per-route **summaries** (saved / empty / failed) — not report content |
| `user_evidence/…` | only the report/TSN source files (`.pdf` / `.xlsx` / `.xls`) you placed via `--evidence-dir`; any other file type there is refused |

**What the bundle NEVER contains (RM05 — credential-safe by construction):** the saved login
(`tsmis_auth.json`), the Edge sign-in profile, failure dumps (`failures/` — screenshots / page
HTML can carry report content), the exported report data (`output/<run>/…`), the TSN input PDFs
(`input/`), or the TSN library. Nothing under the data folder is walked broadly — only the
allowlist above is added, and `--evidence-dir` is itself a **positive allowlist**: a sensitive or
non-evidence file (a copied cookie store / login DB, a saved `.html` page, any non-PDF/Excel file)
is **refused even if you drop it into the evidence folder**. The collector is locked by
`build/check_evidence_bundle.py`, which plants a fake login, an Edge profile, copied browser DBs
(`Cookies`, `Login Data`, …), a saved internal `.html` page, and report data, and proves none of
it — nor any planted secret string — reaches the zip or the manifest.

> It is **safe to send to the TSMIS maintainer**, not "safe to post publicly" — it carries this
> PC's name in paths and the diagnostic settings, which a maintainer needs.

---

## 2. Manual fallback (a PC too locked even for the collector)

If the exe can't write the zip (e.g. an unusual DLP policy), gather the same diagnostics by hand
into a folder you control, then zip that folder yourself:

1. The log: `…\data\logs\tsmis.log` (and any `tsmis.log.1`, `crash.log`, `update_helper.log`).
2. The run reports: every `*.csv` under `…\output\run_reports\`.
3. Only if the maintainer asks: the specific real source PDFs/workbooks named in the request.

**Do NOT copy** `tsmis_auth.json`, the `edge_login_profile` folder, or anything under `failures\`.
Those are the credential / private-content paths the collector deliberately excludes.

---

## 3. Work-PC acceptance checklist (§K2 — the final 8-report shape; gates the v0.18.5 sign-off)

v0.18.1 is accepted when the returned evidence confirms each item. Disposable destinations only
(no disk-full induction); never live-credential / profile access in dev.

- [ ] **v0.18.1 field-bug fixes (live)** — confirm on the work PC against the live dev site:
      **Intersection export now selects** on the nested `cs-submenu` report menu (the `data-value` fix),
      and the **matrix / by-day queue chip clears** after a job drains (the queue-phantom fix). These are
      the two original field bugs; the offline fixtures (`dropdown_nested.html`, the `check_matrix_bridge`
      push-spy) are locked — this confirms them on the real site. Re-confirm the flat **prod** menu still
      selects, too.
- [ ] **P8c live paths** — exact `select_report` (no substring mis-pick), CDP open-on-demand then
      close-on-capture, cancel-in-recover latency — verified against the returned logs.
- [ ] **Carried live-verify (§M)** — P1 partial-keeps-last-good on a **real** refresh; P2
      Defender/lock behavior with a disposable destination + cleanup; P3 a **real** paused-batch
      resume across a restart; P10 a **real** v0.17→v0.18 self-update (staging-retry / checksum /
      rehash-before-swap / rollback); PA both frozen exes **and** the source ZIP on the work PC.
- [ ] **Evidence-driven PDF/parser fixes** — the P12 row-count oracle + the ramp-summary
      misattribution / duplicate-pop items, run against the **returned real source PDFs**; any fix
      landed + locked.
- [ ] **Intersection Detail (PDF) live acceptance (CR-002)** — the forward-ported report's live
      **export → consolidate → PDF-vs-TSN / PDF-vs-Excel / cross-env**, re-confirming the handoff's
      218/218-route, 0-content-diff reconciliation, **and** the v0.17.8 vs-TSN behavior (the
      position-aligned dates, the `S` control crosswalk, the Report View) against the returned real
      PDFs/Excel/TSN. The offline canary shifted with the v0.18.3 numeric-0 fix — Excel is now **≈163,310**
      (was 163,353; the PDF edition shifts by the same fix), locked in `check_compare_intersection_detail_tsn`;
      this confirms it on real data.
- [ ] **No regressions** — the full offline `build/check_*.py` suite still green; every v0.18.1
      code fix is itself offline-RED-proven first.

---

## 4. Sign-off process (the v0.18.1 template — now applies to the owed v0.18.5 sign-off)

1. **Collect** — the user runs `--collect-evidence` on the work PC (or the manual fallback) for
   each report against the live site and returns the zip(s) + any requested real source files.
2. **Diagnose offline** — for each accepted/owed item above, reproduce the finding from the
   returned logs/PDFs in a committed fixture **first** (RED), then fix.
3. **Land fixes (offline-RED-proven, per-commit revertible)** — real-log P8c acceptance fixes,
   the PDF/parser corrections against the returned PDFs, and any Intersection Detail (PDF) live
   reconciliation. Each fix re-bless touches only its own report's canary; `compare_core` stays
   regression-locked.
4. **Re-run the full offline suite** green, set `version.py` to the sign-off version (now **0.18.5**),
   update `CHANGELOG.md`, and cut the release via the existing `release.yml` (the same hash-pinned,
   `.sha256`-enforced flow as v0.18.0).
5. **Sign off** — with the §3 checklist complete, the sign-off release (v0.18.5) is the operationally-
   validated milestone; "enterprise-ready" is claimed there.

> The hard-deferrals stay deferred unless the user separately opts in: DPAPI at-rest auth (O2),
> a runtime signature / code-signing cert (A03), and the `compare_core` `min-cost-pairs` optimum.
