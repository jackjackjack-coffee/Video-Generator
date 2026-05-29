<#
  Phase B one-shot setup for Windows (PowerShell).
  Run from the repo root:  powershell -ExecutionPolicy Bypass -File .\scripts\windows_setup.ps1

  Verifies Python 3.12, installs creativeforge + Playwright Chromium, and runs
  the free pre-flight checks. Does NOT spend any video credits.

  NOTE: we deliberately do NOT set $ErrorActionPreference = "Stop". Native tools
  here (python, pip, playwright, git) routinely write progress/warnings to
  stderr; under "Stop" PowerShell would treat that benign stderr as a fatal
  error. Instead we check $LASTEXITCODE after each native command.
#>

function Step($msg) { Write-Host "`n=== $msg ===" -ForegroundColor Cyan }

function Invoke-Native {
    param([string]$Exe, [string[]]$Args, [string]$What)
    & $Exe @Args
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $What (exit $LASTEXITCODE)" -ForegroundColor Red
        exit 1
    }
}

# --- Python 3.12 check (tolerant of version going to stdout OR stderr) ---------
Step "Python version (want 3.12.x; 3.13 lacks some prebuilt wheels)"
$pyv = (& python --version 2>&1 | Out-String).Trim()
Write-Host $pyv
if ($pyv -notmatch "3\.12") {
    Write-Warning "Python 3.12 not detected (got: '$pyv')."
    Write-Warning "Install it:  winget install -e --id Python.Python.3.12"
    Write-Warning "Then OPEN A NEW terminal and re-run this script."
    Write-Warning "If 'python' opens the Microsoft Store: Settings -> 'Manage app execution aliases' -> turn OFF python.exe / python3.exe."
    exit 1
}

# --- Repo root -----------------------------------------------------------------
Step "Confirm we're at the repo root"
if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "creativeforge")) {
    Write-Warning "Run this from the Video-Generator repo root (pyproject.toml not found here)."
    exit 1
}

# --- Branch (warn only) --------------------------------------------------------
Step "Confirm the verified branch is checked out"
$branch = (& git rev-parse --abbrev-ref HEAD 2>&1 | Out-String).Trim()
Write-Host "On branch: $branch"
if ($branch -ne "claude/compassionate-brahmagupta-eKuPB") {
    Write-Warning "Expected branch claude/compassionate-brahmagupta-eKuPB (PR #2). Run: git checkout claude/compassionate-brahmagupta-eKuPB"
}

# --- Install -------------------------------------------------------------------
Step "Install creativeforge (editable)"
Invoke-Native -Exe "python" -Args @("-m", "pip", "install", "-e", ".") -What "pip install -e ."

Step "Install Playwright Chromium"
Invoke-Native -Exe "python" -Args @("-m", "playwright", "install", "chromium") -What "playwright install chromium"

# --- Free pre-flight (no credits spent) ---------------------------------------
Step "doctor - adapters + environment health"
& creativeforge doctor

Step "dry-run - full plan, spends nothing"
& creativeforge run musinsa-king-choice --dry-run --auto-approve

Step "credits - should read 180 / 1000"
& creativeforge credits musinsa-king-choice

Write-Host "`nSetup OK." -ForegroundColor Green
Write-Host "Next:" -ForegroundColor Green
Write-Host "  1. python scripts/login_google_flow.py      # one-time Google sign-in"
Write-Host "  2. creativeforge run musinsa-king-choice --only s00_character_sheets   # free image stage"
Write-Host "  See PHASE_B_QUICKSTART.md for the selector-iteration loop."
