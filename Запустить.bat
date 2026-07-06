@echo off
cd /d "%~dp0"

rem Launch YouTube-to-MP3 GUI. Dependencies auto-install on first run.
where py >nul 2>nul
if %errorlevel%==0 (
    py app.py
    goto end
)

where python >nul 2>nul
if %errorlevel%==0 (
    python app.py
    goto end
)

echo Python not found. Install Python 3.8+ from https://python.org
pause

:end
if %errorlevel% neq 0 pause
