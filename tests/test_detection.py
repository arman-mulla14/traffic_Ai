import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import numpy as np
import cv2
from app.ai.yolo_detector import YOLODetector

def test_yolo_detector_initialization():
    detector = YOLODetector.get_instance()
    assert detector.is_loaded is True
    assert detector.model is not None
    assert detector.device in ["cpu", "cuda"]

def test_yolo_detection_on_frame():
    detector = YOLODetector.get_instance()
    # Create test BGR frame (480x640)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (120, 120, 120)  # Neutral road asphalt color

    # Draw synthetic road and simulated vehicle shapes
    cv2.rectangle(frame, (200, 180), (380, 300), (40, 40, 200), -1)  # Red box
    cv2.circle(frame, (230, 300), 20, (10, 10, 10), -1)  # Wheels
    cv2.circle(frame, (350, 300), 20, (10, 10, 10), -1)

    # Run inference (should return a list, empty or with detected objects)
    detections = detector.detect_vehicles(frame, conf_threshold=0.20)
    assert isinstance(detections, list)
    for det in detections:
        assert "class_id" in det
        assert "class_name" in det
        assert det["class_name"] in ["car", "motorcycle", "bus", "truck"]
        assert "confidence" in det
        assert len(det["bbox"]) == 4
        assert det["bbox"][0] < det["bbox"][2]
        assert det["bbox"][1] < det["bbox"][3]
