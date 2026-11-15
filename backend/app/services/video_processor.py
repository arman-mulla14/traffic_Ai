import os
import cv2
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.models import Analysis, Video, VehicleTrack, TrafficMetric, Alert, Lane
from app.ai.yolo_detector import YOLODetector
from app.vision.tracker import MultiObjectTracker, TrackedVehicle
from app.vision.counting_line import VirtualCountingLine
from app.vision.incident_detector import IncidentDetector
from app.vision.density_estimator import DensityEstimator

class VideoProcessor:
    """
    Asynchronous Video Analysis Service.
    Processes uploaded traffic video files with YOLOv8, ByteTrack/centroid tracking,
    unique counting lines, incident alerts, and density measurement.
    """
    def __init__(self, db: Session, analysis_id: int):
        self.db = db
        self.analysis_id = analysis_id
        self.detector = YOLODetector.get_instance()
        self.tracker = MultiObjectTracker(max_missed_frames=30)
        self.incident_detector = IncidentDetector()
        self.density_estimator = DensityEstimator()

    def process(self):
        analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
        if not analysis:
            print(f"[VideoProcessor] Analysis #{self.analysis_id} not found.")
            return

        video = self.db.query(Video).filter(Video.id == analysis.video_id).first()
        if not video or not os.path.exists(video.file_path):
            analysis.status = "FAILED"
            analysis.error_message = f"Video file not found at {video.file_path if video else 'None'}"
            self.db.commit()
            return

        cap = cv2.VideoCapture(video.file_path)
        if not cap.isOpened():
            analysis.status = "FAILED"
            analysis.error_message = f"Corrupt or unreadable video file: {video.original_name}"
            self.db.commit()
            return

        # Retrieve video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        analysis.status = "PROCESSING"
        analysis.total_frames = total_frames
        analysis.started_at = datetime.utcnow()
        self.db.commit()

        # Setup virtual counting line across the middle of the frame
        line_y = int(height * 0.6)
        counting_line = VirtualCountingLine(
            line_id=f"line_analysis_{self.analysis_id}",
            p1=(0, line_y),
            p2=(width, line_y),
            name="Analysis Mid-Screen Gate"
        )

        # Default permitted direction (downward vector [0, 1])
        lane_permitted_vec = (0.0, 1.0)

        # Video Writer for processed output
        output_filename = f"processed_{analysis.id}_{int(time.time())}.mp4"
        output_path = settings.PROCESSED_DIR / output_filename
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        frame_idx = 0
        start_time = time.time()
        last_metric_frame = 0

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                t0 = time.time()

                # Process every 2nd frame if video is longer than 500 frames for speed, otherwise every frame
                sample_step = 2 if total_frames > 600 else 1
                if frame_idx % sample_step != 0:
                    continue

                # Run real YOLO inference
                detections = self.detector.detect_vehicles(frame, conf_threshold=0.35)

                # Update tracker with detections
                active_tracks = self.tracker.update_from_detections(detections, frame_idx)

                # Process tracks for counting, wrong-way and stopped incidents
                active_vehicle_dicts = []
                for trk in active_tracks:
                    # Check crossing counting line
                    crossed = counting_line.check_crossing(trk.track_id, trk.trajectory, trk.class_name)
                    if crossed:
                        trk.is_counted = True
                        trk.crossed_line_frame = frame_idx

                    # Check incidents
                    is_ww, ww_alert = self.incident_detector.check_wrong_way(trk, lane_permitted_vec)
                    if is_ww and ww_alert:
                        alert = Alert(
                            analysis_id=self.analysis_id,
                            track_id=trk.track_id,
                            alert_type=ww_alert["alert_type"],
                            severity=ww_alert["severity"],
                            description=ww_alert["description"]
                        )
                        self.db.add(alert)

                    is_st, st_alert = self.incident_detector.check_stopped_vehicle(trk)
                    if is_st and st_alert:
                        alert = Alert(
                            analysis_id=self.analysis_id,
                            track_id=trk.track_id,
                            alert_type=st_alert["alert_type"],
                            severity=st_alert["severity"],
                            description=st_alert["description"]
                        )
                        self.db.add(alert)

                    active_vehicle_dicts.append({
                        "bbox": trk.bbox,
                        "class_name": trk.class_name,
                        "is_stopped": trk.is_stopped,
                        "speed": trk.calculate_average_speed_px(fps)
                    })

                # Compute traffic density & congestion metrics periodically (e.g., every 30 frames)
                if frame_idx - last_metric_frame >= 30:
                    last_metric_frame = frame_idx
                    density_res = self.density_estimator.estimate_lane_density(
                        active_vehicle_dicts,
                        lane_area_px=float(width * height),
                        lane_length_meters=80.0
                    )
                    metric = TrafficMetric(
                        analysis_id=self.analysis_id,
                        vehicle_count=density_res["vehicle_count"],
                        flow_rate_per_min=round(counting_line.total_count * (60.0 / max(1.0, (frame_idx / fps))), 1),
                        occupancy_ratio=density_res["occupancy_ratio"],
                        estimated_queue_length=density_res["estimated_queue_length"],
                        density_score=density_res["density_score"],
                        congestion_level=density_res["congestion_level"],
                        calculation_details=density_res["calculation_details"]
                    )
                    self.db.add(metric)
                    analysis.congestion_level = density_res["congestion_level"]

                # Render overlays onto frame
                self._draw_overlay(frame, active_tracks, counting_line, line_y, width)
                out_writer.write(frame)

                # Calculate progress and FPS
                t1 = time.time()
                current_fps = round(1.0 / max(0.001, (t1 - t0)), 1)
                progress = min(100.0, round((frame_idx / max(1, total_frames)) * 100.0, 1))

                # Periodically update analysis row in DB
                if frame_idx % 25 == 0:
                    analysis.processed_frames = frame_idx
                    analysis.progress_pct = progress
                    analysis.current_fps = current_fps
                    analysis.unique_vehicles_total = counting_line.total_count
                    analysis.cars_count = counting_line.class_counts.get("car", 0)
                    analysis.motorcycles_count = counting_line.class_counts.get("motorcycle", 0)
                    analysis.buses_count = counting_line.class_counts.get("bus", 0)
                    analysis.trucks_count = counting_line.class_counts.get("truck", 0)
                    self.db.commit()

            # Finalize analysis
            analysis.status = "COMPLETED"
            analysis.progress_pct = 100.0
            analysis.processed_frames = frame_idx
            analysis.completed_at = datetime.utcnow()
            analysis.unique_vehicles_total = counting_line.total_count
            analysis.cars_count = counting_line.class_counts.get("car", 0)
            analysis.motorcycles_count = counting_line.class_counts.get("motorcycle", 0)
            analysis.buses_count = counting_line.class_counts.get("bus", 0)
            analysis.trucks_count = counting_line.class_counts.get("truck", 0)
            analysis.processed_video_path = f"/storage/processed/{output_filename}"

            # Save all recorded tracks to db for audit
            for trk in self.tracker.get_all_active_tracks():
                db_track = VehicleTrack(
                    analysis_id=self.analysis_id,
                    track_id=trk.track_id,
                    class_name=trk.class_name,
                    first_seen_frame=trk.first_seen_frame,
                    last_seen_frame=trk.last_seen_frame,
                    trajectory_points_json=json.dumps(trk.trajectory[:50]),
                    is_counted=trk.is_counted,
                    crossed_line_at_frame=trk.crossed_line_frame,
                    average_speed_px=trk.calculate_average_speed_px(fps),
                    is_wrong_way=trk.is_wrong_way,
                    is_stopped=trk.is_stopped
                )
                self.db.add(db_track)

            self.db.commit()
            print(f"[VideoProcessor] Analysis #{self.analysis_id} finished successfully. Unique vehicles: {counting_line.total_count}")

        except Exception as e:
            print(f"[VideoProcessor] Exception during analysis: {e}")
            analysis.status = "FAILED"
            analysis.error_message = str(e)
            self.db.commit()

        finally:
            cap.release()
            out_writer.release()

    def _draw_overlay(
        self,
        frame,
        tracks: List[TrackedVehicle],
        counting_line: VirtualCountingLine,
        line_y: int,
        width: int
    ):
        # Draw virtual counting line (Cyan line)
        cv2.line(frame, (0, line_y), (width, line_y), (255, 255, 0), 2)
        cv2.putText(frame, f"Counting Gate: {counting_line.total_count} Unique Crossed", (15, line_y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 0), 2)

        # Draw vehicle bounding boxes, track IDs, and trajectory tails
        for trk in tracks:
            x1, y1, x2, y2 = [int(v) for v in trk.bbox]
            color = (0, 255, 0)  # Green by default
            if trk.is_wrong_way:
                color = (0, 0, 255)  # Red for wrong-way
            elif trk.is_stopped:
                color = (0, 165, 255)  # Orange for stopped

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            label = f"ID #{trk.track_id} {trk.class_name}"
            if trk.is_counted:
                label += " [COUNTED]"

            cv2.putText(frame, label, (x1, max(18, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw trajectory tail
            pts = trk.trajectory
            for i in range(1, min(len(pts), 15)):
                pt1 = (int(pts[-i][0]), int(pts[-i][1]))
                pt2 = (int(pts[-i-1][0]), int(pts[-i-1][1]))
                cv2.line(frame, pt1, pt2, color, 1)
