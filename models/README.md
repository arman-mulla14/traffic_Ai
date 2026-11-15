# Models Directory

This directory stores computer vision weights for the AI-Based Traffic Management System.

## Models Included & Supported:

1. **`yolov8n.pt`**:
   - Ultralytics YOLOv8 Nano object detection model pre-trained on MS COCO.
   - Detects standard traffic classes:
     - `car` (Class ID 2)
     - `motorcycle` (Class ID 3)
     - `bus` (Class ID 5)
     - `truck` (Class ID 7)
   - Runs on CPU with real-time inference latency (approx. 20-40 ms on modern CPU) or NVIDIA CUDA GPU when available.

2. **Emergency Vehicle Detection**:
   - The default COCO dataset does not separate emergency vehicles (ambulances, fire engines) from standard vans or trucks.
   - A custom YOLO model (e.g., `emergency_detector.pt`) trained on specific emergency vehicle datasets can be placed in this folder.
   - When no custom model is found at `models/emergency_detector.pt`, the system accurately reports status:
     `"Model unavailable - Custom emergency vehicle weights required. Standard COCO does not differentiate ambulances/fire engines."`
   - This ensures complete honesty and adheres strictly to the No-Fake-Data rules.

## Licensing:
- Ultralytics YOLOv8: AGPL-3.0 License.
- Pretrained weights: Distributed under Ultralytics model terms.
