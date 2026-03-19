@echo off
title MCServerPanel Launcher
echo ==========================================
echo     MCServerPanel - Minecraft Server Manager
echo ==========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "venv" (
    echo [*] Creating virtual environment...
    python -m venv venv
)

echo [*] Activating virtual environment...
call venv\Scripts\activate.bat

echo [*] Installing dependencies...
pip install -r requirements.txt --quiet

echo.
echo [*] Starting MCServerPanel on http://localhost:8080
echo [*] API docs at http://localhost:8080/api/docs
echo [*] Press Ctrl+C to stop
echo.
python -m uvicorn app:app --host 0.0.0.0 --port 8080 --reload
pause
