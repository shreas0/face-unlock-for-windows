@echo off
setlocal enabledelayedexpansion
echo =========================================================
echo  Building FaceUnlockProvider.dll (x64)
echo =========================================================
set VSWHERE="%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist %VSWHERE% (
    echo [ERROR] Visual Studio installer / vswhere not found.
    echo Please install Visual Studio 2022 Community with "Desktop development with C++".
    pause
    exit /b 1
)
for /f "usebackq tokens=*" %%i in (`%VSWHERE% -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath`) do (
    set VS_DIR=%%i
)
if "%VS_DIR%"=="" (
    echo [ERROR] No Visual Studio C++ toolchain found.
    pause
    exit /b 1
)
echo Found Visual Studio at: %VS_DIR%
call "%VS_DIR%\VC\Auxiliary\Build\vcvars64.bat"
echo Compiling FaceUnlockProvider.dll...
cl.exe /nologo /W3 /O2 /EHsc /std:c++17 /D_USRDLL /D_WINDLL /I. FaceUnlockProvider.cpp FaceCredential.cpp helpers.cpp /link /DLL /DEF:FaceUnlockProvider.def /OUT:FaceUnlockProvider.dll Advapi32.lib Secur32.lib Crypt32.lib Credui.lib Shlwapi.lib Ole32.lib OleAut32.lib
if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] FaceUnlockProvider.dll built successfully!
    copy /Y FaceUnlockProvider.dll ..\FaceUnlockProvider.dll
) else (
    echo.
    echo [FAILED] Compilation failed with error %ERRORLEVEL%.
)
endlocal
