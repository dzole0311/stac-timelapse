"""Render CMR-backed datasets through titiler-cmr.

This mode bypasses STAC item search and asks titiler-cmr to resolve CMR granules
for a specific temporal value. It is useful for collections such as GPM IMERG
where CMR is the source of truth. The returned PNG is post-processed locally so
very bright dry/no-data pixels can reveal the basemap underneath.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import requests
from PIL import Image
import io
import numpy as np

from .config import Config

LOGGER = logging.getLogger(__name__)


def fetch_cmr_frame(date_str: str, cfg: Config) -> bytes:
    """
    Fetch a rendered PNG from titiler-cmr for a given date.

    Uses /xarray/bbox endpoint. Dry/zero pixels are made transparent in
    post-processing so the basemap shows through.
    """

    fetch_w, fetch_h = cfg.width // 2, cfg.height // 2
    bbox = ",".join(f"{v:g}" for v in cfg.bbox)
    url = f"{cfg.cmr_tiler_url.rstrip('/')}/{cfg.cmr_backend}/bbox/{bbox}/{fetch_w}x{fetch_h}.png"

    params: list[tuple[str, Any]] = [
        ("collection_concept_id", cfg.cmr_collection_concept_id),
        ("temporal", date_str),
        ("variables", cfg.cmr_variable),
        ("rescale", cfg.rescale or "0,100"),
        ("colormap_name", cfg.colormap_name),
    ]
    if cfg.resampling:
        params.append(("resampling", cfg.resampling))

    headers = cfg.auth_headers()
    for attempt in range(1, cfg.download_retries + 1):
        resp = requests.get(url, params=params, headers=headers, timeout=cfg.download_timeout)
        if resp.status_code < 500 or attempt == cfg.download_retries:
            break
        wait = 2 ** (attempt - 1)
        LOGGER.warning("titiler-cmr returned %s for %s, retrying in %ss", resp.status_code, date_str, wait)
        time.sleep(wait)
    resp.raise_for_status()

    raw = Image.open(io.BytesIO(resp.content)).convert("RGBA")
    arr = np.array(raw, dtype=np.float32)

    luminance = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    threshold = cfg.cmr_dry_luminance_threshold
    dry_mask = luminance >= threshold
    arr[:, :, 3] = np.where(dry_mask, 0, arr[:, :, 3])

    result = Image.fromarray(arr.astype(np.uint8), "RGBA")
    if result.size != (cfg.width, cfg.height):
        result = result.resize((cfg.width, cfg.height), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    result.save(buf, "PNG")
    return buf.getvalue()


def generate_dates(cfg: Config) -> list[str]:
    """
    Generate timestamps between datetime_start and datetime_end at the
    configured frequency. Returns ISO-8601 strings.
    """
    from datetime import datetime, timedelta, timezone

    start = datetime.fromisoformat(cfg.datetime_start.replace("Z", "+00:00"))
    end = datetime.fromisoformat(cfg.datetime_end.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    freq = cfg.cmr_date_frequency
    deltas = {
        "30min": timedelta(minutes=30),
        "daily": timedelta(days=1),
        "monthly": None,
    }

    dates: list[str] = []
    current = start
    while current <= end:
        if freq == "30min":
            dates.append(current.strftime("%Y-%m-%dT%H:%M:%SZ"))
        else:
            dates.append(current.strftime("%Y-%m-%d"))

        if freq == "monthly":
            month = current.month + 1
            year = current.year + (month > 12)
            month = month if month <= 12 else 1
            current = current.replace(year=year, month=month, day=1)
        else:
            current += deltas.get(freq, timedelta(days=1))

    return dates
