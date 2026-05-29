<#
  Phase B one-shot setup for Windows (PowerShell).
  Run from the repo root:  ./scripts/windows_setup.ps1

  Verifies Python 3.12, installs creativeforge + Playwright Chromium, and runs
  the free pre-flight checks. Does NOT spend any video credits.
#>

$ErrorActionPreference = "Stop"

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

Step "Python version (want 3.12.x; 3.13 lacks some prebuilt wheels)"
$pyv = (python --version 2>&1)
Write-Host $pyv
if ($pyv -notmatch "3\.12") {
    Write-Warning "Python 3.12 not detected. Install it (winget install -e --id Python.Python.3.12), open a fresh terminal, and re-run."
    exit 1
}

Step "Confirm we're at the repo root"
if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "creativeforge")) {
    Write-Warning "Run this from the Video-Generator repo root (pyproject.toml not found here)."
    exit 1
}

Step "Confirm the verified branch is checked out"
$branch = (git rev-parse --abbrev-ref HEAD)
Write-Host "On branch: $branch"
if ($branch -ne "claude/compassionate-brahmagupta-eKuPB") {
    Write-Warning "Expected branch claude/compassionate-brahmagupta-eKuPB (PR #2). Run: git checkout claude/compassionate-brahmagupta-eKuPB"
}

Step "Install creativeforge (editable)"
pip install -e .

Step "Install Playwright Chromium"
playwright install chromium

Step "doctor — adapters + environment health"
creativeforge doctor

Step "dry-run — full plan, spends nothing"
creativeforge run musinsa-king-choice --dry-run --auto-approve

Step "credits — should read 180 / 1000"
creativeforge credits musinsa-king-choice

Write-Host "`nSetup OK." -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Green
Write-Host "  1. python scripts/login_google_flow.py      # one-time Google sign-in"
Write-Host "  2. creativeforge run musinsa-king-choice --only s00_character_sheets   # free image stage"
Write-Host "  See PHASE_B_QUICKSTART.md for the selector-iteration loop."
