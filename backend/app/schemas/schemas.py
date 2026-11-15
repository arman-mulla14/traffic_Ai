from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, model_validator, ConfigDict

# Camera Schemas
class CameraCreate(BaseModel):
    camera_name: str
    location: str
    road_name: Optional[str] = None
    direction: Optional[str] = "Northbound"
    speed_limit: Optional[int] = 60
    camera_type: str = "CCTV"
    stream_url: Optional[str] = None
    status: str = "ACTIVE"

class CameraUpdate(BaseModel):
    camera_name: Optional[str] = None
    location: Optional[str] = None
    road_name: Optional[str] = None
    direction: Optional[str] = None
    speed_limit: Optional[int] = None
    camera_type: Optional[str] = None
    stream_url: Optional[str] = None
    status: Optional[str] = None

class CameraResponse(BaseModel):
    id: int
    camera_name: str
    location: str
    road_name: Optional[str] = None
    direction: Optional[str] = "Northbound"
    speed_limit: Optional[int] = 60
    camera_type: str
    stream_url: Optional[str] = None
    status: str
    created_at: datetime
    name: Optional[str] = None

    @model_validator(mode="after")
    def sync_names(self) -> "CameraResponse":
        if not self.name and self.camera_name:
            self.name = self.camera_name
        elif not self.camera_name and self.name:
            self.camera_name = self.name
        return self

    model_config = ConfigDict(from_attributes=True)

# Video Schemas
class VideoUrlCreate(BaseModel):
    url: str
    video_name: Optional[str] = None
    download_offline: bool = False

class CameraStreamUpdate(BaseModel):
    stream_url: Optional[str] = None
    video_id: Optional[int] = None
    camera_name: Optional[str] = None
    location: Optional[str] = None

class VideoResponse(BaseModel):
    id: int
    video_name: str
    file_path: str
    file_size: int
    duration: float
    status: str
    uploaded_at: datetime
    # Backward compatible fields
    filename: Optional[str] = None
    original_name: Optional[str] = None
    duration_seconds: Optional[float] = None
    frame_count: Optional[int] = None

    def __init__(self, **data):
        if "video_name" in data:
            data.setdefault("filename", data["video_name"])
            data.setdefault("original_name", data["video_name"])
        if "duration" in data:
            data.setdefault("duration_seconds", data["duration"])
        super().__init__(**data)

    model_config = ConfigDict(from_attributes=True)

# Analysis Schemas
class AnalysisCreate(BaseModel):
    video_id: int

class AnalysisResponse(BaseModel):
    id: int
    video_id: int
    video_name: Optional[str] = None
    processing_status: str
    total_frames: int
    processed_frames: int
    processing_time: float
    average_fps: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: Optional[str] = None  # alias for processing_status

    def __init__(self, **data):
        if "processing_status" in data:
            data.setdefault("status", data["processing_status"])
        elif "status" in data:
            data.setdefault("processing_status", data["status"])
        super().__init__(**data)

    model_config = ConfigDict(from_attributes=True)

# Traffic Record Schemas
class TrafficRecordResponse(BaseModel):
    id: int
    analysis_id: int
    camera_id: Optional[int] = None
    road_name: Optional[str] = None
    timestamp: datetime
    car_count: int
    motorcycle_count: int
    bus_count: int
    truck_count: int
    pedestrian_count: Optional[int] = 0
    total_vehicles: int
    traffic_density: float
    queue_length: int
    direction: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Incident Schemas
class IncidentResponse(BaseModel):
    id: int
    analysis_id: int
    camera_id: Optional[int] = None
    road_name: Optional[str] = None
    incident_type: str
    description: str
    severity: str
    vehicle_track_id: Optional[int] = None
    timestamp: datetime
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class IncidentResolve(BaseModel):
    status: str = "RESOLVED"

# Signal Schemas
class SignalOptimizeRequest(BaseModel):
    intersection_name: Optional[str] = "Intersection Alpha"
    approach_n_count: Optional[int] = None
    approach_s_count: Optional[int] = None
    approach_e_count: Optional[int] = None
    approach_w_count: Optional[int] = None
    cycle_time: Optional[int] = 120
    min_green: Optional[int] = 10
    max_green: Optional[int] = 60

class SignalPlanResponse(BaseModel):
    id: Optional[int] = None
    intersection_name: str
    timestamp: datetime
    approach_n_green: int
    approach_s_green: int
    approach_e_green: int
    approach_w_green: int
    baseline_n_green: int
    baseline_s_green: int
    baseline_e_green: int
    baseline_w_green: int
    cycle_time: int
    estimated_delay_reduction_pct: float
    is_simulation: bool = True
    reasoning: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# Lane Schemas
class LaneResponse(BaseModel):
    id: int
    camera_id: int
    name: str
    approach: str
    permitted_direction: str
    is_active: bool = True
    current_density: Optional[float] = 0.0
    current_vehicles: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)

# Prediction Schemas
class PredictionItem(BaseModel):
    target_timestamp: str
    horizon_minutes: int
    approach: str
    predicted_volume: int
    predicted_density: float
    confidence_interval_low: float
    confidence_interval_high: float
    congestion_level: str

class PredictionResponse(BaseModel):
    status: str  # "VALID" or "INSUFFICIENT_DATA"
    message: str
    model_version: str
    r2_score: Optional[float] = None
    mae: Optional[float] = None
    samples_count: Optional[int] = 0
    predictions: List[PredictionItem] = []

# Dashboard Schemas
class DashboardSummaryResponse(BaseModel):
    total_vehicles: int
    total_videos: int
    total_analyses: int
    avg_density: float
    density_classification: str
    total_incidents: int
    cars_count: int
    motorcycles_count: int
    buses_count: int
    trucks_count: int
