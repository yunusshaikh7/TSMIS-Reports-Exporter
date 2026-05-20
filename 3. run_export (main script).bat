@echo off
cd /d "%~dp0"

REM Auth check — every export script reads scripts\tsmis_auth.json,
REM which is created by "2. login (update login).bat".
if not exist "scripts\tsmis_auth.json" (
    echo.
    echo ================================================================
    echo  NO SAVED SESSION FOUND
    echo ================================================================
    echo.
    echo  scripts\tsmis_auth.json is missing.
    echo.
    echo  Please run  "2. login (update login).bat"  first, then come
    echo  back and run this file again.
    echo.
    echo ================================================================
    echo.
    pause
    exit /b 1
)

:menu
cls
echo ================================================================
echo                TSMIS Reports - Bulk Exporter
echo ================================================================
echo.
echo  Which report do you want to export for ALL routes?
echo.
echo     1.  TSAR: Ramp Summary        (PDF  -^> output\ramp_summary\)
echo     2.  TSAR: Ramp Detail         (XLSX -^> output\ramp_detail\)
echo     3.  Highway Sequence Listing  (XLSX -^> output\highway_sequence\)
echo.
echo     Q.  Quit
echo.
echo ================================================================
echo.
set "choice="
set /p choice="Enter your choice [1, 2, 3, Q]: "

if /i "%choice%"=="1" goto summary
if /i "%choice%"=="2" goto detail
if /i "%choice%"=="3" goto highway_sequence
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="quit" exit /b 0
echo.
echo Invalid choice "%choice%". Please pick 1, 2, 3, or Q.
echo.
pause
goto menu

:summary
python scripts\export_ramp_summary.py
pause
exit /b 0

:detail
python scripts\export_ramp_detail.py
pause
exit /b 0

:highway_sequence
python scripts\export_highway_sequence.py
pause
exit /b 0
