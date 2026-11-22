FROM python:3.11-slim

# Install ffmpeg (required for audio streaming)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bot token is passed via env var BOT_TOKEN
CMD ["python", "bot.py"]