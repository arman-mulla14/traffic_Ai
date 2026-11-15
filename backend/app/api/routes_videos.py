import os
import shutil
import uuid
import cv2
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Video
from app.schemas.schemas import VideoResponse

router = APIRouter(prefix="/api/videos", tags=["Videos"])

@router.post("", response_model=VideoResponse)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Validates and stores uploaded video files (MP4, AVI, MOV, MKV).
    Enforces file extension and size checks, extracts real video metadata via OpenCV.
    """
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed extensions: {', '.join(settings.ALLOWED_VIDEO_EXTENSIONS)}"
        )

    # Generate safe server-side filename
    safe_filename = f"{uuid.uuid4().hex[:12]}_{Path(file.filename).name}"
    save_path = settings.UPLOAD_DIR / safe_filename

    # Save to disk while checking file size
    size_accum = 0
    with open(save_path, "wb") as buffer:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size_accum += len(chunk)
            if size_accum > settings.MAX_UPLOAD_SIZE_BYTES:
                buffer.close()
                if save_path.exists():
                    save_path.unlink()
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum allowable size of {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)} MB."
                )
            buffer.write(chunk)

    # Inspect real video properties using OpenCV
    cap = cv2.VideoCapture(str(save_path))
    if not cap.isOpened():
        if save_path.exists():
            save_path.unlink()
        raise HTTPException(status_code=400, detail="Corrupt or unreadable video file.")

    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = round(frame_count / max(1.0, fps), 2)
    cap.release()

    video_record = Video(
        filename=safe_filename,
        original_name=file.filename,
        file_path=str(save_path),
        file_size_bytes=size_accum,
        duration_seconds=duration,
        fps=fps,
        frame_count=frame_count,
        width=width,
        height=height
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)

    return video_record

@router.get("", response_model=list[VideoResponse])
def list_videos(db: Session = Depends(get_db)):
    return db.query(Video).order_by(Video.uploaded_at.desc()).limit(20).all()
