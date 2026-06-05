# Reproducible portable build for TSMIS Reports Exporter.
#
# Produces a self-contained onefolder under dist\<AppName>\ that bundles Python,
# every dependency, and Chromium -- no installer and no Python required on the
# target machine. Zip that folder to distribute.
#
# Usage (from the repo root):
#   powershell -ExecutionPolicy Bypass -File build\build.ps1
#
# Proven on Windows + Python 3.11 in the Phase 1 spike. See build\app.spec for
# the packaging recipe.

param([switch]$SelfTest)   # -SelfTest builds a headless GUI self-test instead of the windowed app

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

# NOTE: no Chromium is downloaded or bundled. The app drives the machine's
# installed Microsoft Edge / Google Chrome (channel="msedge"/"chrome"), so only
# the Playwright Node driver (node.exe, part of the pip package) ships. This is
# what keeps the bundle small and free of a flagged browser. See app.spec and
# scripts/common.launch_browser.

# --- 2. Package as a portable onefolder -----------------------------------
if ($SelfTest) {
    # Comprehensive headless self-test (console): launches the SYSTEM browser +
    # page.pdf() + a download, runs pdfplumber text/table extraction and an
    # openpyxl round-trip, then constructs the GUI window withdrawn. Verifies the
    # pruned bundle still runs every real code path -- without a visible window or
    # a blocking mainloop.
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

# --- 3. Trim to runtime-only files + DLP guard ----------------------------
# The bundled Playwright driver ships docs / "agent skill" files whose examples
# contain test credit-card numbers; corporate DLP blocks those. Strip the
# non-runtime files and FAIL the build if any markdown doc or credit-card-like
# number remains, so a release can never reintroduce the problem.
$AppDir = Join-Path $DistDir $env:TSMIS_APP_NAME
Write-Host "==> Pruning bundle to runtime-only files and scanning for DLP-blocked content"
& (Join-Path $BuildDir "prune_bundle.ps1") -Target $AppDir

# --- 4. Report ------------------------------------------------------------
if (-not $SelfTest) {
    Copy-Item (Join-Path $BuildDir "dist_readme.txt") (Join-Path $AppDir "Start Here.txt") -Force
}
$SizeMB = (Get-ChildItem $AppDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("`n==> Built {0}  ({1:N0} MB onefolder)" -f $AppDir, $SizeMB)
Write-Host "    Zip this folder to distribute (right-click -> Send to -> Compressed folder)."
