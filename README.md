---
title: AI Traffic Management System
emoji: 🚦
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# AI-Based Traffic Management System (Enterprise Master Edition)

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%2B%20Uvicorn-009688.svg)](https://fastapi.tiangolo.com/)
[![YOLOv8](https://img.shields.io/badge/Computer%20Vision-Ultralytics%20YOLOv8-FF385C.svg)](https://github.com/ultralytics/ultralytics)
[![Frontend](https://img.shields.io/badge/Frontend-Vanilla%20HTML5%20%2F%20CSS3%20%2F%20ES6%20JS-1675D1.svg)](#frontend)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2B%20SQLAlchemy-003B57.svg)](https://www.sqlite.org/)

An enterprise-grade, real-time Computer Vision and Intelligent Transportation System (ITS) built with FastAPI, SQLite, Ultralytics YOLOv8, Chart.js, and pure Vanilla JavaScript. The system monitors live surveillance feeds, processes uploaded traffic recordings, tracks vehicles across frames, classifies categories (Cars, Motorcycles, Buses, Trucks), detects safety anomalies (wrong-way driving, stationary vehicle hazards), calculates lane queue density, and generates authoritative PDF and CSV reports.

---

## 1. Exact Color System & Visual Architecture

The visual interface is built according to an enterprise design system:

```css
:root {
  --primary-navy: #12345A;
  --primary-blue: #2878D0;
  --active-blue: #1675D1;
  --success-green: #16A765;
  --background: #F4F7FB;
  --card-background: #FFFFFF;
  --text-primary: #172B4D;
  --text-secondary: #64748B;
  --border-color: #E2E8F0;
  --danger: #EF4444;
  --warning: #F59E0B;
}
```

- **Fixed Dark Navy Sidebar**: 260px width, deep navy (`#12345A`), active nav highlight in active blue (`#1675D1`), white icons, online status pulse indicator.
- **Top Navigation Bar**: Pristine white background (`#FFFFFF`), live system online badge, real-time clock, notifications dropdown, and administrator profile pill.
- **Card System**: Pure white cards (`#FFFFFF`) with subtle box shadows, 10px rounded corners, and thin `#E2E8F0` borders.

---

## 2. Page Directory & Functionality (All 8 Pages)

1. **Dashboard (`/` or `/frontend/index.html`)**:
   - **Row 1**: Welcome header, subtitle, date range filter, refresh button.
   - **Row 2**: 4 KPI cards (Total Vehicles Detected, Videos Processed, Average Traffic Density, Total Incidents).
   - **Row 3**: 3 Panels (Vehicle Category Distribution donut chart, Traffic Volume Trend line chart, Live Traffic Camera preview with live stats).
   - **Row 4**: 3 Panels (Recent Incidents table with resolve actions, System Status diagnostics, Quick Action shortcuts).

2. **Video Management (`/frontend/pages/video-management.html`)**:
   - Clean dashed drag-and-drop upload zone for MP4, AVI, MOV recordings.
   - White recorded videos table with duration, file size, upload date, status badges (`COMPLETED`, `PROCESSING`, `UPLOADED`).
   - One-click YOLOv8 batch processing and video preview modal.

3. **Live Monitoring (`/frontend/pages/live-monitoring.html`)**:
   - Camera selector dropdown and live MJPEG streaming (`/api/cameras/{id}/stream`).
   - HTML5 Canvas overlay rendering bounding boxes (`car`, `bus`, `truck`, `motorcycle`), tracking IDs, and tripwire counting lines.
   - Right statistics sidebar with real-time vehicle counts, density gauge, queue length, and camera specifications.
   - Controls: Stream Pause/Resume, Bounding Box Toggle, Snapshot, Fullscreen.

4. **Traffic Analytics (`/frontend/pages/traffic-analytics.html`)**:
   - 4 summary KPI cards (Peak Hourly Flow, Average Speed, Highest Density Spike, Heavy Vehicle Ratio).
   - Clean blue and green Chart.js visualizations (Hourly Volume line chart, Density timeline bar chart, Vehicle classification share doughnut).
   - Detailed traffic observation logs table with CSV export.

5. **Incident Management (`/frontend/pages/incident-management.html`)**:
   - Multi-criteria filter toolbar: Search input, Incident Type, Severity, and Status.
   - Incident register table with red, orange, and green status and severity badges.
   - Incident detail modal with narrative and one-click "Mark Resolved" action.

6. **Camera Management (`/frontend/pages/camera-management.html`)**:
   - 4 Camera status KPI cards (Total Cameras, Online Streams, Standby/Inactive, Offline Feeds).
   - White camera table with stream sources, camera types, and green/red online/offline badges.
   - Add Camera modal to register new CCTV, IP RTSP, or webcam streams (`POST /api/cameras`).
   - Test feed preview modal.

7. **Reports (`/frontend/pages/reports.html`)**:
   - 5 white report cards with blue icons:
     1. Daily Traffic Summary Report
     2. Vehicle Classification Breakdown
     3. Traffic Density & Congestion Audit
     4. Incident & Anomaly Safety Log
     5. Video Processing & AI Model Audit
   - Green **Download PDF** and **Download CSV** buttons for every module.
   - Date range selector and generated reports historical archive table.

8. **Settings (`/frontend/pages/settings.html`)**:
   - White settings panels with clean form controls.
   - YOLO model weights selection (`yolov8n.pt`, `yolov8s.pt`, `yolov8m.pt`).
   - Confidence threshold and IoU NMS threshold sliders.
   - Incident safety rules (Wrong-way sensitivity, stationary vehicle duration).
   - Blue "Save Configuration" button with green success confirmation alert.

---

## 3. Technology Stack

- **Backend**: Python 3.11+ / FastAPI / Uvicorn
- **AI & Vision**: Ultralytics YOLOv8 (PyTorch CPU & CUDA auto-detection)
- **Database**: SQLite with SQLAlchemy ORM (`traffic_system.db`)
- **Frontend**: Pure HTML5, CSS3, Vanilla ES6 JavaScript (Zero heavy frameworks)
- **Charts**: Chart.js 4.4+ (UMD)
- **Reporting**: ReportLab PDF and CSV engine

---

## 4. Running the Application

### Option A: Quick Launch (Windows)
Double click `start.bat` or run:
```bat
run.bat
```

### Option B: Manual Command Line
```powershell
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Launch FastAPI backend server
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to:
**`http://127.0.0.1:8000`**
