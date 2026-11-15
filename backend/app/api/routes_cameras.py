import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import Camera
from app.schemas.schemas import CameraCreate, CameraResponse
from app.services.camera_streamer import CameraStreamManager

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])

@router.get("", response_model=list[CameraResponse])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()

@router.post("", response_model=CameraResponse)
def create_camera(data: CameraCreate, db: Session = Depends(get_db)):
    cam = Camera(
        name=data.name,
        stream_url=data.stream_url,
        location=data.location or "Main Intersection",
        fps=data.fps or 30.0,
        status="DISCONNECTED",
        is_active=False
    )
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam

@router.post("/{camera_id}/start")
def start_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    manager = CameraStreamManager.get_or_create(cam.id, cam.stream_url)
    res = manager.start()
    return res

@router.post("/{camera_id}/stop")
def stop_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    manager = CameraStreamManager.get_or_create(cam.id, cam.stream_url)
    res = manager.stop()
    return res

@router.post("/{camera_id}/reconnect")
def reconnect_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    manager = CameraStreamManager.get_or_create(cam.id, cam.stream_url)
    res = manager.reconnect()
    return res

@router.get("/{camera_id}/status")
def get_camera_status(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    manager = CameraStreamManager.get_or_create(cam.id, cam.stream_url)
    return {
        "camera_id": cam.id,
        "name": cam.name,
        "stream_url": cam.stream_url,
        "db_status": cam.status,
        "live_metrics": manager.latest_metrics
    }

def frame_generator(manager: CameraStreamManager):
    """Generates multipart MJPEG frames for browser consumption."""
    while manager.is_running:
        if manager.latest_frame_jpeg is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + manager.latest_frame_jpeg + b'\r\n')
        time.sleep(0.04)

@router.get("/{camera_id}/stream")
def stream_camera(camera_id: int, db: Session = Depends(get_db)):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found.")

    manager = CameraStreamManager.get_or_create(cam.id, cam.stream_url)
    if not manager.is_running:
        raise HTTPException(status_code=400, detail="Camera stream is not active. Click Start to begin streaming.")

    return StreamingResponse(
        frame_generator(manager),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
