@echo off
setlocal
cd /d "%~dp0"

set "TASK_NAME=MCServerPanel + Parsec Startup"
set "LAUNCHER=%~dp0startup_launcher.bat"
set "TASK_COMMAND=cmd.exe /c ""%LAUNCHER%"""

echo [*] Configuring startup task: %TASK_NAME%

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if not errorlevel 1 (
    schtasks /Delete /TN "%TASK_NAME%" /F >nul
)

schtasks /Create /TN "%TASK_NAME%" /TR "%TASK_COMMAND%" /SC ONLOGON /RL LIMITED /F >nul
if errorlevel 1 (
    echo [ERROR] Failed to create startup task.
    echo Try running this script as Administrator.
    exit /b 1
)

echo [OK] Startup task created.
echo It will start Parsec and MCServerPanel at user logon.
exit /b 0
