import os
import cv2
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import SessionLocal
from app.database.models import Video, Analysis, TrafficRecord, Incident, Detection, VehicleTrack
from app.services.detection_service import DetectionService
from app.services.tracking_service import VehicleTracker, VirtualCountingLine, TrackedVehicle
from app.services.traffic_service import TrafficService

class VideoProcessingService:
    """
    Background Video Processing Worker.
    Executes the end-to-end computer vision pipeline:
    OpenCV -> YOLOv8 Detection -> Multi-Object Tracking -> Gate Counting ->
    Density & Queue Estimation -> Incident Detection -> Annotated Video Rendering ->
    Database Record Persistence.
    """

    @classmethod
    def process_analysis_background(cls, analysis_id: int):
        """Entry point for FastAPI BackgroundTasks."""
        db: Session = SessionLocal()
        try:
            worker = cls(db=db, analysis_id=analysis_id)
            worker.run()
        finally:
            db.close()

    def __init__(self, db: Session, analysis_id: int):
        self.db = db
        self.analysis_id = analysis_id
        self.detector = DetectionService.get_instance()

    def run(self):
        analysis = self.db.query(Analysis).filter(Analysis.id == self.analysis_id).first()
        if not analysis:
            print(f"[VideoProcessingService] Analysis ID {self.analysis_id} not found.")
            return

        video = self.db.query(Video).filter(Video.id == analysis.video_id).first()
        if not video or not os.path.exists(video.file_path):
            analysis.processing_status = "FAILED"
            self.db.commit()
            return

        cap = cv2.VideoCapture(video.file_path)
        if not cap.isOpened():
            analysis.processing_status = "FAILED"
            self.db.commit()
            return

        # Video geometry & timing properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        analysis.processing_status = "PROCESSING"
        analysis.total_frames = total_frames
        analysis.started_at = datetime.utcnow()
        video.status = "PROCESSING"
        self.db.commit()

        # Virtual Counting Line across middle of frame
        line_y = int(height * 0.55)
        counting_line = VirtualCountingLine(p1=(0, line_y), p2=(width, line_y))

        # Tracker instance
        tracker = VehicleTracker(max_missed_frames=30)

        # Output processed video writer
        settings.ensure_directories()
        output_filename = f"processed_{analysis.id}_{int(time.time())}.mp4"
        output_path = settings.PROCESSED_DIR / output_filename
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        frame_idx = 0
        start_time = time.time()
        roi_area_px = float(width * height)

        # Periodic record variables
        last_record_frame = 0
        recorded_incident_keys = set()

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1

                # Sample every 2nd frame if long video for faster inference, else every frame
                sample_step = 2 if total_frames > 600 else 1
                if frame_idx % sample_step != 0:
                    continue

                # 1. YOLOv8 Real Detection
                detections = self.detector.detect_vehicles(frame)

                # 2. Tracking Association
                active_tracks = tracker.update(detections, frame_idx)

                # 3. Check Counting Line & Incidents
                for trk in active_tracks:
                    counting_line.check_crossing(trk)

                    # Check wrong-way (default southbound permitted vector: [0, 1])
                    ww_incident = TrafficService.check_wrong_way(trk, permitted_vector=(0.0, 1.0))
                    if ww_incident:
                        inc_key = f"WW_{trk.track_id}"
                        if inc_key not in recorded_incident_keys:
                            recorded_incident_keys.add(inc_key)
                            inc = Incident(
                                analysis_id=self.analysis_id,
                                incident_type=ww_incident["incident_type"],
                                description=ww_incident["description"],
                                severity=ww_incident["severity"],
                                vehicle_track_id=ww_incident["vehicle_track_id"],
                                timestamp=datetime.utcnow(),
                                status="NEW"
                            )
                            self.db.add(inc)

                    # Check stopped vehicle
                    st_incident = TrafficService.check_stopped_vehicle(trk)
                    if st_incident:
                        inc_key = f"ST_{trk.track_id}"
                        if inc_key not in recorded_incident_keys:
                            recorded_incident_keys.add(inc_key)
                            inc = Incident(
                                analysis_id=self.analysis_id,
                                incident_type=st_incident["incident_type"],
                                description=st_incident["description"],
                                severity=st_incident["severity"],
                                vehicle_track_id=st_incident["vehicle_track_id"],
                                timestamp=datetime.utcnow(),
                                status="NEW"
                            )
                            self.db.add(inc)

                # 4. Periodic Traffic Record and Detection persistence (every 30 processed frames)
                density_info = TrafficService.calculate_density(active_tracks, roi_area_px, fps)

                if frame_idx - last_record_frame >= 30:
                    last_record_frame = frame_idx
                    t_record = TrafficRecord(
                        analysis_id=self.analysis_id,
                        timestamp=datetime.utcnow(),
                        car_count=counting_line.class_counts.get("car", 0),
                        motorcycle_count=counting_line.class_counts.get("motorcycle", 0),
                        bus_count=counting_line.class_counts.get("bus", 0),
                        truck_count=counting_line.class_counts.get("truck", 0),
                        pedestrian_count=counting_line.class_counts.get("pedestrian", 0),
                        total_vehicles=counting_line.total_count,
                        traffic_density=density_info["occupancy_pct"],
                        queue_length=density_info["queue_length"],
                        direction="Southbound"
                    )
                    self.db.add(t_record)

                    # Persist keyframe detections to SQLite detections table
                    for det in detections[:20]:
                        d_row = Detection(
                            analysis_id=self.analysis_id,
                            frame_number=frame_idx,
                            timestamp_ms=round((frame_idx / fps) * 1000.0, 2),
                            track_id=None,
                            class_id=det.get("class_id", 2),
                            class_name=det.get("class_name", "car"),
                            confidence=round(det.get("confidence", 0.8), 2),
                            bbox_x1=float(det["bbox"][0]),
                            bbox_y1=float(det["bbox"][1]),
                            bbox_x2=float(det["bbox"][2]),
                            bbox_y2=float(det["bbox"][3])
                        )
                        self.db.add(d_row)

                # 5. Render Visual Annotations
                self._render_overlay(frame, active_tracks, counting_line, line_y, width, density_info)
                out_writer.write(frame)

                # Update progress in DB periodically
                if frame_idx % 20 == 0:
                    elapsed = max(0.1, time.time() - start_time)
                    analysis.processed_frames = frame_idx
                    analysis.processing_time = round(elapsed, 2)
                    analysis.average_fps = round(frame_idx / elapsed, 1)
                    self.db.commit()

            # Video completed
            total_elapsed = max(0.1, time.time() - start_time)
            analysis.processing_status = "COMPLETED"
            analysis.processed_frames = frame_idx
            analysis.processing_time = round(total_elapsed, 2)
            analysis.average_fps = round(frame_idx / total_elapsed, 1)
            analysis.completed_at = datetime.utcnow()
            video.status = "COMPLETED"

            # Final summary record if none added
            final_record = TrafficRecord(
                analysis_id=self.analysis_id,
                timestamp=datetime.utcnow(),
                car_count=counting_line.class_counts.get("car", 0),
                motorcycle_count=counting_line.class_counts.get("motorcycle", 0),
                bus_count=counting_line.class_counts.get("bus", 0),
                truck_count=counting_line.class_counts.get("truck", 0),
                pedestrian_count=counting_line.class_counts.get("pedestrian", 0),
                total_vehicles=counting_line.total_count,
                traffic_density=density_info["occupancy_pct"],
                queue_length=density_info["queue_length"],
                direction="Southbound"
            )
            self.db.add(final_record)

            # Persist tracked vehicles into vehicle_tracks table
            for t_id, trk in tracker.all_tracks.items():
                v_trk = VehicleTrack(
                    analysis_id=self.analysis_id,
                    track_id=t_id,
                    class_name=trk.class_name,
                    first_seen_frame=trk.first_seen_frame,
                    last_seen_frame=trk.last_seen_frame,
                    is_counted=trk.is_counted,
                    is_wrong_way=trk.is_wrong_way,
                    is_stopped=trk.is_stopped
                )
                self.db.add(v_trk)

            self.db.commit()

            print(f"[VideoProcessingService] Completed analysis #{self.analysis_id}. "
                  f"Vehicles counted: {counting_line.total_count}, Processed frames: {frame_idx}")

        except Exception as e:
            print(f"[VideoProcessingService] Error during analysis #{self.analysis_id}: {e}")
            self.db.rollback()
            analysis.processing_status = "FAILED"
            video.status = "FAILED"
            self.db.commit()

        finally:
            cap.release()
            out_writer.release()

    def _render_overlay(
        self,
        frame,
        tracks: List[TrackedVehicle],
        counting_line: VirtualCountingLine,
        line_y: int,
        width: int,
        density_info: Dict[str, Any]
    ):
        """Draws bounding boxes, track IDs, category labels, counting line, and HUD info."""
        # 1. Virtual Counting Line (Cyan)
        cv2.line(frame, (0, line_y), (width, line_y), (255, 255, 0), 2)
        cv2.putText(
            frame,
            f"COUNTING LINE (Unique Total: {counting_line.total_count})",
            (15, line_y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 0),
            2
        )

        # 2. Vehicle Bounding Boxes & Trajectories
        for trk in tracks:
            x1, y1, x2, y2 = [int(v) for v in trk.bbox]
            if trk.class_name in ["pedestrian", "person"]:
                color = (214, 38, 208)  # Vibrant Magenta / Pink for Pedestrians
                label = f"#{trk.track_id} Pedestrian [Walking]"
            elif trk.is_wrong_way:
                color = (0, 0, 255)  # Red for wrong-way
                label = f"#{trk.track_id} {trk.class_name} [WRONG-WAY]"
            elif trk.is_stopped:
                color = (0, 165, 255)  # Orange for stopped
                label = f"#{trk.track_id} {trk.class_name} [STOPPED]"
            else:
                color = (0, 255, 0)  # Green for normal
                label = f"#{trk.track_id} {trk.class_name}"

            if trk.is_counted:
                label += " [COUNTED]"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # Draw trajectory path
            pts = trk.trajectory
            for i in range(1, min(len(pts), 12)):
                p1 = (int(pts[-i][0]), int(pts[-i][1]))
                p2 = (int(pts[-i-1][0]), int(pts[-i-1][1]))
                cv2.line(frame, p1, p2, color, 1)

        # 3. Top-left HUD Card (Real density and counts)
        cv2.rectangle(frame, (10, 10), (340, 140), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, 10), (340, 140), (80, 80, 80), 1)
        cv2.putText(frame, f"Density: {density_info['occupancy_pct']}% ({density_info['density_classification']})",
                    (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        cv2.putText(frame, f"Est. Queue: {density_info['queue_length']} vehicles",
                    (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
        cv2.putText(frame, f"Cars: {counting_line.class_counts.get('car', 0)} | Moto: {counting_line.class_counts.get('motorcycle', 0)}",
                    (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 220, 255), 1)
        cv2.putText(frame, f"Bus: {counting_line.class_counts.get('bus', 0)} | Truck: {counting_line.class_counts.get('truck', 0)}",
                    (20, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 220, 255), 1)
        cv2.putText(frame, f"Humans (Walking): {counting_line.class_counts.get('pedestrian', 0)}",
                    (20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (214, 38, 208), 1)

