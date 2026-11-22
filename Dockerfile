FROM python:3.12-slim AS builder

# Install runtime dependencies (ffmpeg) and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    libc-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default command
CMD ["python", "bot.py"]
