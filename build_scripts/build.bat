@echo off
REM Build Dumont Binary for Windows

echo ╔════════════════════════════════════════════════════════════════╗
echo   ║        Dumont - Binary Build Script                        ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ✗ Python not found
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo ✓ Python %PYTHON_VERSION%

REM Create build environment
echo.
echo ▶ Setting up build environment...

if not exist ".venv_build" (
    python -m venv .venv_build
    echo   ✓ Created build environment
)

call .venv_build\Scripts\activate.bat
echo   ✓ Activated build environment

REM Install dependencies
echo.
echo ▶ Installing dependencies...
python -m pip install -q --upgrade pip
pip install -q -r requirements-worker.txt
pip install -q -r requirements-build.txt
echo   ✓ Dependencies installed

REM Build binary
echo.
echo ▶ Building binary with PyInstaller...
pyinstaller --clean cyclops-worker.spec

if exist "dist\cyclops-worker.exe" (
    echo   ✓ Binary created successfully
) else (
    echo   ✗ Binary creation failed
    exit /b 1
)

REM Create distribution package
echo.
echo ▶ Creating distribution package...

if not exist "dist_binary" mkdir dist_binary
copy dist\cyclops-worker.exe dist_binary\ >nul
echo   ✓ Binary copied to dist_binary/

REM Get binary size
for %%A in (dist_binary\cyclops-worker.exe) do set SIZE=%%~zA
set /a SIZE_MB=%SIZE% / 1048576
echo   ✓ Binary size: %SIZE_MB% MB

REM Test binary
echo.
echo ▶ Testing binary...
dist_binary\cyclops-worker.exe --help >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ✓ Binary is functional
) else (
    echo   ⚠ Warning: Binary test failed
)

REM Create README for distribution
(
echo Dumont - Standalone Binary
echo ====================================
echo.
echo This is a standalone executable that requires no Python installation.
echo.
echo Quick Start:
echo -----------
echo.
echo 1. Check system info:
echo    cyclops-worker.exe info
echo.
echo 2. Validate requirements:
echo    cyclops-worker.exe validate
echo.
echo 3. Test connectivity:
echo    cyclops-worker.exe test --host http://192.168.1.100:5000
echo.
echo 4. Enroll worker:
echo    cyclops-worker.exe enroll --host http://192.168.1.100:5000
echo.
echo 5. Start worker:
echo    cyclops-worker.exe start --host http://192.168.1.100:5000
echo.
echo For help:
echo    cyclops-worker.exe --help
echo.
echo System Requirements:
echo -------------------
echo - No Python required!
echo - Windows 10 or later
echo - Network access to orchestrator
echo - 100MB disk space
echo.
echo Distribution:
echo ------------
echo Just copy the 'cyclops-worker.exe' file to any Windows machine and run it.
echo No installation needed!
) > dist_binary\README.txt

echo   ✓ Created distribution README

REM Create deployment package
echo.
echo ▶ Creating deployment archive...

set ARCHIVE_NAME=cyclops-worker-windows.zip

cd dist_binary
tar -czf ..\%ARCHIVE_NAME% cyclops-worker.exe README.txt 2>nul
if %ERRORLEVEL% NEQ 0 (
    REM Fallback to PowerShell if tar not available
    powershell Compress-Archive -Force -Path cyclops-worker.exe,README.txt -DestinationPath ..\%ARCHIVE_NAME%
)
cd ..

echo   ✓ Created %ARCHIVE_NAME%

REM Summary
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    Build Successful! ✓                         ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo Binary:   dist_binary\cyclops-worker.exe ^(%SIZE_MB% MB^)
echo Archive:  %ARCHIVE_NAME%
echo.
echo To test locally:
echo   dist_binary\cyclops-worker.exe info
echo.
echo To distribute:
echo   Just copy 'cyclops-worker.exe' to target machines - no Python needed!
echo.
echo To run on remote machine:
echo   Copy cyclops-worker.exe and run:
echo   cyclops-worker.exe start --host http://IP:5000
echo.

pause
