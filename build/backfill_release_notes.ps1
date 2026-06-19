# Rewrites every existing GitHub release's notes to the short, per-version form
# (shared header + that version's CHANGELOG.md section), the same notes new
# releases now get from the workflow. Run once to clean up the back catalog.
#
# Requirements: GitHub CLI (`gh`) installed and authenticated (`gh auth login`)
# with write access to the repo. Run from the repo root:
#
#     powershell -ExecutionPolicy Bypass -File build\backfill_release_notes.ps1
#
# Add -WhatIf to preview which releases would change without editing them.

[CmdletBinding(SupportsShouldProcess = $true)]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI (gh) not found. Install it and run 'gh auth login' first."
}

# Every version that has a section in CHANGELOG.md.
$versions = Select-String -Path "CHANGELOG.md" -Pattern '^##\s+(v\S+)' |
    ForEach-Object { $_.Matches[0].Groups[1].Value }

Write-Host "Found $($versions.Count) versions in CHANGELOG.md."

foreach ($tag in $versions) {
    $tmp = New-TemporaryFile
    try {
        python build\gen_release_notes.py $tag -o $tmp.FullName
        if ($PSCmdlet.ShouldProcess($tag, "update release notes")) {
            gh release edit $tag --notes-file $tmp.FullName
            Write-Host "  updated $tag"
        }
        else {
            Write-Host "  would update $tag"
        }
    }
    finally {
        Remove-Item $tmp.FullName -ErrorAction SilentlyContinue
    }
}

Write-Host "Done. Releases without a CHANGELOG.md section (e.g. v0.7.4 and"
Write-Host "earlier, dev-2) were left untouched."
