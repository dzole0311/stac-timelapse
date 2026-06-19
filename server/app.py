"""FastAPI job submission API.

Accepts Config JSON, enqueues to SQS, and exposes job status via S3 sentinel
files — no database required. Job completion is signalled by the presence of
s3://<bucket>/jobs/<job_id>/index.m3u8; failure by error.json at the same prefix.

Environment variables:
  SQS_QUEUE_URL   — required
  S3_BUCKET       — required
  AWS_REGION      — defaults to us-east-1
"""

from __future__ import annotations

import json
import os
import uuid

import boto3
import botocore.exceptions
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="stac-timelapse", version="0.1.0")

_SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
_S3_BUCKET = os.environ["S3_BUCKET"]
_REGION = os.environ.get("AWS_REGION", "us-east-1")

_sqs = boto3.client("sqs", region_name=_REGION)
_s3 = boto3.client("s3", region_name=_REGION)


class JobRequest(BaseModel):
    config: dict


class JobResponse(BaseModel):
    job_id: str
    status: str
    s3_prefix: str


@app.post("/jobs", response_model=JobResponse, status_code=202)
def submit_job(req: JobRequest) -> JobResponse:
    job_id = str(uuid.uuid4())
    prefix = f"jobs/{job_id}"

    payload = {"job_id": job_id, "config": req.config, "s3_prefix": prefix}
    _sqs.send_message(
        QueueUrl=_SQS_QUEUE_URL,
        MessageBody=json.dumps(payload),
    )

    return JobResponse(job_id=job_id, status="queued", s3_prefix=prefix)


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    prefix = f"jobs/{job_id}"

    # Check for error sentinel first
    try:
        obj = _s3.get_object(Bucket=_S3_BUCKET, Key=f"{prefix}/error.json")
        detail = json.loads(obj["Body"].read())
        raise HTTPException(status_code=500, detail=detail)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] not in ("NoSuchKey", "404"):
            raise

    # Check for completion
    try:
        _s3.head_object(Bucket=_S3_BUCKET, Key=f"{prefix}/index.m3u8")
        return JobResponse(job_id=job_id, status="done", s3_prefix=prefix)
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] not in ("NoSuchKey", "404"):
            raise

    return JobResponse(job_id=job_id, status="running", s3_prefix=prefix)
