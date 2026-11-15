from datetime import datetime
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.report_service import ReportService
from app.utils.helpers import parse_date_range

router = APIRouter(prefix="/api/reports", tags=["Reports"])

# =============================================================================
# Core Generic Reports (CSV & PDF)
# =============================================================================
@router.get("/csv")
def download_csv_report(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    analysis_id: Optional[int] = Query(None),
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    from app.services.report_generator import ReportGenerator
    generator = ReportGenerator(db=db)
    report = generator.generate_csv_report(date_from=date_from, date_to=date_to, analysis_id=analysis_id)
    filename = Path(report.file_path).name
    return FileResponse(
        path=report.file_path,
        media_type="text/csv",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/pdf")
def download_pdf_report(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    analysis_id: Optional[int] = Query(None),
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    from app.services.report_generator import ReportGenerator
    generator = ReportGenerator(db=db)
    report = generator.generate_pdf_report(date_from=date_from, date_to=date_to, analysis_id=analysis_id)
    filename = Path(report.file_path).name
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

# =============================================================================
# REPORT 1: Traffic Summary Report
# =============================================================================
@router.get("/traffic-summary/pdf")
def get_traffic_summary_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_traffic_summary_pdf(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="application/pdf", filename=file_path.name)

@router.get("/traffic-summary/csv")
def get_traffic_summary_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_traffic_summary_csv(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="text/csv", filename=file_path.name)

# =============================================================================
# REPORT 2: Vehicle Count Report
# =============================================================================
@router.get("/vehicle-count/pdf")
def get_vehicle_count_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_vehicle_count_pdf(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="application/pdf", filename=file_path.name)

@router.get("/vehicle-count/csv")
def get_vehicle_count_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_vehicle_count_csv(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="text/csv", filename=file_path.name)

# =============================================================================
# REPORT 3: Traffic Density Report
# =============================================================================
@router.get("/density/pdf")
def get_density_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_density_pdf(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="application/pdf", filename=file_path.name)

@router.get("/density/csv")
def get_density_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_density_csv(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="text/csv", filename=file_path.name)

# =============================================================================
# REPORT 4: Traffic Incident Report
# =============================================================================
@router.get("/incidents/pdf")
def get_incidents_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_incidents_pdf(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="application/pdf", filename=file_path.name)

@router.get("/incidents/csv")
def get_incidents_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_incidents_csv(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="text/csv", filename=file_path.name)

# =============================================================================
# REPORT 5: Video Analysis Report
# =============================================================================
@router.get("/video-analysis/pdf")
def get_video_analysis_pdf(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_video_analysis_pdf(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="application/pdf", filename=file_path.name)

@router.get("/video-analysis/csv")
def get_video_analysis_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    camera_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    dt_start, dt_end = parse_date_range(start_date, end_date)
    svc = ReportService(db)
    file_path = svc.generate_video_analysis_csv(dt_start, dt_end, camera_id=camera_id)
    return FileResponse(str(file_path), media_type="text/csv", filename=file_path.name)

