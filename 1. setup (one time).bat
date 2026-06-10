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
echo Downloading the built-in Chromium browser. It becomes the default for
echo sign-in and exports; the Microsoft Edge / Google Chrome already on this
echo PC stay available as fallbacks.
python -m playwright install chromium --no-shell
if errorlevel 1 (
    echo.
    echo WARNING: the Chromium download failed. The tool still works using the
    echo Microsoft Edge or Google Chrome already installed on this PC. Re-run
    echo this setup later to add the built-in Chromium.
)
echo.
echo Setup complete. You can now run "2. login (update login).bat".
pause
