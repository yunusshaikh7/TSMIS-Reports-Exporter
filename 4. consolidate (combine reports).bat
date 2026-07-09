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
echo     1.  TSAR: Ramp Summary        (PDFs -^> XLSX)
echo     2.  TSAR: Ramp Detail         (XLSX -^> XLSX)
echo     3.  Highway Sequence Listing  (XLSX -^> XLSX)
echo     4.  TSMIS Highway Sequence (PDF) (PDF export from output\...\highway_sequence_pdf -^> XLSX)
echo     5.  Intersection Summary      (XLSX -^> XLSX)
echo     6.  Intersection Detail       (XLSX -^> XLSX)
echo     7.  TSMIS Intersection Detail (PDF) (PDF export from output\...\intersection_detail_pdf -^> XLSX)
echo     8.  TSMIS Highway Log (Excel) (Excel export from output\...\highway_log -^> XLSX)
echo     9.  TSMIS Highway Log (PDF)   (PDF export from output\...\highway_log_pdf -^> XLSX)
echo     10. TSN Highway Log (PDF)     (district PDFs from input\tsn_highway_log -^> XLSX)
echo     11. Highway Detail            (XLSX -^> XLSX)
echo     12. TSMIS Highway Detail (PDF) (PDF export from output\...\highway_detail_pdf -^> XLSX)
echo.
echo     Q.  Quit
echo.
echo ================================================================
echo.
set "choice="
set /p choice="Enter your choice [1-12, Q]: "

if /i "%choice%"=="1" goto ramp_summary
if /i "%choice%"=="2" goto ramp_detail
if /i "%choice%"=="3" goto highway_sequence
if /i "%choice%"=="4" goto tsmis_highway_sequence_pdf
if /i "%choice%"=="5" goto intersection_summary
if /i "%choice%"=="6" goto intersection_detail
if /i "%choice%"=="7" goto tsmis_intersection_detail_pdf
if /i "%choice%"=="8" goto highway_log
if /i "%choice%"=="9" goto tsmis_highway_log_pdf
if /i "%choice%"=="10" goto tsn_highway_log
if /i "%choice%"=="11" goto highway_detail
if /i "%choice%"=="12" goto tsmis_highway_detail_pdf
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="quit" exit /b 0
echo.
echo Invalid choice "%choice%". Please pick 1-12, or Q.
echo.
pause
goto menu

:ramp_summary
python scripts\consolidate_ramp_summary.py
pause
exit /b 0

:ramp_detail
python scripts\consolidate_ramp_detail.py
pause
exit /b 0

:highway_sequence
python scripts\consolidate_highway_sequence.py
pause
exit /b 0

:tsmis_highway_sequence_pdf
python scripts\consolidate_tsmis_highway_sequence_pdf.py
pause
exit /b 0

:intersection_summary
python scripts\consolidate_intersection_summary.py
pause
exit /b 0

:intersection_detail
python scripts\consolidate_intersection_detail.py
pause
exit /b 0

:tsmis_intersection_detail_pdf
python scripts\consolidate_tsmis_intersection_detail_pdf.py
pause
exit /b 0

:highway_log
python scripts\consolidate_highway_log.py
pause
exit /b 0

:tsmis_highway_log_pdf
python scripts\consolidate_tsmis_highway_log_pdf.py
pause
exit /b 0

:tsn_highway_log
python scripts\consolidate_tsn_highway_log.py
pause
exit /b 0

:highway_detail
python scripts\consolidate_highway_detail.py
pause
exit /b 0

:tsmis_highway_detail_pdf
python scripts\consolidate_tsmis_highway_detail_pdf.py
pause
exit /b 0
