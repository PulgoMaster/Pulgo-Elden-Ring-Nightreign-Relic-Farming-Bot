<#
.SYNOPSIS
    In-place RelicBot updater -- preserves GPU torch, profiles, and settings.
.DESCRIPTION
    Usage:
      1. Drag-and-drop a RelicBot*.zip onto Update.bat, OR
      2. Place the ZIP next to this script and double-click Update.bat, OR
      3. Run from terminal: powershell -ExecutionPolicy Bypass -File Update.ps1 -ZipPath "path\to\zip"

    GPU acceleration, profiles, app config, and calibration are preserved.
    Everything else is replaced with the new version.
#>

param(
    [string]$ZipPath = ""
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

try {

Write-Host ""
Write-Host "=== RelicBot Updater ===" -ForegroundColor Cyan
Write-Host ""

# --- Check if RelicBot is running ---
$running = Get-Process -Name "RelicBot" -ErrorAction SilentlyContinue
if ($running) {
    Write-Host "ERROR: RelicBot.exe is currently running!" -ForegroundColor Red
    Write-Host ""
    Write-Host "The updater cannot replace files while RelicBot is open." -ForegroundColor Yellow
    Write-Host "Please close RelicBot completely, then run the updater again." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to close"
    exit 1
}

# --- Find the ZIP ---
$zipFile = $null

if ($ZipPath -and (Test-Path $ZipPath) -and $ZipPath -like "*.zip") {
    $zipFile = (Resolve-Path $ZipPath).Path
    Write-Host "ZIP provided via drag-and-drop." -ForegroundColor Green
}

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

# --- Extract to temp ---
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

$newDir = Join-Path $tempDir "RelicBot"
if (-not (Test-Path $newDir)) { $newDir = $tempDir }
Write-Host "Extracted to: $newDir"
Write-Host ""

# --- Detect GPU torch ---
$cudaDll      = Join-Path $scriptDir "_internal\torch\lib\cudart64_12.dll"
$torchCudaDll = Join-Path $scriptDir "_internal\torch\lib\torch_cuda.dll"
$hasGpuTorch  = (Test-Path $cudaDll) -or (Test-Path $torchCudaDll)

Write-Host "--- GPU Check ---" -ForegroundColor Cyan
if ($hasGpuTorch) {
    Write-Host "  GPU torch DETECTED -- will preserve." -ForegroundColor Green
} else {
    Write-Host "  GPU torch not installed -- CPU version will be used." -ForegroundColor Yellow
}
Write-Host ""

# --- Back up preserved items ---
Write-Host "--- Backing up user data ---" -ForegroundColor Cyan
$backupDir = Join-Path $env:TEMP ("RelicBotBackup_" + [System.Guid]::NewGuid().ToString("N").Substring(0, 8))
New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null

$preserveItems = @(
    "profiles",
    "sequences",
    "save_backups",
    "batch_output",
    "overlay_stats.txt",
    "relicbot_config.json",
    "relicbot_calibration.json",
    "relicbot_timing.json",
    ".last_profile",
    "gpu_upgrade_ready",
    "gpu_upgrade.log"
)

foreach ($item in $preserveItems) {
    $src = Join-Path $scriptDir $item
    if (Test-Path $src) {
        $dst = Join-Path $backupDir $item
        Write-Host "  Backing up $item ..." -ForegroundColor Green
        try { Copy-Item -Recurse $src $dst -Force }
        catch { Write-Host "  WARNING: Could not back up ${item}: $_" -ForegroundColor Yellow }
    }
}

if ($hasGpuTorch) {
    $torchSrc = Join-Path $scriptDir "_internal\torch"
    $torchDst = Join-Path $backupDir "_torch_backup"
    Write-Host "  Backing up GPU torch (~2 GB, may take a moment)..." -ForegroundColor Green
    try { Copy-Item -Recurse $torchSrc $torchDst -Force }
    catch {
        Write-Host "  WARNING: Could not back up torch: $_" -ForegroundColor Yellow
        $hasGpuTorch = $false
    }
}
Write-Host ""

# --- Clean install ---
Write-Host "--- Installing new version (clean replacement) ---" -ForegroundColor Cyan

$removed = 0
Get-ChildItem -Path $scriptDir -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -ne "Update.ps1" -and $_.Name -ne "Update.bat" -and $_.Name -notlike "RelicBot*.zip"
} | ForEach-Object {
    try { Remove-Item -Recurse -Force $_.FullName; $removed++ }
    catch { Write-Host "  WARNING: Could not remove $($_.Name): $_" -ForegroundColor Yellow }
}
Write-Host "  Removed $removed old item(s)."

$copied = 0
Get-ChildItem -Path $newDir -ErrorAction SilentlyContinue | ForEach-Object {
    try { Copy-Item -Recurse $_.FullName (Join-Path $scriptDir $_.Name) -Force; $copied++ }
    catch { Write-Host "  WARNING: Could not copy $($_.Name): $_" -ForegroundColor Yellow }
}
Write-Host "  Copied $copied new item(s)."
Write-Host ""

# --- Restore preserved items ---
Write-Host "--- Restoring user data ---" -ForegroundColor Cyan

foreach ($item in $preserveItems) {
    $src = Join-Path $backupDir $item
    if (Test-Path $src) {
        $dst = Join-Path $scriptDir $item
        Write-Host "  Restoring $item ..." -ForegroundColor Green
        try {
            if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
            Copy-Item -Recurse $src $dst -Force
        } catch { Write-Host "  WARNING: Could not restore ${item}: $_" -ForegroundColor Yellow }
    }
}

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
            $hasGpuTorch = $false
        }
    }
}
Write-Host ""

# --- Refresh default sequences ---
Write-Host "--- Refreshing default sequences ---" -ForegroundColor Cyan
$newSeqSrc = Join-Path $scriptDir "_internal\sequences"
$seqDst    = Join-Path $scriptDir "sequences"
if (Test-Path $newSeqSrc) {
    New-Item -ItemType Directory -Path $seqDst -Force | Out-Null
    $seqCount = 0
    $seqSkipped = 0
    Get-ChildItem -Path $newSeqSrc -Filter "*.json" -ErrorAction SilentlyContinue | ForEach-Object {
        $dst = Join-Path $seqDst $_.Name
        if (Test-Path $dst) {
            $seqSkipped++
        } else {
            Copy-Item $_.FullName $dst -Force
            $seqCount++
        }
    }
    Write-Host "  Added $seqCount new sequence(s), kept $seqSkipped existing." -ForegroundColor Green
} else {
    Write-Host "  WARNING: sequences not found -- not refreshed." -ForegroundColor Yellow
}
Write-Host ""

# --- Profile upgrade (fix mirrored mode_data from pre-v1.6.2 bug) ---
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
                $nLen = $nCrit.Length
                $dLen = $dCrit.Length
                $needsFix = ($nCrit -eq $dCrit -and $nLen -gt 50)
                if ($needsFix -or ($nLen -lt 10 -and $dLen -gt 50) -or ($dLen -lt 10 -and $nLen -gt 50)) {
                    if ($dLen -ge $nLen) {
                        $source = "night"
                        $prof.mode_data.normal = $prof.mode_data.night | ConvertTo-Json -Depth 20 | ConvertFrom-Json
                    } else {
                        $source = "normal"
                        $prof.mode_data.night = $prof.mode_data.normal | ConvertTo-Json -Depth 20 | ConvertFrom-Json
                    }
                    Write-Host "  $($_.Name): Fixed -- copied $source data to both modes." -ForegroundColor Yellow
                    $prof | ConvertTo-Json -Depth 20 | Set-Content $_.FullName -Encoding UTF8
                    $fixCount++
                }
            }
        } catch {
            Write-Host "  WARNING: Could not check $($_.Name): $_" -ForegroundColor Yellow
        }
    }
    if ($fixCount -gt 0) {
        Write-Host "  Repaired $fixCount profile(s). Edit whichever mode you want to differ." -ForegroundColor Yellow
    } else {
        Write-Host "  All profiles OK." -ForegroundColor Green
    }
} else {
    Write-Host "  No profiles folder -- skipping." -ForegroundColor Gray
}
Write-Host ""

# --- Cleanup ---
Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force $backupDir -ErrorAction SilentlyContinue

# --- Verify ---
Write-Host "--- Verifying install ---" -ForegroundColor Cyan
$exeOk      = Test-Path (Join-Path $scriptDir "RelicBot.exe")
$profilesOk = Test-Path (Join-Path $scriptDir "profiles")

Write-Host "  RelicBot.exe present   : $(if ($exeOk) { 'YES' } else { 'NO  <-- PROBLEM' })"
if ($hasGpuTorch) {
    $cudaOk  = Test-Path (Join-Path $scriptDir "_internal\torch\lib\cudart64_12.dll")
    $torchOk = Test-Path (Join-Path $scriptDir "_internal\torch\lib\torch_cuda.dll")
    Write-Host "  GPU torch intact       : $(if ($cudaOk -or $torchOk) { 'YES' } else { 'MISSING' })" `
        -ForegroundColor $(if ($cudaOk -or $torchOk) { 'Green' } else { 'Red' })
}
Write-Host "  profiles folder present: $(if ($profilesOk) { 'YES' } else { 'NO (first run is OK)' })"
Write-Host ""

# --- Result ---
Write-Host "==============================" -ForegroundColor Cyan
Write-Host " Update complete!" -ForegroundColor Green
if ($hasGpuTorch) {
    Write-Host " GPU acceleration preserved." -ForegroundColor Green
}
Write-Host "==============================" -ForegroundColor Cyan

} catch {
    Write-Host ""
    Write-Host "==============================" -ForegroundColor Red
    Write-Host " UPDATE FAILED: $_" -ForegroundColor Red
    Write-Host "==============================" -ForegroundColor Red
}

Write-Host ""
