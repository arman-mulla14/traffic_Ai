@echo off
setlocal enabledelayedexpansion

title AI-Based Traffic Management System
cd /d "%~dp0"

set "HOST=127.0.0.1"
set "PORT=8000"
set "AUTO_OPEN_BROWSER=1"

:: -------------------------------------------------------------
:: Argument Parsing
:: -------------------------------------------------------------
:parse_args
if "%~1"=="" goto after_args
if /i "%~1"=="--no-browser" (
    set "AUTO_OPEN_BROWSER=0"
    shift
    goto parse_args
)
if /i "%~1"=="-nb" (
    set "AUTO_OPEN_BROWSER=0"
    shift
    goto parse_args
)
if /i "%~1"=="--port" (
    set "PORT=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--host" (
    set "HOST=%~2"
    shift
    shift
    goto parse_args
)
if /i "%~1"=="--help" goto show_help
if /i "%~1"=="-h" goto show_help
shift
goto parse_args

:show_help
echo.
echo AI-Based Traffic Management System - Launcher
echo -------------------------------------------------------------
echo Usage: run.bat [options]
echo.
echo Options:
echo   --port ^<port^>       Specify custom port (default: 8000)
echo   --host ^<host^>       Specify custom host (default: 127.0.0.1)
echo   --no-browser, -nb   Do not automatically launch web browser
echo   --help, -h          Display this help message
echo.
exit /b 0

:after_args
echo ======================================================================
echo       AI-BASED TRAFFIC MANAGEMENT SYSTEM (ENTERPRISE EDITION)
echo ======================================================================
echo.

:: -------------------------------------------------------------
:: 1. Virtual Environment Detection
:: -------------------------------------------------------------
if exist "%~dp0venv\Scripts\activate.bat" (
    echo [*] Detected virtual environment in 'venv\'. Activating...
    call "%~dp0venv\Scripts\activate.bat"
    goto :venv_done
)
if exist "%~dp0.venv\Scripts\activate.bat" (
    echo [*] Detected virtual environment in '.venv\'. Activating...
    call "%~dp0.venv\Scripts\activate.bat"
    goto :venv_done
)
:venv_done

:: -------------------------------------------------------------
:: 2. Python Detection
:: -------------------------------------------------------------
set "PYTHON_CMD="
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
    goto :python_detected
)
py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
    goto :python_detected
)

echo.
echo [ERROR] Python was not found in your system PATH!
echo.
echo Please install Python 3.11, 3.12, or 3.13 from https://www.python.org/
echo Make sure to check the option "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:python_detected
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%i"
echo [*] Using: !PY_VER!

:: -------------------------------------------------------------
:: 3. Core Dependencies Verification
:: -------------------------------------------------------------
%PYTHON_CMD% -c "import fastapi, uvicorn, ultralytics, torch" >nul 2>&1
if %ERRORLEVEL% EQU 0 goto :deps_ok

echo.
echo [!] Required Python dependencies not detected.
echo [*] Installing dependencies from backend\requirements.txt...
echo.
%PYTHON_CMD% -m pip install -r "%~dp0backend\requirements.txt"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install dependencies. Please run manually:
    echo         pip install -r backend\requirements.txt
    echo.
    pause
    exit /b 1
)

:deps_ok
echo [*] Core dependencies verified (FastAPI, Uvicorn, YOLOv8, PyTorch).

:: -------------------------------------------------------------
:: 4. Storage Directory Setup
:: -------------------------------------------------------------
if not exist "%~dp0storage" mkdir "%~dp0storage"
if not exist "%~dp0storage\uploads" mkdir "%~dp0storage\uploads"
if not exist "%~dp0storage\processed" mkdir "%~dp0storage\processed"
if not exist "%~dp0storage\reports" mkdir "%~dp0storage\reports"

:: -------------------------------------------------------------
:: 5. Database Initialization
:: -------------------------------------------------------------
set "PYTHONPATH=%~dp0backend;%PYTHONPATH%"
echo [*] Initializing SQLite database and table schema...
%PYTHON_CMD% -c "import sys; sys.path.insert(0, 'backend'); from app.database.init_db import init_db; init_db()"
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Database initialization reported an issue. Continuing...
)

:: -------------------------------------------------------------
:: 6. Launch Browser (in background after short delay)
:: -------------------------------------------------------------
if "%AUTO_OPEN_BROWSER%"=="1" (
    echo [*] Web browser will open automatically once the server is ready.
    start "" cmd /c "timeout /t 3 /nobreak >nul 2>&1 & start http://%HOST%:%PORT%/"
)

:: -------------------------------------------------------------
:: 7. Start FastAPI / Uvicorn Server
:: -------------------------------------------------------------
echo.
echo ======================================================================
echo  Server running at:    http://%HOST%:%PORT%/
echo  Database Admin (DAP): http://%HOST%:%PORT%/dap
echo  API Documentation:    http://%HOST%:%PORT%/docs
echo.
echo  Press Ctrl+C in this window to stop the server at any time.
echo ======================================================================
echo.

%PYTHON_CMD% -m uvicorn app.main:app --host %HOST% --port %PORT% --reload --app-dir backend

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] Server stopped with error code %ERRORLEVEL%.
    pause
)

echo.
echo [*] Traffic Management System has been stopped.
