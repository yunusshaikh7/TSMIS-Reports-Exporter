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
    # [IO.Path]::GetTempFileName() rather than New-TemporaryFile: the latter is
    # itself ShouldProcess-aware, so under -WhatIf it does NOT create the file
    # and the generate step below got an empty -o path (the preview errored
    # instead of previewing). Only `gh release edit` should be gated by -WhatIf.
    $tmp = [System.IO.Path]::GetTempFileName()
    try {
        python build\gen_release_notes.py $tag -o $tmp
        # $ErrorActionPreference = "Stop" does NOT stop on a native command's
        # nonzero exit in PS 5.1 -- without this check a generation failure
        # would blank the release's notes.
        if ($LASTEXITCODE -ne 0) {
            throw "gen_release_notes.py failed for $tag (exit $LASTEXITCODE); notes NOT updated."
        }
        if ($PSCmdlet.ShouldProcess($tag, "update release notes")) {
            gh release edit $tag --notes-file $tmp
            Write-Host "  updated $tag"
        }
        else {
            Write-Host "  would update $tag"
        }
    }
    finally {
        # -WhatIf:$false so the temp file is cleaned up even during a preview.
        Remove-Item $tmp -Force -WhatIf:$false -ErrorAction SilentlyContinue
    }
}

Write-Host "Done. The 'dev-2' prerelease has no CHANGELOG.md section and was"
Write-Host "left untouched (delete it on GitHub if you don't want it listed)."
