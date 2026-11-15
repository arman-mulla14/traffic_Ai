import os
import json
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import get_db
from app.database.init_db import init_db
from app.database.models import Camera, Analysis, Video, Incident
from app.services.detection_service import DetectionService

# Import simplified routers
from app.routes.dashboard import router as dashboard_router
from app.routes.videos import router as videos_router
from app.routes.traffic import router as traffic_router
from app.routes.incidents import router as incidents_router
from app.routes.reports import router as reports_router
from app.routes.analytics_ai import router as analytics_ai_router
from app.routes.db_admin import router as db_admin_router
from app.routes.signals import router as signals_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[*] Starting {settings.PROJECT_NAME} v{settings.VERSION}...")
    init_db()
    # Warm up YOLO model singleton
    try:
        det = DetectionService.get_instance()
        print(f"[*] Detection Service ready: loaded={det.is_loaded}, device={det.device}")
    except Exception as e:
        print(f"[!] Warning initializing YOLO detector: {e}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="MCA Major Project: AI-Based Traffic Management System featuring YOLOv8 detection, multi-object tracking, density calculation, incident alerts, and 5 reporting modules.",
    lifespan=lifespan
)

# Enable CORS for flexible local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(dashboard_router)
app.include_router(videos_router)
app.include_router(traffic_router)
app.include_router(incidents_router)
app.include_router(reports_router)
app.include_router(analytics_ai_router)
app.include_router(db_admin_router)
app.include_router(signals_router)

# Compatibility routes for legacy browser tabs
@app.get("/api/traffic/metrics", tags=["Compatibility"])
def legacy_traffic_metrics():
    return {
        "status": "success",
        "total_vehicles": 14,
        "density": 48.5,
        "avg_speed": 42.0,
        "co2": 4.8
    }

@app.get("/api/alerts", tags=["Compatibility"])
def legacy_alerts():
    return []

@app.websocket("/ws/monitoring")
async def ws_monitoring_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({
                "type": "telemetry",
                "vehicles": 14,
                "density": 48.5,
                "status": "ONLINE"
            })
            await asyncio.sleep(2.0)
    except Exception:
        pass

# Mount static storage directories
settings.ensure_directories()
app.mount("/storage/processed", StaticFiles(directory=str(settings.PROCESSED_DIR)), name="processed")
app.mount("/storage/reports", StaticFiles(directory=str(settings.REPORTS_DIR)), name="reports")

# Settings file persistence
SETTINGS_FILE = settings.STORAGE_DIR / "system_settings.json"
DEFAULT_SETTINGS = {
    "detection_model": "yolov8n.pt",
    "confidence_threshold": 0.35,
    "iou_threshold": 0.45,
    "processing_fps": 30,
    "density_threshold": 75,
    "wrong_way_sensitivity": "HIGH",
    "stopped_vehicle_seconds": 3,
    "auto_purge_days": 30,
    "alert_notifications": True,
    "device": "cpu"
}

@app.get("/api/settings", tags=["Settings"])
def get_settings():
    """Returns persistent application configuration settings."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_SETTINGS

@app.post("/api/settings", tags=["Settings"])
def save_settings(data: dict = Body(...)):
    """Saves application configuration settings."""
    current = get_settings()
    current.update(data)
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(current, f, indent=2)
    except Exception as e:
        return {"status": "error", "message": str(e)}
    return {"status": "success", "settings": current}

# Mount frontend assets and pages so direct relative links work smoothly
app.mount("/frontend", StaticFiles(directory=str(settings.FRONTEND_DIR)), name="frontend")
app.mount("/pages", StaticFiles(directory=str(settings.FRONTEND_DIR / "pages")), name="pages")
app.mount("/css", StaticFiles(directory=str(settings.FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(settings.FRONTEND_DIR / "js")), name="js")
if (settings.FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(settings.FRONTEND_DIR / "assets")), name="assets")

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for system readiness and database connectivity."""
    cams_count = db.query(Camera).count()
    videos_count = db.query(Video).count()
    analyses_count = db.query(Analysis).count()

    det = DetectionService.get_instance()
    return {
        "status": "HEALTHY",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "model_loaded": det.is_loaded,
        "model_device": det.device,
        "database_connected": True,
        "total_cameras": cams_count,
        "total_videos": videos_count,
        "total_analyses": analyses_count,
        "system_time": datetime.now(timezone.utc)
    }

@app.get("/")
@app.get("/dashboard")
@app.get("/index.html")
def root_dashboard():
    """Serves the main central operations dashboard."""
    index_file = settings.FRONTEND_DIR / "index.html"
    return FileResponse(str(index_file))

@app.get("/database-admin")
@app.get("/dap")
def serve_db_admin():
    """Serves the SQLite Database Admin Page (DAP)."""
    dap_file = settings.FRONTEND_DIR / "pages" / "database-admin.html"
    return FileResponse(str(dap_file))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
