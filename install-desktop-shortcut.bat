@echo off
REM Install RedmondHR Desktop (+ Start Menu) shortcut on Windows.
REM Prefers OneDrive / known-folder Desktop when present.
REM
REM Safe on WSL UNC (\\wsl.localhost\...): do NOT "cd" into the project —
REM CMD rejects UNC as current directory. %~dp0 still expands correctly;
REM PowerShell -File accepts the UNC path to the .ps1.
REM The .ps1 auto-detects WSL UNC and writes a wsl.exe .lnk (WorkingDirectory
REM = %USERPROFILE%, never UNC).
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "PS1=%SCRIPT_DIR%\install-desktop-shortcut.ps1"

if not exist "%PS1%" (
  echo ERROR: install-desktop-shortcut.ps1 not found next to this script.
  echo Expected: %PS1%
  pause
  exit /b 1
)

REM --- Explicit WSL override: --wsl <Distro> <LinuxPath> [--no-start-menu] ---
if /I "%~1"=="--wsl" goto :wsl_flags
if /I "%~1"=="/wsl" goto :wsl_flags
goto :normal_flags

:wsl_flags
if "%~2"=="" goto :wsl_usage
if "%~3"=="" goto :wsl_usage
set "NSM="
if /I "%~4"=="--no-start-menu" set "NSM=-NoStartMenu"
if /I "%~4"=="/no-start-menu" set "NSM=-NoStartMenu"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -ProjectRoot "%SCRIPT_DIR%" -WslDistro "%~2" -WslLinuxPath "%~3" %NSM%
goto :after_ps

:wsl_usage
echo Usage: install-desktop-shortcut.bat --wsl ^<Distro^> ^<LinuxPath^> [--no-start-menu]
echo Example: install-desktop-shortcut.bat --wsl Ubuntu /home/adamredmond/workspace/redmondhr
pause
exit /b 1

:normal_flags
set "EXTRA="
if /I "%~1"=="--no-start-menu" set "EXTRA=-NoStartMenu"
if /I "%~1"=="/no-start-menu" set "EXTRA=-NoStartMenu"
if /I "%~1"=="--force-wsl" set "EXTRA=%EXTRA% -ForceWsl"
if /I "%~1"=="/force-wsl" set "EXTRA=%EXTRA% -ForceWsl"
if /I "%~1"=="--force-windows" set "EXTRA=%EXTRA% -ForceWindows"
if /I "%~1"=="/force-windows" set "EXTRA=%EXTRA% -ForceWindows"

REM Do not cd /d "%SCRIPT_DIR%" — fails on UNC and is unnecessary.
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" -ProjectRoot "%SCRIPT_DIR%" %EXTRA%

:after_ps
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
  echo.
  echo Shortcut install failed.
  echo.
  echo Quick fix from PowerShell ^(Adam WSL Ubuntu path^):
  echo   See README / APPLY-wsl-shortcut.md one-liner, or:
  echo   Target: wsl.exe
  echo   Args:   -d Ubuntu --cd /home/adamredmond/workspace/redmondhr -- bash ./start-redmondhr.sh
  echo   WorkDir: %%USERPROFILE%%  ^(NOT the UNC project path^)
  echo.
  pause
  exit /b %RC%
)

echo.
echo Done.
exit /b 0
