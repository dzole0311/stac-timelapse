"""SQS worker — polls for jobs and runs the render pipeline.

Each message body is a JSON object with keys:
  job_id     — UUID string
  config     — veda_timelapse.Config fields as a dict
  s3_prefix  — S3 key prefix for this job's output

On success, HLS files are uploaded to s3://<S3_BUCKET>/<s3_prefix>/.
On failure, an error.json sentinel is written to the same prefix.

Environment variables:
  SQS_QUEUE_URL          — required
  S3_BUCKET              — required
  AWS_REGION             — defaults to us-east-1
  WORKER_POLL_INTERVAL   — seconds between empty-queue polls (default 5)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
import time
import traceback

import boto3

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)

_SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
_S3_BUCKET = os.environ["S3_BUCKET"]
_REGION = os.environ.get("AWS_REGION", "us-east-1")
_POLL_INTERVAL = int(os.environ.get("WORKER_POLL_INTERVAL", "5"))

_sqs = boto3.client("sqs", region_name=_REGION)
_s3 = boto3.client("s3", region_name=_REGION)


def _write_error(prefix: str, message: str) -> None:
    body = json.dumps({"error": message}).encode()
    _s3.put_object(
        Bucket=_S3_BUCKET,
        Key=f"{prefix}/error.json",
        Body=body,
        ContentType="application/json",
    )


def _process(message: dict) -> None:
    body = json.loads(message["Body"])
    job_id: str = body["job_id"]
    config_dict: dict = body["config"]
    s3_prefix: str = body["s3_prefix"]

    LOGGER.info("Processing job %s", job_id)

    from veda_timelapse.config import Config
    from veda_timelapse import pipeline, s3 as s3_mod

    with tempfile.TemporaryDirectory(prefix=f"veda_{job_id}_") as tmp:
        config_dict["output_dir"] = tmp
        config_dict["s3_bucket"] = None  # upload manually below
        cfg = Config(**config_dict)

        try:
            playlist = pipeline.run(cfg)
            url = s3_mod.upload(cfg.output_path, _S3_BUCKET, s3_prefix)
            LOGGER.info("Job %s done → %s", job_id, url)
        except Exception:
            err = traceback.format_exc()
            LOGGER.error("Job %s failed:\n%s", job_id, err)
            _write_error(s3_prefix, err)


def main() -> None:
    LOGGER.info("Worker started, polling %s", _SQS_QUEUE_URL)
    while True:
        resp = _sqs.receive_message(
            QueueUrl=_SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=20,  # long-poll
        )
        messages = resp.get("Messages", [])
        if not messages:
            time.sleep(_POLL_INTERVAL)
            continue

        msg = messages[0]
        receipt = msg["ReceiptHandle"]
        try:
            _process(msg)
            _sqs.delete_message(QueueUrl=_SQS_QUEUE_URL, ReceiptHandle=receipt)
        except Exception:
            LOGGER.error("Unhandled error processing message; leaving on queue for redelivery")


if __name__ == "__main__":
    main()
