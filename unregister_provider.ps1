#Requires -RunAsAdministrator
$Guid = "{E7A2A9B8-4384-48C8-8547-074C46A2C59D}"
$TargetDll = "C:\Windows\System32\FaceUnlockProvider.dll"
Write-Host "Unregistering FaceUnlock Credential Provider..." -ForegroundColor Yellow
$cpPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Authentication\Credential Providers\$Guid"
if (Test-Path $cpPath) {
    Remove-Item -Path $cpPath -Recurse -Force
    Write-Host "  [OK] Removed Credential Provider registry key" -ForegroundColor Green
}
$clsidPath = "HKLM:\SOFTWARE\Classes\CLSID\$Guid"
if (Test-Path $clsidPath) {
    Remove-Item -Path $clsidPath -Recurse -Force
    Write-Host "  [OK] Removed COM CLSID registry key" -ForegroundColor Green
}
if (Test-Path $TargetDll) {
    try {
        Remove-Item -Path $TargetDll -Force -ErrorAction Stop
        Write-Host "  [OK] Removed $TargetDll" -ForegroundColor Green
    } catch {
        Write-Warning "Could not delete $TargetDll immediately (locked by LogonUI). It will be inactive since registry keys were removed."
    }
}
Write-Host "`n[OK] FaceUnlock Credential Provider has been completely disabled and unregistered." -ForegroundColor Green
