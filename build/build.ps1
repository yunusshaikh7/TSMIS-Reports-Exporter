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
    [switch]$SelfTest,        # after building+pruning, gate the EXACT windowed exe via `--self-test` (R1-B04)
    [switch]$BundleChromium,  # ships Playwright's own Chromium inside the bundle (the with-browser variant)
    [switch]$Sign,            # sign the built .exe with a self-signed cert (interim, local trust only)
    [string]$CertSubject = "CN=TSMIS Exporter (self-signed)"
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

# --- 2. Package the real windowed app as a portable onefolder -------------
# ALWAYS the exact shipped artifact (gui_main.py, windowed). -SelfTest no longer
# builds a separate console exe -- it runs THIS exe's --self-test gate after
# copy + prune (R1-B04), so the artifact that ships is the artifact that passed.
$env:TSMIS_ENTRY    = Join-Path $RepoRoot "scripts\gui_main.py"
$env:TSMIS_APP_NAME = "TSMIS Exporter"
$env:TSMIS_CONSOLE  = "0"

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

# --- 3. Add the user-facing docs BEFORE the prune+scan --------------------
# Copy our own readmes in first so the DLP content guard (step 4) scans them too
# -- a release can't ship a doc the scanner would block. (Previously copied AFTER
# the scan, escaping it -- F10.) They land at the app root, not under _internal,
# so the prune's doc-removal never touches them.
Write-Host "==> Adding user-facing docs (Start Here.txt, IT-README.txt)"
Copy-Item (Join-Path $BuildDir "dist_readme.txt") (Join-Path $AppDir "Start Here.txt") -Force
Copy-Item (Join-Path $BuildDir "it_readme.txt") (Join-Path $AppDir "IT-README.txt") -Force

# --- 4. Trim to runtime-only files + DLP guard ----------------------------
# The bundled Playwright driver ships docs / "agent skill" files whose examples
# contain test credit-card numbers; corporate DLP blocks those. Strip the
# non-runtime files and FAIL the build if any markdown doc or credit-card-like
# number remains, so a release can never reintroduce the problem.
Write-Host "==> Pruning bundle to runtime-only files and scanning for DLP-blocked content"
& (Join-Path $BuildDir "prune_bundle.ps1") -Target $AppDir

# --- 5. Frozen exact-artifact self-test (the real release gate) ------------
# Run the EXACT shipped windowed exe's --self-test over the PRUNED bundle, so the
# artifact that ships is the artifact that passed (R1-B04). The windowed exe has
# no console, so capture the exit code via Start-Process -Wait and read the
# human-readable result from TSMIS_SELFTEST_OUT. Runs for whichever windowed
# variant was just built (the caller passes -BundleChromium for with-browser).
if ($SelfTest) {
    $ExactExe = Join-Path $AppDir ("{0}.exe" -f $env:TSMIS_APP_NAME)
    $SelfTestOut = Join-Path $WorkDir "selftest-output.txt"
    if (Test-Path $SelfTestOut) { Remove-Item $SelfTestOut -Force }
    $env:TSMIS_SELFTEST_OUT = $SelfTestOut
    Write-Host "==> Running frozen exact-artifact self-test: `"$ExactExe`" --self-test"
    $proc = Start-Process -FilePath $ExactExe -ArgumentList "--self-test" -Wait -PassThru
    Remove-Item Env:TSMIS_SELFTEST_OUT
    if (Test-Path $SelfTestOut) {
        Get-Content $SelfTestOut | ForEach-Object { Write-Host "    $_" }
    }
    if ($proc.ExitCode -ne 0) {
        throw "frozen self-test failed (exit $($proc.ExitCode)) -- see output above"
    }
    Write-Host "==> Frozen self-test PASSED (the EXACT shipped exe runs every code path)."
}

# --- 6. Optional self-signing (interim) -----------------------------------
# -Sign signs the built .exe with a SELF-SIGNED certificate. This is a stop-gap
# for local/test machines and for exercising the signing toolchain -- other PCs
# will NOT trust it unless the certificate is imported into Trusted Root. Real,
# broadly-trusted signing is done in CI via SignPath (see release.yml); leave
# -Sign off for the artifacts you publish from that pipeline. (-SelfTest now
# builds the real shippable exe, so signing applies even with -SelfTest.)
if ($Sign) {
    $cert = Get-ChildItem Cert:\CurrentUser\My |
        Where-Object { $_.Subject -eq $CertSubject -and $_.HasPrivateKey } |
        Select-Object -First 1
    if (-not $cert) {
        Write-Host "==> Creating self-signed code-signing certificate: $CertSubject"
        $cert = New-SelfSignedCertificate -Type CodeSigningCert -Subject $CertSubject `
            -CertStoreLocation Cert:\CurrentUser\My -KeyUsage DigitalSignature `
            -KeyExportPolicy Exportable
    }
    $ExeToSign = Join-Path $AppDir ("{0}.exe" -f $env:TSMIS_APP_NAME)
    Write-Host "==> Self-signing $ExeToSign"
    $r = Set-AuthenticodeSignature -FilePath $ExeToSign -Certificate $cert `
        -HashAlgorithm SHA256 -TimestampServer "http://timestamp.digicert.com"
    if ($r.Status -ne "Valid") { throw "Signing failed: $($r.Status) - $($r.StatusMessage)" }
    Write-Host "==> Signed (self-signed; trusted only where this cert is installed)."
}
$SizeMB = (Get-ChildItem $AppDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("`n==> Built {0}  ({1:N0} MB onefolder)" -f $AppDir, $SizeMB)
Write-Host "    Zip this folder to distribute (right-click -> Send to -> Compressed folder)."
