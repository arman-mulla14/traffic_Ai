import torch
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
from ultralytics import YOLO
from app.core.config import settings

class YOLODetector:
    _instance: Optional['YOLODetector'] = None

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.DEFAULT_MODEL_PATH
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.is_loaded = False
        self.load_model()

    @classmethod
    def get_instance(cls) -> 'YOLODetector':
        if cls._instance is None:
            cls._instance = YOLODetector()
        return cls._instance

    def load_model(self):
        try:
            print(f"[YOLODetector] Loading model from {self.model_path} on {self.device}...")
            self.model = YOLO(self.model_path)
            self.is_loaded = True
            print(f"[YOLODetector] Model successfully loaded on {self.device}.")
        except Exception as e:
            print(f"[YOLODetector] ERROR loading YOLO model: {e}")
            self.is_loaded = False
            self.model = None

    def detect_vehicles(self, frame: np.ndarray, conf_threshold: float = 0.35) -> List[Dict[str, Any]]:
        """
        Runs real YOLO inference on a single BGR frame.
        Filters strictly for vehicle classes (car, motorcycle, bus, truck).
        Returns bounding boxes [x1, y1, x2, y2], class_id, class_name, and confidence.
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("YOLO model is not loaded. Cannot run inference.")

        # Run inference
        results = self.model.predict(
            source=frame,
            conf=conf_threshold,
            device=self.device,
            verbose=False
        )

        detections = []
        if not results:
            return detections

        r = results[0]
        boxes = r.boxes
        if boxes is None:
            return detections

        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            # Check if class is a supported vehicle
            if cls_id in settings.VEHICLE_CLASS_NAMES:
                conf = float(boxes.conf[i].item())
                xyxy = boxes.xyxy[i].cpu().numpy().tolist()
                detections.append({
                    "class_id": cls_id,
                    "class_name": settings.VEHICLE_CLASS_NAMES[cls_id],
                    "confidence": round(conf, 3),
                    "bbox": [round(coord, 1) for coord in xyxy]
                })

        return detections

    def track_vehicles(self, frame: np.ndarray, conf_threshold: float = 0.35, persist: bool = True) -> List[Dict[str, Any]]:
        """
        Runs YOLO tracking using ByteTrack on a video frame.
        Returns tracked vehicles with unique track IDs.
        """
        if not self.is_loaded or self.model is None:
            raise RuntimeError("YOLO model is not loaded. Cannot run tracking.")

        results = self.model.track(
            source=frame,
            conf=conf_threshold,
            device=self.device,
            classes=settings.VEHICLE_CLASS_IDS,
            persist=persist,
            verbose=False,
            tracker="bytetrack.yaml"
        )

        tracks = []
        if not results:
            return tracks

        r = results[0]
        boxes = r.boxes
        if boxes is None or len(boxes) == 0:
            return tracks

        for i in range(len(boxes)):
            cls_id = int(boxes.cls[i].item())
            if cls_id in settings.VEHICLE_CLASS_NAMES:
                conf = float(boxes.conf[i].item())
                xyxy = boxes.xyxy[i].cpu().numpy().tolist()
                track_id = int(boxes.id[i].item()) if boxes.id is not None else None
                
                tracks.append({
                    "track_id": track_id,
                    "class_id": cls_id,
                    "class_name": settings.VEHICLE_CLASS_NAMES[cls_id],
                    "confidence": round(conf, 3),
                    "bbox": [round(coord, 1) for coord in xyxy]
                })

        return tracks
