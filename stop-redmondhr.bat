@echo off
REM Stop RedmondHR started by start-redmondhr.bat (uses pid file).
setlocal EnableExtensions

set "ROOT=%~dp0"
if not defined REDMONDHR_DATA_DIR set "REDMONDHR_DATA_DIR=%ROOT%data"
if not defined REDMONDHR_PID set "REDMONDHR_PID=%REDMONDHR_DATA_DIR%\redmondhr.pid"
if not defined REDMONDHR_PORT set "REDMONDHR_PORT=8000"

if not exist "%REDMONDHR_PID%" (
  echo No pid file at %REDMONDHR_PID% — RedmondHR may not be running via the launcher.
  echo If something is still listening on port %REDMONDHR_PORT%, stop it in Task Manager
  echo or: netstat -ano ^| findstr :%REDMONDHR_PORT%
  exit /b 0
)

set /p PID=<"%REDMONDHR_PID%"
if "%PID%"=="" (
  del /f /q "%REDMONDHR_PID%" >nul 2>&1
  echo Empty pid file removed.
  exit /b 0
)

tasklist /FI "PID eq %PID%" 2>nul | findstr /I /C:"%PID%" >nul
if errorlevel 1 (
  del /f /q "%REDMONDHR_PID%" >nul 2>&1
  echo Process %PID% not running; cleaned up pid file.
  exit /b 0
)

echo Stopping RedmondHR ^(pid %PID%^)...
taskkill /PID %PID% /T >nul 2>&1
timeout /t 1 /nobreak >nul
tasklist /FI "PID eq %PID%" 2>nul | findstr /I /C:"%PID%" >nul
if not errorlevel 1 (
  echo Still running; forcing...
  taskkill /F /PID %PID% /T >nul 2>&1
)

del /f /q "%REDMONDHR_PID%" >nul 2>&1
echo RedmondHR stopped.
