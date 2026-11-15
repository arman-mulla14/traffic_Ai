import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from app.core.config import settings

class EmergencyVehicleDetector:
    """
    Emergency Vehicle Detection Module.
    Standard COCO dataset does NOT differentiate ambulances or fire engines from general vans/trucks.
    This module looks for a dedicated fine-tuned model at `models/emergency_detector.pt`.
    If absent, it strictly and transparently reports "Model unavailable" as per project integrity rules.
    """
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = Path(model_path or settings.EMERGENCY_MODEL_PATH)
        self.model = None
        self.is_loaded = False
        self.status_message = "Initializing"
        self.check_and_load_model()

    def check_and_load_model(self):
        if not self.model_path.exists():
            self.is_loaded = False
            self.model = None
            self.status_message = (
                "Model unavailable. A custom fine-tuned weights file (e.g. models/emergency_detector.pt) "
                "is required to classify ambulances and fire engines. Standard COCO weights do not support emergency classification."
            )
            return

        try:
            from ultralytics import YOLO
            self.model = YOLO(str(self.model_path))
            self.is_loaded = True
            self.status_message = "Custom emergency vehicle detector loaded successfully."
        except Exception as e:
            self.is_loaded = False
            self.model = None
            self.status_message = f"Failed to load custom emergency model: {str(e)}"

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_available": self.is_loaded,
            "model_path": str(self.model_path),
            "status_message": self.status_message,
            "supported_classes": ["ambulance", "fire_engine"] if self.is_loaded else []
        }

    def detect_emergency(self, frame: np.ndarray, conf_threshold: float = 0.4) -> List[Dict[str, Any]]:
        if not self.is_loaded or self.model is None:
            return []

        results = self.model.predict(source=frame, conf=conf_threshold, verbose=False)
        detections = []
        if not results:
            return detections

        r = results[0]
        boxes = r.boxes
        if boxes is None:
            return detections

        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            cls_name = r.names.get(cls_id, f"class_{cls_id}")
            conf = float(boxes.conf[i].item())
            xyxy = boxes.xyxy[i].cpu().numpy().tolist()
            detections.append({
                "class_id": cls_id,
                "class_name": cls_name,
                "confidence": round(conf, 3),
                "bbox": [round(c, 1) for c in xyxy]
            })

        return detections
