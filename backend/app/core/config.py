import os
from pathlib import Path
from dataclasses import dataclass, field

# Root directory of the repository
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

@dataclass
class Settings:
    PROJECT_NAME: str = "AI-Based Traffic Management System"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Server settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Paths
    BASE_DIR: Path = BASE_DIR
    STORAGE_DIR: Path = BASE_DIR / "storage"
    UPLOAD_DIR: Path = BASE_DIR / "storage" / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "storage" / "processed"
    REPORTS_DIR: Path = BASE_DIR / "storage" / "reports"
    MODELS_DIR: Path = BASE_DIR / "models"
    FRONTEND_DIR: Path = BASE_DIR / "frontend"

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/traffic_system.db"

    # AI Model configuration
    DEFAULT_MODEL_PATH: str = str(BASE_DIR / "models" / "yolov8n.pt")
    EMERGENCY_MODEL_PATH: str = str(BASE_DIR / "models" / "emergency_detector.pt")
    CONFIDENCE_THRESHOLD: float = 0.35
    IOU_THRESHOLD: float = 0.45

    # Supported COCO detection class mappings (Humans/Pedestrians + Vehicles)
    # Class IDs: 0: pedestrian/person, 2: car, 3: motorcycle, 5: bus, 7: truck
    VEHICLE_CLASS_IDS: list[int] = field(default_factory=lambda: [0, 2, 3, 5, 7])
    VEHICLE_CLASS_NAMES: dict[int, str] = field(default_factory=lambda: {
        0: "pedestrian",
        2: "car",
        3: "motorcycle",
        5: "bus",
        7: "truck"
    })
    PEDESTRIAN_CONFIDENCE_THRESHOLD: float = 0.15

    # Congestion thresholds (vehicles in monitored scene / flow)
    LOW_CONGESTION_THRESHOLD: int = 5
    MEDIUM_CONGESTION_THRESHOLD: int = 15

    # Signal Optimization parameters (Webster / Equal Saturation)
    MIN_GREEN_SECONDS: int = 10
    MAX_GREEN_SECONDS: int = 60
    YELLOW_CLEARANCE_SECONDS: int = 4
    ALL_RED_CLEARANCE_SECONDS: int = 2
    DEFAULT_CYCLE_SECONDS: int = 120

    # Incident thresholds
    WRONG_WAY_MIN_FRAMES: int = 8
    WRONG_WAY_COSINE_THRESHOLD: float = -0.5  # Angle > 120 degrees opposing permitted lane vector
    STOPPED_VEHICLE_MIN_FRAMES: int = 45  # At 15-30 fps, approx 2-3 seconds stationary
    STOPPED_DISPLACEMENT_MAX_PX: float = 12.0

    # Upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 300 * 1024 * 1024  # 300 MB
    ALLOWED_VIDEO_EXTENSIONS: set[str] = field(default_factory=lambda: {".mp4", ".avi", ".mov", ".mkv"})

settings = Settings()

# Ensure directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
settings.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
settings.MODELS_DIR.mkdir(parents=True, exist_ok=True)
