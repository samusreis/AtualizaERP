@echo off
setlocal
cd /d "%~dp0"

py -3.10-64 --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.10 64-bit is required. Install it and run this script again.
    exit /b 1
)

if not exist ".venv-pyside2\Scripts\python.exe" (
    py -3.10-64 -m venv .venv-pyside2
    if errorlevel 1 goto :error
)

".venv-pyside2\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

".venv-pyside2\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

".venv-pyside2\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name AssistenteReleaseGuardian src\main.py
if errorlevel 1 goto :error

echo.
echo Executable created at dist\AssistenteReleaseGuardian.exe
goto :end

:error
echo.
echo Build failed. Review the error output above.
exit /b 1

:end
pause
