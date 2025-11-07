@echo off
REM Dumont - Installation Script for Windows
REM This script sets up a clean Python environment and installs the worker

setlocal enabledelayedexpansion

echo ╔════════════════════════════════════════════════════════════════╗
echo  ║           Dumont - Installation Script                       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

set VENV_NAME=.venv_worker

REM Step 1: Check Python
echo ▶ Checking Python Installation
echo ──────────────────────────────────────────────────────────────────

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Python not found
    echo   Please install Python 3.8 or higher from https://www.python.org/downloads/
    echo   Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION% found

REM Step 2: Create virtual environment
echo.
echo ▶ Creating Virtual Environment
echo ──────────────────────────────────────────────────────────────────

if exist "%VENV_NAME%" (
    echo ⚠ Virtual environment already exists
    choice /C YN /M "Remove and recreate"
    if !ERRORLEVEL! EQU 1 (
        rmdir /s /q "%VENV_NAME%"
        echo ✓ Removed old environment
    )
)

if not exist "%VENV_NAME%" (
    python -m venv %VENV_NAME%
    echo ✓ Virtual environment created
)

REM Activate virtual environment
call %VENV_NAME%\Scripts\activate.bat
echo ✓ Virtual environment activated

REM Step 3: Upgrade pip
echo.
echo ▶ Upgrading pip
echo ──────────────────────────────────────────────────────────────────
python -m pip install --quiet --upgrade pip setuptools wheel
echo ✓ pip upgraded

REM Step 4: Install worker package
echo.
echo ▶ Installing Dumont Package
echo ──────────────────────────────────────────────────────────────────
echo ℹ Windows detected - installing with DirectML support
pip install -e ".[windows]"
echo ✓ Worker package installed

REM Step 5: Verify installation
echo.
echo ▶ Verifying Installation
echo ──────────────────────────────────────────────────────────────────

where cyclops-worker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ✗ cyclops-worker command not found
    pause
    exit /b 1
)
echo ✓ cyclops-worker command available

REM Run validation
cyclops-worker validate

REM Step 6: Create activation script
echo.
echo ▶ Creating Activation Helper
echo ──────────────────────────────────────────────────────────────────

(
echo @echo off
echo REM Activate Dumont environment
echo call .venv_worker\Scripts\activate.bat
echo echo ✓ Dumont environment activated
echo echo.
echo echo Available commands:
echo echo   cyclops-worker start --orchestrator-url ^<url^>
echo echo   cyclops-worker enroll --orchestrator-url ^<url^>
echo echo   cyclops-worker info
echo echo   cyclops-worker validate
echo echo.
) > activate_worker.bat

echo ✓ Created activation script: activate_worker.bat

REM Success message
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                 Installation Successful! ✓                     ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Quick Start:
echo.
echo   1. Activate the environment:
echo      activate_worker.bat
echo.
echo   2. Check system info:
echo      cyclops-worker info
echo.
echo   3. Enroll with orchestrator:
echo      cyclops-worker enroll --orchestrator-url http://^<ip^>:5000
echo.
echo   4. Start the worker:
echo      cyclops-worker start --orchestrator-url http://^<ip^>:5000
echo.
echo For help:
echo   cyclops-worker --help
echo.

pause
