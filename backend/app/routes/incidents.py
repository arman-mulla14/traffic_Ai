from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Incident
from app.schemas.schemas import IncidentResponse, IncidentResolve
from app.utils.helpers import parse_date_range

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])

@router.get("", response_model=List[IncidentResponse])
def list_incidents(
    incident_type: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Lists detected traffic incidents with multiple filter criteria."""
    query = db.query(Incident)

    if incident_type:
        query = query.filter(Incident.incident_type == incident_type)
    if severity:
        query = query.filter(Incident.severity == severity)
    if status:
        query = query.filter(Incident.status == status)

    dt_start, dt_end = parse_date_range(start_date, end_date)
    if dt_start:
        query = query.filter(Incident.timestamp >= dt_start)
    if dt_end:
        query = query.filter(Incident.timestamp <= dt_end)

    return query.order_by(Incident.timestamp.desc()).offset(offset).limit(limit).all()

@router.get("/{id}", response_model=IncidentResponse)
def get_incident(id: int, db: Session = Depends(get_db)):
    """Retrieves a single incident by ID."""
    inc = db.query(Incident).filter(Incident.id == id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")
    return inc

@router.patch("/{id}/resolve", response_model=IncidentResponse)
def resolve_incident(
    id: int,
    payload: Optional[IncidentResolve] = None,
    db: Session = Depends(get_db)
):
    """Marks an incident as ACKNOWLEDGED or RESOLVED."""
    inc = db.query(Incident).filter(Incident.id == id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    inc.status = payload.status if payload and payload.status else "RESOLVED"
    db.commit()
    db.refresh(inc)
    return inc

