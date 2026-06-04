@echo off
cd /d "%~dp0"

REM ===========================================================================
REM  EXPERIMENTAL "fast mode": runs several headless browsers at once (each
REM  using the SAME saved login) to export routes in parallel. Faster, but
REM  heavier on your PC and on the TSMIS server. The normal one-browser flow is
REM  still "3. run_export (main script).bat" -- use that if anything misbehaves.
REM
REM  How many browsers? The limit is the TSMIS server, not your PC:
REM     3       polite, ~2.5-3x faster, low risk  (recommended)
REM     4 - 5   usually still fine
REM     6       experimental maximum (the script caps higher numbers at 6)
REM ===========================================================================

REM Auth check -- every export script reads scripts\tsmis_auth.json,
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

:workers
cls
echo ================================================================
echo      TSMIS Reports - Bulk Exporter   (FAST MODE, experimental)
echo ================================================================
echo.
echo  How many browsers should run at the same time?
echo.
echo     More browsers = faster, but heavier on your PC and on the
echo     TSMIS server. Recommended: 3 or 4.  Maximum: 6.
echo.
set "workers=3"
set /p workers="Number of browsers [default 3]: "
set "TSMIS_FAST_WORKERS=%workers%"

:menu
cls
echo ================================================================
echo      TSMIS Reports - FAST MODE  (%TSMIS_FAST_WORKERS% browsers at once)
echo ================================================================
echo.
echo  Which report do you want to export for ALL routes?
echo.
echo     1.  TSAR: Ramp Summary        (PDF  -^> output\ramp_summary\)
echo     2.  TSAR: Ramp Detail         (XLSX -^> output\ramp_detail\)
echo     3.  Highway Sequence Listing  (XLSX -^> output\highway_sequence\)
echo.
echo     C.  Change number of browsers (currently %TSMIS_FAST_WORKERS%)
echo     Q.  Quit
echo.
echo ================================================================
echo.
set "choice="
set /p choice="Enter your choice [1, 2, 3, C, Q]: "

if /i "%choice%"=="1" goto summary
if /i "%choice%"=="2" goto detail
if /i "%choice%"=="3" goto highway_sequence
if /i "%choice%"=="C" goto workers
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="quit" exit /b 0
echo.
echo Invalid choice "%choice%". Please pick 1, 2, 3, C, or Q.
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
