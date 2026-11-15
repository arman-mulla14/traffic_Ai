import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set

from app.db.session import SessionLocal
from app.db.models import Camera, TrafficMetric, Alert
from app.services.camera_streamer import CameraStreamManager

router = APIRouter(tags=["WebSocket Monitoring"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        dead_sockets = set()
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                dead_sockets.add(conn)
        for dead in dead_sockets:
            self.active_connections.discard(dead)

manager = ConnectionManager()

@router.websocket("/ws/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Gather current system snapshot from DB and active camera streams
            db = SessionLocal()
            try:
                active_cam = db.query(Camera).filter(Camera.status == "CONNECTED").first()
                latest_metric = db.query(TrafficMetric).order_by(TrafficMetric.timestamp.desc()).first()
                recent_alerts = db.query(Alert).filter(Alert.is_reviewed == False).order_by(Alert.timestamp.desc()).limit(5).all()

                stream_metrics = None
                if active_cam:
                    stream_mgr = CameraStreamManager.get_or_create(active_cam.id, active_cam.stream_url)
                    stream_metrics = stream_mgr.latest_metrics

                payload = {
                    "type": "METRICS_UPDATE",
                    "camera_connected": active_cam is not None,
                    "camera_name": active_cam.name if active_cam else None,
                    "stream_metrics": stream_metrics,
                    "latest_db_metric": {
                        "vehicle_count": latest_metric.vehicle_count if latest_metric else 0,
                        "flow_rate": latest_metric.flow_rate_per_min if latest_metric else 0.0,
                        "density_score": latest_metric.density_score if latest_metric else 0.0,
                        "congestion_level": latest_metric.congestion_level if latest_metric else "LOW",
                        "queue_length": latest_metric.estimated_queue_length if latest_metric else 0,
                        "timestamp": latest_metric.timestamp.isoformat() if latest_metric else None
                    } if latest_metric else None,
                    "unreviewed_alerts_count": len(recent_alerts),
                    "latest_alert": {
                        "id": recent_alerts[0].id,
                        "type": recent_alerts[0].alert_type,
                        "severity": recent_alerts[0].severity,
                        "description": recent_alerts[0].description
                    } if recent_alerts else None
                }
            finally:
                db.close()

            await websocket.send_json(payload)

            # Wait 1.5 seconds between updates or receive client ping
            try:
                # Wait for any incoming message with 1.5s timeout
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.5)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
        manager.disconnect(websocket)
