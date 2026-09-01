@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges to register startup task...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
powershell.exe -ExecutionPolicy Bypass -File "%~dp0setup_task.ps1"
pause
