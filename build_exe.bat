@echo off
setlocal
cd /d "%~dp0"

set "BUILD_ROOT=%~dp0"
set "POWERSHELL=%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe"
set "PYTHON_INSTALLER=%TEMP%\python-3.10.11-amd64.exe"
set "PYTHON_INSTALL_DIR=%LOCALAPPDATA%\Programs\Python\Python310"
set "VENV_DIR=.venv-pyside2"
set "PYTHON="

if not exist "%POWERSHELL%" (
    echo Windows PowerShell was not found at "%POWERSHELL%".
    echo Install or repair Windows PowerShell before running this build.
    goto :error
)

call :download_missing_project_files
if errorlevel 1 goto :error

if exist "%PYTHON_INSTALL_DIR%\python.exe" (
    set "PYTHON=%PYTHON_INSTALL_DIR%\python.exe"
    call :check_python
    if not errorlevel 1 goto :python_found
    set "PYTHON="
)

for /f "delims=" %%P in ('py -3.10 -c "import sys; print(sys.executable)" 2^>nul') do set "PYTHON=%%P"
call :check_python
if not errorlevel 1 goto :python_found
set "PYTHON="

echo Python 3.10 64-bit was not found. Downloading the official installer...
"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe' -OutFile $env:PYTHON_INSTALLER } catch { Write-Error ('Python download failed: ' + $_); exit 1 }"
if errorlevel 1 goto :error

"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 TargetDir="%PYTHON_INSTALL_DIR%" PrependPath=0 Include_pip=1 Include_test=0
if errorlevel 1 (
    echo Python installation failed.
    goto :error
)
del /q "%PYTHON_INSTALLER%" >nul 2>nul
set "PYTHON=%PYTHON_INSTALL_DIR%\python.exe"
call :check_python
if errorlevel 1 (
    echo Python 3.10 64-bit could not be verified after installation.
    goto :error
)

:python_found
"%PYTHON%" --version
if errorlevel 1 goto :error

if exist ".venv-pyside2\Scripts\python.exe" (
    ".venv-pyside2\Scripts\python.exe" -c "import sys, struct; sys.exit(0 if sys.version_info[:2] == (3, 10) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
    if errorlevel 1 set "VENV_DIR=.venv-pyside2-310"
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
    "%PYTHON%" -m venv "%VENV_DIR%"
    if errorlevel 1 goto :error
)

"%VENV_DIR%\Scripts\python.exe" -c "import sys, struct; sys.exit(0 if sys.version_info[:2] == (3, 10) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
if errorlevel 1 (
    echo The existing virtual environment is not Python 3.10 64-bit.
    goto :error
)

"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error

"%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

"%VENV_DIR%\Scripts\python.exe" -m PyInstaller --noconfirm --clean --onefile --windowed --name AssistenteReleaseGuardian src\main.py
if errorlevel 1 goto :error

echo.
echo Executable created at dist\AssistenteReleaseGuardian.exe
goto :end

:check_python
if not exist "%PYTHON%" exit /b 1
"%PYTHON%" -c "import sys, struct; sys.exit(0 if sys.version_info[:2] == (3, 10) and struct.calcsize('P') == 8 else 1)" >nul 2>nul
exit /b %errorlevel%

:download_missing_project_files
"%POWERSHELL%" -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference = 'Stop'; [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $files = @('requirements.txt', 'src/main.py', 'src/automation.py', 'src/highlighter.py', 'src/ui_constants.py'); $missing = @($files | Where-Object { -not (Test-Path -LiteralPath (Join-Path $env:BUILD_ROOT $_)) }); if ($missing.Count -eq 0) { exit 0 }; try { $repo = Invoke-RestMethod -Headers @{ 'User-Agent' = 'AtualizaERP-build' } -Uri 'https://api.github.com/repos/samusreis/AtualizaERP'; $branch = $repo.default_branch; foreach ($relative in $missing) { $destination = Join-Path $env:BUILD_ROOT $relative; $parent = Split-Path -Parent $destination; if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }; $temporary = $destination + '.download'; try { $uri = 'https://raw.githubusercontent.com/samusreis/AtualizaERP/' + $branch + '/' + $relative; Invoke-WebRequest -UseBasicParsing -Headers @{ 'User-Agent' = 'AtualizaERP-build' } -Uri $uri -OutFile $temporary; if ((Get-Item -LiteralPath $temporary).Length -eq 0) { throw ('Downloaded file is empty: ' + $relative) }; Move-Item -LiteralPath $temporary -Destination $destination; Write-Host ('Downloaded missing file: ' + $relative) } catch { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue; throw } } } catch { Write-Error ('Could not download missing project files from the configured GitHub repository: ' + $_); exit 1 }"
exit /b %errorlevel%

:error
echo.
echo Build failed. Review the error output above.
exit /b 1

:end
pause
