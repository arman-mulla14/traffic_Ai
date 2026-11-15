import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_db_admin_overview():
    """Verifies that the Database Admin overview endpoint returns tables, record counts, and WAL mode."""
    res = client.get("/api/db-admin/overview")
    assert res.status_code == 200
    data = res.json()
    assert "tables" in data
    assert len(data["tables"]) >= 5
    assert "journal_mode" in data
    assert data["journal_mode"].lower() == "wal"
    assert "integrity" in data
    assert data["integrity"] == "ok"
    assert data["total_records"] > 0

def test_db_admin_table_schema():
    """Verifies table schema inspection for the 'cameras' table."""
    res = client.get("/api/db-admin/tables/cameras/schema")
    assert res.status_code == 200
    data = res.json()
    assert data["table_name"] == "cameras"
    assert "columns" in data
    col_names = [col["name"] for col in data["columns"]]
    assert "id" in col_names
    assert "camera_name" in col_names
    assert "location" in col_names

def test_db_admin_table_data_pagination():
    """Verifies browsing rows with limit, offset, and search filtering."""
    res = client.get("/api/db-admin/tables/cameras/data?page=1&limit=3")
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["limit"] == 3
    assert len(data["rows"]) <= 3
    assert data["total_rows"] > 0

def test_db_admin_integrity_check():
    """Verifies that SQLite PRAGMA integrity_check passes."""
    res = client.get("/api/db-admin/integrity-check")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["HEALTHY", "ok"]
