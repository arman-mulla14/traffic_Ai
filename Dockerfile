# Production Dockerfile for AI Traffic Management System
# Fully optimized for Hugging Face Spaces (16GB RAM / 2 vCPU) and standard cloud servers
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOST=0.0.0.0
ENV PORT=7860

# Install essential system libraries for OpenCV, PyTorch, and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face runs with user ID 1000
RUN useradd -m -u 1000 user
WORKDIR /app

# Install Python requirements (CPU optimized torch)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY --chown=user:user backend /app/backend
COPY --chown=user:user frontend /app/frontend
COPY --chown=user:user models /app/models

# Create persistent storage directories with full permissions for user 1000
RUN mkdir -p /app/storage/uploads /app/storage/processed /app/storage/reports /app/storage/evidence /app/models && \
    chown -R user:user /app && \
    chmod -R 777 /app/storage /app/models

# Initialize database schema as user
USER user
RUN python -c "import sys; sys.path.insert(0, 'backend'); from app.database.init_db import init_db; init_db()"

# Hugging Face Spaces default port
EXPOSE 7860

# Start FastAPI server on port 7860 (or $PORT if overridden)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860} --app-dir backend"]
