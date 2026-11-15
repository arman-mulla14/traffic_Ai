import math
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.config import settings
from app.database.models import TrafficRecord, Incident, Analysis, Video
from app.services.tracking_service import TrackedVehicle
from app.utils.helpers import classify_density

class TrafficService:
    """
    Traffic Density Calculation and Incident Detection Engine.
    Handles mathematical evaluation of road occupancy, queue length,
    wrong-way driving detection, and stationary vehicle detection.
    """

    @staticmethod
    def calculate_density(
        active_vehicles: List[TrackedVehicle],
        roi_area_px: float,
        fps: float = 30.0
    ) -> Dict[str, Any]:
        """
        Calculates occupancy percentage and queue estimate inside the region of interest.
        """
        vehicle_count = len(active_vehicles)
        total_vehicle_area = 0.0
        queue_count = 0

        for trk in active_vehicles:
            x1, y1, x2, y2 = trk.bbox
            w = max(0.0, x2 - x1)
            h = max(0.0, y2 - y1)
            total_vehicle_area += (w * h)

            # Count in queue if stopped or moving very slowly (<10px/s)
            dx, dy, dist = trk.get_displacement(lookback_frames=15)
            speed_px = (dist / max(1, 15)) * fps
            if trk.is_stopped or speed_px < 10.0:
                queue_count += 1

        # Occupancy percentage (0.0 to 100.0%)
        occupancy_pct = min(100.0, (total_vehicle_area / max(1.0, roi_area_px)) * 100.0)
        classification = classify_density(occupancy_pct)

        return {
            "vehicle_count": vehicle_count,
            "occupancy_pct": round(occupancy_pct, 1),
            "density_classification": classification,
            "queue_length": queue_count
        }

    @staticmethod
    def check_wrong_way(
        vehicle: TrackedVehicle,
        permitted_vector: Tuple[float, float] = (0.0, 1.0)
    ) -> Optional[Dict[str, Any]]:
        """
        Determines if a tracked vehicle is traveling counter to the permitted traffic vector.
        Requires minimum movement threshold (>25px) and negative cosine similarity (< -0.5).
        """
        if len(vehicle.trajectory) < settings.WRONG_WAY_MIN_FRAMES:
            return None

        dx, dy, dist = vehicle.get_displacement(lookback_frames=settings.WRONG_WAY_MIN_FRAMES)
        if dist < 25.0:
            return None  # Ignore negligible movement/jitter

        # Normalize displacement vector
        mv_x = dx / dist
        mv_y = dy / dist

        # Normalize permitted vector
        px, py = permitted_vector
        p_len = math.hypot(px, py)
        if p_len == 0:
            return None
        px /= p_len
        py /= p_len

        # Dot product gives cosine of angle
        cos_sim = mv_x * px + mv_y * py

        if cos_sim < settings.WRONG_WAY_COSINE_THRESHOLD:
            vehicle.wrong_way_counter += 1
            if vehicle.wrong_way_counter >= 2 and not vehicle.is_wrong_way:
                vehicle.is_wrong_way = True
                return {
                    "incident_type": "WRONG_WAY",
                    "severity": "CRITICAL",
                    "vehicle_track_id": vehicle.track_id,
                    "description": (
                        f"Wrong-way vehicle detected: Track #{vehicle.track_id} ({vehicle.class_name}) "
                        f"moving against designated traffic vector (cos: {cos_sim:.2f})."
                    )
                }
        else:
            vehicle.wrong_way_counter = max(0, vehicle.wrong_way_counter - 1)

        return None

    @staticmethod
    def check_stopped_vehicle(
        vehicle: TrackedVehicle
    ) -> Optional[Dict[str, Any]]:
        """
        Detects if a vehicle has remained stationary for longer than the configured threshold.
        """
        if len(vehicle.trajectory) < settings.STOPPED_VEHICLE_MIN_FRAMES:
            return None

        dx, dy, dist = vehicle.get_displacement(lookback_frames=settings.STOPPED_VEHICLE_MIN_FRAMES)

        if dist < settings.STOPPED_DISP_THRESHOLD_PX:
            vehicle.stationary_counter += 1
            if vehicle.stationary_counter >= 2 and not vehicle.is_stopped:
                vehicle.is_stopped = True
                return {
                    "incident_type": "STOPPED_VEHICLE",
                    "severity": "HIGH",
                    "vehicle_track_id": vehicle.track_id,
                    "description": (
                        f"Stationary vehicle alert: Track #{vehicle.track_id} ({vehicle.class_name}) "
                        f"stationary for > {settings.STOPPED_VEHICLE_MIN_FRAMES} frames."
                    )
                }
        else:
            vehicle.stationary_counter = max(0, vehicle.stationary_counter - 1)
            vehicle.is_stopped = False

        return None

    @staticmethod
    def get_traffic_summary(db: Session, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, camera_id: Optional[int] = None) -> dict:
        """Retrieves aggregated KPI metrics across completed analyses, with optional road/camera filtering."""
        from app.database.models import Camera
        q_records = db.query(TrafficRecord)
        q_incidents = db.query(Incident)
        q_analyses = db.query(Analysis).filter(Analysis.processing_status == "COMPLETED")

        road_info = None
        if camera_id is not None:
            q_records = q_records.filter(TrafficRecord.camera_id == camera_id)
            q_incidents = q_incidents.filter(Incident.camera_id == camera_id)
            cam = db.query(Camera).filter(Camera.id == camera_id).first()
            if cam:
                road_info = f"Road {cam.id}: {cam.camera_name}"

        if date_from:
            q_records = q_records.filter(TrafficRecord.timestamp >= date_from)
            q_incidents = q_incidents.filter(Incident.timestamp >= date_from)
            q_analyses = q_analyses.filter(Analysis.completed_at >= date_from)
        if date_to:
            q_records = q_records.filter(TrafficRecord.timestamp <= date_to)
            q_incidents = q_incidents.filter(Incident.timestamp <= date_to)
            q_analyses = q_analyses.filter(Analysis.completed_at <= date_to)

        total_analyses = q_analyses.count()
        total_incidents = q_incidents.count()

        agg = q_records.with_entities(
            func.sum(TrafficRecord.car_count),
            func.sum(TrafficRecord.motorcycle_count),
            func.sum(TrafficRecord.bus_count),
            func.sum(TrafficRecord.truck_count),
            func.sum(TrafficRecord.total_vehicles),
            func.avg(TrafficRecord.traffic_density)
        ).first()

        total_cars = agg[0] or 0
        total_motorcycles = agg[1] or 0
        total_buses = agg[2] or 0
        total_trucks = agg[3] or 0
        total_vehicles = agg[4] or 0
        avg_density = round(float(agg[5] or 0.0), 1)

        return {
            "camera_id": camera_id,
            "road_name": road_info or "All Roads (Full Intersection)",
            "total_analyses": total_analyses,
            "total_vehicles": total_vehicles,
            "total_cars": total_cars,
            "total_motorcycles": total_motorcycles,
            "total_buses": total_buses,
            "total_trucks": total_trucks,
            "avg_density": avg_density,
            "density_classification": classify_density(avg_density),
            "total_incidents": total_incidents
        }

