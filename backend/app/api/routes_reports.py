import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Report
from app.schemas.schemas import ReportResponse
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("/csv")
def download_csv_report(
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    analysis_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    generator = ReportGenerator(db=db)
    report = generator.generate_csv_report(date_from=date_from, date_to=date_to, analysis_id=analysis_id)
    
    filename = os.path.basename(report.file_path)
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
    db: Session = Depends(get_db)
):
    generator = ReportGenerator(db=db)
    report = generator.generate_pdf_report(date_from=date_from, date_to=date_to, analysis_id=analysis_id)
    
    filename = os.path.basename(report.file_path)
    return FileResponse(
        path=report.file_path,
        media_type="application/pdf",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/history")
def list_reports(db: Session = Depends(get_db)):
    reports = db.query(Report).order_by(Report.generated_at.desc()).limit(20).all()
    return [{
        "id": r.id,
        "report_type": r.report_type,
        "record_count": r.record_count,
        "file_size_bytes": r.file_size_bytes,
        "generated_at": r.generated_at,
        "filename": os.path.basename(r.file_path),
        "download_url": f"/api/reports/download/{os.path.basename(r.file_path)}"
    } for r in reports]

@router.get("/download/{filename}")
def download_file(filename: str):
    file_path = settings.REPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Requested report file not found.")

    media_type = "application/pdf" if filename.endswith(".pdf") else "text/csv"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
