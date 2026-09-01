#Requires -RunAsAdministrator
param(
    [string]$ProjectDir = $PSScriptRoot,
    [string]$TaskName = "FaceUnlock_Helper",
    [string]$ScriptName = "face_helper.py"
)
if (-not $ProjectDir) {
    $ProjectDir = "C:\Users\shres\FaceUnlock"
}
$username = $env:USERNAME
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$venvDir = Join-Path $ProjectDir ".venv"
$venvPythonw = Join-Path $venvDir "Scripts\pythonw.exe"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPythonw) -and -not (Test-Path $venvPython)) {
    Write-Error "Project venv not found at $venvDir. Create/repair it with the real python.org interpreter before registering the task."
    exit 1
}
if (-not (Test-Path $venvPythonw)) {
    $venvPythonw = $venvPython
    Write-Warning "pythonw.exe missing from .venv; using python.exe instead: $venvPythonw"
}
$pythonw = $venvPythonw
if (-not (Test-Path $pythonw)) {
    Write-Warning "No project venv interpreter found. Checking system PATH as last resort..."
    $fallback = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
    if (-not $fallback) {
        $fallback = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    }
    if ($fallback) {
        if ($fallback -like "*WindowsApps*") {
            Write-Error "Resolved Python path '$fallback' is a Windows Store App Execution Alias stub.`nThis alias fails when launched via CreateProcessW from Credential Provider DLL / non-interactive contexts.`nPlease install a real python.org interpreter and recreate the project .venv."
            exit 1
        }
        Write-Warning "Using system Python fallback: $fallback"
        $pythonw = $fallback
    } else {
        Write-Error "No Python interpreter found. Please install Python and create the project .venv."
        exit 1
    }
}
$scriptPath = Join-Path $ProjectDir $ScriptName
if (-not (Test-Path $scriptPath)) {
    Write-Error "Script not found at $scriptPath"
    exit 1
}
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " FaceUnlock: Persistent Startup Task Registration" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Task Name:   $TaskName"
Write-Host "  User:        $username $(if ($isAdmin) { '(Elevated Admin)' } else { '(Standard User)' })"
Write-Host "  Python:      $pythonw"
Write-Host "  Script:      $scriptPath"
Write-Host "  Trigger:     System Boot (AtStartup) + User Logon (AtLogOn)"
Write-Host ""
Unregister-ScheduledTask -TaskName "FaceUnlock_SystemWatcher" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$scriptPath`"" -WorkingDirectory $ProjectDir
$triggerBoot = New-ScheduledTaskTrigger -AtStartup
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn -User $username
$triggers = @($triggerBoot, $triggerLogon)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -RestartCount 3 `
    -ExecutionTimeLimit ([TimeSpan]::Zero)
if ($isAdmin) {
    $principal = New-ScheduledTaskPrincipal -UserId $username -LogonType Interactive -RunLevel Highest
} else {
    $principal = New-ScheduledTaskPrincipal -UserId $username -LogonType Interactive
}
$taskParams = @{
    TaskName    = $TaskName
    Action      = $action
    Trigger     = $triggers
    Settings    = $settings
    Principal   = $principal
    Description = "FaceUnlock real-time biometric Named Pipe IPC service for Windows LogonUI Secure Desktop"
    Force       = $true
}
Register-ScheduledTask @taskParams | Out-Null
Write-Host "[OK] Task '$TaskName' registered successfully with Highest Privileges!" -ForegroundColor Green
Write-Host "Running Python interpreter self-test..." -ForegroundColor Yellow
$testProc = Start-Process -FilePath $pythonw -ArgumentList "-c `"import sys; print(sys.executable)`"" -PassThru -Wait -NoNewWindow
if ($testProc.ExitCode -ne 0) {
    Write-Error "Python self-test failed with exit code $($testProc.ExitCode) for interpreter '$pythonw'."
    exit 1
}
Write-Host "[OK] Python interpreter self-test passed." -ForegroundColor Green
$mediapipeCheck = & $venvPython -c "import mediapipe; import sys; print('tensorflow' in sys.modules)"
if ($mediapipeCheck -eq "True") {
    Write-Warning "mediapipe imported tensorflow in the project venv; startup may be slower than expected."
} else {
    Write-Host "[OK] mediapipe did not pull in tensorflow." -ForegroundColor Green
}
if (-not (Test-Path $pythonw)) {
    Write-Error "Validation failed: Python path does not exist on disk: '$pythonw'"
    exit 1
}
if ($pythonw -like "*WindowsApps*") {
    Write-Error "Validation failed: Refusing to write WindowsApps alias path to HKLM: '$pythonw'"
    exit 1
}
try {
    $configPath = "HKLM:\SOFTWARE\FaceUnlock"
    New-Item -Path $configPath -Force -ErrorAction SilentlyContinue | Out-Null
    Set-ItemProperty -Path $configPath -Name "InstallDir" -Value $ProjectDir -ErrorAction Stop
    Set-ItemProperty -Path $configPath -Name "PythonPath" -Value $pythonw -ErrorAction Stop
    Set-ItemProperty -Path $configPath -Name "ScriptPath" -Value $scriptPath -ErrorAction Stop
    Write-Host "[OK] Updated HKLM:\SOFTWARE\FaceUnlock (PythonPath: $pythonw)" -ForegroundColor Green
} catch {
    Write-Error "Failed to update HKLM configuration: $_"
    exit 1
}
Write-Host "Starting '$TaskName' now..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 1
$state = (Get-ScheduledTask -TaskName $TaskName).State
Write-Host "Current Task Status: $state" -ForegroundColor Green
Write-Host ""
Write-Host "Management Commands:" -ForegroundColor Yellow
Write-Host "  Check Status: (Get-ScheduledTask -TaskName '$TaskName').State"
Write-Host "  Start Task:   Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  Stop Task:    Stop-ScheduledTask -TaskName '$TaskName'"
Write-Host "  View Logs:    Get-Content '$ProjectDir\data\face_helper.log' -Tail 20"
Write-Host "  Remove Task:  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host "==========================================================" -ForegroundColor Cyan
