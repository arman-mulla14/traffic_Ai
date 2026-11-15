from typing import List, Dict, Any, Tuple
from app.core.config import settings

class DensityEstimator:
    """
    Computes traffic density, queue length, occupancy, and congestion level.
    Provides full mathematical explanations for college grading and transparency.
    """
    def __init__(
        self,
        low_thresh: int = settings.LOW_CONGESTION_THRESHOLD,
        med_thresh: int = settings.MEDIUM_CONGESTION_THRESHOLD
    ):
        self.low_thresh = low_thresh
        self.med_thresh = med_thresh

    def estimate_lane_density(
        self,
        active_vehicles: List[Dict[str, Any]],
        lane_area_px: float = 640.0 * 480.0,
        lane_length_meters: float = 80.0
    ) -> Dict[str, Any]:
        vehicle_count = len(active_vehicles)
        
        # Calculate bounding box total area
        total_vehicle_area_px = 0.0
        for v in active_vehicles:
            bbox = v.get("bbox", [0, 0, 0, 0])
            w = max(0.0, bbox[2] - bbox[0])
            h = max(0.0, bbox[3] - bbox[1])
            total_vehicle_area_px += (w * h)

        # Occupancy ratio
        occupancy_ratio = min(1.0, total_vehicle_area_px / max(1.0, lane_area_px))

        # Density score (vehicles per 100 meters equivalent)
        density_per_100m = (vehicle_count / max(1.0, lane_length_meters)) * 100.0

        # Queue length estimation (count of stopped/slow moving vehicles in queue formation)
        queue_count = sum(1 for v in active_vehicles if v.get("is_stopped", False) or v.get("speed", 50.0) < 5.0)

        # Classification based on measured thresholds
        if vehicle_count <= self.low_thresh and occupancy_ratio < 0.20:
            congestion_level = "LOW"
            explanation = (
                f"Classified as LOW congestion: observed {vehicle_count} active vehicle(s) (threshold <= {self.low_thresh}) "
                f"with road occupancy ratio of {occupancy_ratio:.1%} (< 20%). Traffic is flowing smoothly."
            )
        elif vehicle_count <= self.med_thresh and occupancy_ratio < 0.45:
            congestion_level = "MEDIUM"
            explanation = (
                f"Classified as MEDIUM congestion: observed {vehicle_count} active vehicles (range {self.low_thresh+1}-{self.med_thresh}) "
                f"with road occupancy ratio of {occupancy_ratio:.1%}. Moderate vehicle platooning observed."
            )
        else:
            congestion_level = "HIGH"
            explanation = (
                f"Classified as HIGH congestion: observed {vehicle_count} active vehicles (threshold > {self.med_thresh}) "
                f"or road occupancy ratio {occupancy_ratio:.1%} (> 45%). Potential bottleneck / queue forming."
            )

        return {
            "vehicle_count": vehicle_count,
            "occupancy_ratio": round(occupancy_ratio, 3),
            "density_score": round(density_per_100m, 1),
            "estimated_queue_length": queue_count,
            "congestion_level": congestion_level,
            "calculation_details": explanation
        }
