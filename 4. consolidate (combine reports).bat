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
echo     3.  TSMIS Ramp Detail (PDF)   (PDF export from output\...\ramp_detail_pdf -^> XLSX)
echo     4.  Highway Sequence Listing  (XLSX -^> XLSX)
echo     5.  TSMIS Highway Sequence (PDF) (PDF export from output\...\highway_sequence_pdf -^> XLSX)
echo     6.  Intersection Summary      (XLSX -^> XLSX)
echo     7.  Intersection Detail       (XLSX -^> XLSX)
echo     8.  TSMIS Intersection Detail (PDF) (PDF export from output\...\intersection_detail_pdf -^> XLSX)
echo     9.  TSMIS Highway Log (Excel) (Excel export from output\...\highway_log -^> XLSX)
echo     10. TSMIS Highway Log (PDF)   (PDF export from output\...\highway_log_pdf -^> XLSX)
echo     11. TSN Highway Log (PDF)     (district PDFs from tsn_library\highway_log\raw -^> XLSX)
echo     12. Highway Detail            (XLSX -^> XLSX)
echo     13. TSMIS Highway Detail (PDF) (PDF export from output\...\highway_detail_pdf -^> XLSX)
echo     14. Highway Summary           (XLSX -^> XLSX)
echo     15. TSAR: Ramp Summary (Excel) (XLSX -^> XLSX)
echo     16. TSMIS Intersection Summary (PDF) (PDF export from output\...\intersection_summary_pdf -^> XLSX)
echo     17. TSMIS Highway Summary (PDF) (PDF export from output\...\highway_summary_pdf -^> XLSX)
echo     18. Clean Road: Highway (XLSX -^> XLSX)
echo     19. TSMIS Clean Road: Highway (PDF) (PDF export from output\...\clean_highway_pdf -^> XLSX)
echo     20. Clean Road: Intersection (XLSX -^> XLSX)
echo     21. TSMIS Clean Road: Intersection (PDF) (PDF export from output\...\clean_intersection_pdf -^> XLSX)
echo     22. Clean Road: Ramp (XLSX -^> XLSX)
echo     23. TSMIS Clean Road: Ramp (PDF) (PDF export from output\...\clean_ramp_pdf -^> XLSX)
echo.
echo     Q.  Quit
echo.
echo ================================================================
echo.
set "choice="
set /p choice="Enter your choice [1-23, Q]: "

if /i "%choice%"=="1" goto ramp_summary
if /i "%choice%"=="2" goto ramp_detail
if /i "%choice%"=="3" goto tsmis_ramp_detail_pdf
if /i "%choice%"=="4" goto highway_sequence
if /i "%choice%"=="5" goto tsmis_highway_sequence_pdf
if /i "%choice%"=="6" goto intersection_summary
if /i "%choice%"=="7" goto intersection_detail
if /i "%choice%"=="8" goto tsmis_intersection_detail_pdf
if /i "%choice%"=="9" goto highway_log
if /i "%choice%"=="10" goto tsmis_highway_log_pdf
if /i "%choice%"=="11" goto tsn_highway_log
if /i "%choice%"=="12" goto highway_detail
if /i "%choice%"=="13" goto tsmis_highway_detail_pdf
if /i "%choice%"=="14" goto highway_summary
if /i "%choice%"=="15" goto ramp_summary_excel
if /i "%choice%"=="16" goto tsmis_intersection_summary_pdf
if /i "%choice%"=="17" goto tsmis_highway_summary_pdf
if /i "%choice%"=="18" goto clean_road_highway
if /i "%choice%"=="19" goto tsmis_clean_highway_pdf
if /i "%choice%"=="20" goto clean_road_intersection
if /i "%choice%"=="21" goto tsmis_clean_intersection_pdf
if /i "%choice%"=="22" goto clean_road_ramp
if /i "%choice%"=="23" goto tsmis_clean_ramp_pdf
if /i "%choice%"=="Q" exit /b 0
if /i "%choice%"=="quit" exit /b 0
echo.
echo Invalid choice "%choice%". Please pick 1-23, or Q.
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

:tsmis_ramp_detail_pdf
python scripts\consolidate_tsmis_ramp_detail_pdf.py
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

:highway_summary
python scripts\consolidate_highway_summary.py
pause
exit /b 0

:ramp_summary_excel
python scripts\consolidate_ramp_summary_excel.py
pause
exit /b 0

:tsmis_intersection_summary_pdf
python scripts\consolidate_tsmis_intersection_summary_pdf.py
pause
exit /b 0

:tsmis_highway_summary_pdf
python scripts\consolidate_tsmis_highway_summary_pdf.py
pause
exit /b 0

:clean_road_highway
python scripts\consolidate_clean_road_highway.py
pause
exit /b 0

:tsmis_clean_highway_pdf
python scripts\consolidate_tsmis_clean_highway_pdf.py
pause
exit /b 0

:clean_road_intersection
python scripts\consolidate_clean_road_intersection.py
pause
exit /b 0

:tsmis_clean_intersection_pdf
python scripts\consolidate_tsmis_clean_intersection_pdf.py
pause
exit /b 0

:clean_road_ramp
python scripts\consolidate_clean_road_ramp.py
pause
exit /b 0

:tsmis_clean_ramp_pdf
python scripts\consolidate_tsmis_clean_ramp_pdf.py
pause
exit /b 0
