FROM python:3.12-slim

# System dependencies for ffmpeg
RUN apt-get update && apt-get install -y ffmpeg git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# Create a non‑root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

CMD ["python", "-m", "bot"]
