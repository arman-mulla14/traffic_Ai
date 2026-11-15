import cv2
import time
import threading
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime

from app.ai.yolo_detector import YOLODetector
from app.vision.tracker import MultiObjectTracker
from app.vision.counting_line import VirtualCountingLine
from app.vision.incident_detector import IncidentDetector
from app.vision.density_estimator import DensityEstimator
from app.db.session import SessionLocal
from app.db.models import Camera, Alert, TrafficMetric

class CameraStreamManager:
    """
    Manages live camera streams (webcam 0, RTSP, or IP camera HTTP).
    Runs genuine frame capture, YOLO detection, tracking, and metric calculation in background thread.
    Exposes latest processed JPEG frame and latest analytics metrics.
    Strictly verifies connection: Never pretends disconnected camera is online!
    """
    _instances: Dict[int, 'CameraStreamManager'] = {}
    _lock = threading.Lock()

    def __init__(self, camera_id: int, stream_url: str):
        self.camera_id = camera_id
        self.stream_url = stream_url
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.cap: Optional[cv2.VideoCapture] = None
        
        self.latest_frame_jpeg: Optional[bytes] = None
        self.latest_metrics: Dict[str, Any] = {
            "status": "DISCONNECTED",
            "fps": 0.0,
            "vehicle_count": 0,
            "class_counts": {"car": 0, "motorcycle": 0, "bus": 0, "truck": 0},
            "congestion_level": "LOW",
            "density_score": 0.0,
            "occupancy_ratio": 0.0,
            "explanation": "No active stream connected.",
            "last_error": None
        }

        self.detector = YOLODetector.get_instance()
        self.tracker = MultiObjectTracker(max_missed_frames=20)
        self.incident_detector = IncidentDetector()
        self.density_estimator = DensityEstimator()
        self.counting_line: Optional[VirtualCountingLine] = None

    @classmethod
    def get_or_create(cls, camera_id: int, stream_url: str) -> 'CameraStreamManager':
        with cls._lock:
            if camera_id not in cls._instances:
                cls._instances[camera_id] = CameraStreamManager(camera_id, stream_url)
            return cls._instances[camera_id]

    def start(self) -> Dict[str, Any]:
        if self.is_running:
            return {"status": "ALREADY_RUNNING", "message": "Camera stream is already active."}

        # Validate connection first
        src = 0 if self.stream_url in ["0", "webcam", "default"] else self.stream_url
        try:
            test_cap = cv2.VideoCapture(int(src) if str(src).isdigit() else src)
            if not test_cap.isOpened():
                test_cap.release()
                self._update_db_status("DISCONNECTED", last_error=f"Cannot open stream source: {self.stream_url}")
                return {"status": "ERROR", "message": f"Failed to connect to stream source '{self.stream_url}'."}
            ret, _ = test_cap.read()
            test_cap.release()
            if not ret:
                self._update_db_status("DISCONNECTED", last_error="Connected but failed to read initial frame.")
                return {"status": "ERROR", "message": "Stream opened but returned no frames."}
        except Exception as e:
            self._update_db_status("ERROR", last_error=str(e))
            return {"status": "ERROR", "message": f"Connection exception: {str(e)}"}

        self.is_running = True
        self._update_db_status("CONNECTED", last_error=None)
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return {"status": "CONNECTED", "message": "Camera stream started successfully."}

    def stop(self) -> Dict[str, Any]:
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        self._update_db_status("DISCONNECTED", last_error=None)
        self.latest_metrics["status"] = "DISCONNECTED"
        self.latest_frame_jpeg = None
        return {"status": "STOPPED", "message": "Camera stream stopped."}

    def reconnect(self) -> Dict[str, Any]:
        self.stop()
        time.sleep(0.5)
        return self.start()

    def _update_db_status(self, status: str, last_error: Optional[str] = None):
        db = SessionLocal()
        try:
            cam = db.query(Camera).filter(Camera.id == self.camera_id).first()
            if cam:
                cam.status = status
                cam.last_error = last_error
                cam.is_active = (status == "CONNECTED")
                db.commit()
        except Exception as e:
            print(f"[CameraStreamManager] Error updating DB status: {e}")
        finally:
            db.close()

    def _capture_loop(self):
        src = 0 if self.stream_url in ["0", "webcam", "default"] else self.stream_url
        self.cap = cv2.VideoCapture(int(src) if str(src).isdigit() else src)
        frame_idx = 0
        last_metric_save = time.time()

        try:
            while self.is_running and self.cap.isOpened():
                t0 = time.time()
                ret, frame = self.cap.read()
                if not ret:
                    self._update_db_status("DISCONNECTED", last_error="Lost connection to video source during streaming.")
                    self.latest_metrics["status"] = "DISCONNECTED"
                    self.latest_metrics["last_error"] = "Lost stream connection."
                    break

                frame_idx += 1
                h, w = frame.shape[:2]

                if self.counting_line is None:
                    line_y = int(h * 0.6)
                    self.counting_line = VirtualCountingLine("live_cam_line", (0, line_y), (w, line_y), "Live Road Gate")

                # Run YOLO inference
                detections = self.detector.detect_vehicles(frame, conf_threshold=0.35)
                active_tracks = self.tracker.update_from_detections(detections, frame_idx)

                active_vehicle_dicts = []
                for trk in active_tracks:
                    crossed = self.counting_line.check_crossing(trk.track_id, trk.trajectory, trk.class_name)
                    if crossed:
                        trk.is_counted = True

                    # Incident checks
                    is_ww, ww_alert = self.incident_detector.check_wrong_way(trk, (0.0, 1.0))
                    if is_ww and ww_alert:
                        self._record_live_alert(ww_alert)

                    is_st, st_alert = self.incident_detector.check_stopped_vehicle(trk)
                    if is_st and st_alert:
                        self._record_live_alert(st_alert)

                    active_vehicle_dicts.append({
                        "bbox": trk.bbox,
                        "class_name": trk.class_name,
                        "is_stopped": trk.is_stopped,
                        "speed": trk.calculate_average_speed_px(30.0)
                    })

                # Compute density
                density = self.density_estimator.estimate_lane_density(active_vehicle_dicts, lane_area_px=float(w * h))
                t1 = time.time()
                fps = round(1.0 / max(0.001, t1 - t0), 1)

                # Annotate frame
                self._draw_overlay(frame, active_tracks, int(h * 0.6), w, fps)

                # Encode JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                self.latest_frame_jpeg = buffer.tobytes()

                # Update live metrics dictionary
                self.latest_metrics = {
                    "status": "CONNECTED",
                    "fps": fps,
                    "vehicle_count": density["vehicle_count"],
                    "class_counts": self.counting_line.class_counts,
                    "unique_crossed_total": self.counting_line.total_count,
                    "congestion_level": density["congestion_level"],
                    "density_score": density["density_score"],
                    "occupancy_ratio": density["occupancy_ratio"],
                    "explanation": density["calculation_details"],
                    "last_error": None
                }

                # Save metric to DB every 10 seconds
                if time.time() - last_metric_save >= 10.0:
                    last_metric_save = time.time()
                    self._record_live_metric(density)

                # Moderate loop FPS to 25 FPS
                elapsed = time.time() - t0
                if elapsed < 0.04:
                    time.sleep(0.04 - elapsed)

        except Exception as e:
            print(f"[CameraStreamManager] Error in capture loop: {e}")
            self._update_db_status("ERROR", last_error=str(e))
        finally:
            if self.cap:
                self.cap.release()
            self.is_running = False

    def _draw_overlay(self, frame, tracks, line_y, width, fps):
        # Draw Gate
        cv2.line(frame, (0, line_y), (width, line_y), (255, 255, 0), 2)
        total_crossed = self.counting_line.total_count if self.counting_line else 0
        cv2.putText(frame, f"LIVE GATE: {total_crossed} Unique Vehicles Crossed", (15, line_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        # Draw HUD banner
        cv2.putText(frame, f"FPS: {fps} | Active Vehicles: {len(tracks)}", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        for trk in tracks:
            x1, y1, x2, y2 = [int(c) for c in trk.bbox]
            color = (0, 0, 255) if trk.is_wrong_way else ((0, 165, 255) if trk.is_stopped else (0, 255, 0))
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"#{trk.track_id} {trk.class_name}", (x1, max(18, y1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    def _record_live_alert(self, alert_data: Dict[str, Any]):
        db = SessionLocal()
        try:
            alert = Alert(
                camera_id=self.camera_id,
                track_id=alert_data.get("track_id"),
                alert_type=alert_data["alert_type"],
                severity=alert_data["severity"],
                description=alert_data["description"]
            )
            db.add(alert)
            db.commit()
        except Exception as e:
            print(f"[CameraStreamManager] Failed to record alert: {e}")
        finally:
            db.close()

    def _record_live_metric(self, density_data: Dict[str, Any]):
        db = SessionLocal()
        try:
            metric = TrafficMetric(
                camera_id=self.camera_id,
                vehicle_count=density_data["vehicle_count"],
                flow_rate_per_min=float(self.counting_line.total_count) if self.counting_line else 0.0,
                occupancy_ratio=density_data["occupancy_ratio"],
                estimated_queue_length=density_data["estimated_queue_length"],
                density_score=density_data["density_score"],
                congestion_level=density_data["congestion_level"],
                calculation_details=density_data["calculation_details"]
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            print(f"[CameraStreamManager] Failed to record metric: {e}")
        finally:
            db.close()
