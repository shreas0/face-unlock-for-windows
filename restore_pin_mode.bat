@echo off
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting Administrator privileges to restore PIN mode...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
echo ========================================================
echo Restoring Windows Default Lock Screen (PIN / Password)
echo ========================================================
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Authentication\Credential Providers\{E7A2A9B8-4384-48C8-8547-074C46A2C59D}" /f >nul 2>&1
echo [OK] Removed FaceUnlock Credential Provider from LogonUI.
reg delete "HKLM\SOFTWARE\Classes\CLSID\{E7A2A9B8-4384-48C8-8547-074C46A2C59D}" /f >nul 2>&1
reg delete "HKCR\CLSID\{E7A2A9B8-4384-48C8-8547-074C46A2C59D}" /f >nul 2>&1
echo [OK] Removed COM CLSID registration.
schtasks /End /TN "FaceUnlock_Helper" >nul 2>&1
schtasks /Change /TN "FaceUnlock_Helper" /DISABLE >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1
echo [OK] Stopped FaceUnlock helper task.
del /f /q "C:\Windows\System32\FaceUnlockProvider.dll" >nul 2>&1
echo.
echo [SUCCESS] Windows Lock Screen has been restored to default PIN/Password mode!
echo You can now lock your screen (Win + L) and it will default to PIN mode.
echo.
pause
