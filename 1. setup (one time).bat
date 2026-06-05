@echo off
cd /d "%~dp0"
echo Installing Python packages...
python -m pip install --upgrade pip
REM Install the exact, pinned versions from requirements.txt so the end-user
REM install matches what the app is built and tested against.
python -m pip install -r requirements.txt
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
