<#
.SYNOPSIS
    In-place RelicBot updater — preserves GPU torch, profiles, and calibration.
.DESCRIPTION
    Drop a new RelicBot*.zip next to this script (or one folder up) and run it.
    GPU acceleration, profiles, and calibration are kept; everything else is
    replaced with the new version.  Works for both release and test ZIPs.
.NOTES
    Run by right-clicking -> "Run with PowerShell", or from a terminal:
        powershell -ExecutionPolicy Bypass -File Update.ps1
#>

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=== RelicBot Updater ===" -ForegroundColor Cyan
Write-Host ""

# ── Find the ZIP ──────────────────────────────────────────────────────────── #
$zipFile = $null
foreach ($searchDir in @($scriptDir, (Split-Path -Parent $scriptDir))) {
    if (-not $searchDir) { continue }
    $found = Get-ChildItem -Path $searchDir -Filter "RelicBot*.zip" -ErrorAction SilentlyContinue |
             Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($found) { $zipFile = $found.FullName; break }
}
if (-not $zipFile) {
    Write-Host "ERROR: No RelicBot*.zip found in this folder or the parent folder." -ForegroundColor Red
    Write-Host "Put the new ZIP next to this script (or one level up), then run again."
    Write-Host ""; Read-Host "Press Enter to exit"; exit 1
}
Write-Host "ZIP      : $zipFile"
Write-Host "Install  : $scriptDir"
Write-Host ""

# ── Extract to temp ───────────────────────────────────────────────────────── #
$tempDir = Join-Path $env:TEMP ("RelicBotUpd_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $tempDir | Out-Null

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

# ── Preserve user data (profiles, calibration, GPU flag files) ─────────────── #
Write-Host "--- Preserving user data ---" -ForegroundColor Cyan

# Items to copy from current install into the new extract before installing
$preserveItems = @(
    "profiles",
    "relicbot_calibration.json",
    ".last_profile"
)

# GPU marker files — kept in place (not overwritten by new CPU zip)
# These signal to the app that GPU accel was installed.
$gpuMarkerFiles = @(
    "gpu_upgrade_ready",
    "gpu_upgrade.log"
)

foreach ($item in $preserveItems) {
    $src = Join-Path $scriptDir $item
    if (Test-Path $src) {
        $dst = Join-Path $newDir $item
        Write-Host "  Preserving $item ..." -ForegroundColor Green
        try {
            if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
            Copy-Item -Recurse $src $dst -Force
        } catch {
            Write-Host "  WARNING: Could not preserve ${item}: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Skipping $item (not present)"
    }
}
Write-Host ""

# ── Install ───────────────────────────────────────────────────────────────── #
Write-Host "--- Installing new version ---" -ForegroundColor Cyan

# Names to never delete or overwrite from the current install folder
$keepNames = @("Update.ps1") + $gpuMarkerFiles

if ($hasGpuTorch) {
    Write-Host "  Mode: GPU-preserve (keeping _internal\torch\ intact)" -ForegroundColor Green
    $oldInternal = Join-Path $scriptDir "_internal"
    $newInternal = Join-Path $newDir "_internal"

    # Delete old _internal items except torch\
    Write-Host "  Clearing old _internal (except torch\)..."
    if (Test-Path $oldInternal) {
        $removed = 0
        Get-ChildItem -Path $oldInternal | Where-Object { $_.Name -ne "torch" } |
            ForEach-Object {
                Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
                $removed++
            }
        Write-Host "    Removed $removed item(s) from _internal."
    }

    # Copy new _internal items except torch\ (CPU torch discarded)
    Write-Host "  Copying new _internal (except torch\)..."
    if (Test-Path $newInternal) {
        $copied = 0
        Get-ChildItem -Path $newInternal | Where-Object { $_.Name -ne "torch" } |
            ForEach-Object {
                Copy-Item -Recurse $_.FullName (Join-Path $oldInternal $_.Name) -Force
                $copied++
            }
        Write-Host "    Copied $copied item(s) into _internal."
    }

    # Replace everything outside _internal\ (EXE, docs, sequences, icons, etc.)
    Write-Host "  Replacing root-level files..."
    $replaced = 0
    Get-ChildItem -Path $newDir | Where-Object { $_.Name -ne "_internal" } |
        ForEach-Object {
            if ($_.Name -in $keepNames) {
                Write-Host "    Keeping (protected): $($_.Name)"
                return
            }
            $dest = Join-Path $scriptDir $_.Name
            if (Test-Path $dest) { Remove-Item -Recurse -Force $dest -ErrorAction SilentlyContinue }
            Copy-Item -Recurse $_.FullName $dest -Force
            $replaced++
        }
    Write-Host "    Replaced $replaced root-level item(s)."

} else {
    Write-Host "  Mode: Full replacement (no GPU torch detected)" -ForegroundColor Yellow
    $removed = 0
    Get-ChildItem -Path $scriptDir | Where-Object {
        $_.Name -notin $keepNames -and $_.Name -notlike "RelicBot*.zip"
    } | ForEach-Object {
        Remove-Item -Recurse -Force $_.FullName -ErrorAction SilentlyContinue
        $removed++
    }
    Write-Host "  Removed $removed old item(s)."

    $copied = 0
    Get-ChildItem -Path $newDir | ForEach-Object {
        Copy-Item -Recurse $_.FullName (Join-Path $scriptDir $_.Name) -Force
        $copied++
    }
    Write-Host "  Copied $copied new item(s)."
}

Write-Host ""

# ── Refresh default sequences ─────────────────────────────────────────────── #
# The app only seeds sequences from _internal/ if they don't already exist, so
# old sequences survive an in-place update and can break changed phase logic.
# Force-overwrite the default sequences from the newly installed _internal/ here.
Write-Host "--- Refreshing default sequences ---" -ForegroundColor Cyan
$newSeqSrc = Join-Path $scriptDir "_internal\sequences"
$seqDst    = Join-Path $scriptDir "sequences"
if (Test-Path $newSeqSrc) {
    New-Item -ItemType Directory -Path $seqDst -Force | Out-Null
    $seqCount = 0
    Get-ChildItem -Path $newSeqSrc -Filter "*.json" | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $seqDst $_.Name) -Force
        $seqCount++
    }
    Write-Host "  Refreshed $seqCount default sequence file(s)." -ForegroundColor Green
    Write-Host "  NOTE: If you have custom re-recorded sequences, re-record them again." -ForegroundColor Yellow
} else {
    Write-Host "  WARNING: _internal\sequences not found — sequences not refreshed." -ForegroundColor Yellow
}
Write-Host ""

# ── Cleanup ───────────────────────────────────────────────────────────────── #
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue

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

Write-Host ""
Read-Host "Press Enter to exit"
