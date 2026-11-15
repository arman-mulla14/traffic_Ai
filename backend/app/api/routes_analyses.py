from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db, SessionLocal
from app.db.models import Analysis, Video, VehicleTrack
from app.schemas.schemas import AnalysisCreate, AnalysisResponse
from app.services.video_processor import VideoProcessor

router = APIRouter(prefix="/api/analyses", tags=["Analyses"])

def run_analysis_background(analysis_id: int):
    db = SessionLocal()
    try:
        processor = VideoProcessor(db=db, analysis_id=analysis_id)
        processor.process()
    finally:
        db.close()

@router.post("", response_model=AnalysisResponse)
def create_analysis(
    req: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    if not req.video_id:
        raise HTTPException(status_code=400, detail="video_id is required.")

    video = db.query(Video).filter(Video.id == req.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail=f"Video #{req.video_id} not found.")

    # Check if analysis is already currently running for this video
    active_job = db.query(Analysis).filter(
        Analysis.video_id == req.video_id,
        Analysis.status.in_(["PENDING", "PROCESSING"])
    ).first()
    if active_job:
        return active_job

    analysis = Analysis(
        video_id=video.id,
        status="PENDING",
        progress_pct=0.0,
        total_frames=video.frame_count
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Launch background processing
    background_tasks.add_task(run_analysis_background, analysis.id)

    return analysis

@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis #{analysis_id} not found.")
    return analysis

@router.get("", response_model=list[AnalysisResponse])
def list_analyses(db: Session = Depends(get_db)):
    return db.query(Analysis).order_by(Analysis.created_at.desc()).limit(20).all()

@router.get("/{analysis_id}/tracks")
def get_analysis_tracks(analysis_id: int, db: Session = Depends(get_db)):
    tracks = db.query(VehicleTrack).filter(VehicleTrack.analysis_id == analysis_id).all()
    return [{
        "track_id": t.track_id,
        "class_name": t.class_name,
        "first_seen_frame": t.first_seen_frame,
        "last_seen_frame": t.last_seen_frame,
        "is_counted": t.is_counted,
        "average_speed_px": t.average_speed_px,
        "is_wrong_way": t.is_wrong_way,
        "is_stopped": t.is_stopped
    } for t in tracks]
