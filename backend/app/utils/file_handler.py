import os
import shutil
import uuid
from pathlib import Path
from typing import Tuple, Optional
import cv2
from fastapi import UploadFile, HTTPException

from app.config import settings

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
MAX_FILE_SIZE_BYTES = 1024 * 1024 * 1024  # 1024 MB (1 GB) for 4K/UHD traffic recordings

def validate_video_file(filename: str, file_size: Optional[int] = None) -> None:
    """Validates video extension and size limits."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    if file_size and file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB."
        )

def save_uploaded_video(upload_file: UploadFile) -> Tuple[str, Path, int]:
    """
    Saves an uploaded file to the storage/uploads/ directory.
    Returns (safe_filename, target_path, file_size_bytes).
    """
    settings.ensure_directories()
    original_name = upload_file.filename or "video.mp4"
    validate_video_file(original_name)

    # Prefix with short uuid to guarantee uniqueness while keeping original name
    unique_prefix = uuid.uuid4().hex[:8]
    safe_name = f"{unique_prefix}_{Path(original_name).name}"
    target_path = settings.UPLOAD_DIR / safe_name

    bytes_written = 0
    with open(target_path, "wb") as buffer:
        while chunk := upload_file.file.read(1024 * 1024):  # 1MB chunks
            bytes_written += len(chunk)
            if bytes_written > MAX_FILE_SIZE_BYTES:
                buffer.close()
                if target_path.exists():
                    target_path.unlink()
                raise HTTPException(status_code=400, detail="Uploaded file exceeds maximum allowed size (1000 MB).")
            buffer.write(chunk)

    return original_name, target_path, bytes_written

def extract_video_metadata(file_path: str) -> dict:
    """
    Extracts frame count, duration, FPS, width, and height using OpenCV.
    """
    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        return {
            "fps": 30.0,
            "total_frames": 0,
            "duration": 0.0,
            "width": 640,
            "height": 480
        }

    fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = round(total_frames / max(1.0, fps), 2)
    cap.release()

    return {
        "fps": fps,
        "total_frames": total_frames,
        "duration": duration,
        "width": width,
        "height": height
    }

