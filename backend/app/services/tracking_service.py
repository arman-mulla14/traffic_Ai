import math
from typing import List, Dict, Any, Tuple, Optional, Set
import numpy as np

def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Checks whether points A, B, C are in counterclockwise order."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def line_segments_intersect(
    A: Tuple[float, float],
    B: Tuple[float, float],
    C: Tuple[float, float],
    D: Tuple[float, float]
) -> bool:
    """Returns True if line segment AB intersects line segment CD."""
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

def calculate_iou(boxA: List[float], boxB: List[float]) -> float:
    """Calculates Intersection over Union (IoU) of two bounding boxes [x1, y1, x2, y2]."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    inter_w = max(0.0, xB - xA)
    inter_h = max(0.0, yB - yA)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0

    boxA_area = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxB_area = max(1.0, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    return inter_area / float(boxA_area + boxB_area - inter_area)

class TrackedVehicle:
    """Represents a single persistent vehicle track with trajectory and motion statistics."""
    def __init__(self, track_id: int, class_id: int, class_name: str, bbox: List[float], frame_idx: int):
        self.track_id = track_id
        self.class_id = class_id
        self.class_name = class_name
        self.bbox = bbox
        self.first_seen_frame = frame_idx
        self.last_seen_frame = frame_idx
        self.centroid = self._calc_centroid(bbox)
        # Trajectory list of tuples: (x, y, frame_idx)
        self.trajectory: List[Tuple[float, float, int]] = [(self.centroid[0], self.centroid[1], frame_idx)]

        # Unique counting flag
        self.is_counted = False

        # Incident status
        self.wrong_way_counter = 0
        self.is_wrong_way = False
        self.stationary_counter = 0
        self.is_stopped = False

    def _calc_centroid(self, bbox: List[float]) -> Tuple[float, float]:
        return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)

    def update(self, bbox: List[float], frame_idx: int):
        self.bbox = bbox
        self.last_seen_frame = frame_idx
        new_centroid = self._calc_centroid(bbox)
        self.centroid = new_centroid
        self.trajectory.append((new_centroid[0], new_centroid[1], frame_idx))
        if len(self.trajectory) > 120:
            self.trajectory.pop(0)

    def get_displacement(self, lookback_frames: int = 15) -> Tuple[float, float, float]:
        """Calculates (dx, dy, distance) over the last lookback_frames."""
        if len(self.trajectory) < 2:
            return 0.0, 0.0, 0.0
        start_idx = max(0, len(self.trajectory) - lookback_frames)
        p0 = self.trajectory[start_idx]
        p1 = self.trajectory[-1]
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]
        dist = math.hypot(dx, dy)
        return dx, dy, dist

class VehicleTracker:
    """
    Centroid and IoU Multi-Object Tracker.
    Maintains persistent track IDs and updates trajectories across frames.
    """
    def __init__(self, max_missed_frames: int = 30, distance_threshold: float = 75.0):
        self.tracks: Dict[int, TrackedVehicle] = {}
        self.all_tracks: Dict[int, TrackedVehicle] = {}
        self.next_id = 1
        self.max_missed_frames = max_missed_frames
        self.distance_threshold = distance_threshold

    def update(self, detections: List[Dict[str, Any]], frame_idx: int) -> List[TrackedVehicle]:
        """
        Updates tracked vehicles with new detections.
        Matches using combination of IoU overlap and Euclidean centroid distance.
        """
        active_ids = list(self.tracks.keys())
        unmatched_detections = []

        if not active_ids:
            for det in detections:
                trk = TrackedVehicle(self.next_id, det["class_id"], det["class_name"], det["bbox"], frame_idx)
                self.tracks[self.next_id] = trk
                self.all_tracks[self.next_id] = trk
                self.next_id += 1
            return list(self.tracks.values())

        # Build distance / matching matrix
        matched_tracks = set()
        matched_dets = set()

        for det_idx, det in enumerate(detections):
            best_id = None
            best_score = float("inf")

            det_cx = (det["bbox"][0] + det["bbox"][2]) / 2.0
            det_cy = (det["bbox"][1] + det["bbox"][3]) / 2.0

            for t_id in active_ids:
                if t_id in matched_tracks:
                    continue
                trk = self.tracks[t_id]
                dist = math.hypot(det_cx - trk.centroid[0], det_cy - trk.centroid[1])
                iou = calculate_iou(det["bbox"], trk.bbox)

                # Prioritize IoU or close centroid distance
                if iou > 0.3 or dist < self.distance_threshold:
                    score = dist - (iou * 50.0)
                    if score < best_score:
                        best_score = score
                        best_id = t_id

            if best_id is not None:
                self.tracks[best_id].update(det["bbox"], frame_idx)
                self.all_tracks[best_id] = self.tracks[best_id]
                matched_tracks.add(best_id)
                matched_dets.add(det_idx)
            else:
                unmatched_detections.append(det)

        # Register new tracks for unmatched detections
        for det in unmatched_detections:
            trk = TrackedVehicle(self.next_id, det["class_id"], det["class_name"], det["bbox"], frame_idx)
            self.tracks[self.next_id] = trk
            self.all_tracks[self.next_id] = trk
            self.next_id += 1

        # Purge stale tracks that haven't been seen in max_missed_frames
        stale_ids = [
            t_id for t_id, trk in self.tracks.items()
            if (frame_idx - trk.last_seen_frame) > self.max_missed_frames
        ]
        for t_id in stale_ids:
            del self.tracks[t_id]

        return [trk for trk in self.tracks.values() if trk.last_seen_frame == frame_idx]

class VirtualCountingLine:
    """
    Virtual counting line that determines vehicle gate crossings.
    Enforces strictly unique vehicle counts using persistent track IDs.
    """
    def __init__(self, p1: Tuple[float, float], p2: Tuple[float, float]):
        self.p1 = p1
        self.p2 = p2
        self.counted_ids: Set[int] = set()
        self.class_counts: Dict[str, int] = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0,
            "pedestrian": 0
        }
        self.total_count = 0

    def check_crossing(self, vehicle: TrackedVehicle) -> bool:
        """
        Tests if vehicle trajectory crossed the counting line in recent frames.
        Returns True at most once per unique track_id.
        """
        if vehicle.track_id in self.counted_ids:
            return False

        if len(vehicle.trajectory) < 2:
            return False

        # Look back up to last 4 steps to handle fast motion
        steps = min(len(vehicle.trajectory) - 1, 4)
        for i in range(len(vehicle.trajectory) - steps, len(vehicle.trajectory)):
            pt_prev = (vehicle.trajectory[i - 1][0], vehicle.trajectory[i - 1][1])
            pt_curr = (vehicle.trajectory[i][0], vehicle.trajectory[i][1])

            if line_segments_intersect(self.p1, self.p2, pt_prev, pt_curr):
                self.counted_ids.add(vehicle.track_id)
                vehicle.is_counted = True
                self.total_count += 1
                cls_name = vehicle.class_name.lower()
                if cls_name in self.class_counts:
                    self.class_counts[cls_name] += 1
                else:
                    self.class_counts[cls_name] = 1
                return True

        return False

