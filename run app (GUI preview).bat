@echo off
cd /d "%~dp0"
REM Preview the desktop GUI in dev. Uses your global Python + the packages
REM installed by "1. setup (one time).bat" (Playwright, pdfplumber, openpyxl).
REM Phase 6 will ship this as a windowed .exe with no console window.
python scripts\gui_main.py
if errorlevel 1 pause
