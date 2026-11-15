import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.vision.tracker import TrackedVehicle
from app.vision.incident_detector import IncidentDetector

def test_wrong_way_detection():
    detector = IncidentDetector(wrong_way_frames_thresh=5, wrong_way_cosine_thresh=-0.5)

    # Permitted lane direction is DOWN [0, 1]
    lane_permitted_vec = (0.0, 1.0)

    # Vehicle traveling UP (wrong way)
    vehicle = TrackedVehicle(track_id=101, class_id=2, class_name="car", bbox=[100, 300, 150, 360], frame_idx=1)

    # Simulate movement upwards for 6 frames
    triggered_alert = None
    for f in range(2, 8):
        new_bbox = [100, 300 - f * 10, 150, 360 - f * 10]
        vehicle.update(new_bbox, f)
        is_ww, alert = detector.check_wrong_way(vehicle, lane_permitted_vec)
        if is_ww:
            triggered_alert = alert

    # Should trigger wrong-way alert
    assert vehicle.is_wrong_way is True
    assert triggered_alert is not None
    assert triggered_alert["alert_type"] == "WRONG_WAY"
    assert triggered_alert["track_id"] == 101

def test_stopped_vehicle_detection():
    detector = IncidentDetector(stopped_frames_thresh=10, stopped_disp_thresh_px=5.0)

    # Vehicle stationary in active lane
    vehicle = TrackedVehicle(track_id=202, class_id=2, class_name="car", bbox=[200, 200, 250, 250], frame_idx=1)

    triggered_alert = None
    for f in range(2, 15):
        # Barely moving (jitter of 0.1px)
        new_bbox = [200.05, 200.05, 250.05, 250.05]
        vehicle.update(new_bbox, f)
        is_stopped, alert = detector.check_stopped_vehicle(vehicle, in_stop_permitted_zone=False)
        if is_stopped:
            triggered_alert = alert

    assert vehicle.is_stopped is True
    assert triggered_alert is not None
    assert triggered_alert["alert_type"] == "STOPPED_VEHICLE"
    assert "Potential stopped vehicle" in triggered_alert["description"]

def test_stopped_vehicle_permitted_zone_immunity():
    detector = IncidentDetector(stopped_frames_thresh=10, stopped_disp_thresh_px=5.0)

    # Vehicle stopped at red light / stop zone -> should NOT trigger incident alert
    vehicle = TrackedVehicle(track_id=303, class_id=2, class_name="car", bbox=[200, 200, 250, 250], frame_idx=1)

    for f in range(2, 15):
        new_bbox = [200, 200, 250, 250]
        vehicle.update(new_bbox, f)
        is_stopped, alert = detector.check_stopped_vehicle(vehicle, in_stop_permitted_zone=True)

    assert is_stopped is False
    assert alert is None
