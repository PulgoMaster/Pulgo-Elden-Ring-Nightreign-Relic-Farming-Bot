"""Embedded PowerShell updater script.

Written to %TEMP% as a .ps1 file when the user clicks the in-UI Update
button.  The script is invoked with `-ZipPath`, `-InstallDir`, and the
`-WaitForBot` switch so it can wait for RelicBot.exe to release its file
lock before replacing files.

Differences vs. the legacy bundled Update.ps1:
  * Accepts `-InstallDir` instead of relying on its own folder location
    (it lives in %TEMP%, not alongside the EXE).
  * `-WaitForBot` polls for RelicBot.exe to exit instead of refusing when
    the process is still alive.
  * No self-exemption for Update.ps1 / Update.bat — the legacy files are
    no longer shipped and get cleaned up like any other orphan.
"""

UPDATER_PS1 = r"""<#
.SYNOPSIS
    RelicBot in-UI updater -- runs from %TEMP% against a user-picked ZIP.
.DESCRIPTION
    Parameters:
      -ZipPath     Full path to the RelicBot update ZIP.
      -InstallDir  Target install directory (where RelicBot.exe lives).
      -WaitForBot  If set, polls for RelicBot.exe to exit before replacing
                   files instead of erroring out immediately.

    Preserved across updates: profiles, sequences, save_backups, batch_output,
    overlay_stats.txt, relicbot_*.json, .last_profile, gpu_upgrade_ready,
    gpu_upgrade.log, and the ~2 GB _internal\torch\ GPU CUDA install.
    Everything else is wiped and replaced with the new ZIP's contents.
#>

param(
    [string]$ZipPath = "",
    [string]$InstallDir = "",
    [switch]$WaitForBot
)

$scriptDir = if ($InstallDir) { $InstallDir } else { Split-Path -Parent $MyInvocation.MyCommand.Path }

try {

Write-Host ""
Write-Host "=== RelicBot Updater ===" -ForegroundColor Cyan
Write-Host ""

# --- Wait for or check that RelicBot is closed ---
if ($WaitForBot) {
    $maxWait = 30
    $waited = 0
    while ((Get-Process -Name "RelicBot" -ErrorAction SilentlyContinue) -and ($waited -lt $maxWait)) {
        if ($waited -eq 0) {
            Write-Host "Waiting for RelicBot to close..." -ForegroundColor Yellow
        }
        Start-Sleep -Seconds 1
        $waited++
    }
    if ((Get-Process -Name "RelicBot" -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: RelicBot did not close within ${maxWait}s." -ForegroundColor Red
        Write-Host "Close RelicBot manually, then re-run the update." -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    if ($waited -gt 0) {
        Write-Host "RelicBot closed. Proceeding with update." -ForegroundColor Green
    }
} else {
    $running = Get-Process -Name "RelicBot" -ErrorAction SilentlyContinue
    if ($running) {
        Write-Host "ERROR: RelicBot.exe is currently running!" -ForegroundColor Red
        Write-Host "Close RelicBot completely, then run the updater again." -ForegroundColor Yellow
        Read-Host "Press Enter to close"
        exit 1
    }
}

# --- Validate ZIP argument ---
if (-not $ZipPath -or -not (Test-Path $ZipPath)) {
    Write-Host "ERROR: ZIP path was not provided or does not exist: $ZipPath" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
$zipFile = (Resolve-Path $ZipPath).Path

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
# Only downloaded RelicBot*.zip files are exempt so user-downloaded ZIPs
# don't get wiped.  The legacy Update.ps1 / Update.bat files used to be
# self-exempt but are no longer shipped, so any leftover copies on disk
# get cleaned up here.
Write-Host "--- Installing new version (clean replacement) ---" -ForegroundColor Cyan

$removed = 0
Get-ChildItem -Path $scriptDir -ErrorAction SilentlyContinue | Where-Object {
    $_.Name -notlike "RelicBot*.zip"
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
Read-Host "Press Enter to close this window and launch RelicBot"

# --- Launch new RelicBot ---
$newExe = Join-Path $scriptDir "RelicBot.exe"
if (Test-Path $newExe) {
    Start-Process -FilePath $newExe -WorkingDirectory $scriptDir
}
"""
