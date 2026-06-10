@echo off
cd /d "%~dp0"

REM ===========================================================================
REM  EXPERIMENTAL "fast mode": runs several headless browsers at once (each
REM  using the SAME saved login) to export routes in parallel. Faster, but each
REM  browser uses memory and CPU on THIS PC. The normal one-browser flow is
REM  still "3. run_export (main script).bat" -- use that if anything misbehaves.
REM
REM  How many browsers? The TSMIS server handles high concurrency fine, so the
REM  limit is this PC's RAM/CPU (budget ~0.5 GB per browser):
REM     3        safe default, ~2.5-3x faster
REM     8 - 12   big speedup on a healthy multi-core PC
REM     30       maximum (the script caps higher numbers at 30)
REM ===========================================================================

REM A saved session (scripts\tsmis_auth.json) is no longer required: without
REM one, each browser tries automatic sign-in using this PC's work account in
REM Microsoft Edge (works on managed Caltrans PCs).
if not exist "scripts\tsmis_auth.json" (
    echo.
    echo  NOTE: no saved session found. The export will try automatic sign-in
    echo  using this PC's work account in Microsoft Edge. If that does not
    echo  work, run "2. login (update login).bat" first.
    echo.
    pause
)

:workers
cls
echo ================================================================
echo      TSMIS Reports - Bulk Exporter   (FAST MODE, experimental)
echo ================================================================
echo.
echo  How many browsers should run at the same time?
echo.
echo     More browsers = faster, but each one uses memory and CPU on
echo     THIS PC (roughly 0.5 GB each). Default 3.  Maximum: 30.
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
echo  Which report do you want to export?
echo  After choosing, you'll pick which routes - all, or just some.
echo.
echo     1.  TSAR: Ramp Summary        (PDF  -^> output\ramp_summary\)
echo     2.  TSAR: Ramp Detail         (XLSX -^> output\ramp_detail\)
echo     3.  Highway Sequence Listing  (XLSX -^> output\highway_sequence\)
echo     4.  Highway Log               (XLSX -^> output\highway_log\)
echo.
echo     A.  Several / all report types at once
echo     C.  Change number of browsers (currently %TSMIS_FAST_WORKERS%)
echo     Q.  Quit
echo.
echo ================================================================
echo.
set "choice="
set /p choice="Enter your choice [1, 2, 3, 4, A, C, Q]: "

if /i "%choice%"=="1" goto summary
if /i "%choice%"=="2" goto detail
if /i "%choice%"=="3" goto highway_sequence
if /i "%choice%"=="4" goto highway_log
if /i "%choice%"=="A" goto multi
if /i "%choice%"=="C" goto workers
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="quit" exit /b 0
echo.
echo Invalid choice "%choice%". Please pick 1, 2, 3, 4, A, C, or Q.
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

:highway_log
python scripts\export_highway_log.py
pause
exit /b 0

:multi
python scripts\export_multi.py
pause
exit /b 0
