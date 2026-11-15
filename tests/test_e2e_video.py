import sys
import time
from pathlib import Path

# Add backend directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from fastapi.testclient import TestClient
from app.main import app

def run_e2e_video_test():
    client = TestClient(app)
    video_path = Path("datasets/sample_traffic.mp4")
    assert video_path.exists(), "Sample video does not exist!"

    with open(video_path, "rb") as f:
        res = client.post("/api/videos", files={"file": ("sample_traffic.mp4", f, "video/mp4")})

    assert res.status_code == 200
    video_data = res.json()
    print(f"Uploaded video: ID={video_data['id']}, Frames={video_data['frame_count']}, Duration={video_data['duration_seconds']}s")

    # Start analysis
    res = client.post("/api/analyses", json={"video_id": video_data["id"]})
    assert res.status_code == 200
    analysis_data = res.json()
    analysis_id = analysis_data["id"]
    print(f"Analysis started: ID={analysis_id}, Status={analysis_data['status']}")

    # Wait for completion (in background task)
    completed = False
    for i in range(20):
        time.sleep(1)
        res = client.get(f"/api/analyses/{analysis_id}")
        assert res.status_code == 200
        status = res.json()
        print(f"[{i+1}s] Status: {status['status']}, Progress: {status['progress_pct']}%, Processed: {status['processed_frames']}/{status['total_frames']}, FPS: {status['current_fps']}")
        if status["status"] in ["COMPLETED", "FAILED"]:
            completed = True
            break

    assert completed, "Analysis did not finish within 20 seconds!"
    assert status["status"] == "COMPLETED"
    assert status["processed_frames"] > 0
    print(f"SUCCESS: Analysis completed! Unique Vehicles: {status['unique_vehicles_total']}, Congestion: {status['congestion_level']}")

if __name__ == "__main__":
    run_e2e_video_test()
