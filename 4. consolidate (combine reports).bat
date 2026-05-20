@echo off
cd /d "%~dp0"

:menu
cls
echo ================================================================
echo            TSMIS Reports - Bulk Consolidator
echo ================================================================
echo.
echo  Combine per-route exports into one Excel file in
echo  output\consolidated\.  Run the matching export from
echo  "3. run_export (main script).bat" first.
echo.
echo  Which report do you want to consolidate?
echo.
echo     1.  TSAR: Ramp Summary       (PDFs   -^> XLSX)
echo     2.  TSAR: Ramp Detail        (coming soon)
echo     3.  Highway Sequence Listing (coming soon)
echo.
echo     Q.  Quit
echo.
echo ================================================================
echo.
set "choice="
set /p choice="Enter your choice [1, 2, 3, Q]: "

if /i "%choice%"=="1" goto ramp_summary
if /i "%choice%"=="2" goto not_yet
if /i "%choice%"=="3" goto not_yet
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="quit" exit /b 0
echo.
echo Invalid choice "%choice%". Please pick 1, 2, 3, or Q.
echo.
pause
goto menu

:ramp_summary
python scripts\consolidate_ramp_summary.py
pause
exit /b 0

:not_yet
echo.
echo That consolidator is not implemented yet.
echo.
pause
goto menu
