@echo off
REM RedmondHR offline launcher (Windows)
REM Starts uvicorn in the background and opens the default browser.
REM Designed for double-click / Desktop .lnk (preferably WindowStyle=Minimized).
setlocal EnableExtensions

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not defined REDMONDHR_HOST set "REDMONDHR_HOST=127.0.0.1"
if not defined REDMONDHR_PORT set "REDMONDHR_PORT=8000"
set "URL=http://%REDMONDHR_HOST%:%REDMONDHR_PORT%"

if not defined REDMONDHR_DATA_DIR set "REDMONDHR_DATA_DIR=%ROOT%data"
if not defined REDMONDHR_LOG set "REDMONDHR_LOG=%REDMONDHR_DATA_DIR%\redmondhr.log"
if not defined REDMONDHR_PID set "REDMONDHR_PID=%REDMONDHR_DATA_DIR%\redmondhr.pid"

if not exist "%REDMONDHR_DATA_DIR%" mkdir "%REDMONDHR_DATA_DIR%"

set "PYTHON=%ROOT%.venv\Scripts\python.exe"
set "PYTHONW=%ROOT%.venv\Scripts\pythonw.exe"

if not exist "%PYTHON%" (
  echo RedmondHR: virtual environment not found at:
  echo   %ROOT%.venv
  echo.
  echo One-time setup ^(needs internet once^):
  echo   cd /d "%ROOT%"
  echo   python -m venv .venv
  echo   .venv\Scripts\activate
  echo   pip install -r requirements.txt
  echo.
  echo Then run start-redmondhr.bat again ^(no internet required after that^).
  pause
  exit /b 1
)

REM Prefer pythonw so the server itself has no console window
if exist "%PYTHONW%" (
  set "PY=%PYTHONW%"
) else (
  set "PY=%PYTHON%"
)

REM If pid file exists and process is alive, just open browser
if exist "%REDMONDHR_PID%" (
  set /p OLD_PID=<"%REDMONDHR_PID%"
  call :pid_alive %OLD_PID%
  if not errorlevel 1 (
    start "" "%URL%"
    exit /b 0
  )
  del /f /q "%REDMONDHR_PID%" >nul 2>&1
)

REM Rough port check via PowerShell (optional; ignore failures)
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient('%REDMONDHR_HOST%', %REDMONDHR_PORT%); $c.Close(); exit 0 } catch { exit 1 }" >nul 2>&1
if not errorlevel 1 (
  start "" "%URL%"
  exit /b 0
)

echo ===== %DATE% %TIME% starting RedmondHR =====>> "%REDMONDHR_LOG%"
echo ROOT=%ROOT% HOST=%REDMONDHR_HOST% PORT=%REDMONDHR_PORT%>> "%REDMONDHR_LOG%"

set "PYTHONUNBUFFERED=1"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"

REM Detach via cmd /c so stdout/stderr redirect into the log reliably.
REM /MIN keeps any brief console out of the way when launched from Explorer.
start "RedmondHR" /MIN /B cmd /c ""%PY%" -m uvicorn app.main:app --host %REDMONDHR_HOST% --port %REDMONDHR_PORT% >> "%REDMONDHR_LOG%" 2>&1"

REM Brief wait, then capture listening pid (best-effort)
timeout /t 1 /nobreak >nul
powershell -NoProfile -Command ^
  "$p = Get-NetTCPConnection -LocalPort %REDMONDHR_PORT% -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty OwningProcess; if ($p) { Set-Content -Path '%REDMONDHR_PID%' -Value $p -NoNewline; exit 0 } else { exit 1 }" >nul 2>&1

start "" "%URL%"
exit /b 0

:pid_alive
REM Returns errorlevel 0 if pid is alive
tasklist /FI "PID eq %~1" 2>nul | findstr /I /C:"%~1" >nul
exit /b %ERRORLEVEL%
