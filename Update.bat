@echo off
title RelicBot Updater
echo.
echo Starting RelicBot Updater...
echo.
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0Update.ps1"
if errorlevel 1 (
    echo.
    echo Update encountered an issue. Check the messages above.
    echo.
)
pause
