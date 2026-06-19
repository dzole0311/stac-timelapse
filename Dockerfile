FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY stac_timelapse/ stac_timelapse/
COPY cli.py .
COPY server/ server/

RUN pip install --no-cache-dir ".[aws,server]"

# Default: run the API. Override CMD to run the worker.
# API:    docker run -e SQS_QUEUE_URL=... -e S3_BUCKET=... <image>
# Worker: docker run -e SQS_QUEUE_URL=... -e S3_BUCKET=... <image> python server/worker.py
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
