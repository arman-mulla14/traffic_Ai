# Datasets Directory

This directory contains test datasets, sample benchmark video references, and lane configuration templates.

## Sample Videos
To test video analysis and tracking:
- Users can upload any standard traffic footage (MP4, AVI, MOV, MKV) via the web interface.
- Sample synthetic/benchmark traffic videos can be generated using our test generator script `tests/generate_test_video.py` or placed here directly.

## Structure:
- `sample_traffic.mp4`: Synthetic or recorded video with road lanes and crossing vehicles for automated verification.
- `annotations/`: Optional ground truth bounding boxes and crossing counts for testing precision and recall.
