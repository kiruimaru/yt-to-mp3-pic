@echo off
cd /d "%~dp0"

rem === Build a standalone Windows .exe (Python + ffmpeg bundled inside) ===
rem Just double-click this file. The result appears in the dist folder.

echo ============================================
echo   Building YouTube-to-MP3.exe
echo   This may take a few minutes on first run.
echo ============================================
echo.

rem Pick python launcher
set PY=python
where py >nul 2>nul && set PY=py

echo [1/2] Installing build tools and dependencies...
%PY% -m pip install --upgrade pyinstaller yt-dlp imageio-ffmpeg
if %errorlevel% neq 0 goto fail

echo.
echo [2/2] Building the .exe ...
%PY% -m PyInstaller --noconfirm --onefile --windowed --name "YouTube-to-MP3" --collect-all imageio_ffmpeg app.py
if %errorlevel% neq 0 goto fail

echo.
echo ============================================
echo   DONE!  Your program is here:
echo   dist\YouTube-to-MP3.exe
echo   Send THAT single file to anyone.
echo ============================================
pause
exit /b 0

:fail
echo.
echo Build failed. Make sure Python 3.8+ is installed from https://python.org
echo (during install, tick "Add Python to PATH").
pause
exit /b 1
