import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.vision.tracker import MultiObjectTracker, TrackedVehicle
from app.vision.counting_line import VirtualCountingLine, intersect

def test_line_intersection_math():
    # Line AB: horizontal from (0, 100) to (200, 100)
    A = (0.0, 100.0)
    B = (200.0, 100.0)

    # Segment CD: vertical crossing from (100, 50) to (100, 150) -> should intersect!
    C = (100.0, 50.0)
    D = (100.0, 150.0)
    assert intersect(A, B, C, D) is True

    # Segment EF: above line from (100, 20) to (100, 80) -> should NOT intersect
    E = (100.0, 20.0)
    F = (100.0, 80.0)
    assert intersect(A, B, E, F) is False

def test_unique_vehicle_counting_no_duplicates():
    # Setup counting line at y = 200
    counting_line = VirtualCountingLine(
        line_id="test_line",
        p1=(0.0, 200.0),
        p2=(640.0, 200.0)
    )

    track_id = 42
    class_name = "car"

    # Frame 1: Vehicle above line at y = 150
    trajectory = [(300.0, 150.0, 1)]
    assert counting_line.check_crossing(track_id, trajectory, class_name) is False
    assert counting_line.total_count == 0

    # Frame 2: Vehicle moves down to y = 180 (still hasn't crossed)
    trajectory.append((300.0, 180.0, 2))
    assert counting_line.check_crossing(track_id, trajectory, class_name) is False
    assert counting_line.total_count == 0

    # Frame 3: Vehicle crosses line to y = 220 -> FIRST TIME CROSSING!
    trajectory.append((300.0, 220.0, 3))
    assert counting_line.check_crossing(track_id, trajectory, class_name) is True
    assert counting_line.total_count == 1
    assert counting_line.class_counts["car"] == 1

    # Frame 4: Vehicle continues to y = 250 -> MUST NOT BE COUNTED AGAIN!
    trajectory.append((300.0, 250.0, 4))
    assert counting_line.check_crossing(track_id, trajectory, class_name) is False
    assert counting_line.total_count == 1  # Strictly enforces unique vehicle count rule

    # Frame 5: Vehicle continues to y = 280 -> STILL MUST NOT BE COUNTED AGAIN
    trajectory.append((300.0, 280.0, 5))
    assert counting_line.check_crossing(track_id, trajectory, class_name) is False
    assert counting_line.total_count == 1
