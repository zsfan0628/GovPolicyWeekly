@echo off
setlocal

cd /d "%~dp0"

echo This script will build GovPolicyWeekly for Windows.
echo It can install local Python and Playwright Chromium when missing.
echo This build uses the Qt/PySide6 UI, so it does not require tkinter.
echo If you previously built a broken version, delete python310, .venv, build, and dist before rebuilding.
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 (
  echo.
  echo Build failed. Please read the error message above.
  pause
  exit /b 1
)

echo.
echo Build finished.
pause
