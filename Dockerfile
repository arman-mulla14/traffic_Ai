# Production Dockerfile for AI Traffic Management System
FROM python:3.11-slim

# Avoid prompts from debian
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install essential system libraries for OpenCV and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend /app/backend
COPY frontend /app/frontend
COPY models /app/models

# Create persistent storage directories
RUN mkdir -p /app/storage/uploads /app/storage/processed /app/storage/reports /app/storage/evidence /app/models

# Initialize database schema
RUN python -c "import sys; sys.path.insert(0, 'backend'); from app.database.init_db import init_db; init_db()"

EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--app-dir", "backend"]
