@echo off
cd /d "%~dp0"

REM A saved session (scripts\tsmis_auth.json) is no longer required: without
REM one, the export tries automatic sign-in using this PC's work account in
REM Microsoft Edge (works on managed Caltrans PCs).
if not exist "scripts\tsmis_auth.json" (
    echo.
    echo  NOTE: no saved session found. The export will try automatic sign-in
    echo  using this PC's work account in Microsoft Edge. If that does not
    echo  work, run "2. login (update login).bat" first.
    echo.
    pause
)

:menu
cls
echo ================================================================
echo                TSMIS Reports - Bulk Exporter
echo ================================================================
echo.
echo  Which report do you want to export?
echo  After choosing, you'll pick which routes - all, or just some.
echo.
echo     1.  TSAR: Ramp Summary        (PDF  -^> output\ramp_summary\)
echo     2.  TSAR: Ramp Detail         (XLSX -^> output\ramp_detail\)
echo     3.  Highway Sequence Listing  (XLSX -^> output\highway_sequence\)
echo     4.  Highway Log               (XLSX -^> output\highway_log\)
echo     5.  Intersection Summary      (XLSX -^> output\intersection_summary\)
echo     6.  Intersection Detail       (XLSX -^> output\intersection_detail\)
echo.
echo     A.  Several / all report types at once
echo     Q.  Quit
echo.
echo ================================================================
echo.
set "choice="
set /p choice="Enter your choice [1-6, A, Q]: "

if /i "%choice%"=="1" goto summary
if /i "%choice%"=="2" goto detail
if /i "%choice%"=="3" goto highway_sequence
if /i "%choice%"=="4" goto highway_log
if /i "%choice%"=="5" goto intersection_summary
if /i "%choice%"=="6" goto intersection_detail
if /i "%choice%"=="A" goto multi
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="quit" exit /b 0
echo.
echo Invalid choice "%choice%". Please pick 1-6, A, or Q.
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

:intersection_summary
python scripts\export_intersection_summary.py
pause
exit /b 0

:intersection_detail
python scripts\export_intersection_detail.py
pause
exit /b 0

:multi
python scripts\export_multi.py
pause
exit /b 0
