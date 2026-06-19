"""Upload HLS output (m3u8 + segments) to S3.

Only imported when ``Config.s3_bucket`` is set. boto3 is an optional
dependency; install with ``pip install stac-timelapse[aws]``.
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path

LOGGER = logging.getLogger(__name__)

_CONTENT_TYPES = {
    ".m3u8": "application/vnd.apple.mpegurl",
    ".ts": "video/mp2t",
}


def upload(output_dir: Path, bucket: str, prefix: str, public: bool = False) -> str:
    """Upload all HLS files in ``output_dir`` to S3 and return the m3u8 URL."""

    try:
        import boto3
    except ImportError as exc:
        raise ImportError(
            "boto3 is required for S3 upload. Install with: pip install stac-timelapse[aws]"
        ) from exc

    s3 = boto3.client("s3")
    prefix = prefix.rstrip("/")
    extra: dict = {}
    if public:
        extra["ACL"] = "public-read"

    uploaded = []
    for path in sorted(output_dir.iterdir()):
        if path.suffix not in _CONTENT_TYPES:
            continue
        key = f"{prefix}/{path.name}"
        content_type = _CONTENT_TYPES[path.suffix]
        LOGGER.info("Uploading s3://%s/%s", bucket, key)
        s3.upload_file(
            str(path),
            bucket,
            key,
            ExtraArgs={"ContentType": content_type, **extra},
        )
        uploaded.append(key)

    if not uploaded:
        raise RuntimeError(f"No HLS files found in {output_dir}")

    m3u8_key = f"{prefix}/index.m3u8"
    return f"s3://{bucket}/{m3u8_key}"
