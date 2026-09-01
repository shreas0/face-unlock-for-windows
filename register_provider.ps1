#Requires -RunAsAdministrator
param(
    [string]$SourceDll = "$PSScriptRoot\FaceUnlockProvider\FaceUnlockProvider.dll"
)
$Guid = "{E7A2A9B8-4384-48C8-8547-074C46A2C59D}"
$TargetDll = "C:\Windows\System32\FaceUnlockProvider.dll"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Windows Credential Provider Registration" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
if (-not (Test-Path $SourceDll)) {
    $fallback = "$PSScriptRoot\FaceUnlockProvider.dll"
    if (Test-Path $fallback) {
        $SourceDll = $fallback
    } else {
        Write-Error "FaceUnlockProvider.dll not found! Please compile the C++ project first using build_provider.bat."
        exit 1
    }
}
Write-Host "1. Installing DLL to System32..."
Copy-Item -Path $SourceDll -Destination $TargetDll -Force
Write-Host "   Installed: $TargetDll" -ForegroundColor Green
Write-Host "2. Registering COM CLSID..."
$clsidPath = "HKLM:\SOFTWARE\Classes\CLSID\$Guid"
New-Item -Path $clsidPath -Force | Out-Null
Set-ItemProperty -Path $clsidPath -Name "(Default)" -Value "FaceUnlockProvider"
$inprocPath = "$clsidPath\InprocServer32"
New-Item -Path $inprocPath -Force | Out-Null
Set-ItemProperty -Path $inprocPath -Name "(Default)" -Value $TargetDll
Set-ItemProperty -Path $inprocPath -Name "ThreadingModel" -Value "Apartment"
Write-Host "   COM InProcServer32 registered." -ForegroundColor Green
Write-Host "3. Registering Credential Provider in Windows..."
$cpPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Authentication\Credential Providers\$Guid"
New-Item -Path $cpPath -Force | Out-Null
Set-ItemProperty -Path $cpPath -Name "(Default)" -Value "FaceUnlockProvider"
Write-Host "   Credential Provider registered in LogonUI." -ForegroundColor Green
Write-Host "4. Registering FaceUnlock Registry Configuration for Auto-Launch..."
$configPath = "HKLM:\SOFTWARE\FaceUnlock"
New-Item -Path $configPath -Force | Out-Null
Set-ItemProperty -Path $configPath -Name "InstallDir" -Value $PSScriptRoot
$venvDir = Join-Path $PSScriptRoot ".venv"
$venvPythonw = Join-Path $venvDir "Scripts\pythonw.exe"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (Test-Path $venvPythonw) {
    $pythonExe = $venvPythonw
} elseif (Test-Path $venvPython) {
    $pythonExe = $venvPython
} else {
    $pythonExe = (python -c "import sys; print(sys.executable)" 2>$null)
    if (-not $pythonExe) { $pythonExe = "pythonw.exe" }
}
Set-ItemProperty -Path $configPath -Name "PythonPath" -Value $pythonExe
Set-ItemProperty -Path $configPath -Name "ScriptPath" -Value "$PSScriptRoot\face_helper.py"
Write-Host "   FaceUnlock HKLM configuration stored (InstallDir: $PSScriptRoot, Python: $pythonExe)." -ForegroundColor Green
Write-Host ""
Write-Host "[SUCCESS] FaceUnlock Credential Provider is now active with On-Demand Auto-Launch!" -ForegroundColor Green
Write-Host "Your standard PIN and Password login tiles remain 100% available as safe fallbacks."
Write-Host ""
Write-Host "Next Step:" -ForegroundColor Yellow
Write-Host "  Run setup_task.ps1 to register startup task, or test lock screen directly (Win + L)."
Write-Host "==========================================================" -ForegroundColor Cyan
