from typing import List, Tuple, Optional, Set
import numpy as np

def ccw(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float]) -> bool:
    """Checks whether the points A, B, C are listed in a counterclockwise order."""
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def intersect(A: Tuple[float, float], B: Tuple[float, float], C: Tuple[float, float], D: Tuple[float, float]) -> bool:
    """Return true if line segments AB and CD intersect."""
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

class VirtualCountingLine:
    """
    Manages a virtual line on the road and counts unique vehicles crossing it.
    Strictly prevents duplicate vehicle counting across consecutive frames.
    """
    def __init__(self, line_id: str, p1: Tuple[float, float], p2: Tuple[float, float], name: str = "Main Counting Line"):
        self.line_id = line_id
        self.p1 = p1  # (x1, y1)
        self.p2 = p2  # (x2, y2)
        self.name = name
        self.counted_track_ids: Set[int] = set()
        self.total_count = 0
        self.class_counts = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0
        }

    def check_crossing(self, track_id: int, trajectory: List[Tuple[float, float, int]], class_name: str) -> bool:
        """
        Determines if the vehicle trajectory has crossed the counting line in the recent frames.
        Returns True only ONCE per unique track_id.
        """
        if track_id in self.counted_track_ids:
            return False  # Already counted! Enforce unique counting rule

        if len(trajectory) < 2:
            return False

        # Check intersection with the most recent step or steps
        # Look back up to last 4 steps to handle potential high-speed frames
        lookback = min(len(trajectory) - 1, 4)
        for i in range(len(trajectory) - lookback, len(trajectory)):
            prev_pt = (trajectory[i - 1][0], trajectory[i - 1][1])
            curr_pt = (trajectory[i][0], trajectory[i][1])

            if intersect(self.p1, self.p2, prev_pt, curr_pt):
                self.counted_track_ids.add(track_id)
                self.total_count += 1
                if class_name in self.class_counts:
                    self.class_counts[class_name] += 1
                else:
                    self.class_counts[class_name] = 1
                return True

        return False

    def reset(self):
        self.counted_track_ids.clear()
        self.total_count = 0
        for k in self.class_counts:
            self.class_counts[k] = 0
