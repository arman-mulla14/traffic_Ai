import os
import csv
import io
import time
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database.models import Video, Analysis, TrafficRecord, Incident
from app.utils.helpers import classify_density

class ReportService:
    """
    Five Functional Traffic Reports Generator.
    Produces authentic, date-filtered PDF and CSV reports derived directly
    from SQLite database records.
    """

    def __init__(self, db: Session):
        self.db = db
        settings.ensure_directories()
        self.styles = getSampleStyleSheet()
        self._init_custom_styles()

    def _init_custom_styles(self):
        self.title_style = ParagraphStyle(
            "ReportTitle",
            parent=self.styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#1E1B4B"),
            spaceAfter=6
        )
        self.subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=self.styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#4B5563"),
            spaceAfter=12
        )
        self.header_style = ParagraphStyle(
            "TableHeader",
            parent=self.styles["Normal"],
            fontSize=9,
            leading=11,
            fontName="Helvetica-Bold",
            textColor=colors.whitesmoke
        )
        self.cell_style = ParagraphStyle(
            "TableCell",
            parent=self.styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1F2937")
        )
        self.meta_style = ParagraphStyle(
            "MetaText",
            parent=self.styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#374151")
        )

    # -------------------------------------------------------------------------
    def _get_road_label(self, camera_id: Optional[int]) -> str:
        if not camera_id:
            return "All Roads (Full Intersection Approaches)"
        from app.database.models import Camera
        cam = self.db.query(Camera).filter(Camera.id == camera_id).first()
        if cam:
            return f"Road {cam.id}: {cam.camera_name}"
        return f"Road Approach #{camera_id}"

    # -------------------------------------------------------------------------
    # REPORT 1: Traffic Summary Report
    # -------------------------------------------------------------------------
    def generate_traffic_summary_csv(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"traffic_summary_road_{camera_id or 'all'}_{int(time.time())}.csv"
        path = settings.REPORTS_DIR / filename

        data = self._get_traffic_summary_data(date_from, date_to, camera_id=camera_id)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Report", "Traffic Summary Report"])
            writer.writerow(["Target Road / Approach", self._get_road_label(camera_id)])
            writer.writerow(["Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
            writer.writerow(["Date Range", f"{date_from or 'All'} to {date_to or 'All'}"])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Target Road", self._get_road_label(camera_id)])
            writer.writerow(["Total Videos Processed", data["total_videos"]])
            writer.writerow(["Total Vehicles Detected", data["total_vehicles"]])
            writer.writerow(["Total Cars", data["total_cars"]])
            writer.writerow(["Total Motorcycles", data["total_motorcycles"]])
            writer.writerow(["Total Buses", data["total_buses"]])
            writer.writerow(["Total Trucks", data["total_trucks"]])
            writer.writerow(["Average Traffic Density", f"{data['avg_density']}%"])
            writer.writerow(["Density Classification", data["density_classification"]])
            writer.writerow(["Total Incidents Detected", data["total_incidents"]])

        return path

    def generate_traffic_summary_pdf(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"traffic_summary_road_{camera_id or 'all'}_{int(time.time())}.pdf"
        path = settings.REPORTS_DIR / filename

        data = self._get_traffic_summary_data(date_from, date_to, camera_id=camera_id)
        doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        story.append(Paragraph("REPORT 1: Traffic Summary Report", self.title_style))
        story.append(Paragraph(f"<b>Target Road:</b> {self._get_road_label(camera_id)}", self.meta_style))
        story.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Filter: {date_from.strftime('%Y-%m-%d') if date_from else 'All'} to {date_to.strftime('%Y-%m-%d') if date_to else 'All'}", self.subtitle_style))
        story.append(Spacer(1, 10))

        # KPI Metrics Table
        table_data = [
            [Paragraph("Key Performance Indicator", self.header_style), Paragraph("Observed Value", self.header_style)],
            [Paragraph("Monitored Road / Approach", self.cell_style), Paragraph(self._get_road_label(camera_id), self.cell_style)],
            [Paragraph("Total Videos Processed", self.cell_style), Paragraph(str(data["total_videos"]), self.cell_style)],
            [Paragraph("Total Vehicles Detected", self.cell_style), Paragraph(str(data["total_vehicles"]), self.cell_style)],
            [Paragraph("Cars Detected", self.cell_style), Paragraph(str(data["total_cars"]), self.cell_style)],
            [Paragraph("Motorcycles Detected", self.cell_style), Paragraph(str(data["total_motorcycles"]), self.cell_style)],
            [Paragraph("Buses Detected", self.cell_style), Paragraph(str(data["total_buses"]), self.cell_style)],
            [Paragraph("Trucks Detected", self.cell_style), Paragraph(str(data["total_trucks"]), self.cell_style)],
            [Paragraph("Average Traffic Density", self.cell_style), Paragraph(f"{data['avg_density']}% ({data['density_classification']})", self.cell_style)],
            [Paragraph("Total Traffic Incidents", self.cell_style), Paragraph(str(data["total_incidents"]), self.cell_style)]
        ]

        t = Table(table_data, colWidths=[280, 260])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F46E5")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        doc.build(story)
        return path

    def _get_traffic_summary_data(self, date_from, date_to, camera_id=None):
        q_v = self.db.query(Video).filter(Video.status == "COMPLETED")
        q_tr = self.db.query(TrafficRecord)
        q_inc = self.db.query(Incident)

        if camera_id:
            q_tr = q_tr.filter(TrafficRecord.camera_id == camera_id)
            q_inc = q_inc.filter(Incident.camera_id == camera_id)

        if date_from:
            q_v = q_v.filter(Video.uploaded_at >= date_from)
            q_tr = q_tr.filter(TrafficRecord.timestamp >= date_from)
            q_inc = q_inc.filter(Incident.timestamp >= date_from)
        if date_to:
            q_v = q_v.filter(Video.uploaded_at <= date_to)
            q_tr = q_tr.filter(TrafficRecord.timestamp <= date_to)
            q_inc = q_inc.filter(Incident.timestamp <= date_to)

        total_videos = q_v.count()
        total_incidents = q_inc.count()

        agg = q_tr.with_entities(
            func.sum(TrafficRecord.car_count),
            func.sum(TrafficRecord.motorcycle_count),
            func.sum(TrafficRecord.bus_count),
            func.sum(TrafficRecord.truck_count),
            func.sum(TrafficRecord.total_vehicles),
            func.avg(TrafficRecord.traffic_density)
        ).first()

        cars = agg[0] or 0
        motorcycles = agg[1] or 0
        buses = agg[2] or 0
        trucks = agg[3] or 0
        total_vehicles = agg[4] or 0
        avg_density = round(float(agg[5] or 0.0), 1)

        return {
            "total_videos": total_videos,
            "total_vehicles": total_vehicles,
            "total_cars": cars,
            "total_motorcycles": motorcycles,
            "total_buses": buses,
            "total_trucks": trucks,
            "avg_density": avg_density,
            "density_classification": classify_density(avg_density),
            "total_incidents": total_incidents
        }

    # -------------------------------------------------------------------------
    # REPORT 2: Vehicle Count Report
    # -------------------------------------------------------------------------
    def generate_vehicle_count_csv(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"vehicle_count_road_{camera_id or 'all'}_{int(time.time())}.csv"
        path = settings.REPORTS_DIR / filename

        records = self._get_traffic_records(date_from, date_to, camera_id=camera_id)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Report", "Vehicle Classification Breakdown Report"])
            writer.writerow(["Target Road / Approach", self._get_road_label(camera_id)])
            writer.writerow(["Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
            writer.writerow(["Date Range", f"{date_from or 'All'} to {date_to or 'All'}"])
            writer.writerow([])
            writer.writerow(["Analysis ID", "Road / Approach", "Timestamp (UTC)", "Cars", "Motorcycles", "Buses", "Trucks", "Total Vehicles", "Direction"])
            for r in records:
                writer.writerow([
                    r.analysis_id,
                    r.road_name or self._get_road_label(r.camera_id),
                    r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "",
                    r.car_count,
                    r.motorcycle_count,
                    r.bus_count,
                    r.truck_count,
                    r.total_vehicles,
                    r.direction
                ])

        return path

    def generate_vehicle_count_pdf(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"vehicle_count_road_{camera_id or 'all'}_{int(time.time())}.pdf"
        path = settings.REPORTS_DIR / filename

        records = self._get_traffic_records(date_from, date_to, camera_id=camera_id)
        doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        story.append(Paragraph("REPORT 2: Vehicle Count Report", self.title_style))
        story.append(Paragraph(f"<b>Target Road:</b> {self._get_road_label(camera_id)}", self.meta_style))
        story.append(Paragraph(f"Category breakdown across analysis intervals. Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", self.subtitle_style))
        story.append(Spacer(1, 10))

        # Calculate category percentages
        total_cars = sum(r.car_count for r in records)
        total_motos = sum(r.motorcycle_count for r in records)
        total_buses = sum(r.bus_count for r in records)
        total_trucks = sum(r.truck_count for r in records)
        grand_total = max(1, total_cars + total_motos + total_buses + total_trucks)

        dist_data = [
            [Paragraph("Category", self.header_style), Paragraph("Total Count", self.header_style), Paragraph("Percentage", self.header_style)],
            [Paragraph("Cars", self.cell_style), Paragraph(str(total_cars), self.cell_style), Paragraph(f"{(total_cars/grand_total)*100:.1f}%", self.cell_style)],
            [Paragraph("Motorcycles", self.cell_style), Paragraph(str(total_motos), self.cell_style), Paragraph(f"{(total_motos/grand_total)*100:.1f}%", self.cell_style)],
            [Paragraph("Buses", self.cell_style), Paragraph(str(total_buses), self.cell_style), Paragraph(f"{(total_buses/grand_total)*100:.1f}%", self.cell_style)],
            [Paragraph("Trucks", self.cell_style), Paragraph(str(total_trucks), self.cell_style), Paragraph(f"{(total_trucks/grand_total)*100:.1f}%", self.cell_style)],
            [Paragraph("<b>TOTAL</b>", self.cell_style), Paragraph(f"<b>{grand_total}</b>", self.cell_style), Paragraph("<b>100.0%</b>", self.cell_style)]
        ]
        t_dist = Table(dist_data, colWidths=[180, 180, 180])
        t_dist.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3B82F6")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_dist)
        story.append(Spacer(1, 15))

        # Recent breakdown table
        story.append(Paragraph("<b>Recent Analysis Record Breakdown:</b>", self.meta_style))
        story.append(Spacer(1, 5))

        table_rows = [
            [Paragraph("ID", self.header_style), Paragraph("Road Approach", self.header_style), Paragraph("Timestamp (UTC)", self.header_style),
             Paragraph("Cars", self.header_style), Paragraph("Motorcycles", self.header_style),
             Paragraph("Buses", self.header_style), Paragraph("Trucks", self.header_style),
             Paragraph("Total", self.header_style)]
        ]

        for r in records[:25]:  # Show top 25 recent
            rname = r.road_name or f"Cam #{r.camera_id}"
            table_rows.append([
                Paragraph(str(r.analysis_id), self.cell_style),
                Paragraph(rname[:18], self.cell_style),
                Paragraph(r.timestamp.strftime("%Y-%m-%d %H:%M") if r.timestamp else "", self.cell_style),
                Paragraph(str(r.car_count), self.cell_style),
                Paragraph(str(r.motorcycle_count), self.cell_style),
                Paragraph(str(r.bus_count), self.cell_style),
                Paragraph(str(r.truck_count), self.cell_style),
                Paragraph(str(r.total_vehicles), self.cell_style)
            ])

        t_records = Table(table_rows, colWidths=[35, 115, 95, 60, 65, 55, 55, 60])
        t_records.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_records)

        doc.build(story)
        return path

    # -------------------------------------------------------------------------
    # REPORT 3: Traffic Density Report
    # -------------------------------------------------------------------------
    def generate_density_csv(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"traffic_density_road_{camera_id or 'all'}_{int(time.time())}.csv"
        path = settings.REPORTS_DIR / filename

        records = self._get_traffic_records(date_from, date_to, camera_id=camera_id)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Report", "Traffic Density & Congestion Audit Report"])
            writer.writerow(["Target Road / Approach", self._get_road_label(camera_id)])
            writer.writerow(["Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
            writer.writerow(["Date Range", f"{date_from or 'All'} to {date_to or 'All'}"])
            writer.writerow([])
            writer.writerow(["Record ID", "Road / Approach", "Timestamp (UTC)", "Density (%)", "Classification", "Queue Length", "Direction"])
            for r in records:
                writer.writerow([
                    r.id,
                    r.road_name or self._get_road_label(r.camera_id),
                    r.timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.timestamp else "",
                    f"{r.traffic_density:.1f}%",
                    classify_density(r.traffic_density),
                    r.queue_length,
                    r.direction
                ])

        return path

    def generate_density_pdf(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"traffic_density_road_{camera_id or 'all'}_{int(time.time())}.pdf"
        path = settings.REPORTS_DIR / filename

        records = self._get_traffic_records(date_from, date_to, camera_id=camera_id)
        doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        story.append(Paragraph("REPORT 3: Traffic Density Report", self.title_style))
        story.append(Paragraph(f"<b>Target Road:</b> {self._get_road_label(camera_id)}", self.meta_style))
        story.append(Paragraph(f"Road occupancy measurements and queue length analysis. Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", self.subtitle_style))
        story.append(Spacer(1, 10))

        # Peak and lowest density detection
        peak_rec = max(records, key=lambda r: r.traffic_density) if records else None
        low_rec = min(records, key=lambda r: r.traffic_density) if records else None

        summary_data = [
            [Paragraph("Analysis Dimension", self.header_style), Paragraph("Observed Observation", self.header_style)],
            [Paragraph("Target Road Approach", self.cell_style), Paragraph(self._get_road_label(camera_id), self.cell_style)],
            [Paragraph("Peak Density Recorded", self.cell_style),
             Paragraph(f"{peak_rec.traffic_density:.1f}% ({classify_density(peak_rec.traffic_density)}) on {peak_rec.timestamp.strftime('%Y-%m-%d %H:%M')}" if peak_rec else "N/A", self.cell_style)],
            [Paragraph("Lowest Density Recorded", self.cell_style),
             Paragraph(f"{low_rec.traffic_density:.1f}% ({classify_density(low_rec.traffic_density)}) on {low_rec.timestamp.strftime('%Y-%m-%d %H:%M')}" if low_rec else "N/A", self.cell_style)],
            [Paragraph("Maximum Queue Length", self.cell_style),
             Paragraph(f"{max((r.queue_length for r in records), default=0)} vehicles" if records else "0", self.cell_style)]
        ]
        t_summary = Table(summary_data, colWidths=[240, 300])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0D9488")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 15))

        # Density log table
        table_rows = [
            [Paragraph("ID", self.header_style), Paragraph("Road Approach", self.header_style), Paragraph("Timestamp (UTC)", self.header_style),
             Paragraph("Occupancy (%)", self.header_style), Paragraph("Classification", self.header_style),
             Paragraph("Queue", self.header_style), Paragraph("Direction", self.header_style)]
        ]

        for r in records[:30]:
            rname = r.road_name or f"Cam #{r.camera_id}"
            table_rows.append([
                Paragraph(str(r.id), self.cell_style),
                Paragraph(rname[:18], self.cell_style),
                Paragraph(r.timestamp.strftime("%Y-%m-%d %H:%M") if r.timestamp else "", self.cell_style),
                Paragraph(f"{r.traffic_density:.1f}%", self.cell_style),
                Paragraph(classify_density(r.traffic_density), self.cell_style),
                Paragraph(str(r.queue_length), self.cell_style),
                Paragraph(r.direction or "Southbound", self.cell_style)
            ])

        t_records = Table(table_rows, colWidths=[35, 125, 95, 80, 85, 60, 60])
        t_records.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#111827")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_records)

        doc.build(story)
        return path

    # -------------------------------------------------------------------------
    # REPORT 4: Traffic Incident Report
    # -------------------------------------------------------------------------
    def generate_incidents_csv(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"traffic_incidents_road_{camera_id or 'all'}_{int(time.time())}.csv"
        path = settings.REPORTS_DIR / filename

        incidents = self._get_incidents(date_from, date_to, camera_id=camera_id)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Report", "Traffic Incident & Safety Audit Report"])
            writer.writerow(["Target Road / Approach", self._get_road_label(camera_id)])
            writer.writerow(["Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
            writer.writerow(["Date Range", f"{date_from or 'All'} to {date_to or 'All'}"])
            writer.writerow([])
            writer.writerow(["Incident ID", "Road / Approach", "Incident Type", "Severity", "Track ID", "Timestamp (UTC)", "Status", "Description"])
            for inc in incidents:
                writer.writerow([
                    inc.id,
                    inc.road_name or self._get_road_label(inc.camera_id),
                    inc.incident_type,
                    inc.severity,
                    inc.vehicle_track_id or "N/A",
                    inc.timestamp.strftime("%Y-%m-%d %H:%M:%S") if inc.timestamp else "",
                    inc.status,
                    inc.description
                ])

        return path

    def generate_incidents_pdf(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"traffic_incidents_road_{camera_id or 'all'}_{int(time.time())}.pdf"
        path = settings.REPORTS_DIR / filename

        incidents = self._get_incidents(date_from, date_to, camera_id=camera_id)
        doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        story.append(Paragraph("REPORT 4: Traffic Incident Report", self.title_style))
        story.append(Paragraph(f"<b>Target Road:</b> {self._get_road_label(camera_id)}", self.meta_style))
        story.append(Paragraph(f"Detected safety violations and traffic anomalies. Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", self.subtitle_style))
        story.append(Spacer(1, 10))

        # Incident Breakdown
        total_inc = len(incidents)
        ww_count = sum(1 for i in incidents if i.incident_type == "WRONG_WAY")
        st_count = sum(1 for i in incidents if i.incident_type == "STOPPED_VEHICLE")
        resolved = sum(1 for i in incidents if i.status == "RESOLVED")

        summary_data = [
            [Paragraph("Incident Classification", self.header_style), Paragraph("Count", self.header_style)],
            [Paragraph("Target Road Approach", self.cell_style), Paragraph(self._get_road_label(camera_id), self.cell_style)],
            [Paragraph("Total Incidents Logged", self.cell_style), Paragraph(str(total_inc), self.cell_style)],
            [Paragraph("Wrong-Way Driving Incidents", self.cell_style), Paragraph(str(ww_count), self.cell_style)],
            [Paragraph("Stationary Vehicle Alerts", self.cell_style), Paragraph(str(st_count), self.cell_style)],
            [Paragraph("Resolved Incidents", self.cell_style), Paragraph(str(resolved), self.cell_style)]
        ]
        t_summary = Table(summary_data, colWidths=[270, 270])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#DC2626")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 15))

        # Incidents List Table
        table_rows = [
            [Paragraph("ID", self.header_style), Paragraph("Road Approach", self.header_style), Paragraph("Type", self.header_style),
             Paragraph("Severity", self.header_style), Paragraph("Track", self.header_style),
             Paragraph("Time (UTC)", self.header_style), Paragraph("Status", self.header_style)]
        ]

        for inc in incidents[:30]:
            rname = inc.road_name or f"Cam #{inc.camera_id}"
            table_rows.append([
                Paragraph(str(inc.id), self.cell_style),
                Paragraph(rname[:18], self.cell_style),
                Paragraph(inc.incident_type, self.cell_style),
                Paragraph(inc.severity, self.cell_style),
                Paragraph(str(inc.vehicle_track_id or "-"), self.cell_style),
                Paragraph(inc.timestamp.strftime("%Y-%m-%d %H:%M") if inc.timestamp else "", self.cell_style),
                Paragraph(inc.status, self.cell_style)
            ])

        t_records = Table(table_rows, colWidths=[30, 130, 95, 60, 45, 95, 85])
        t_records.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1F2937")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_records)

        doc.build(story)
        return path

    # -------------------------------------------------------------------------
    # REPORT 5: Video Analysis Report
    # -------------------------------------------------------------------------
    def generate_video_analysis_csv(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"video_analysis_road_{camera_id or 'all'}_{int(time.time())}.csv"
        path = settings.REPORTS_DIR / filename

        analyses = self._get_analyses(date_from, date_to, camera_id=camera_id)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Report", "Video Processing & AI Audit Report"])
            writer.writerow(["Target Road / Approach", self._get_road_label(camera_id)])
            writer.writerow(["Generated At", datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")])
            writer.writerow(["Date Range", f"{date_from or 'All'} to {date_to or 'All'}"])
            writer.writerow([])
            writer.writerow(["Analysis ID", "Video Name", "Status", "Total Frames", "Processed Frames", "Processing Time (s)", "Average FPS", "Started At", "Completed At"])
            for a in analyses:
                vname = a.video.video_name if a.video else "N/A"
                writer.writerow([
                    a.id,
                    vname,
                    a.processing_status,
                    a.total_frames,
                    a.processed_frames,
                    a.processing_time,
                    a.average_fps,
                    a.started_at.strftime("%Y-%m-%d %H:%M:%S") if a.started_at else "",
                    a.completed_at.strftime("%Y-%m-%d %H:%M:%S") if a.completed_at else ""
                ])

        return path

    def generate_video_analysis_pdf(self, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> Path:
        filename = f"video_analysis_road_{camera_id or 'all'}_{int(time.time())}.pdf"
        path = settings.REPORTS_DIR / filename

        analyses = self._get_analyses(date_from, date_to, camera_id=camera_id)
        doc = SimpleDocTemplate(str(path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        story.append(Paragraph("REPORT 5: Video Analysis Report", self.title_style))
        story.append(Paragraph(f"<b>Target Road:</b> {self._get_road_label(camera_id)}", self.meta_style))
        story.append(Paragraph(f"Execution performance and vehicle detection audit. Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}", self.subtitle_style))
        story.append(Spacer(1, 10))

        table_rows = [
            [Paragraph("ID", self.header_style), Paragraph("Video Name", self.header_style),
             Paragraph("Status", self.header_style), Paragraph("Frames", self.header_style),
             Paragraph("Duration", self.header_style), Paragraph("Avg FPS", self.header_style),
             Paragraph("Completed", self.header_style)]
        ]

        for a in analyses[:30]:
            vname = a.video.video_name if a.video else "N/A"
            table_rows.append([
                Paragraph(str(a.id), self.cell_style),
                Paragraph(vname[:22] + "..." if len(vname) > 22 else vname, self.cell_style),
                Paragraph(a.processing_status, self.cell_style),
                Paragraph(f"{a.processed_frames}/{a.total_frames}", self.cell_style),
                Paragraph(f"{a.processing_time:.1f}s", self.cell_style),
                Paragraph(str(a.average_fps), self.cell_style),
                Paragraph(a.completed_at.strftime("%Y-%m-%d %H:%M") if a.completed_at else "-", self.cell_style)
            ])

        t_records = Table(table_rows, colWidths=[35, 140, 75, 75, 65, 55, 95])
        t_records.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#7C3AED")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_records)

        doc.build(story)
        return path

    # -------------------------------------------------------------------------
    # Helper Data Queries
    # -------------------------------------------------------------------------
    def _get_traffic_records(self, date_from, date_to, camera_id=None):
        q = self.db.query(TrafficRecord)
        if camera_id:
            q = q.filter(TrafficRecord.camera_id == camera_id)
        if date_from:
            q = q.filter(TrafficRecord.timestamp >= date_from)
        if date_to:
            q = q.filter(TrafficRecord.timestamp <= date_to)
        return q.order_by(TrafficRecord.timestamp.desc()).all()

    def _get_incidents(self, date_from, date_to, camera_id=None):
        q = self.db.query(Incident)
        if camera_id:
            q = q.filter(Incident.camera_id == camera_id)
        if date_from:
            q = q.filter(Incident.timestamp >= date_from)
        if date_to:
            q = q.filter(Incident.timestamp <= date_to)
        return q.order_by(Incident.timestamp.desc()).all()

    def _get_analyses(self, date_from, date_to, camera_id=None):
        q = self.db.query(Analysis)
        if camera_id:
            analysis_ids = [r[0] for r in self.db.query(TrafficRecord.analysis_id).filter(TrafficRecord.camera_id == camera_id).distinct().all()]
            if analysis_ids:
                q = q.filter(Analysis.id.in_(analysis_ids))
        if date_from:
            q = q.filter(Analysis.started_at >= date_from)
        if date_to:
            q = q.filter(Analysis.started_at <= date_to)
        return q.order_by(Analysis.id.desc()).all()

