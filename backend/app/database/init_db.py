import os
from datetime import datetime
from pathlib import Path
from app.database.connection import engine, Base, SessionLocal
from app.database.models import Camera, Video
from app.config import settings

def init_db():
    """
    Initializes SQLite tables for the 5 core models and seeds default operational data.
    """
    settings.ensure_directories()
    # Create all 5 tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Seed default cameras if empty
        if db.query(Camera).count() == 0:
            default_cameras = [
                Camera(
                    camera_name="Main Junction - North Approach",
                    location="North Highway Intersection (Lane 1-2)",
                    camera_type="CCTV",
                    stream_url="0",
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                ),
                Camera(
                    camera_name="Eastern Expressway Gate",
                    location="Eastbound Arterial Road",
                    camera_type="IP_CAMERA",
                    stream_url=None,
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                ),
                Camera(
                    camera_name="South Ring Road Overpass",
                    location="South Overpass Corridor",
                    camera_type="CCTV",
                    stream_url=None,
                    status="INACTIVE",
                    created_at=datetime.utcnow()
                )
            ]
            db.add_all(default_cameras)
            db.commit()
            print("[init_db] Seeded default cameras.")

        # Check for sample dataset video and register if no videos exist
        sample_video_path = settings.BASE_DIR / "datasets" / "sample_traffic.mp4"
        if sample_video_path.exists() and db.query(Video).count() == 0:
            file_size = sample_video_path.stat().st_size
            sample_video = Video(
                video_name="sample_traffic.mp4",
                file_path=str(sample_video_path),
                file_size=file_size,
                duration=10.0,
                status="UPLOADED",
                uploaded_at=datetime.utcnow()
            )
            db.add(sample_video)
            db.commit()
            print("[init_db] Seeded sample traffic video record.")

    except Exception as e:
        db.rollback()
        print(f"[init_db] Error seeding data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()

