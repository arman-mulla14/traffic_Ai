@echo off
setlocal enabledelayedexpansion

title SQLite Database Admin Panel (DAP) - Traffic Management System
cd /d "%~dp0"

set "HOST=127.0.0.1"
set "PORT=8000"
set "DAP_URL=http://%HOST%:%PORT%/dap?t=%RANDOM%"

echo ======================================================================
echo    SQLITE DATABASE ADMIN PANEL (DAP) - MYSQL / SQLITE WEB STUDIO
echo ======================================================================
echo.
echo [*] Project Root: %~dp0
echo [*] Database Target: %~dp0traffic_system.db
echo.

:: 1. Activate Virtual Environment if available
if exist "%~dp0venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment in 'venv\'...
    call "%~dp0venv\Scripts\activate.bat"
) else if exist "%~dp0.venv\Scripts\activate.bat" (
    echo [*] Activating virtual environment in '.venv\'...
    call "%~dp0.venv\Scripts\activate.bat"
)

:: 2. Python Detection
set "PYTHON_CMD="
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=python"
    goto :python_ok
)
py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
    goto :python_ok
)

echo [ERROR] Python not found in system PATH.
pause
exit /b 1

:python_ok
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%i"
echo [*] Python Runtime: !PY_VER!

:: 3. Check if server is already running on port 8000
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [*] Traffic Management server is already active on port %PORT%.
    goto :open_browser
)

:: 4. Start Server if not already active
echo [*] Starting backend server with SQLite Database Admin engine...
start "AI Traffic Server (DAP Backend)" /min %PYTHON_CMD% -m uvicorn app.main:app --host %HOST% --port %PORT% --app-dir backend

:: Wait 3 seconds for server boot
timeout /t 3 /nobreak >nul 2>&1

:open_browser
echo.
echo ======================================================================
echo   DATABASE ADMIN STUDIO IS READY!
echo   Opening: %DAP_URL%
echo ======================================================================
echo.
echo   Tables Available to Browse, Edit, Delete and Query:
echo    - cameras          - videos             - analyses
echo    - traffic_records  - incidents          - predictions
echo    - signal_plans     - reports            - lanes
echo    - zones            - detections         - vehicle_tracks
echo    - traffic_metrics  - alerts
echo.
echo   Press any key to re-open the Database Admin Panel in browser.
echo ======================================================================

:: Launch browser
start "" "%DAP_URL%"

:loop
pause >nul
start "" "%DAP_URL%"
goto :loop

