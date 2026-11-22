FROM python:3.12-slim AS builder

# Install build deps (ffmpeg & git)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        git && \
    rm -rf /var/lib/apt/lists/*

# Create non‑root user
RUN useradd -m botuser
WORKDIR /app

# Copy requirement file & install
COPY requirements.txt ./
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Switch to non‑root user
USER botuser

# Runtime command
CMD ["python", "bot.py"]
