import os
import csv
import io
import time
from datetime import datetime, timezone
from typing import Optional, List
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from sqlalchemy.orm import Session
from app.config import settings
from app.database.models import Analysis, TrafficMetric, Alert, Report

class ReportGenerator:
    """
    Generates genuine PDF and CSV traffic reports from stored SQLite observations.
    Includes date-range filters, summary metrics, incident alerts, and vehicle distributions.
    """
    def __init__(self, db: Session):
        self.db = db

    def generate_csv_report(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        analysis_id: Optional[int] = None
    ) -> Report:
        filename = f"traffic_report_{int(time.time())}.csv"
        filepath = settings.REPORTS_DIR / filename

        query = self.db.query(TrafficMetric)
        if date_from:
            query = query.filter(TrafficMetric.timestamp >= date_from)
        if date_to:
            query = query.filter(TrafficMetric.timestamp <= date_to)
        if analysis_id:
            query = query.filter(TrafficMetric.analysis_id == analysis_id)

        metrics = query.order_by(TrafficMetric.timestamp.desc()).all()

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Metric ID", "Timestamp (UTC)", "Analysis ID", "Camera ID",
                "Vehicle Count", "Flow Rate (/min)", "Occupancy Ratio",
                "Queue Length Est", "Density Score", "Congestion Level", "Calculation Details"
            ])
            for m in metrics:
                writer.writerow([
                    m.id,
                    m.timestamp.strftime("%Y-%m-%d %H:%M:%S") if m.timestamp else "",
                    m.analysis_id or "N/A",
                    m.camera_id or "N/A",
                    m.vehicle_count,
                    m.flow_rate_per_min,
                    f"{m.occupancy_ratio:.1%}",
                    m.estimated_queue_length,
                    m.density_score,
                    m.congestion_level,
                    m.calculation_details
                ])

        file_size = os.path.getsize(filepath)
        report = Report(
            report_type="CSV",
            date_from=date_from,
            date_to=date_to,
            file_path=str(filepath),
            record_count=len(metrics),
            file_size_bytes=file_size
        )
        self.db.add(report)
        self.db.commit()
        return report

    def generate_pdf_report(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        analysis_id: Optional[int] = None
    ) -> Report:
        filename = f"traffic_report_{int(time.time())}.pdf"
        filepath = settings.REPORTS_DIR / filename

        # Fetch metrics & alerts
        m_query = self.db.query(TrafficMetric)
        a_query = self.db.query(Alert)
        if date_from:
            m_query = m_query.filter(TrafficMetric.timestamp >= date_from)
            a_query = a_query.filter(Alert.timestamp >= date_from)
        if date_to:
            m_query = m_query.filter(TrafficMetric.timestamp <= date_to)
            a_query = a_query.filter(Alert.timestamp <= date_to)
        if analysis_id:
            m_query = m_query.filter(TrafficMetric.analysis_id == analysis_id)
            a_query = a_query.filter(Alert.analysis_id == analysis_id)

        metrics = m_query.order_by(TrafficMetric.timestamp.desc()).limit(50).all()
        alerts = a_query.order_by(Alert.timestamp.desc()).limit(20).all()

        doc = SimpleDocTemplate(str(filepath), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1E1B4B"),
            spaceAfter=6
        )
        subtitle_style = ParagraphStyle(
            name="SubtitleStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=15
        )
        h2_style = ParagraphStyle(
            name="H2Style",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#312E81"),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = styles["Normal"]

        # Title Block
        elements.append(Paragraph("AI-Based Traffic Management System", title_style))
        elements.append(Paragraph(
            f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | "
            f"Filter Scope: {date_from.strftime('%Y-%m-%d') if date_from else 'All Time'} to {date_to.strftime('%Y-%m-%d') if date_to else 'Present'}",
            subtitle_style
        ))
        elements.append(Spacer(1, 10))

        # Executive Summary Stats
        total_records = len(metrics)
        avg_vehicles = round(sum(m.vehicle_count for m in metrics) / max(1, total_records), 1) if total_records else 0.0
        total_alerts = len(alerts)

        summary_data = [
            ["Metric Parameter", "Observed Value"],
            ["Total Analyzed Intervals", str(total_records)],
            ["Average Vehicle Count / Interval", str(avg_vehicles)],
            ["Total Recorded Safety Incidents", str(total_alerts)],
            ["Model Pipeline", "Ultralytics YOLOv8 + ByteTrack / Centroid Association"]
        ]
        summary_table = Table(summary_data, colWidths=[240, 240])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor("#4F46E5")),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F8FAFC")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 15))

        # Traffic Observations Table
        elements.append(Paragraph("Recent Traffic Density & Flow Observations", h2_style))
        obs_header = ["Timestamp", "Count", "Flow (/min)", "Occupancy", "Density", "Congestion"]
        obs_rows = [obs_header]
        for m in metrics[:12]:
            obs_rows.append([
                m.timestamp.strftime("%H:%M:%S") if m.timestamp else "",
                str(m.vehicle_count),
                f"{m.flow_rate_per_min:.1f}",
                f"{m.occupancy_ratio:.1%}",
                f"{m.density_score:.1f}",
                m.congestion_level
            ])

        if len(obs_rows) == 1:
            obs_rows.append(["No records found", "-", "-", "-", "-", "-"])

        obs_table = Table(obs_rows, colWidths=[80, 50, 70, 70, 60, 90])
        obs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ]))
        elements.append(obs_table)
        elements.append(Spacer(1, 15))

        # Safety Incidents & Alerts Table
        elements.append(Paragraph("Recorded Safety Incidents & Alerts", h2_style))
        alert_header = ["Timestamp", "Type", "Severity", "Description"]
        alert_rows = [alert_header]
        for a in alerts[:8]:
            alert_rows.append([
                a.timestamp.strftime("%H:%M:%S") if a.timestamp else "",
                a.alert_type,
                a.severity,
                Paragraph(a.description[:120] + ("..." if len(a.description) > 120 else ""), styles["Normal"])
            ])

        if len(alert_rows) == 1:
            alert_rows.append(["No incidents recorded", "-", "-", "All monitored movements complied with safety rules."])

        alert_table = Table(alert_rows, colWidths=[70, 80, 60, 270])
        alert_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#991B1B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#FECACA")),
        ]))
        elements.append(alert_table)

        # Build PDF
        doc.build(elements)
        file_size = os.path.getsize(filepath)

        report = Report(
            report_type="PDF",
            date_from=date_from,
            date_to=date_to,
            file_path=str(filepath),
            record_count=total_records,
            file_size_bytes=file_size
        )
        self.db.add(report)
        self.db.commit()
        return report
