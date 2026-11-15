import math
from typing import List, Dict, Any, Optional, Tuple
from app.vision.tracker import TrackedVehicle

class IncidentDetector:
    """
    Detects traffic anomalies and safety incidents:
    - Wrong-Way Driving (vector direction vs permitted lane direction)
    - Stopped Vehicles (stationary duration check outside designated stop points)
    - Distinguishes potential stopped vehicles from confirmed accidents honestly.
    """
    def __init__(
        self,
        wrong_way_frames_thresh: int = 8,
        wrong_way_cosine_thresh: float = -0.5,
        stopped_frames_thresh: int = 45,
        stopped_disp_thresh_px: float = 12.0
    ):
        self.wrong_way_frames_thresh = wrong_way_frames_thresh
        self.wrong_way_cosine_thresh = wrong_way_cosine_thresh
        self.stopped_frames_thresh = stopped_frames_thresh
        self.stopped_disp_thresh_px = stopped_disp_thresh_px

    def check_wrong_way(
        self,
        vehicle: TrackedVehicle,
        lane_permitted_vector: Tuple[float, float]
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Calculates cosine similarity between vehicle displacement vector and lane direction vector.
        Requires sufficient displacement (>25px) and persistent counter to avoid false alarms.
        """
        # Need at least 8 trajectory points to establish stable heading
        if len(vehicle.trajectory) < self.wrong_way_frames_thresh:
            return False, None

        dx, dy, dist = vehicle.get_displacement_over_frames(num_frames=self.wrong_way_frames_thresh)
        if dist < 25.0:
            # Jitter or near-stationary vehicle should not trigger wrong-way alert
            return False, None

        # Normalized movement vector
        mv_x = dx / dist
        mv_y = dy / dist

        # Lane permitted vector normalization
        lx, ly = lane_permitted_vector
        lane_len = math.hypot(lx, ly)
        if lane_len == 0:
            return False, None
        lx /= lane_len
        ly /= lane_len

        # Dot product (cosine of angle between vectors)
        cos_sim = mv_x * lx + mv_y * ly

        if cos_sim < self.wrong_way_cosine_thresh:
            vehicle.wrong_way_counter += 1
            if vehicle.wrong_way_counter >= 2 and not vehicle.is_wrong_way:
                vehicle.is_wrong_way = True
                alert_data = {
                    "alert_type": "WRONG_WAY",
                    "severity": "CRITICAL",
                    "track_id": vehicle.track_id,
                    "class_name": vehicle.class_name,
                    "description": (
                        f"Wrong-way vehicle detected: Track #{vehicle.track_id} ({vehicle.class_name}) "
                        f"traveling opposing designated lane vector (cos similarity: {cos_sim:.2f})."
                    ),
                    "cosine_similarity": round(cos_sim, 2),
                    "centroid": vehicle.centroid
                }
                return True, alert_data
        else:
            vehicle.wrong_way_counter = max(0, vehicle.wrong_way_counter - 1)

        return False, None

    def check_stopped_vehicle(
        self,
        vehicle: TrackedVehicle,
        in_stop_permitted_zone: bool = False
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Detects if vehicle has been stationary for >= stopped_frames_thresh.
        If in a designated stop zone (like waiting for red signal), does not raise incident.
        Labels event as 'Potential stopped vehicle' per integrity guidelines.
        """
        if in_stop_permitted_zone:
            vehicle.stopped_counter = 0
            return False, None

        if len(vehicle.trajectory) < self.stopped_frames_thresh:
            return False, None

        dx, dy, dist = vehicle.get_displacement_over_frames(num_frames=self.stopped_frames_thresh)

        if dist <= self.stopped_disp_thresh_px:
            vehicle.stopped_counter += 1
            if vehicle.stopped_counter >= 2 and not vehicle.is_stopped:
                vehicle.is_stopped = True
                alert_data = {
                    "alert_type": "STOPPED_VEHICLE",
                    "severity": "HIGH",
                    "track_id": vehicle.track_id,
                    "class_name": vehicle.class_name,
                    "description": (
                        f"Potential stopped vehicle: Track #{vehicle.track_id} ({vehicle.class_name}) "
                        f"has remained stationary (displacement {dist:.1f}px over {self.stopped_frames_thresh} frames) "
                        f"in an active traffic lane."
                    ),
                    "displacement_px": round(dist, 1),
                    "centroid": vehicle.centroid
                }
                return True, alert_data
        else:
            vehicle.stopped_counter = max(0, vehicle.stopped_counter - 2)

        return False, None
