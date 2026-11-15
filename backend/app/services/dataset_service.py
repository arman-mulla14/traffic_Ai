import os
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.config import settings

DATASETS_DIR = settings.STORAGE_DIR / "datasets"
DATASET_CSV = DATASETS_DIR / "traffic_telemetry_dataset.csv"

CSV_HEADERS = [
    "timestamp",
    "hour_of_day",
    "day_of_week",
    "camera_id",
    "camera_name",
    "total_vehicles",
    "cars",
    "motorcycles",
    "buses",
    "trucks",
    "pedestrians",
    "density_pct",
    "congestion_level",
    "avg_speed_kmh",
    "co2_kg_per_hr",
    "incident_flag"
]

class DatasetService:
    """
    Continuous Telemetry Dataset Collector & Exporter.
    Logs multi-modal computer vision telemetry (vehicles, pedestrians, speeds, density, carbon footprint)
    into structured CSV & JSON datasets for machine learning model training.
    """

    @classmethod
    def ensure_dataset_file(cls):
        DATASETS_DIR.mkdir(parents=True, exist_ok=True)
        if not DATASET_CSV.exists() or os.path.getsize(DATASET_CSV) == 0:
            with open(DATASET_CSV, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)
            # Pre-seed with realistic baseline data if brand new
            cls._seed_initial_history()

    @classmethod
    def _seed_initial_history(cls):
        """Seeds realistic historical observations across peak and off-peak hours for instant training."""
        now = time.time()
        rows = []
        import random
        # Generate 120 historical hours of data points
        for i in range(120, 0, -1):
            ts = now - (i * 1800)  # every 30 mins
            dt = datetime.fromtimestamp(ts)
            hour = dt.hour
            dow = dt.weekday()
            
            # Rush hours 8-10 AM and 5-8 PM
            is_rush = (8 <= hour <= 10) or (17 <= hour <= 20)
            base_vol = random.randint(22, 38) if is_rush else random.randint(8, 18)
            cars = int(base_vol * random.uniform(0.60, 0.75))
            motos = int(base_vol * random.uniform(0.12, 0.22))
            buses = random.randint(1, 3)
            trucks = random.randint(1, 4)
            peds = random.randint(2, 9) if is_rush else random.randint(0, 3)
            total = cars + motos + buses + trucks
            density = min(98.0, round((total / 40.0) * 100.0, 1))

            if density < 35.0:
                cong = "FREE_FLOW"
                speed = round(random.uniform(50.0, 68.0), 1)
            elif density < 65.0:
                cong = "MODERATE"
                speed = round(random.uniform(32.0, 48.0), 1)
            elif density < 85.0:
                cong = "CONGESTED"
                speed = round(random.uniform(18.0, 30.0), 1)
            else:
                cong = "HEAVY_JAM"
                speed = round(random.uniform(6.0, 15.0), 1)

            co2 = round((total * 0.18) + (total * (60.0 - speed) * 0.005), 2)
            has_inc = 1 if (density > 75 and random.random() < 0.2) else 0

            rows.append([
                dt.strftime("%Y-%m-%d %H:%M:%S"),
                hour,
                dow,
                1,
                "Junction Alpha - North Approach",
                total,
                cars,
                motos,
                buses,
                trucks,
                peds,
                density,
                cong,
                speed,
                co2,
                has_inc
            ])

        with open(DATASET_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    @classmethod
    def record_observation(cls, data: Dict[str, Any]):
        """Records a single live telemetry observation into the dataset."""
        cls.ensure_dataset_file()
        now = datetime.utcnow()
        row = [
            now.strftime("%Y-%m-%d %H:%M:%S"),
            now.hour,
            now.weekday(),
            data.get("camera_id", 1),
            data.get("camera_name", "Surveillance Camera"),
            data.get("total_vehicles", 0),
            data.get("cars", 0),
            data.get("motorcycles", 0),
            data.get("buses", 0),
            data.get("trucks", 0),
            data.get("pedestrians", 0),
            data.get("density_pct", 0.0),
            data.get("congestion_level", "MODERATE"),
            data.get("avg_speed_kmh", 40.0),
            data.get("co2_kg_per_hr", 5.2),
            data.get("incident_flag", 0)
        ]
        with open(DATASET_CSV, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    @classmethod
    def get_dataset_stats(cls, camera_id: Optional[int] = None) -> Dict[str, Any]:
        """Returns statistics on the collected dataset, with optional camera filtering."""
        cls.ensure_dataset_file()
        total_rows = 0
        total_peds = 0
        total_vehicles = 0
        with open(DATASET_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if camera_id is not None and str(r.get("camera_id", "")).strip() != str(camera_id).strip():
                    continue
                total_rows += 1
                try:
                    total_peds += int(r.get("pedestrians", 0))
                    total_vehicles += int(r.get("total_vehicles", 0))
                except Exception:
                    pass

        return {
            "camera_id": camera_id,
            "total_samples": total_rows,
            "total_records": total_rows,
            "total_vehicles_recorded": total_vehicles,
            "total_vehicles": total_vehicles,
            "total_pedestrians_recorded": total_peds,
            "total_pedestrians": total_peds,
            "dataset_file_path": str(DATASET_CSV),
            "file_size_kb": round(os.path.getsize(DATASET_CSV) / 1024.0, 1),
            "last_updated": datetime.fromtimestamp(os.path.getmtime(DATASET_CSV)).strftime("%Y-%m-%d %H:%M:%S")
        }
