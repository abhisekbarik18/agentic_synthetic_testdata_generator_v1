@echo off
setlocal enabledelayedexpansion

title Agentic Test Data Simulator - Stopping Servers

echo ==========================================================
echo     Agentic LLM Test Data Simulator - Stopping Servers
echo ==========================================================
echo.

:: Execute the PowerShell shutdown script with ExecutionPolicy Bypass
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
set STOP_EXIT=%ERRORLEVEL%

if %STOP_EXIT% NEQ 0 (
    echo.
    echo [ERROR] Shutdown script encountered an error [Exit code: %STOP_EXIT%]
    exit /b %STOP_EXIT%
)

echo.
echo Shutdown complete.
exit /b 0
