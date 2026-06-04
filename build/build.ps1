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

$ErrorActionPreference = "Stop"

$BuildDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $BuildDir
$VenvDir  = Join-Path $BuildDir ".venv"
$VenvPy   = Join-Path $VenvDir  "Scripts\python.exe"
$Browsers = Join-Path $BuildDir "ms-playwright"
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

# --- 2. Bundled Chromium (matched to the pinned Playwright) ---------------
# Drop chrome-headless-shell + ffmpeg afterward: the app runs headless via
# channel="chromium" using the full browser, so the shell is not needed.
if (-not (Test-Path (Join-Path $Browsers "chromium-*"))) {
    Write-Host "==> Downloading Chromium into $Browsers"
    $env:PLAYWRIGHT_BROWSERS_PATH = $Browsers
    & $VenvPy -m playwright install chromium; Assert-LastExit "playwright install"
}
Get-ChildItem $Browsers -Directory -Filter "chromium_headless_shell-*" -ErrorAction Ignore | Remove-Item -Recurse -Force
Get-ChildItem $Browsers -Directory -Filter "ffmpeg-*" -ErrorAction Ignore | Remove-Item -Recurse -Force

# --- 3. Package as a portable onefolder -----------------------------------
$env:TSMIS_ENTRY    = Join-Path $BuildDir "smoke_entry.py"   # TODO Phase 4: point at the GUI entry point
$env:TSMIS_APP_NAME = "TSMIS Exporter"
$env:TSMIS_BROWSERS = $Browsers
$env:TSMIS_CONSOLE  = "1"                                    # TODO Phase 4: set "0" for a windowed GUI

Write-Host "==> Running PyInstaller"
& $VenvPy -m PyInstaller (Join-Path $BuildDir "app.spec") `
    --distpath $DistDir --workpath $WorkDir --noconfirm
Assert-LastExit "PyInstaller"

# --- 4. Report ------------------------------------------------------------
$AppDir = Join-Path $DistDir $env:TSMIS_APP_NAME
$SizeMB = (Get-ChildItem $AppDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("`n==> Built {0}  ({1:N0} MB onefolder)" -f $AppDir, $SizeMB)
Write-Host "    Zip this folder to distribute (right-click -> Send to -> Compressed folder)."
