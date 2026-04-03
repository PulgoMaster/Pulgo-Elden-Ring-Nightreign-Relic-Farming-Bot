<#
.SYNOPSIS
    In-place RelicBot updater — preserves GPU torch, profiles, and settings.
.DESCRIPTION
    Usage:
      1. Drag-and-drop a RelicBot*.zip onto Update.bat, OR
      2. Place the ZIP next to this script and double-click Update.bat, OR
      3. Run from terminal: powershell -ExecutionPolicy Bypass -File Update.ps1 -ZipPath "path\to\zip"

    GPU acceleration, profiles, app config, and calibration are preserved.
    Everything else is replaced with the new version.
.NOTES
    The update does a CLEAN replacement: old files deleted, new files copied,
    then preserved items restored. Prevents stale files from interfering.
#>

param(
    [string]$ZipPath = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

try {

Write-Host ""
Write-Host "=== RelicBot Updater ===" -ForegroundColor Cyan
Write-Host ""

# ── Find the ZIP ──────────────────────────────────────────────────────────── #
$zipFile = $null

# Priority 1: ZIP path passed as argument (drag-and-drop or command line)
if ($ZipPath -and (Test-Path $ZipPath) -and $ZipPath -like "*.zip") {
    $zipFile = (Resolve-Path $ZipPath).Path
    Write-Host "ZIP provided via drag-and-drop." -ForegroundColor Green
}

# Priority 2: Search next to script and one level up
if (-not $zipFile) {
    foreach ($searchDir in @($scriptDir, (Split-Path -Parent $scriptDir))) {
        if (-not $searchDir) { continue }
        $found = Get-ChildItem -Path $searchDir -Filter "RelicBot*.zip" -ErrorAction SilentlyContinue |
                 Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($found) { $zipFile = $found.FullName; break }
    }
}

if (-not $zipFile) {
    Write-Host "ERROR: No RelicBot*.zip found." -ForegroundColor Red
    Write-Host ""
    Write-Host "How to update:" -ForegroundColor Yellow
    Write-Host "  1. Download the new RelicBot ZIP from GitHub"
    Write-Host "  2. Drag the ZIP file onto Update.bat"
    Write-Host "  OR place the ZIP next to Update.bat and double-click it."
    Write-Host ""
    exit 1
}
Write-Host "ZIP      : $zipFile"
Write-Host "Install  : $scriptDir"
Write-Host ""

# ── Extract to temp ───────────────────────────────────────────────────────── #
$tempDir = Join-Path $env:TEMP ("RelicBotUpd_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $tempDir -ErrorAction Stop | Out-Null

Write-Host "Extracting ZIP..." -ForegroundColor Yellow
try {
    Expand-Archive -Path $zipFile -DestinationPath $tempDir -Force
} catch {
    Write-Host "ERROR: Could not extract ZIP: $_" -ForegroundColor Red
    Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
    Write-Host ""; Read-Host "Press Enter to exit"; exit 1
}

# ZIP may contain a RelicBot\ subfolder
$newDir = Join-Path $tempDir "RelicBot"
if (-not (Test-Path $newDir)) { $newDir = $tempDir }
Write-Host "Extracted to: $newDir"
Write-Host ""

# ── Detect GPU torch ──────────────────────────────────────────────────────── #
$cudaDll      = Join-Path $scriptDir "_internal\torch\lib\cudart64_12.dll"
$torchCudaDll = Join-Path $scriptDir "_internal\torch\lib\torch_cuda.dll"
$hasGpuTorch  = (Test-Path $cudaDll) -or (Test-Path $torchCudaDll)

Write-Host "--- GPU Check ---" -ForegroundColor Cyan
Write-Host "  cudart64_12.dll  : $(if (Test-Path $cudaDll) { 'FOUND' } else { 'not found' })"
Write-Host "  torch_cuda.dll   : $(if (Test-Path $torchCudaDll) { 'FOUND' } else { 'not found' })"
if ($hasGpuTorch) {
    Write-Host "  Result           : GPU torch DETECTED — will preserve." -ForegroundColor Green
} else {
    Write-Host "  Result           : GPU torch not installed — CPU version will be used." -ForegroundColor Yellow
}
Write-Host ""

# ── Back up preserved items to temp ───────────────────────────────────────── #
# Everything is backed up BEFORE the old install is wiped, then restored after.
Write-Host "--- Backing up user data ---" -ForegroundColor Cyan

$backupDir = Join-Path $env:TEMP ("RelicBotBackup_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null

# User data to preserve across updates
$preserveItems = @(
    "profiles",
    "relicbot_config.json",
    "relicbot_calibration.json",
    "relicbot_timing.json",
    ".last_profile"
)

# GPU marker files
$gpuMarkerFiles = @(
    "gpu_upgrade_ready",
    "gpu_upgrade.log"
)

foreach ($item in $preserveItems + $gpuMarkerFiles) {
    $src = Join-Path $scriptDir $item
    if (Test-Path $src) {
        $dst = Join-Path $backupDir $item
        Write-Host "  Backing up $item ..." -ForegroundColor Green
        try {
            Copy-Item -Recurse $src $dst -Force
        } catch {
            Write-Host "  WARNING: Could not back up ${item}: $_" -ForegroundColor Yellow
        }
    }
}

# Back up GPU torch directory if present
if ($hasGpuTorch) {
    $torchSrc = Join-Path $scriptDir "_internal\torch"
    $torchDst = Join-Path $backupDir "_torch_backup"
    Write-Host "  Backing up GPU torch (~2 GB, may take a moment)..." -ForegroundColor Green
    try {
        Copy-Item -Recurse $torchSrc $torchDst -Force
    } catch {
        Write-Host "  WARNING: Could not back up torch: $_" -ForegroundColor Yellow
        Write-Host "  GPU acceleration may need to be reinstalled." -ForegroundColor Yellow
        $hasGpuTorch = $false
    }
}
Write-Host ""

# ── Clean install — wipe old, copy new ────────────────────────────────────── #
# This is the key difference from the old script: EVERYTHING is deleted first
# (except the ZIP itself and this script), then new files are copied.  This
# prevents stale files from previous versions from persisting and interfering.
Write-Host "--- Installing new version (clean replacement) ---" -ForegroundColor Cyan

# Delete all old items
$removed = 0
Get-ChildItem -Path $scriptDir -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -ne "Update.ps1" -and $_.Name -ne "Update.bat" -and $_.Name -notlike "RelicBot*.zip"
} | ForEach-Object {
    try {
        Remove-Item -Recurse -Force $_.FullName
        $removed++
    } catch {
        Write-Host "  WARNING: Could not remove $($_.Name): $_" -ForegroundColor Yellow
    }
}
Write-Host "  Removed $removed old item(s)."

# Copy all new items (including the new Update.ps1 — self-update)
$copied = 0
Get-ChildItem -Path $newDir -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Copy-Item -Recurse $_.FullName (Join-Path $scriptDir $_.Name) -Force
        $copied++
    } catch {
        Write-Host "  WARNING: Could not copy $($_.Name): $_" -ForegroundColor Yellow
    }
}
Write-Host "  Copied $copied new item(s)."
Write-Host ""

# ── Restore preserved items ───────────────────────────────────────────────── #
Write-Host "--- Restoring user data ---" -ForegroundColor Cyan

foreach ($item in $preserveItems + $gpuMarkerFiles) {
    $src = Join-Path $backupDir $item
    if (Test-Path $src) {
        $dst = Join-Path $scriptDir $item
        Write-Host "  Restoring $item ..." -ForegroundColor Green
        try {
            if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
            Copy-Item -Recurse $src $dst -Force
        } catch {
            Write-Host "  WARNING: Could not restore ${item}: $_" -ForegroundColor Yellow
        }
    }
}

# Restore GPU torch
if ($hasGpuTorch) {
    $torchBackup = Join-Path $backupDir "_torch_backup"
    $torchDst    = Join-Path $scriptDir "_internal\torch"
    if (Test-Path $torchBackup) {
        Write-Host "  Restoring GPU torch..." -ForegroundColor Green
        try {
            if (Test-Path $torchDst) { Remove-Item -Recurse -Force $torchDst }
            Copy-Item -Recurse $torchBackup $torchDst -Force
        } catch {
            Write-Host "  WARNING: Could not restore torch: $_" -ForegroundColor Yellow
            Write-Host "  You may need to reinstall GPU Acceleration." -ForegroundColor Yellow
            $hasGpuTorch = $false
        }
    }
}
Write-Host ""

# ── Refresh default sequences ─────────────────────────────────────────────── #
# Force-overwrite the default sequences from the newly installed _internal/.
Write-Host "--- Refreshing default sequences ---" -ForegroundColor Cyan
$newSeqSrc = Join-Path $scriptDir "_internal\sequences"
$seqDst    = Join-Path $scriptDir "sequences"
if (Test-Path $newSeqSrc) {
    New-Item -ItemType Directory -Path $seqDst -Force | Out-Null
    $seqCount = 0
    Get-ChildItem -Path $newSeqSrc -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $seqDst $_.Name) -Force
        $seqCount++
    }
    Write-Host "  Refreshed $seqCount default sequence file(s)." -ForegroundColor Green
    Write-Host "  NOTE: If you have custom re-recorded sequences, re-record them again." -ForegroundColor Yellow
} else {
    Write-Host "  WARNING: _internal\sequences not found — sequences not refreshed." -ForegroundColor Yellow
}
Write-Host ""

# ── Profile upgrade — fix mirrored mode_data from pre-v1.6.2 bug ─────────── #
# Versions before v1.6.2 could save identical data for both Normal and Deep of
# Night modes due to shared object references. This detects the corruption and
# ensures the JSON has proper deep-copied independent data for each mode.
# Both modes keep the same data (since we can't guess which is "correct") —
# the user can then edit whichever mode they want to differ.
Write-Host "--- Checking profiles for mode_data bug ---" -ForegroundColor Cyan
$profilesDir = Join-Path $scriptDir "profiles"
if (Test-Path $profilesDir) {
    $fixCount = 0
    Get-ChildItem -Path $profilesDir -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $raw = Get-Content $_.FullName -Raw -Encoding UTF8
            $prof = $raw | ConvertFrom-Json
            if ($prof.mode_data -and $prof.mode_data.normal -and $prof.mode_data.night) {
                $nCrit = ($prof.mode_data.normal.criteria | ConvertTo-Json -Depth 10 -Compress)
                $dCrit = ($prof.mode_data.night.criteria  | ConvertTo-Json -Depth 10 -Compress)
                if ($nCrit -eq $dCrit -and $nCrit.Length -gt 50) {
                    Write-Host "  $($_.Name): MIRRORED data detected — re-saving with independent copies." -ForegroundColor Yellow
                    # Re-serialize with proper formatting to break any shared references.
                    # Both modes keep their current data — user edits whichever they want.
                    $prof | ConvertTo-Json -Depth 20 | Set-Content $_.FullName -Encoding UTF8
                    $fixCount++
                }
            }
        } catch {
            Write-Host "  WARNING: Could not check $($_.Name): $_" -ForegroundColor Yellow
        }
    }
    if ($fixCount -gt 0) {
        Write-Host "  Repaired $fixCount profile(s). Both modes have the same data for now." -ForegroundColor Yellow
        Write-Host "  Open RelicBot, switch to the mode you want to change, edit it, and save." -ForegroundColor Yellow
    } else {
        Write-Host "  All profiles OK." -ForegroundColor Green
    }
} else {
    Write-Host "  No profiles folder found — skipping." -ForegroundColor Gray
}
Write-Host ""

# ── Cleanup ───────────────────────────────────────────────────────────────── #
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $backupDir -ErrorAction SilentlyContinue

# ── Post-install verification ─────────────────────────────────────────────── #
Write-Host "--- Verifying install ---" -ForegroundColor Cyan

$exeOk      = Test-Path (Join-Path $scriptDir "RelicBot.exe")
$cudaOk     = Test-Path (Join-Path $scriptDir "_internal\torch\lib\cudart64_12.dll")
$torchOk    = Test-Path (Join-Path $scriptDir "_internal\torch\lib\torch_cuda.dll")
$profilesOk = Test-Path (Join-Path $scriptDir "profiles")

Write-Host "  RelicBot.exe present   : $(if ($exeOk) { 'YES' } else { 'NO  <-- PROBLEM' })"
if ($hasGpuTorch) {
    Write-Host "  cudart64_12.dll intact : $(if ($cudaOk) { 'YES' } else { 'NO  <-- GPU LOST - PROBLEM!' })" `
        -ForegroundColor $(if ($cudaOk) { 'Green' } else { 'Red' })
    Write-Host "  torch_cuda.dll intact  : $(if ($torchOk) { 'YES' } else { 'NO  <-- GPU LOST - PROBLEM!' })" `
        -ForegroundColor $(if ($torchOk) { 'Green' } else { 'Red' })
}
Write-Host "  profiles folder present: $(if ($profilesOk) { 'YES' } else { 'NO (no profiles yet — OK if first run)' })"
Write-Host ""

# ── Result ────────────────────────────────────────────────────────────────── #
$gpuLost = $hasGpuTorch -and (-not $cudaOk) -and (-not $torchOk)

if ($gpuLost) {
    Write-Host "==============================" -ForegroundColor Red
    Write-Host " WARNING: GPU torch was detected before update" -ForegroundColor Red
    Write-Host " but CUDA DLLs are missing after update!" -ForegroundColor Red
    Write-Host " You may need to reinstall GPU Acceleration." -ForegroundColor Red
    Write-Host "==============================" -ForegroundColor Red
} else {
    Write-Host "==============================" -ForegroundColor Cyan
    Write-Host " Update complete!" -ForegroundColor Green
    if ($hasGpuTorch) {
        Write-Host " GPU acceleration preserved." -ForegroundColor Green
        Write-Host " No reinstall needed." -ForegroundColor Green
    }
    Write-Host "==============================" -ForegroundColor Cyan
}

} catch {
    Write-Host ""
    Write-Host "==============================" -ForegroundColor Red
    Write-Host " UPDATE FAILED" -ForegroundColor Red
    Write-Host " Error: $_" -ForegroundColor Red
    Write-Host "==============================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please report this error." -ForegroundColor Yellow
}

Write-Host ""
# When run via Update.bat, the .bat handles the pause.
# When run directly, also pause so the window stays open.
if (-not $env:PROMPT) { Read-Host "Press Enter to exit" }
