FROM python:3.11-slim

# Install system dependencies (FFmpeg is required for pydub to process audio)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and templates
COPY src/ ./src/
COPY templates/ ./templates/

# Create runtime directories
RUN mkdir -p output bgm data

# Expose port (Hugging Face default is 7860)
EXPOSE 7860

# Run FastAPI server
CMD ["python", "src/main.py", "--action", "serve"]
