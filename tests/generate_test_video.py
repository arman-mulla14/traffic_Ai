import cv2
import numpy as np
from pathlib import Path

def generate_sample_traffic_video(output_path: str = "datasets/sample_traffic.mp4", duration_sec: int = 5, fps: int = 30):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    width, height = 640, 480
    total_frames = duration_sec * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # Road coordinates
    road_left = 120
    road_right = 520
    lane_divider = 320

    # Moving vehicles state: [x, y, w, h, speed_y, color, label]
    vehicles = [
        {"x": 180, "y": 20, "w": 70, "h": 100, "vy": 4.5, "color": (50, 50, 220), "name": "car_1"},
        {"x": 370, "y": 60, "w": 80, "h": 140, "vy": 3.8, "color": (20, 180, 50), "name": "truck_1"},
        {"x": 200, "y": -120, "w": 65, "h": 90, "vy": 5.2, "color": (220, 160, 20), "name": "car_2"},
        {"x": 380, "y": -80, "w": 50, "h": 70, "vy": 6.0, "color": (200, 40, 200), "name": "motorcycle_1"},
    ]

    for f in range(total_frames):
        # Draw background: dark surroundings
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (35, 40, 45)

        # Draw asphalt road
        cv2.rectangle(frame, (road_left, 0), (road_right, height), (75, 80, 85), -1)

        # Draw road borders (white lines)
        cv2.line(frame, (road_left, 0), (road_left, height), (255, 255, 255), 3)
        cv2.line(frame, (road_right, 0), (road_right, height), (255, 255, 255), 3)

        # Draw dashed center divider
        dash_len = 25
        gap_len = 20
        y_dash = (f * 3) % (dash_len + gap_len) - (dash_len + gap_len)
        while y_dash < height:
            if y_dash >= 0:
                cv2.line(frame, (lane_divider, int(y_dash)), (lane_divider, int(min(height, y_dash + dash_len))), (255, 255, 255), 2)
            y_dash += dash_len + gap_len

        # Draw vehicles
        for v in vehicles:
            curr_y = int(v["y"] + f * v["vy"]) % (height + 150) - 100
            vx = v["x"]
            vw = v["w"]
            vh = v["h"]
            # Vehicle body
            cv2.rectangle(frame, (vx, curr_y), (vx + vw, curr_y + vh), v["color"], -1)
            cv2.rectangle(frame, (vx, curr_y), (vx + vw, curr_y + vh), (255, 255, 255), 2)
            # Windshield
            cv2.rectangle(frame, (vx + 8, curr_y + int(vh * 0.2)), (vx + vw - 8, curr_y + int(vh * 0.45)), (220, 220, 240), -1)
            # Headlights
            cv2.circle(frame, (vx + 10, curr_y + vh - 6), 5, (0, 255, 255), -1)
            cv2.circle(frame, (vx + vw - 10, curr_y + vh - 6), 5, (0, 255, 255), -1)

        # Timestamp HUD
        cv2.putText(frame, f"TRAFFIC SIM CCTV-01 | Frame: {f+1}/{total_frames}", (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

        out.write(frame)

    out.release()
    print(f"Sample traffic video generated at: {output_path} ({total_frames} frames, {duration_sec}s)")

if __name__ == "__main__":
    generate_sample_traffic_video()
