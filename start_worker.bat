@echo off
REM Dumont Startup Script - Windows
REM Handles Windows-specific setup and starts the worker agent
REM
REM Usage:
REM   start_worker.bat [options]
REM   
REM Options:
REM   --host URL     Orchestrator URL (default: http://localhost:5000)
REM   --redis-host HOST          Redis host (default: localhost)
REM   --redis-port PORT          Redis port (default: 6379)
REM   --debug                    Enable debug logging
REM   --no-venv                  Don't activate virtual environment
REM   --help                     Show this help message

setlocal enabledelayedexpansion

REM Configuration
set ORCHESTRATOR_URL=http://localhost:5000
set REDIS_HOST=localhost
set REDIS_PORT=6379
set DEBUG_MODE=0
set USE_VENV=1
set DEBUG_FLAG=

REM Parse arguments
:parse_args
if "%1"=="" goto args_done
if "%1"=="--host" (
    set ORCHESTRATOR_URL=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--redis-host" (
    set REDIS_HOST=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--redis-port" (
    set REDIS_PORT=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--debug" (
    set DEBUG_MODE=1
    set DEBUG_FLAG=--debug
    shift
    goto parse_args
)
if "%1"=="--no-venv" (
    set USE_VENV=0
    shift
    goto parse_args
)
if "%1"=="--help" (
    goto show_help
)
shift
goto parse_args

:args_done

REM Print header
cls
echo.
echo ====================================================================
echo                     Dumont Agent
echo ====================================================================
echo.

REM Step 1: Check Python
echo [1/6] Checking Python Environment
python --version >nul 2>&1
if errorlevel 1 (
    echo   [X] Python 3 not found
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   [V] Python %PYTHON_VERSION%

REM Step 2: Activate virtual environment (if needed)
echo.
echo [2/6] Setting Up Virtual Environment
if %USE_VENV% equ 1 (
    if exist ".env_worker\Scripts\activate.bat" (
        call .env_worker\Scripts\activate.bat
        echo   [V] Virtual environment activated
    ) else if exist ".env\Scripts\activate.bat" (
        call .env\Scripts\activate.bat
        echo   [V] Virtual environment activated
    ) else (
        echo   [!] Virtual environment not found
        echo   [i] Create one with: python -m venv .env_worker
    )
) else (
    echo   [i] Virtual environment not activated (--no-venv flag)
)

REM Step 3: Verify dependencies
echo.
echo [3/6] Verifying Dependencies
set MISSING_DEPS=0

python -c "import psutil" >nul 2>&1
if errorlevel 1 (
    echo   [X] psutil (missing: pip install psutil)
    set MISSING_DEPS=1
) else (
    echo   [V] psutil
)

python -c "import numpy" >nul 2>&1
if errorlevel 1 (
    echo   [X] numpy (missing: pip install numpy)
    set MISSING_DEPS=1
) else (
    echo   [V] numpy
)

python -c "import pandas" >nul 2>&1
if errorlevel 1 (
    echo   [X] pandas (missing: pip install pandas)
    set MISSING_DEPS=1
) else (
    echo   [V] pandas
)

python -c "import onnxruntime" >nul 2>&1
if errorlevel 1 (
    echo   [X] onnxruntime (missing: pip install onnxruntime)
    set MISSING_DEPS=1
) else (
    echo   [V] onnxruntime
)

python -c "import redis" >nul 2>&1
if errorlevel 1 (
    echo   [X] redis (missing: pip install redis)
    set MISSING_DEPS=1
) else (
    echo   [V] redis
)

python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo   [X] flask (missing: pip install flask)
    set MISSING_DEPS=1
) else (
    echo   [V] flask
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo   [X] requests (missing: pip install requests)
    set MISSING_DEPS=1
) else (
    echo   [V] requests
)

if %MISSING_DEPS% equ 1 (
    echo.
    echo   Missing dependencies. Install with: pip install -r requirements.txt
    exit /b 1
)

REM Step 4: Detect platform
echo.
echo [4/6] Detecting Platform
python -c "import coremltools" >nul 2>&1
if errorlevel 1 (
    echo   [V] Platform: Windows
) else (
    echo   [i] CoreML detected (unusual on Windows)
)

REM Step 5: Test connectivity
echo.
echo [5/6] Testing Connectivity
echo   Testing orchestrator: %ORCHESTRATOR_URL%

python << 'PYEOF' >nul 2>&1
import requests
import sys
import os
try:
    response = requests.get(os.environ.get('ORCHESTRATOR_URL', 'http://localhost:5000') + '/api/health', timeout=2)
    if response.status_code == 200:
        sys.exit(0)
    else:
        sys.exit(1)
except:
    sys.exit(1)
PYEOF

if errorlevel 1 (
    echo   [!] Orchestrator not reachable (will retry at startup)
) else (
    echo   [V] Orchestrator reachable
)

REM Step 6: Start worker
echo.
echo [6/6] Starting Worker Agent
echo.
echo   Configuration:
echo     Orchestrator: %ORCHESTRATOR_URL%
echo     Redis Host: %REDIS_HOST%:%REDIS_PORT%

if %DEBUG_MODE% equ 1 (
    echo     Debug: Enabled
)

echo.
echo Starting worker...
echo.

REM Start the worker
python worker/worker_agent.py ^
    --host %ORCHESTRATOR_URL% ^
    --redis-host %REDIS_HOST% ^
    --redis-port %REDIS_PORT% ^
    %DEBUG_FLAG%

echo.
echo Worker stopped
exit /b 0

:show_help
echo Dumont Startup Script - Windows
echo.
echo Usage: %0 [options]
echo.
echo Options:
echo   --host URL     Orchestrator URL (default: http://localhost:5000)
echo   --redis-host HOST          Redis host (default: localhost)
echo   --redis-port PORT          Redis port (default: 6379)
echo   --debug                    Enable debug logging
echo   --no-venv                  Don't activate virtual environment
echo   --help                     Show this help message
echo.
echo Examples:
echo   start_worker.bat
echo   start_worker.bat --host http://192.168.1.100:5000
echo   start_worker.bat --debug --redis-host 192.168.1.100
echo.
exit /b 0

