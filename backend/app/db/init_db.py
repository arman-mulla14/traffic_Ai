import json
from app.db.session import engine, Base, SessionLocal
from app.db.models import Camera, Lane, Zone

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if default camera exists
        cam = db.query(Camera).first()
        if not cam:
            default_cam = Camera(
                name="Intersection Alpha - Main Feeder",
                stream_url="0",  # Webcam index 0 or configured RTSP
                location="Main 4-Way Junction (North Approach)",
                is_active=False,
                status="DISCONNECTED",
                fps=30.0
            )
            db.add(default_cam)
            db.flush()

            # Add 4 default lanes for 4-way intersection simulation
            lanes = [
                Lane(
                    camera_id=default_cam.id,
                    name="North Approach (Inbound)",
                    approach="NORTH",
                    permitted_direction="DOWN",
                    direction_vector_json=json.dumps([0, 1]),
                    counting_line_json=json.dumps([100, 360, 540, 360])
                ),
                Lane(
                    camera_id=default_cam.id,
                    name="South Approach (Inbound)",
                    approach="SOUTH",
                    permitted_direction="UP",
                    direction_vector_json=json.dumps([0, -1]),
                    counting_line_json=json.dumps([100, 360, 540, 360])
                ),
                Lane(
                    camera_id=default_cam.id,
                    name="East Approach (Inbound)",
                    approach="EAST",
                    permitted_direction="LEFT",
                    direction_vector_json=json.dumps([-1, 0]),
                    counting_line_json=json.dumps([320, 100, 320, 400])
                ),
                Lane(
                    camera_id=default_cam.id,
                    name="West Approach (Inbound)",
                    approach="WEST",
                    permitted_direction="RIGHT",
                    direction_vector_json=json.dumps([1, 0]),
                    counting_line_json=json.dumps([320, 100, 320, 400])
                ),
            ]
            for l in lanes:
                db.add(l)

            # Add default critical intersection clearance zone
            zone = Zone(
                camera_id=default_cam.id,
                name="Intersection Yellow Box",
                zone_type="NO_STOPPING",
                polygon_coords_json=json.dumps([[180, 150], [460, 150], [460, 380], [180, 380]])
            )
            db.add(zone)

            db.commit()
            print("Database initialized with default camera, lanes, and zones.")
        else:
            print("Database already initialized.")
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
