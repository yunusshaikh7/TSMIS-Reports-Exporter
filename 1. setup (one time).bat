@echo off
echo Installing Python packages...
python -m pip install --upgrade pip
python -m pip install playwright pdfplumber openpyxl
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. Is Python installed and on PATH?
    pause
    exit /b 1
)
echo.
echo This tool uses the Microsoft Edge (or Chrome) already installed on this PC,
echo so there is no browser to download.
echo.
echo Setup complete. You can now run "2. login (update login).bat".
pause
