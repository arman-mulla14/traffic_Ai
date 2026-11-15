import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_signal_agent_status():
    """Verifies that the 4-way intersection agent returns complete approach telemetry and lamp states."""
    res = client.get("/api/signals/agent/status")
    assert res.status_code == 200
    data = res.json()
    assert "active_approach" in data
    assert data["active_approach"] in ["NORTH", "EAST", "SOUTH", "WEST"]
    assert "phase_state" in data
    assert data["phase_state"] in ["GREEN", "YELLOW"]
    assert data["phase_remaining_seconds"] > 0
    assert "approaches" in data
    for app_name in ["NORTH", "EAST", "SOUTH", "WEST"]:
        assert app_name in data["approaches"]
        app_data = data["approaches"][app_name]
        assert app_data["color"] in ["GREEN", "YELLOW", "RED"]
        assert app_data["countdown_seconds"] >= 0
        assert "telemetry" in app_data
        assert "vehicles" in app_data["telemetry"]
        assert "density" in app_data["telemetry"]

def test_signal_agent_override():
    """Tests manual operator override to force green on a specific approach."""
    payload = {"approach": "EAST", "duration": 42}
    res = client.post("/api/signals/agent/override", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "current_status" in data
    assert data["current_status"]["active_approach"] == "EAST"
    assert data["current_status"]["approaches"]["EAST"]["color"] == "GREEN"

def test_signal_agent_emergency_hold():
    """Tests emergency corridor activation and release."""
    # Activate on NORTH
    res_on = client.post("/api/signals/agent/emergency", json={"approach": "NORTH"})
    assert res_on.status_code == 200
    data_on = res_on.json()
    assert data_on["status"] == "success"
    assert data_on["current_status"]["emergency_override"] == "NORTH"
    assert data_on["current_status"]["approaches"]["NORTH"]["color"] == "GREEN"

    # Release
    res_off = client.post("/api/signals/agent/emergency", json={"approach": None})
    assert res_off.status_code == 200
    data_off = res_off.json()
    assert data_off["status"] == "success"
    assert data_off["current_status"]["emergency_override"] is None

def test_signal_agent_config():
    """Tests updating agent cycle time and active mode."""
    payload = {"agent_active": True, "cycle_seconds": 150}
    res = client.post("/api/signals/agent/config", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["cycle_seconds"] == 150
    assert data["agent_active"] is True

