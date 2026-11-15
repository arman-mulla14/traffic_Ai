from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.db.models import Alert
from app.schemas.schemas import AlertResponse, AlertUpdate
from app.ai.emergency_detector import EmergencyVehicleDetector

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])
emergency_detector = EmergencyVehicleDetector()

@router.get("", response_model=List[AlertResponse])
def get_alerts(
    is_reviewed: Optional[bool] = Query(None),
    alert_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db)
):
    query = db.query(Alert)
    if is_reviewed is not None:
        query = query.filter(Alert.is_reviewed == is_reviewed)
    if alert_type is not None:
        query = query.filter(Alert.alert_type == alert_type)

    alerts = query.order_by(Alert.timestamp.desc()).limit(limit).all()
    return alerts

@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(alert_id: int, req: AlertUpdate, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert #{alert_id} not found.")

    alert.is_reviewed = req.is_reviewed
    if req.is_reviewed:
        alert.reviewed_at = datetime.utcnow()
    else:
        alert.reviewed_at = None

    db.commit()
    db.refresh(alert)
    return alert

@router.get("/emergency-status")
def get_emergency_detector_status():
    """
    Returns real status of emergency vehicle detection module.
    Explains whether custom weights are present or missing honestly.
    """
    return emergency_detector.get_status()
