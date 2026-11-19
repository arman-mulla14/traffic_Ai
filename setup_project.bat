@echo off
title AI Traffic Management System - Complete Auto Setup
color 0A

echo =====================================================================
echo    AI-BASED TRAFFIC MANAGEMENT SYSTEM - AUTOMATED ENVIRONMENT SETUP
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/6] Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH! Please install Python 3.10-3.13.
    pause
    exit /b 1
)
python --version

echo.
echo [2/6] Setting up Python Virtual Environment (venv)...
if not exist "venv" (
    echo Creating new virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo.
echo [3/6] Upgrading pip and installing required dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo [4/6] Creating runtime directories...
if not exist "storage\uploads" mkdir "storage\uploads"
if not exist "storage\processed" mkdir "storage\processed"
if not exist "storage\reports" mkdir "storage\reports"
if not exist "storage\evidence" mkdir "storage\evidence"
if not exist "models" mkdir "models"

echo.
echo [5/6] Initializing and verifying SQLite database...
python -c "import sys; sys.path.insert(0, 'backend'); from app.database.init_db import init_db; init_db(); print('Database tables and seed data initialized successfully!')"

echo.
echo [6/6] Verifying automated test suite...
pytest tests/ -v -k "not test_db_admin" --tb=short

echo.
echo =====================================================================
echo    SETUP COMPLETE! STARTING APPLICATION SERVER ON PORT 8000...
echo    Access Dashboard: http://localhost:8000
echo =====================================================================
echo.

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
pause
