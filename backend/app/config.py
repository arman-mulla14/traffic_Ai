from pathlib import Path
import os

# Prevent ultralytics network check delay
os.environ["YOLO_OFFLINE"] = "1"
os.environ["YOLO_VERBOSE"] = "False"

# Root directory of the repository (traffic_Ai)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings:
    PROJECT_NAME: str = "AI-Based Traffic Management System"
    VERSION: str = "2.0.0"
    DEBUG: bool = True

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", 8000))

    # Base paths
    BASE_DIR: Path = BASE_DIR
    STORAGE_DIR: Path = BASE_DIR / "storage"
    UPLOAD_DIR: Path = BASE_DIR / "storage" / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "storage" / "processed"
    REPORTS_DIR: Path = BASE_DIR / "storage" / "reports"
    MODELS_DIR: Path = BASE_DIR / "models"
    FRONTEND_DIR: Path = BASE_DIR / "frontend"

    # SQLite Database URL
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/traffic_system.db")

    # AI Model configuration
    MODEL_PATH: Path = BASE_DIR / "models" / "yolov8n.pt"
    CONFIDENCE_THRESHOLD: float = 0.25
    PEDESTRIAN_CONFIDENCE_THRESHOLD: float = 0.15
    PEDESTRIAN_STRICT_DETECTION: bool = True
    IOU_THRESHOLD: float = 0.45

    # Supported COCO detection class mappings (Humans/Pedestrians + Vehicles)
    VEHICLE_CLASS_IDS: list[int] = [0, 2, 3, 5, 7]
    VEHICLE_CLASS_NAMES: dict[int, str] = {
        0: "pedestrian",
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck"
    }

    # Density thresholds (Percentage occupancy)
    DENSITY_LOW_MAX: float = 30.0
    DENSITY_MODERATE_MAX: float = 60.0
    DENSITY_HIGH_MAX: float = 80.0

    # Incident thresholds
    WRONG_WAY_MIN_FRAMES: int = 8
    WRONG_WAY_COSINE_THRESHOLD: float = -0.5
    STOPPED_VEHICLE_MIN_FRAMES: int = 45
    STOPPED_DISP_THRESHOLD_PX: float = 15.0

    def ensure_directories(self):
        """Ensure all required runtime storage directories exist."""
        for d in [self.STORAGE_DIR, self.UPLOAD_DIR, self.PROCESSED_DIR, self.REPORTS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
