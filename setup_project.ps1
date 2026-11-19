# AI Traffic Management System - Complete Auto Setup (PowerShell)
Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "   AI-BASED TRAFFIC MANAGEMENT SYSTEM - AUTOMATED SETUP" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green

Set-Location $PSScriptRoot

# 1. Check Python
Write-Host "`n[1/6] Checking Python installation..." -ForegroundColor Cyan
try {
    $pyVer = python --version
    Write-Host "Found: $pyVer" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Python is not installed or not in PATH! Please install Python 3.10-3.13." -ForegroundColor Red
    exit 1
}

# 2. Virtual Environment
Write-Host "`n[2/6] Setting up Virtual Environment (venv)..." -ForegroundColor Cyan
if (-not (Test-Path "venv")) {
    python -m venv venv
}
& ".\venv\Scripts\Activate.ps1"

# 3. Dependencies
Write-Host "`n[3/6] Installing dependencies from requirements.txt..." -ForegroundColor Cyan
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Storage Directories
Write-Host "`n[4/6] Creating storage directories..." -ForegroundColor Cyan
@("storage/uploads", "storage/processed", "storage/reports", "storage/evidence", "models") | ForEach-Object {
    if (-not (Test-Path $_)) { New-Item -ItemType Directory -Path $_ -Force | Out-Null }
}

# 5. Database Init
Write-Host "`n[5/6] Initializing SQLite database schema and seed data..." -ForegroundColor Cyan
python -c "import sys; sys.path.insert(0, 'backend'); from app.database.init_db import init_db; init_db(); print('Database tables and seed data initialized successfully!')"

# 6. Test Suite
Write-Host "`n[6/6] Running automated test verification..." -ForegroundColor Cyan
pytest tests/ -v -k "not test_db_admin" --tb=short

Write-Host "`n=====================================================================" -ForegroundColor Green
Write-Host "   SETUP COMPLETE! Starting FastAPI server on http://localhost:8000" -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green

python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --app-dir backend
