import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.db.models import Camera, Analysis, TrafficMetric

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert "version" in data
    assert "model_device" in data
    assert data["database_connected"] is True

def test_cameras_endpoint():
    response = client.get("/api/cameras")
    assert response.status_code == 200
    cams = response.json()
    assert isinstance(cams, list)
    assert len(cams) >= 1
    assert cams[0]["name"] is not None

def test_all_cameras_telemetry_endpoint():
    response = client.get("/api/cameras/telemetry/all")
    assert response.status_code == 200
    tele = response.json()
    assert isinstance(tele, dict)
    assert len(tele) >= 1
    first_key = list(tele.keys())[0]
    cam_data = tele[first_key]
    assert "vehicles_in_frame" in cam_data
    assert "density" in cam_data
    assert "fps" in cam_data

def test_lanes_endpoint():
    response = client.get("/api/traffic/lanes")
    assert response.status_code == 200
    lanes = response.json()
    assert isinstance(lanes, list)
    assert len(lanes) >= 4  # North, South, East, West default lanes

def test_signal_optimization_endpoint():
    req_body = {
        "intersection_name": "Test Crossroads",
        "approach_n_count": 25,
        "approach_s_count": 10,
        "approach_e_count": 40,
        "approach_w_count": 5,
        "cycle_time": 120,
        "min_green": 10,
        "max_green": 60
    }
    response = client.post("/api/signals/optimize", json=req_body)
    assert response.status_code == 200
    plan = response.json()
    assert plan["approach_e_green"] > plan["approach_w_green"]  # Highest volume gets more green
    assert plan["approach_w_green"] >= 10  # Enforces minimum green
    assert plan["approach_e_green"] <= 60  # Enforces maximum green
    assert plan["is_simulation"] is True  # Mandatory safety tag
    assert "Webster/Equal-Saturation" in plan["reasoning"]

def test_prediction_insufficient_data():
    # Clear any metrics for this test or check status when insufficient
    # By default on fresh DB or with < 5 items, must return INSUFFICIENT_DATA
    response = client.get("/api/traffic/predictions")
    assert response.status_code == 200
    pred = response.json()
    assert "status" in pred
    assert pred["status"] in ["VALID", "INSUFFICIENT_DATA"]
    if pred["status"] == "INSUFFICIENT_DATA":
        assert "Insufficient historical data" in pred["message"]

def test_reports_csv_generation():
    response = client.get("/api/reports/csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Metric ID,Timestamp" in response.text

def test_reports_pdf_generation():
    response = client.get("/api/reports/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")
