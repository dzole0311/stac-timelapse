"""Coordinate data retrieval, compositing, frame writing, and HLS encoding.

The pipeline supports two render modes: both use STAC, but differ in tiler backend —
the default uses the Raster API, while the titiler-cmr mode uses titiler-cmr's
xarray or rasterio backends. It renders intermediate PNG frames to a configured or
temporary directory, then invokes ffmpeg to produce a video-on-demand HLS playlist.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from PIL import Image
from tqdm import tqdm

from . import basemap, encode, overlay, render, render_cmr, stac
from .config import Config

LOGGER = logging.getLogger(__name__)


def run(cfg: Config) -> Path:
    """Run the configured render mode and return the generated HLS playlist."""

    cfg.validate()

    if cfg.basemap:
        basemap_img = basemap.fetch_basemap(cfg)
    else:
        basemap_img = Image.new("RGBA", (cfg.width, cfg.height), (0, 0, 0, 255))

    frames_dir = cfg.frames_path or Path(tempfile.mkdtemp(prefix="stac_timelapse_frames_"))
    frames_dir.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Writing frames to %s", frames_dir)

    if cfg.use_cmr:
        _run_cmr(cfg, basemap_img, frames_dir)
    else:
        _run_stac(cfg, basemap_img, frames_dir)

    playlist = encode.encode_hls(frames_dir, cfg.output_path, cfg)

    if cfg.s3_bucket:
        from . import s3 as s3_mod
        s3_url = s3_mod.upload(cfg.output_path, cfg.s3_bucket, cfg.s3_prefix, cfg.s3_public)
        LOGGER.info("Uploaded to %s", s3_url)
        return Path(s3_url)

    return playlist


def _run_stac(cfg: Config, basemap_img: Image.Image, frames_dir: Path) -> None:
    items = stac.get_items(cfg)
    if not items:
        raise RuntimeError("No STAC items matched the requested collection/date/bbox")

    search_cache: dict[str, str] = {}
    for index, item in enumerate(tqdm(items, desc="Rendering frames")):
        sid = render.register_search(item, cfg, search_cache)
        data_png = render.fetch_frame(sid, cfg)
        props = item["properties"]
        datetime_str = props.get("datetime") or props.get("start_datetime") or ""
        frame = overlay.compose_frame(data_png, basemap_img, datetime_str, cfg)
        (frames_dir / f"frame_{index:05d}.png").write_bytes(frame)



def _run_cmr(cfg: Config, basemap_img: Image.Image, frames_dir: Path) -> None:
    if not cfg.cmr_collection_concept_id:
        raise ValueError("cmr_collection_concept_id is required when use_cmr=True")
    if not cfg.cmr_variable:
        raise ValueError("cmr_variable is required when use_cmr=True")

    dates = render_cmr.generate_dates(cfg)
    LOGGER.info("CMR mode: %s dates/times from %s to %s", len(dates), dates[0], dates[-1])

    for index, date_str in enumerate(tqdm(dates, desc="Rendering frames")):
        data_png = render_cmr.fetch_cmr_frame(date_str, cfg)
        frame = overlay.compose_frame(data_png, basemap_img, date_str, cfg)
        (frames_dir / f"frame_{index:05d}.png").write_bytes(frame)
