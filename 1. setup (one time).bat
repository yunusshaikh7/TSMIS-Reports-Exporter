@echo off
echo Installing Playwright...
python -m pip install --upgrade pip
python -m pip install playwright
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. Is Python installed and on PATH?
    pause
    exit /b 1
)
echo.
echo Downloading Chromium browser...
python -m playwright install chromium
if errorlevel 1 (
    echo.
    echo ERROR: Chromium download failed.
    pause
    exit /b 1
)
echo.
echo Setup complete. You can now run "2. login (update login).bat".
pause
