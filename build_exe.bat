@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

set "PYTHON_CMD=python"
if defined PYTHON_EXE set "PYTHON_CMD=%PYTHON_EXE%"

%PYTHON_CMD% -c "import sys; print(sys.executable)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python interpreter not found.
    echo [HINT]  set PYTHON_EXE=full\path\to\python.exe
    pause
    exit /b 1
)

for /f "usebackq delims=" %%I in (`%PYTHON_CMD% -c "import os,sys; print(os.path.dirname(sys.executable))"`) do set "PY_ENV_DIR=%%I"
if defined PY_ENV_DIR (
    set "PATH=%PY_ENV_DIR%;%PY_ENV_DIR%\Scripts;%PY_ENV_DIR%\Library\bin;%PY_ENV_DIR%\Library\usr\bin;%PY_ENV_DIR%\Library\mingw-w64\bin;%PATH%"
)

%PYTHON_CMD% -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed in current Python environment.
    echo [HINT]  %PYTHON_CMD% -m pip install pyinstaller
    pause
    exit /b 1
)

set "ICON_ARGS="
set "DATA_ARGS="
if exist "tray_icon.ico" (
    set "ICON_ARGS=--icon tray_icon.ico"
    set "DATA_ARGS=--add-data tray_icon.ico;."
)

set "MODE=--onedir"
if /I "%~1"=="--onefile" set "MODE=--onefile"

%PYTHON_CMD% -m PyInstaller --noconfirm --clean --windowed %MODE% --name DesktopReminder %ICON_ARGS% %DATA_ARGS% desktop_reminder.py
if errorlevel 1 (
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

echo [OK] Build succeeded.
if /I "%MODE%"=="--onefile" (
    echo [OUT] %SCRIPT_DIR%dist\DesktopReminder.exe
) else (
    echo [OUT] %SCRIPT_DIR%dist\DesktopReminder\DesktopReminder.exe
    echo [NOTE] onedir mode avoids the extra bootstrap process of onefile.
)
exit /b 0
