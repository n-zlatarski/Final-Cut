@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py main.py
) else (
    python main.py
)
if errorlevel 1 (
    echo.
    echo Final Cut stopped with an error. Make sure the requirement is installed:
    echo     py -m pip install -r requirements.txt
    echo.
    pause
)
