import os
from typing import List, Dict, Any, Optional
import numpy as np
import cv2
from ultralytics import YOLO
import torch

from app.config import settings

class DetectionService:
    """
    Singleton YOLOv8 Vehicle Detection Service.
    Loads Ultralytics YOLOv8 weights and performs real vehicle detection on frames.
    Filters exclusively for COCO classes: car (2), motorcycle (3), bus (5), truck (7).
    """
    _instance: Optional["DetectionService"] = None

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        model_path = str(settings.MODEL_PATH)

        if not os.path.exists(model_path):
            print(f"[DetectionService] YOLO weights not found at {model_path}, downloading yolov8n.pt...")
            self.model = YOLO("yolov8n.pt")
            # Save downloaded model to models/
            try:
                settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
                self.model.save(model_path)
            except Exception:
                pass
        else:
            self.model = YOLO(model_path)

        self.model.to(self.device)
        self.is_loaded = True
        print(f"[DetectionService] Initialized YOLOv8 on device={self.device}")

    @classmethod
    def get_instance(cls) -> "DetectionService":
        if cls._instance is None:
            cls._instance = DetectionService()
        return cls._instance

    def detect_vehicles(
        self,
        frame: np.ndarray,
        conf_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Runs YOLOv8 inference on a single BGR frame.
        Detects both vehicles and walking humans/pedestrians strictly.
        """
        conf = conf_threshold or settings.CONFIDENCE_THRESHOLD
        ped_conf = getattr(settings, "PEDESTRIAN_CONFIDENCE_THRESHOLD", 0.15)
        # Run inference with sensitive threshold to strictly detect walking pedestrians
        infer_conf = min(conf, ped_conf)
        iou = iou_threshold or settings.IOU_THRESHOLD

        # Run model inference without verbose print spam
        results = self.model.predict(
            source=frame,
            conf=infer_conf,
            iou=iou,
            classes=settings.VEHICLE_CLASS_IDS,
            verbose=False,
            device=self.device
        )

        detections = []
        if not results or len(results) == 0:
            return detections

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return detections

        for box in boxes:
            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            # Pedestrians strictly kept above ped_conf (0.15), vehicles above conf (0.25)
            if cls_id == 0 and confidence < ped_conf:
                continue
            elif cls_id != 0 and confidence < conf:
                continue

            xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            class_name = settings.VEHICLE_CLASS_NAMES.get(cls_id, "vehicle")

            detections.append({
                "class_id": cls_id,
                "class_name": class_name,
                "confidence": round(confidence, 3),
                "bbox": [float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])]
            })

        return detections

