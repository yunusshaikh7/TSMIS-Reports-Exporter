# Reproducible portable build for TSMIS Reports Exporter.
#
# Produces a self-contained onefolder under dist\<AppName>\ that bundles Python
# and every dependency -- no installer and no Python required on the target
# machine. No browser is bundled: the app drives the machine's installed Edge /
# Chrome (only Playwright's Node driver ships). Zip that folder to distribute.
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File build\build.ps1
#
# Proven on Windows + Python 3.11 in the Phase 1 spike. See build\app.spec for
# the packaging recipe.

param(
    [switch]$SelfTest,        # builds a headless self-test instead of the windowed app
    [switch]$BundleChromium   # ships Playwright's own Chromium inside the bundle (the with-browser variant)
)

$ErrorActionPreference = "Stop"

$BuildDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $BuildDir
$VenvDir  = Join-Path $BuildDir ".venv"
$VenvPy   = Join-Path $VenvDir  "Scripts\python.exe"
$WorkDir  = Join-Path $BuildDir "pyi-work"
$DistDir  = Join-Path $RepoRoot "dist"

function Assert-LastExit($what) {
    if ($LASTEXITCODE -ne 0) { throw "$what failed (exit $LASTEXITCODE)" }
}

# --- 1. Isolated build venv ----------------------------------------------
if (-not (Test-Path $VenvPy)) {
    Write-Host "==> Creating build venv"
    python -m venv $VenvDir; Assert-LastExit "venv creation"
}
Write-Host "==> Installing pinned build dependencies"
& $VenvPy -m pip install --upgrade pip --quiet; Assert-LastExit "pip upgrade"
& $VenvPy -m pip install -r (Join-Path $RepoRoot "requirements-build.txt"); Assert-LastExit "pip install"

# NOTE: by default no Chromium is downloaded or bundled. The app drives the
# machine's installed Microsoft Edge / Google Chrome (channel="msedge"/
# "chrome"), so only the Playwright Node driver (node.exe, part of the pip
# package) ships -- this is what keeps the default bundle small and free of a
# flagged browser. -BundleChromium builds the with-browser variant instead
# (step 2b). See app.spec and scripts/common.launch_browser.

# --- 2. Package as a portable onefolder -----------------------------------
if ($SelfTest) {
    # Comprehensive headless self-test (console): launches the SYSTEM browser +
    # page.pdf() + a download, runs pdfplumber text/table extraction and an
    # openpyxl round-trip, then cycles a hidden WebView window through the real
    # JS bridge. Verifies the pruned bundle still runs every real code path
    # without anything visible.
    $env:TSMIS_ENTRY    = Join-Path $BuildDir "full_smoke.py"
    $env:TSMIS_APP_NAME = "TSMIS SelfTest"
    $env:TSMIS_CONSOLE  = "1"
} else {
    # The real windowed deliverable.
    $env:TSMIS_ENTRY    = Join-Path $RepoRoot "scripts\gui_main.py"
    $env:TSMIS_APP_NAME = "TSMIS Exporter"
    $env:TSMIS_CONSOLE  = "0"
}

Write-Host "==> Running PyInstaller"
& $VenvPy -m PyInstaller (Join-Path $BuildDir "app.spec") `
    --distpath $DistDir --workpath $WorkDir --noconfirm
Assert-LastExit "PyInstaller"

# --- 2b. Optionally bundle the Built-in Chromium ---------------------------
# The with-browser variant ships Playwright's own Chromium inside
# _internal\ms-playwright. At runtime paths.py points PLAYWRIGHT_BROWSERS_PATH
# at that folder, and common.py then lists "Built-in Chromium" as the default
# channel (Edge/Chrome stay in the picker). --no-shell skips the separate
# headless shell: channel="chromium" runs the full browser in new-headless
# mode, so one binary serves headed sign-in AND headless exports. Done BEFORE
# the prune so its locale trimming applies to the browser too.
$AppDir = Join-Path $DistDir $env:TSMIS_APP_NAME
if ($BundleChromium) {
    Write-Host "==> Downloading the Built-in Chromium into the bundle"
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $AppDir "_internal\ms-playwright"
    & $VenvPy -m playwright install chromium --no-shell
    Assert-LastExit "playwright install chromium"
    Remove-Item Env:PLAYWRIGHT_BROWSERS_PATH
}

# --- 3. Trim to runtime-only files + DLP guard ----------------------------
# The bundled Playwright driver ships docs / "agent skill" files whose examples
# contain test credit-card numbers; corporate DLP blocks those. Strip the
# non-runtime files and FAIL the build if any markdown doc or credit-card-like
# number remains, so a release can never reintroduce the problem.
Write-Host "==> Pruning bundle to runtime-only files and scanning for DLP-blocked content"
& (Join-Path $BuildDir "prune_bundle.ps1") -Target $AppDir

# --- 3b. Run the frozen self-test (the real release gate) -----------------
# Building the self-test exe only proves it links; RUN it so -SelfTest actually
# verifies the PRUNED frozen bundle exercises every real code path (system
# browser pdf+download, pdfplumber, openpyxl, GUI). A nonzero exit fails the build.
if ($SelfTest) {
    $SelfTestExe = Join-Path $AppDir ("{0}.exe" -f $env:TSMIS_APP_NAME)
    Write-Host "==> Running frozen self-test: $SelfTestExe"
    & $SelfTestExe
    Assert-LastExit "frozen self-test"
    Write-Host "==> Frozen self-test PASSED (pruned bundle runs every code path)."
}

# --- 4. Report ------------------------------------------------------------
if (-not $SelfTest) {
    Copy-Item (Join-Path $BuildDir "dist_readme.txt") (Join-Path $AppDir "Start Here.txt") -Force
}
$SizeMB = (Get-ChildItem $AppDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("`n==> Built {0}  ({1:N0} MB onefolder)" -f $AppDir, $SizeMB)
Write-Host "    Zip this folder to distribute (right-click -> Send to -> Compressed folder)."
