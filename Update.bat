@echo off
title RelicBot Updater
echo.
echo Starting RelicBot Updater...
echo.

if "%~1"=="" (
    REM No file dropped — run normally, script will search for ZIP
    powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Update.ps1"
) else (
    REM File was dropped onto this .bat — pass the ZIP path to PowerShell
    powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Update.ps1" -ZipPath "%~1"
)

if errorlevel 1 (
    echo.
    echo Update encountered an issue. Check the messages above.
    echo.
)
pause
