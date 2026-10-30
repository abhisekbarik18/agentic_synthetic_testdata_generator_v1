@echo off
setlocal

title Agentic Test Data Simulator - Launcher

echo ==========================================================
echo     Agentic LLM Test Data Simulator - Setup ^& Startup
echo ==========================================================
echo.

:: Execute the PowerShell setup and launcher script with ExecutionPolicy Bypass
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"

set SCRIPT_EXIT=%ERRORLEVEL%
if %SCRIPT_EXIT% NEQ 0 (
    echo.
    echo [ERROR] Startup script encountered an error [Exit code: %SCRIPT_EXIT%]
    pause
)

exit /b %SCRIPT_EXIT%
