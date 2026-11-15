import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

class TrackedVehicle:
    def __init__(self, track_id: int, class_id: int, class_name: str, bbox: List[float], frame_idx: int):
        self.track_id = track_id
        self.class_id = class_id
        self.class_name = class_name
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.first_seen_frame = frame_idx
        self.last_seen_frame = frame_idx
        self.centroid = self._calc_centroid(bbox)
        # Store trajectory as list of (x, y, frame_idx)
        self.trajectory: List[Tuple[float, float, int]] = [(self.centroid[0], self.centroid[1], frame_idx)]
        self.is_counted = False
        self.crossed_line_frame: Optional[int] = None
        self.wrong_way_counter = 0
        self.is_wrong_way = False
        self.stopped_counter = 0
        self.is_stopped = False
        self.lane_id: Optional[int] = None

    def _calc_centroid(self, bbox: List[float]) -> Tuple[float, float]:
        x1, y1, x2, y2 = bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def update(self, bbox: List[float], frame_idx: int):
        self.bbox = bbox
        self.last_seen_frame = frame_idx
        new_centroid = self._calc_centroid(bbox)
        self.centroid = new_centroid
        self.trajectory.append((new_centroid[0], new_centroid[1], frame_idx))
        # Keep trajectory bounded to last 150 points for memory efficiency
        if len(self.trajectory) > 150:
            self.trajectory.pop(0)

    def get_displacement_over_frames(self, num_frames: int = 30) -> Tuple[float, float, float]:
        """
        Returns (dx, dy, total_distance) over the last num_frames.
        """
        if len(self.trajectory) < 2:
            return 0.0, 0.0, 0.0
        
        start_idx = max(0, len(self.trajectory) - num_frames)
        p_start = self.trajectory[start_idx]
        p_end = self.trajectory[-1]
        
        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]
        dist = math.hypot(dx, dy)
        return dx, dy, dist

    def calculate_average_speed_px(self, fps: float = 30.0) -> float:
        """
        Calculates average speed in pixels per second.
        """
        if len(self.trajectory) < 2:
            return 0.0
        total_dist = 0.0
        for i in range(1, len(self.trajectory)):
            p0 = self.trajectory[i - 1]
            p1 = self.trajectory[i]
            total_dist += math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        
        frame_span = max(1, self.trajectory[-1][2] - self.trajectory[0][2])
        time_sec = frame_span / fps
        return round(total_dist / time_sec, 1)

class MultiObjectTracker:
    """
    Integrates YOLO detections with unique tracking management.
    Handles track assignment, trajectory updates, and active lifespan.
    """
    def __init__(self, max_missed_frames: int = 30):
        self.tracks: Dict[int, TrackedVehicle] = {}
        self.next_internal_id = 1
        self.max_missed_frames = max_missed_frames

    def update_from_detections(self, detections: List[Dict[str, Any]], frame_idx: int) -> List[TrackedVehicle]:
        """
        Accepts detections (which may already have a YOLO track_id from ByteTrack, or bounding boxes).
        """
        active_track_ids = set()

        for det in detections:
            bbox = det["bbox"]
            cls_id = det["class_id"]
            cls_name = det["class_name"]
            yolo_id = det.get("track_id")

            # If YOLO tracker supplied an ID, use it directly
            if yolo_id is not None:
                track_id = yolo_id
            else:
                # Fallback to nearest centroid matching if no tracker ID
                track_id = self._match_or_create(bbox, cls_id, cls_name, frame_idx)

            if track_id in self.tracks:
                self.tracks[track_id].update(bbox, frame_idx)
            else:
                self.tracks[track_id] = TrackedVehicle(track_id, cls_id, cls_name, bbox, frame_idx)

            active_track_ids.add(track_id)

        # Cleanup lost tracks
        lost_ids = []
        for tid, trk in self.tracks.items():
            if frame_idx - trk.last_seen_frame > self.max_missed_frames:
                lost_ids.append(tid)

        for tid in lost_ids:
            del self.tracks[tid]

        return [self.tracks[tid] for tid in active_track_ids if tid in self.tracks]

    def _match_or_create(self, bbox: List[float], cls_id: int, cls_name: str, frame_idx: int) -> int:
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0

        best_id = None
        min_dist = 60.0  # Max pixel distance threshold for frame-to-frame association

        for tid, trk in self.tracks.items():
            if trk.class_id == cls_id and (frame_idx - trk.last_seen_frame) <= 5:
                dist = math.hypot(cx - trk.centroid[0], cy - trk.centroid[1])
                if dist < min_dist:
                    min_dist = dist
                    best_id = tid

        if best_id is not None:
            return best_id

        assigned_id = self.next_internal_id
        self.next_internal_id += 1
        return assigned_id

    def get_all_active_tracks(self) -> List[TrackedVehicle]:
        return list(self.tracks.values())
