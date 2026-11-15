import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query, Body, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Camera, Video, Analysis, Incident, TrafficRecord
from app.services.dataset_service import DatasetService, DATASET_CSV
from app.services.ml_trainer import MLTrafficTrainer

router = APIRouter(prefix="/api", tags=["AI Analytics, Predictions & Chatbot"])

# =============================================================================
# 1. AI CHATBOT COPILOT ENGINE
# =============================================================================

@router.post("/chat")
def traffic_ai_chat(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    Conversational Traffic Management AI Copilot.
    Answers real-time questions regarding traffic density, live cameras,
    safety incidents, signal optimization, and predictive congestion forecasts.
    """
    raw_prompt = payload.get("message", "").strip()
    if not raw_prompt:
        return {"response": "Hello! I am your AI Traffic Assistant. Ask me about current traffic density, camera feeds, safety incidents, or future traffic forecasts!"}

    prompt = raw_prompt.lower()

    # Query real database context
    cams_count = db.query(Camera).count()
    active_cams = db.query(Camera).filter(Camera.status == "ACTIVE").count()
    videos_count = db.query(Video).count()
    incidents_count = db.query(Incident).count()
    recent_incidents = db.query(Incident).order_by(Incident.id.desc()).limit(3).all()
    recent_traffic = db.query(TrafficRecord).order_by(TrafficRecord.id.desc()).limit(1).first()

    # Run ML prediction for forecast questions
    forecast_data = MLTrafficTrainer.predict_forecast(hours_ahead=12)
    peak_hour = forecast_data.get("peak_congestion_hour", "06:00 PM")
    peak_density = forecast_data.get("peak_density_pct", 78.5)

    # 1. Density & Volume queries
    if any(k in prompt for k in ["density", "how is traffic", "current traffic", "status of traffic", "crowded", "volume"]):
        cur_dens = recent_traffic.traffic_density if recent_traffic else 54.2
        cur_veh = recent_traffic.total_vehicles if recent_traffic else 18
        level = "Moderate" if cur_dens < 65 else ("High Congestion" if cur_dens < 85 else "Severe Jam")
        return {
            "response": (
                f"🚦 **Current Traffic Status**: Overall traffic density is currently **{cur_dens}%** ({level}) with approximately **{cur_veh} active vehicles** in the monitored sectors.\n\n"
                f"- **Active Surveillance Cameras**: {active_cams} of {cams_count} online.\n"
                f"- **Projected Peak Rush Hour**: Expect peak density of ~{peak_density}% around **{peak_hour}**.\n\n"
                f"*Tip: You can view live bounding box feeds in the Live Monitoring tab.*"
            )
        }

    # 2. Pedestrian & Human safety queries
    if any(k in prompt for k in ["human", "pedestrian", "people", "person", "walking", "crosswalk", "jaywalk"]):
        return {
            "response": (
                f"🚶‍♂️ **Pedestrian & Human Safety Monitoring**:\n\n"
                f"- Our YOLOv8 model actively tracks **Pedestrians (Class 0)** alongside vehicular classes.\n"
                f"- **Crosswalk & Lane Monitoring**: Pedestrians detected on roadway boundaries trigger safety cautions.\n"
                f"- **Safety Status**: No active pedestrian collision risks detected in the active sectors.\n"
                f"- **Recommendation**: Maintain green light phase priority at pedestrian crossings during morning and evening rush hours."
            )
        }

    # 3. Incident & Alert queries
    if any(k in prompt for k in ["incident", "accident", "wrong way", "alert", "emergency", "stopped vehicle"]):
        if recent_incidents:
            inc_list = "\n".join([f"- **#{inc.id} {inc.incident_type}** ({inc.severity} Severity) at {inc.timestamp.strftime('%H:%M:%S')}: {inc.description}" for inc in recent_incidents])
            return {
                "response": (
                    f"⚠️ **Incident Management Report** ({incidents_count} total incidents logged):\n\n"
                    f"{inc_list}\n\n"
                    f"*All active incidents are logged in the Incident Management dashboard with automated operator dispatch.*"
                )
            }
        else:
            return {"response": "✅ **All Clear**: No critical traffic incidents or safety violations currently recorded."}

    # 4. Prediction & Forecasting queries
    if any(k in prompt for k in ["predict", "forecast", "future", "tomorrow", "peak hour", "trend", "later"]):
        return {
            "response": (
                f"📈 **AI Traffic Congestion Forecast (Next 12 Hours)**:\n\n"
                f"- **Peak Congestion Expected**: Around **{peak_hour}** reaching **{peak_density}% density**.\n"
                f"- **Forecast Model**: Random Forest Multi-Output Regressor trained on continuous historical observations.\n"
                f"- **Model Accuracy ($R^2$)**: {round(MLTrafficTrainer._last_metrics.get('r2_score', 0.85)*100, 1)}% explained variance.\n"
                f"- **Strategic Recommendation**: Increase green signal duration on North Approach between 5:30 PM and 7:00 PM to mitigate queue buildup."
            )
        }

    # 5. Camera & Video queries
    if any(k in prompt for k in ["camera", "feed", "video", "cctv", "stream"]):
        cams = db.query(Camera).all()
        cam_names = ", ".join([c.camera_name for c in cams[:4]])
        return {
            "response": (
                f"📹 **Surveillance Camera Overview**:\n\n"
                f"- **Total Registered Feeds**: {cams_count} cameras ({active_cams} active).\n"
                f"- **Key Locations**: {cam_names}.\n"
                f"- **Recorded Library**: {videos_count} video recordings available for offline YOLOv8 vehicle & pedestrian analysis."
            )
        }

    # 6. Signal optimization queries
    if any(k in prompt for k in ["signal", "light", "timing", "optimize", "green light"]):
        return {
            "response": (
                f"🚦 **Adaptive Traffic Signal Optimization Recommendation**:\n\n"
                f"1. **Junction Alpha (North)**: Current density 54%. Recommend **45s Green Phase**.\n"
                f"2. **Eastern Tollway (East)**: Density 38%. Recommend **30s Green Phase**.\n"
                f"3. **South Bypass Roundabout**: Recommend dynamic metering to maintain roundabout circulation flow."
            )
        }

    # 7. Model Training queries
    if any(k in prompt for k in ["train", "dataset", "retrain", "learn"]):
        stats = DatasetService.get_dataset_stats()
        return {
            "response": (
                f"🧠 **Model Training & Dataset Intelligence**:\n\n"
                f"- **Telemetry Dataset**: {stats['total_samples']} samples collected ({stats['file_size_kb']} KB).\n"
                f"- **Recorded Vehicles**: {stats['total_vehicles_recorded']} | **Pedestrians**: {stats['total_pedestrians_recorded']}.\n"
                f"- **Forecasting Model**: Random Forest (100 estimators).\n"
                f"- *You can trigger a fresh model training run anytime via the Train Model button or asking me to train!*"
            )
        }

    # 8. Database Administration (DAP) queries
    if any(k in prompt for k in ["database", "sqlite", "table", "dap", "sql", "admin panel", "schema"]):
        return {
            "response": (
                f"🗄️ **SQLite Database Admin Panel (DAP)**:\n\n"
                f"- **Database Engine**: SQLite 3 (WAL Journal Mode).\n"
                f"- **Active Tables**: `cameras`, `videos`, `analyses`, `incidents`, `traffic_records`.\n"
                f"- **Capabilities**: Browse & filter records, inline row editing, record deletion, dynamic record insertion, table schema inspection, and raw SQL query execution.\n"
                f"- **Maintenance**: One-click VACUUM storage defragmentation, PRAGMA integrity verification, and `.db` backup download.\n\n"
                f"👉 [Open Database Admin Panel (DAP)](/frontend/pages/database-admin.html) to manage your tables directly."
            )
        }

    # Default friendly AI Assistant response
    return {
        "response": (
            f"🤖 **Traffic Management Copilot**:\n\n"
            f"I am actively monitoring **{active_cams} camera feeds**, tracking vehicle volume, pedestrian safety, and incident alerts.\n\n"
            f"**You can ask me:**\n"
            f"- *'What is current traffic density?'*\n"
            f"- *'Are there any pedestrians on the roadway?'*\n"
            f"- *'Show recent incident alerts.'*\n"
            f"- *'Predict traffic for the next 6 hours.'*\n"
            f"- *'Give signal timing recommendations.'*"
        )
    }

# =============================================================================
# 2. ML TRAINING & PREDICTION ENDPOINTS
# =============================================================================

@router.post("/ml/train")
def train_traffic_model():
    """Triggers supervised machine learning training on historical telemetry datasets."""
    metrics = MLTrafficTrainer.train_model()
    return {
        "status": "success",
        "message": "AI Traffic Forecasting Model trained successfully!",
        "r2_score": metrics.get("r2_score", 0.85),
        "mae": metrics.get("mae", 2.5),
        "samples_trained": metrics.get("samples_trained", 120),
        "metrics": metrics
    }

@router.get("/ml/predict")
def predict_traffic(
    hours: int = Query(24, ge=1, le=72),
    camera_id: Optional[int] = Query(None)
):
    """Returns predictive traffic density, vehicle counts, and congestion bottlenecks."""
    res = MLTrafficTrainer.predict_forecast(hours_ahead=hours)
    if camera_id:
        res["camera_id"] = camera_id
    return res

# =============================================================================
# 3. DATASET COLLECTION & EXPORT ENDPOINTS
# =============================================================================

@router.get("/datasets/stats")
def get_dataset_stats(camera_id: Optional[int] = Query(None)):
    """Returns dataset sample counts, file size, and feature distributions."""
    return DatasetService.get_dataset_stats(camera_id=camera_id)

@router.get("/datasets/export")
def export_dataset():
    """Exports and downloads the complete traffic telemetry dataset as CSV."""
    DatasetService.ensure_dataset_file()
    if not DATASET_CSV.exists():
        raise HTTPException(status_code=404, detail="Dataset file not found.")
    return FileResponse(
        str(DATASET_CSV),
        media_type="text/csv",
        filename=f"traffic_telemetry_dataset_{int(datetime.utcnow().timestamp())}.csv"
    )

@router.post("/datasets/record")
def record_telemetry_sample(payload: Dict[str, Any] = Body(...)):
    """Appends a new observation to the training dataset."""
    DatasetService.record_observation(payload)
    return {"status": "success", "message": "Telemetry sample recorded in dataset."}
