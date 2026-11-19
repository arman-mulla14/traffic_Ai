from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database.connection import Base

def utc_now():
    """Generates timezone-aware UTC datetime replacing deprecated datetime.utcnow."""
    return datetime.now(timezone.utc)

class Street(Base):
    """
    TABLE: streets
    Stores streets and intersections that group multiple roads together in one place.
    """
    __tablename__ = "streets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)  # e.g. "Gandhi Chowk"
    location = Column(String(255), nullable=True)                        # e.g. "Kodoli"
    description = Column(String(255), nullable=True)
    speed_limit = Column(Integer, default=60)                            # default km/h
    created_at = Column(DateTime, default=utc_now, index=True)

class Camera(Base):
    """
    TABLE 1: cameras
    Stores registered surveillance and traffic camera details.
    """
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    camera_name = Column(String(120), nullable=False, index=True)
    location = Column(String(255), nullable=False)
    street_name = Column(String(150), nullable=True, default="Gandhi Chowk")  # Associated street (groups multiple roads)
    road_name = Column(String(150), nullable=True)  # Associated street or intersection road approach
    direction = Column(String(50), default="Northbound")  # Northbound, Southbound, Eastbound, Westbound
    speed_limit = Column(Integer, default=60)  # km/h
    camera_type = Column(String(50), default="CCTV")  # CCTV, WEBCAM, IP_CAMERA
    stream_url = Column(String(500), nullable=True)   # Stream URL or webcam device index
    status = Column(String(50), default="ACTIVE")     # ACTIVE, INACTIVE, OFFLINE
    created_at = Column(DateTime, default=utc_now, index=True)

class Video(Base):
    """
    TABLE 2: videos
    Stores uploaded traffic video files and metadata.
    """
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    video_name = Column(String(255), nullable=False, index=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)        # Size in bytes
    duration = Column(Float, default=0.0)             # Duration in seconds
    status = Column(String(50), default="UPLOADED")   # UPLOADED, PROCESSING, COMPLETED, FAILED
    uploaded_at = Column(DateTime, default=utc_now, index=True)

    # Relationship to analyses
    analyses = relationship("Analysis", back_populates="video", cascade="all, delete-orphan")

class Analysis(Base):
    """
    TABLE 3: analyses
    Tracks video processing jobs, inference progress, and execution performance.
    """
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, index=True)
    processing_status = Column(String(50), default="PENDING", index=True)  # PENDING, PROCESSING, COMPLETED, FAILED
    total_frames = Column(Integer, default=0)
    processed_frames = Column(Integer, default=0)
    processing_time = Column(Float, default=0.0)      # Total duration in seconds
    average_fps = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    video = relationship("Video", back_populates="analyses")
    traffic_records = relationship("TrafficRecord", back_populates="analysis", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="analysis", cascade="all, delete-orphan")

class TrafficRecord(Base):
    """
    TABLE 4: traffic_records
    Stores real vehicle counting, density estimation, and queue records for each processing interval.
    """
    __tablename__ = "traffic_records"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True, index=True)
    road_name = Column(String(100), nullable=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    car_count = Column(Integer, default=0)
    motorcycle_count = Column(Integer, default=0)
    bus_count = Column(Integer, default=0)
    truck_count = Column(Integer, default=0)
    pedestrian_count = Column(Integer, default=0)
    total_vehicles = Column(Integer, default=0)
    traffic_density = Column(Float, default=0.0)      # Occupancy percentage (0.0 to 100.0)
    queue_length = Column(Integer, default=0)         # Estimated queued vehicle count
    direction = Column(String(50), default="Southbound")
    created_at = Column(DateTime, default=utc_now)

    # Relationship to analysis & camera
    analysis = relationship("Analysis", back_populates="traffic_records")
    camera = relationship("Camera")

class Incident(Base):
    """
    TABLE 5: incidents
    Stores genuine detected traffic safety incidents (wrong-way driving & stationary vehicles).
    """
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True, index=True)
    road_name = Column(String(100), nullable=True)
    incident_type = Column(String(100), nullable=False, index=True)  # WRONG_WAY, STOPPED_VEHICLE
    description = Column(Text, nullable=False)
    severity = Column(String(50), default="MEDIUM", index=True)      # LOW, MEDIUM, HIGH, CRITICAL
    vehicle_track_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    status = Column(String(50), default="NEW", index=True)           # NEW, ACKNOWLEDGED, RESOLVED
    created_at = Column(DateTime, default=utc_now)

    # Relationship to analysis & camera
    analysis = relationship("Analysis", back_populates="incidents")
    camera = relationship("Camera")



class Prediction(Base):
    """TABLE 6: predictions - Predictive traffic density and flow projections."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utc_now)
    target_timestamp = Column(DateTime, nullable=False)
    horizon_minutes = Column(Integer, default=60)
    approach = Column(String(20), default="North")
    predicted_flow_rate = Column(Float, default=0.0)
    predicted_density = Column(Float, default=0.0)
    confidence_lower = Column(Float, default=0.0)
    confidence_upper = Column(Float, default=0.0)
    model_name = Column(String(100), default="RandomForest")
    mae_score = Column(Float, default=0.0)
    sample_count = Column(Integer, default=0)
    status = Column(String(50), default="COMPLETED")

class SignalPlan(Base):
    """TABLE 7: signal_plans - Adaptive signal timing plans."""
    __tablename__ = "signal_plans"

    id = Column(Integer, primary_key=True, index=True)
    intersection_name = Column(String(100), default="Junction Alpha")
    timestamp = Column(DateTime, default=utc_now)
    approach_n_green = Column(Integer, nullable=False, default=45)
    approach_s_green = Column(Integer, nullable=False, default=45)
    approach_e_green = Column(Integer, nullable=False, default=30)
    approach_w_green = Column(Integer, nullable=False, default=30)
    baseline_n_green = Column(Integer, default=40)
    baseline_s_green = Column(Integer, default=40)
    baseline_e_green = Column(Integer, default=30)
    baseline_w_green = Column(Integer, default=30)
    cycle_duration = Column(Integer, default=120)
    clearance_interval = Column(Integer, default=4)
    reasoning = Column(Text, nullable=False, default="Adaptive load balancing")
    is_simulation = Column(Boolean, default=False)

class Report(Base):
    """TABLE 8: reports - Generated PDF/CSV analytics reports."""
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(10), nullable=False)  # PDF, CSV
    date_from = Column(DateTime, nullable=True)
    date_to = Column(DateTime, nullable=True)
    file_path = Column(String(500), nullable=False)
    record_count = Column(Integer, default=0)
    file_size_bytes = Column(Integer, default=0)
    generated_at = Column(DateTime, default=utc_now)

class Lane(Base):
    """TABLE 9: lanes - Lane boundary & directional counting vectors."""
    __tablename__ = "lanes"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    name = Column(String(100), nullable=False)
    approach = Column(String(10), default="North")
    permitted_direction = Column(String(50), default="Forward")
    direction_vector_json = Column(Text, nullable=True)
    counting_line_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class Zone(Base):
    """TABLE 10: zones - Geographic intersection monitoring zones."""
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    name = Column(String(100), nullable=False)
    zone_type = Column(String(50), default="INTERSECTION")
    polygon_coords_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

class Detection(Base):
    """TABLE 11: detections - Frame-by-frame object detections."""
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    frame_number = Column(Integer, nullable=False)
    timestamp_ms = Column(Float, default=0.0)
    track_id = Column(Integer, nullable=True)
    class_id = Column(Integer, nullable=False)
    class_name = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    bbox_x1 = Column(Float, nullable=False)
    bbox_y1 = Column(Float, nullable=False)
    bbox_x2 = Column(Float, nullable=False)
    bbox_y2 = Column(Float, nullable=False)

class VehicleTrack(Base):
    """TABLE 12: vehicle_tracks - DeepSORT multi-object tracks."""
    __tablename__ = "vehicle_tracks"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    track_id = Column(Integer, nullable=False)
    class_name = Column(String(50), nullable=False)
    first_seen_frame = Column(Integer, default=0)
    last_seen_frame = Column(Integer, default=0)
    trajectory_points_json = Column(Text, nullable=True)
    is_counted = Column(Boolean, default=False)
    crossed_line_at_frame = Column(Integer, nullable=True)
    average_speed_px = Column(Float, default=0.0)
    is_wrong_way = Column(Boolean, default=False)
    is_stopped = Column(Boolean, default=False)
    lane_id = Column(Integer, ForeignKey("lanes.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now)

class TrafficMetric(Base):
    """TABLE 13: traffic_metrics - Continuous telemetry metrics."""
    __tablename__ = "traffic_metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utc_now)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    lane_id = Column(Integer, ForeignKey("lanes.id"), nullable=True)
    vehicle_count = Column(Integer, default=0)
    flow_rate_per_min = Column(Float, default=0.0)
    occupancy_ratio = Column(Float, default=0.0)
    estimated_queue_length = Column(Integer, default=0)
    density_score = Column(Float, default=0.0)
    congestion_level = Column(String(20), default="MODERATE")
    calculation_details = Column(Text, nullable=True)

class Alert(Base):
    """TABLE 14: alerts - Traffic system safety and operation alerts."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=utc_now)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    track_id = Column(Integer, nullable=True)
    lane_id = Column(Integer, ForeignKey("lanes.id"), nullable=True)
    alert_type = Column(String(50), nullable=False)
    severity = Column(String(20), default="MEDIUM")
    description = Column(Text, nullable=False)
    evidence_frame_path = Column(String(500), nullable=True)
    is_reviewed = Column(Boolean, default=False)
    reviewed_at = Column(DateTime, nullable=True)
