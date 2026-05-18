@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

REM ----- 1) Try the official Python Launcher for Windows ('py') first -----
where py >nul 2>&1
if errorlevel 1 goto :try_python

py -3 --version >nul 2>&1
if errorlevel 1 goto :try_python

py -3 "%~dp0run_server.py"
goto :end

REM ----- 2) Fall back to 'python', but verify it's NOT the MS Store stub -----
:try_python
where python >nul 2>&1
if errorlevel 1 goto :no_python

REM The MS Store stub returns non-zero on --version, real Python returns 0.
python --version >nul 2>&1
if errorlevel 1 goto :no_python

python "%~dp0run_server.py"
goto :end

REM ----- 3) No real Python found - show install guide -----
:no_python
echo.
echo [Error] Python 3 is not installed (or only the Microsoft Store stub is on PATH).
echo.
echo  How to fix:
echo  1. Install Python 3 from https://www.python.org/downloads/
echo     During installation, CHECK the box "Add Python to PATH".
echo.
echo  2. If running 'python' opens the Microsoft Store window,
echo     disable the App Installer aliases:
echo     - Open Windows Settings
echo     - Apps ^> Advanced app settings ^> App execution aliases
echo     - Turn OFF "python.exe" and "python3.exe"
echo.

:end
pause
