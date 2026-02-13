@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

if not exist "desktop_reminder.py" (
    echo [ERROR] desktop_reminder.py not found in: "%SCRIPT_DIR%"
    pause
    exit /b 1
)

if not exist "logs" mkdir "logs"

for /f %%i in ('powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd_HHmmss')"') do set "TS=%%i"
set "LOG_FILE=%SCRIPT_DIR%logs\desktop_reminder_%TS%.log"
set "PID_FILE=%SCRIPT_DIR%desktop_reminder.pid"

set "PY_EXE="
set "PY_PREFIX_ARGS="
where pythonw >nul 2>&1
if not errorlevel 1 set "PY_EXE=pythonw"

if not defined PY_EXE (
    python -V >nul 2>&1
    if not errorlevel 1 set "PY_EXE=python"
)

if not defined PY_EXE (
    where pyw >nul 2>&1
    if not errorlevel 1 (
        set "PY_EXE=pyw"
        set "PY_PREFIX_ARGS=-3"
    )
)

if not defined PY_EXE (
    where py >nul 2>&1
    if not errorlevel 1 (
        set "PY_EXE=py"
        set "PY_PREFIX_ARGS=-3"
    )
)

if not defined PY_EXE (
    echo [ERROR] Python not found. Install Python 3 and add it to PATH.
    pause
    exit /b 1
)

set "USER_ARGS=%*"
set "APP_ARGS=%PY_PREFIX_ARGS% ""%SCRIPT_DIR%desktop_reminder.py"" --log-file ""%LOG_FILE%"" --pid-file ""%PID_FILE%"" %USER_ARGS%"

powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ^
  "$exe = $env:PY_EXE;" ^
  "$args = $env:APP_ARGS;" ^
  "$wd = $env:SCRIPT_DIR;" ^
  "$p = Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $wd -PassThru;" ^
  "Start-Sleep -Milliseconds 600;" ^
  "if ($p.HasExited) { exit $p.ExitCode } else { exit 0 }"

if %errorlevel%==2 (
    echo [INFO] Reminder is already running.
    exit /b 0
)

if errorlevel 1 (
    echo [ERROR] Failed to start reminder process.
    pause
    exit /b 1
)

echo [OK] Reminder started in background.
echo [LOG] %LOG_FILE%
exit /b 0
