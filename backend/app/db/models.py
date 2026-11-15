from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    stream_url = Column(String(500), nullable=False)  # "0" for local webcam or RTSP/HTTP URL
    location = Column(String(200), default="Main Intersection")
    is_active = Column(Boolean, default=True)
    status = Column(String(50), default="DISCONNECTED")  # CONNECTED, DISCONNECTED, ERROR
    last_error = Column(Text, nullable=True)
    fps = Column(Float, default=30.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lanes = relationship("Lane", back_populates="camera", cascade="all, delete-orphan")
    zones = relationship("Zone", back_populates="camera", cascade="all, delete-orphan")
    analyses = relationship("Analysis", back_populates="camera")
    alerts = relationship("Alert", back_populates="camera")

class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    duration_seconds = Column(Float, default=0.0)
    fps = Column(Float, default=0.0)
    frame_count = Column(Integer, default=0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    analyses = relationship("Analysis", back_populates="video", cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED, CANCELLED
    progress_pct = Column(Float, default=0.0)
    current_fps = Column(Float, default=0.0)
    total_frames = Column(Integer, default=0)
    processed_frames = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Aggregated Summary Counts
    unique_vehicles_total = Column(Integer, default=0)
    cars_count = Column(Integer, default=0)
    motorcycles_count = Column(Integer, default=0)
    buses_count = Column(Integer, default=0)
    trucks_count = Column(Integer, default=0)
    avg_speed_px = Column(Float, default=0.0)
    congestion_level = Column(String(20), default="LOW")
    
    # Stored processed video path if rendered
    processed_video_path = Column(String(500), nullable=True)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    video = relationship("Video", back_populates="analyses")
    camera = relationship("Camera", back_populates="analyses")
    tracks = relationship("VehicleTrack", back_populates="analysis", cascade="all, delete-orphan")
    traffic_metrics = relationship("TrafficMetric", back_populates="analysis", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="analysis", cascade="all, delete-orphan")

class Lane(Base):
    __tablename__ = "lanes"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    name = Column(String(100), nullable=False)  # e.g., "Lane 1 (Northbound)"
    approach = Column(String(10), default="NORTH")  # NORTH, SOUTH, EAST, WEST
    permitted_direction = Column(String(50), default="UP")  # UP, DOWN, LEFT, RIGHT
    direction_vector_json = Column(Text, default="[0, -1]")  # [dx, dy] normalized
    counting_line_json = Column(Text, default="[0, 200, 640, 200]")  # [x1, y1, x2, y2]
    created_at = Column(DateTime, default=datetime.utcnow)

    camera = relationship("Camera", back_populates="lanes")
    traffic_metrics = relationship("TrafficMetric", back_populates="lane")

class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    name = Column(String(100), nullable=False)
    zone_type = Column(String(50), default="OCCUPANCY")  # OCCUPANCY, NO_STOPPING, INTERSECTION_BOX
    polygon_coords_json = Column(Text, default="[]")  # [[x1, y1], [x2, y2], ...]
    created_at = Column(DateTime, default=datetime.utcnow)

    camera = relationship("Camera", back_populates="zones")

class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    frame_number = Column(Integer, nullable=False, index=True)
    timestamp_ms = Column(Float, default=0.0)
    track_id = Column(Integer, nullable=True, index=True)
    class_id = Column(Integer, nullable=False)
    class_name = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    bbox_x1 = Column(Float, nullable=False)
    bbox_y1 = Column(Float, nullable=False)
    bbox_x2 = Column(Float, nullable=False)
    bbox_y2 = Column(Float, nullable=False)

class VehicleTrack(Base):
    __tablename__ = "vehicle_tracks"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    track_id = Column(Integer, nullable=False, index=True)
    class_name = Column(String(50), nullable=False)
    first_seen_frame = Column(Integer, default=0)
    last_seen_frame = Column(Integer, default=0)
    trajectory_points_json = Column(Text, default="[]")  # [[x, y, frame], ...]
    is_counted = Column(Boolean, default=False)
    crossed_line_at_frame = Column(Integer, nullable=True)
    average_speed_px = Column(Float, default=0.0)
    is_wrong_way = Column(Boolean, default=False)
    is_stopped = Column(Boolean, default=False)
    lane_id = Column(Integer, ForeignKey("lanes.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="tracks")

class TrafficMetric(Base):
    __tablename__ = "traffic_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    lane_id = Column(Integer, ForeignKey("lanes.id"), nullable=True)
    vehicle_count = Column(Integer, default=0)
    flow_rate_per_min = Column(Float, default=0.0)
    occupancy_ratio = Column(Float, default=0.0)  # 0.0 to 1.0
    estimated_queue_length = Column(Integer, default=0)
    density_score = Column(Float, default=0.0)
    congestion_level = Column(String(20), default="LOW")  # LOW, MEDIUM, HIGH
    calculation_details = Column(Text, default="")

    analysis = relationship("Analysis", back_populates="traffic_metrics")
    lane = relationship("Lane", back_populates="traffic_metrics")

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    target_timestamp = Column(DateTime, nullable=False)
    horizon_minutes = Column(Integer, default=15)
    approach = Column(String(20), default="NORTH")
    predicted_flow_rate = Column(Float, default=0.0)
    predicted_density = Column(Float, default=0.0)
    confidence_lower = Column(Float, default=0.0)
    confidence_upper = Column(Float, default=0.0)
    model_name = Column(String(100), default="MovingAverage-HoltWinters")
    mae_score = Column(Float, nullable=True)
    sample_count = Column(Integer, default=0)
    status = Column(String(50), default="VALID")  # VALID, INSUFFICIENT_DATA

class SignalPlan(Base):
    __tablename__ = "signal_plans"

    id = Column(Integer, primary_key=True, index=True)
    intersection_name = Column(String(100), default="Intersection Alpha")
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Recommended green timings (seconds)
    approach_n_green = Column(Integer, nullable=False)
    approach_s_green = Column(Integer, nullable=False)
    approach_e_green = Column(Integer, nullable=False)
    approach_w_green = Column(Integer, nullable=False)
    
    # Baselines
    baseline_n_green = Column(Integer, default=30)
    baseline_s_green = Column(Integer, default=30)
    baseline_e_green = Column(Integer, default=30)
    baseline_w_green = Column(Integer, default=30)
    
    cycle_duration = Column(Integer, default=120)
    clearance_interval = Column(Integer, default=6)  # yellow + red
    reasoning = Column(Text, nullable=False)
    is_simulation = Column(Boolean, default=True)  # Mandatory safety tag: never live physical control

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    track_id = Column(Integer, nullable=True)
    lane_id = Column(Integer, nullable=True)
    alert_type = Column(String(50), nullable=False)  # WRONG_WAY, STOPPED_VEHICLE, CONGESTION, EMERGENCY_VEHICLE, CAMERA_OFFLINE
    severity = Column(String(20), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(Text, nullable=False)
    evidence_frame_path = Column(String(500), nullable=True)
    is_reviewed = Column(Boolean, default=False)
    reviewed_at = Column(DateTime, nullable=True)

    analysis = relationship("Analysis", back_populates="alerts")
    camera = relationship("Camera", back_populates="alerts")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(10), nullable=False)  # PDF, CSV
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    file_path = Column(String(500), nullable=False)
    record_count = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)
    generated_at = Column(DateTime, default=datetime.utcnow)
