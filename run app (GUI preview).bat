@echo off
cd /d "%~dp0"
REM Preview the desktop GUI in dev. Uses your global Python + the packages
REM installed by "1. setup (one time).bat" (Playwright, pdfplumber, openpyxl,
REM pywebview -- the window is an Edge WebView2 rendering scripts\ui).
REM The packaged windowed .exe (no console) is produced by build\build.ps1.
python scripts\gui_main.py
if errorlevel 1 pause
