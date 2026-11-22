# ------------------------------------------------------------
# Multi‑stage Docker image for the Telegram VC music bot
# ------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install system dependencies (ffmpeg and git)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg git && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------
# Runtime stage – keep only the necessary parts
# ------------------------------------------------------------
FROM python:3.12-slim

# System deps (ffmpeg only – git not needed at runtime)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . /app

# Create a non‑root user for security
RUN useradd -m botuser && chown -R botuser:botuser /app
USER botuser

ENV PYTHONUNBUFFERED=1

CMD ["python", "bot.py"]
