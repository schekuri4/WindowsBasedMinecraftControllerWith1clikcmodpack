@echo off
setlocal
cd /d "%~dp0"

set "PARSEC_PATH=C:\Program Files\Parsec\parsecd.exe"

if exist "%PARSEC_PATH%" (
    tasklist /FI "IMAGENAME eq parsecd.exe" | find /I "parsecd.exe" >nul
    if errorlevel 1 (
        start "" "%PARSEC_PATH%"
        timeout /t 2 /nobreak >nul
    )
)

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+.
    exit /b 1
)

set "VENV_DIR=.venv"
if not exist "%VENV_DIR%\Scripts\python.exe" (
    set "VENV_DIR=venv"
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    python -m venv venv
    set "VENV_DIR=venv"
)

set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

"%PYTHON_EXE%" -c "import uvicorn" >nul 2>&1
if errorlevel 1 (
    "%PYTHON_EXE%" -m pip install -r requirements.txt --quiet
)

"%PYTHON_EXE%" -m uvicorn app:app --host 0.0.0.0 --port 8080
