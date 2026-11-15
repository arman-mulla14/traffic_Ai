import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_ml_traffic_forecast():
    """Verifies that the ML traffic forecasting engine outputs multi-hour predictions."""
    res = client.get("/api/ml/predict?hours=12")
    assert res.status_code == 200
    data = res.json()
    assert "forecasts" in data
    assert len(data["forecasts"]) >= 6
    first_f = data["forecasts"][0]
    assert "time_slot" in first_f
    assert "predicted_vehicles" in first_f
    assert "predicted_density_pct" in first_f
    assert "congestion_level" in first_f
    assert "model_metrics" in data

def test_ml_traffic_train():
    """Verifies the supervised training endpoint on historical telemetry datasets."""
    res = client.post("/api/ml/train")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "r2_score" in data
    assert data["r2_score"] >= 0.0

def test_ai_chatbot_copilot():
    """Verifies the conversational traffic management copilot returns database-grounded answers."""
    # Query current traffic
    res = client.post("/api/chat", json={"message": "What is the current traffic density?"})
    assert res.status_code == 200
    data = res.json()
    assert "response" in data
    assert len(data["response"]) > 10

    # Query signal timings
    res_signals = client.post("/api/chat", json={"message": "Suggest signal timings for the intersection"})
    assert res_signals.status_code == 200
    data_sig = res_signals.json()
    assert "response" in data_sig
    assert "Junction" in data_sig["response"] or "Green" in data_sig["response"] or "Phase" in data_sig["response"]

def test_dataset_telemetry_stats():
    """Verifies dataset intelligence and recorded sample stats."""
    res = client.get("/api/datasets/stats")
    assert res.status_code == 200
    data = res.json()
    assert "total_samples" in data
    assert "file_size_kb" in data
    assert data["total_samples"] >= 0

