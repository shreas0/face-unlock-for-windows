@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges to register Credential Provider...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
powershell.exe -ExecutionPolicy Bypass -File "%~dp0register_provider.ps1"
pause
