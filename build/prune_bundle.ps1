# Strip a built TSMIS Exporter bundle down to runtime-only files, then GUARD
# against shipping anything a corporate DLP scanner would flag.
#
# Why this exists
#   The bundled Playwright Node driver ships documentation / "agent skill" files
#   (e.g. driver\package\lib\tools\cli-client\skill\references\tracing.md) whose
#   examples contain test credit-card numbers like 4111111111111111. Microsoft
#   365 / SharePoint DLP detects "Credit Card Number" and BLOCKS the file -- so a
#   released zip becomes partly inaccessible. We do not use any of that tooling
#   (codegen agent, trace viewer, report dashboard) -- only headless launch +
#   page.pdf() and downloads -- so those files are pure dead weight. This script
#   deletes them and then fails hard if any markdown doc or credit-card-like
#   number remains, so a future Playwright bump can never silently reintroduce
#   the problem.
#
# Usage
#   Run automatically by build.ps1 on a fresh build. Also reusable on any
#   already-built / extracted release folder (the "TSMIS Exporter" dir that
#   contains the .exe and _internal\):
#     powershell -ExecutionPolicy Bypass -File build\prune_bundle.ps1 -Target "C:\path\to\TSMIS Exporter"
#   -GuardOnly verifies a bundle without pruning (e.g. to audit a release).
#
# Safety: the prune set below is exactly what was verified to keep a real
# Chromium launch + page.pdf() + downloads working. The Chromium browser folder
# (_internal\ms-playwright) is an unmodified upstream distribution and is left
# untouched and excluded from the content scan.

param(
    [Parameter(Mandatory = $true)][string]$Target,
    [switch]$GuardOnly,     # verify only -- do not delete anything
    [switch]$Quiet
)
$ErrorActionPreference = "Stop"

function Log($m) { if (-not $Quiet) { Write-Host $m } }

if (-not (Test-Path $Target)) { throw "Target not found: $Target" }
$Target = (Resolve-Path $Target).Path

# --- locate the bundled Playwright driver --------------------------------
$Playwright = Join-Path $Target "_internal\playwright"
if (-not (Test-Path $Playwright)) {
    $Playwright = Get-ChildItem $Target -Recurse -Directory -Filter "playwright" -ErrorAction Ignore |
        Where-Object { Test-Path (Join-Path $_.FullName "driver") } |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $Playwright -or -not (Test-Path $Playwright)) {
    throw "Could not find the bundled 'playwright' folder under: $Target"
}
$Driver = Join-Path $Playwright "driver"

# --- credit-card detection (mirrors DLP: IIN prefix + length + Luhn) ------
function Test-Luhn([string]$n) {
    $sum = 0; $alt = $false
    for ($i = $n.Length - 1; $i -ge 0; $i--) {
        $d = [int][string]$n[$i]
        if ($alt) { $d *= 2; if ($d -gt 9) { $d -= 9 } }
        $sum += $d; $alt = -not $alt
    }
    return ($sum % 10) -eq 0
}
function Test-CreditCard([string]$n) {
    # n is digits only. Require a real card brand prefix + canonical length so
    # random 16-digit hashes in JS bundles are not false-positives.
    $len = $n.Length
    $ok = $false
    if ($n -match '^4' -and ($len -eq 13 -or $len -eq 16 -or $len -eq 19)) { $ok = $true }            # Visa
    elseif ($n -match '^3[47]' -and $len -eq 15) { $ok = $true }                                       # Amex
    elseif ($n -match '^5[1-5]' -and $len -eq 16) { $ok = $true }                                       # Mastercard
    elseif ($n -match '^2[2-7]' -and $len -eq 16) {                                                     # Mastercard 2-series
        $p = [int]$n.Substring(0, 4); if ($p -ge 2221 -and $p -le 2720) { $ok = $true } }
    elseif ($n -match '^(6011|65|64[4-9])' -and ($len -eq 16 -or $len -eq 19)) { $ok = $true }          # Discover
    elseif ($n -match '^(30[0-5]|36|38)' -and $len -eq 14) { $ok = $true }                              # Diners
    elseif ($n -match '^35' -and $len -ge 16 -and $len -le 19) { $ok = $true }                          # JCB
    if (-not $ok) { return $false }
    return (Test-Luhn $n)
}

# --- 1. prune non-runtime files ------------------------------------------
$before = (Get-ChildItem $Target -Recurse -File -ErrorAction Ignore | Measure-Object Length -Sum).Sum

if (-not $GuardOnly) {
    # Directories never reached by headless launch / pdf / download: the codegen
    # agent skill (source of the credit-card examples), the trace viewer, the
    # report dashboard, the trace-viewer web assets, and TypeScript declarations.
    $killDirs = @(
        "package\lib\tools\cli-client\skill",
        "package\lib\tools\trace",
        "package\lib\tools\dashboard",
        "package\lib\vite",
        "package\types"
    ) | ForEach-Object { Join-Path $Driver $_ }

    $removed = 0
    foreach ($d in $killDirs) {
        if (Test-Path $d) { Remove-Item $d -Recurse -Force; $removed++; Log "  - removed $d" }
    }
    # Loose docs (*.md) and TypeScript declarations (*.d.ts) anywhere in the driver.
    Get-ChildItem $Driver -Recurse -File -Include *.md, *.d.ts -ErrorAction Ignore | ForEach-Object {
        Remove-Item $_.FullName -Force; $removed++
    }

    # Chromium ships UI string packs for ~220 locales; headless automation only
    # ever needs the default (en-US). Keep en-US.pak, drop the rest (~42 MB).
    $msPw = Join-Path $Target "_internal\ms-playwright"
    Get-ChildItem $msPw -Recurse -Directory -Filter "locales" -ErrorAction Ignore | ForEach-Object {
        Get-ChildItem $_.FullName -File -Filter *.pak -ErrorAction Ignore |
            Where-Object { $_.Name -ne "en-US.pak" } |
            ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }
    }

    # Safety net for the PyInstaller `excludes` (Pillow / pypdfium2): if a hook
    # re-bundled them, drop the package dir + its dist-info. (openpyxl imports
    # Pillow eagerly, so it loads when present -- but the app's used code paths,
    # text/table extraction + plain workbooks, don't need it and tolerate its
    # absence; excluding it is verified safe by the frozen self-test,
    # build/full_smoke.py.)
    $internal = Join-Path $Target "_internal"
    foreach ($name in @("PIL", "Pillow", "pypdfium2", "pypdfium2_raw")) {
        Get-ChildItem $internal -Directory -ErrorAction Ignore |
            Where-Object { $_.Name -eq $name -or $_.Name -like "$name-*" } |
            ForEach-Object { Remove-Item $_.FullName -Recurse -Force; $removed++; Log "  - removed _internal\$($_.Name)" }
    }

    # Generic dead weight in bundled Python packages: test suites and type stubs
    # (never imported at runtime). Skip the Chromium folder, handled above.
    Get-ChildItem $internal -Recurse -Directory -ErrorAction Ignore |
        Where-Object { $_.Name -in @("tests", "test") -and $_.FullName -notmatch '\\ms-playwright\\' } |
        ForEach-Object { Remove-Item $_.FullName -Recurse -Force; $removed++ }
    Get-ChildItem $internal -Recurse -File -Filter *.pyi -ErrorAction Ignore |
        Where-Object { $_.FullName -notmatch '\\ms-playwright\\' } |
        ForEach-Object { Remove-Item $_.FullName -Force; $removed++ }

    $after = (Get-ChildItem $Target -Recurse -File -ErrorAction Ignore | Measure-Object Length -Sum).Sum
    Log ("==> Pruned {0} item(s), reclaimed {1:N1} MB" -f $removed, (($before - $after) / 1MB))
}

# --- 2. GUARD -------------------------------------------------------------
# (a) No markdown docs may remain under the bundled Playwright driver -- that is
#     the exact file type DLP blocked.
$mds = Get-ChildItem $Playwright -Recurse -File -Filter *.md -ErrorAction Ignore
if ($mds) {
    throw "GUARD FAILED: markdown docs still bundled under playwright:`n  " + (($mds.FullName) -join "`n  ")
}

# (b) No credit-card-like number in any text file across the bundle, EXCEPT the
#     upstream Chromium folder (unmodifiable; excluded to stay fast + false-
#     positive-free). Scans common text extensions only; binaries are skipped.
$msPlaywright = Join-Path $Target "_internal\ms-playwright"
$textExt = @('.md', '.markdown', '.txt', '.text', '.json', '.yml', '.yaml',
    '.js', '.mjs', '.cjs', '.ts', '.html', '.htm', '.css', '.xml', '.csv', '.cfg', '.ini')
$rx = [regex]'(?<![0-9A-Za-z])[0-9](?:[ -]?[0-9]){12,18}(?![0-9A-Za-z])'

$hits = New-Object System.Collections.Generic.List[string]
Get-ChildItem $Target -Recurse -File -ErrorAction Ignore | ForEach-Object {
    $f = $_
    if ($f.FullName.StartsWith($msPlaywright, [System.StringComparison]::OrdinalIgnoreCase)) { return }
    if ($textExt -notcontains $f.Extension.ToLower()) { return }
    try { $text = [System.IO.File]::ReadAllText($f.FullName) } catch { return }
    foreach ($m in $rx.Matches($text)) {
        $digits = ($m.Value -replace '[^0-9]', '')
        if (Test-CreditCard $digits) {
            $hits.Add(("  {0}  ->  {1}" -f $f.FullName.Substring($Target.Length + 1), $digits))
            break
        }
    }
}
if ($hits.Count -gt 0) {
    throw ("GUARD FAILED: credit-card-like number(s) found in the bundle:`n" + ($hits -join "`n"))
}

Log "==> Guard passed: no markdown docs and no credit-card-like content in the bundle."
