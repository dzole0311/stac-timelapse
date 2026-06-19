"""Configuration for the stac-timelapse rendering pipeline.

The dataclass is the public contract for CLI and Python runs. It keeps
service URLs, cache locations, rendering controls, annotation settings, and
ffmpeg options in one place so deployments can target different STAC services,
self-hosted titiler instances, or offline cache locations without changing
module internals.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Config:
    """Single source of truth for a rendering run."""

    stac_api: str = "https://openveda.cloud/api/stac"
    raster_api: str = "https://openveda.cloud/api/raster"
    auth_token: str | None = None

    collection_id: str = ""
    datetime_start: str = ""
    datetime_end: str = ""
    bbox: list[float] = field(default_factory=lambda: [-180, -90, 180, 90])
    assets: list[str] = field(default_factory=list)
    expression: str | None = None
    colormap_name: str = "rdbu"
    rescale: str | None = "0,3000"
    algorithm: str | None = None
    resampling: str | None = "bilinear"
    color_formula: str | None = None

    use_cmr: bool = False
    cmr_tiler_url: str = "https://openveda.cloud/api/titiler-cmr"
    cmr_collection_concept_id: str = ""
    cmr_variable: str = ""
    cmr_backend: str = "xarray"
    cmr_date_frequency: str = "daily"
    cmr_dry_luminance_threshold: float = 230.0

    cache_dir: str = "~/.cache/stac_timelapse"
    download_retries: int = 3
    download_timeout: int = 180

    width: int = 1920
    height: int = 1080
    fps: int = 10
    frame_hold: int = 1

    data_blur_radius: float = 0.0

    basemap: bool = True
    basemap_style: str = "boundaries"
    basemap_layer: str = "BlueMarble_ShadedRelief_Bathymetry"
    basemap_max_zoom: int = 8
    basemap_tile_workers: int = 16
    basemap_opacity: float = 1.0
    data_opacity: float = 0.85

    colorbar: bool = True
    colorbar_label: str = ""
    colorbar_width: int = 30
    colorbar_height: int = 300
    colorbar_position: str = "bottom-right"
    colorbar_ticks: int = 5

    title: str = ""
    show_date: bool = True
    date_format: str = "%Y-%m-%d"
    font_size: int = 36
    label_color: tuple[int, int, int] = (20, 20, 20)
    label_shadow: bool = True
    label_shadow_offset: int = 2

    s3_bucket: str | None = None
    s3_prefix: str = "renders"
    s3_public: bool = False

    output_dir: str = "./output"
    frames_dir: str | None = None
    hls_segment_duration: int = 4
    video_codec: str = "libx264"
    crf: int = 18
    preset: str = "slow"

    def validate(self) -> None:
        """Raise a clear error for invalid or incomplete configuration."""

        if not self.use_cmr and not self.collection_id:
            raise ValueError("collection_id is required (or set use_cmr=True)")
        if self.use_cmr:
            if not self.cmr_collection_concept_id:
                raise ValueError("cmr_collection_concept_id is required when use_cmr=True")
            if not self.cmr_variable:
                raise ValueError("cmr_variable is required when use_cmr=True")
            if self.cmr_backend not in {"xarray", "rasterio"}:
                raise ValueError("cmr_backend must be one of: xarray, rasterio")
            if self.cmr_date_frequency not in {"30min", "daily", "monthly"}:
                raise ValueError("cmr_date_frequency must be one of: 30min, daily, monthly")
        if not self.datetime_start or not self.datetime_end:
            raise ValueError("datetime_start and datetime_end are required")
        if len(self.bbox) != 4:
            raise ValueError("bbox must contain four values: west,south,east,north")
        west, south, east, north = self.bbox
        if west >= east:
            raise ValueError("bbox west must be less than east")
        if south >= north:
            raise ValueError("bbox south must be less than north")
        if not -180 <= west <= 180 or not -180 <= east <= 180:
            raise ValueError("bbox longitude values must be between -180 and 180")
        if not -90 <= south <= 90 or not -90 <= north <= 90:
            raise ValueError("bbox latitude values must be between -90 and 90")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if self.fps <= 0:
            raise ValueError("fps must be positive")
        if self.frame_hold <= 0:
            raise ValueError("frame_hold must be positive")
        if self.download_retries <= 0:
            raise ValueError("download_retries must be positive")
        if self.download_timeout <= 0:
            raise ValueError("download_timeout must be positive")
        if self.basemap_style not in {"satellite", "boundaries"}:
            raise ValueError("basemap_style must be one of: satellite, boundaries")
        if self.basemap_max_zoom < 0:
            raise ValueError("basemap_max_zoom must be non-negative")
        if self.basemap_tile_workers <= 0:
            raise ValueError("basemap_tile_workers must be positive")
        if not 0 <= self.basemap_opacity <= 1:
            raise ValueError("basemap_opacity must be between 0 and 1")
        if not 0 <= self.data_opacity <= 1:
            raise ValueError("data_opacity must be between 0 and 1")
        if self.colorbar_ticks < 2:
            raise ValueError("colorbar_ticks must be at least 2")
        if self.label_shadow_offset < 0:
            raise ValueError("label_shadow_offset must be non-negative")
        if self.colorbar_position not in {
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
        }:
            raise ValueError(
                "colorbar_position must be one of: top-left, top-right, "
                "bottom-left, bottom-right"
            )

    @property
    def datetime_interval(self) -> str:
        """Return a STAC datetime interval string."""

        return f"{self.datetime_start}/{self.datetime_end}"

    @property
    def output_path(self) -> Path:
        return Path(self.output_dir).expanduser()

    @property
    def cache_path(self) -> Path:
        return Path(self.cache_dir).expanduser()

    @property
    def frames_path(self) -> Path | None:
        if self.frames_dir is None:
            return None
        return Path(self.frames_dir).expanduser()

    def auth_headers(self) -> dict[str, str]:
        if not self.auth_token:
            return {}
        return {"Authorization": f"Bearer {self.auth_token}"}


def parse_bbox(value: str) -> list[float]:
    """Parse a comma-separated bbox string."""

    try:
        bbox = [float(part.strip()) for part in value.split(",")]
    except ValueError as exc:
        raise ValueError("bbox must be comma-separated numbers") from exc
    if len(bbox) != 4:
        raise ValueError("bbox must contain four values: west,south,east,north")
    return bbox


def parse_csv(value: str | None) -> list[str]:
    """Parse a comma-separated string into non-empty values."""

    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_rgb(value: str | tuple[int, int, int]) -> tuple[int, int, int]:
    """Parse an RGB tuple from a string like ``255,255,255``."""

    if isinstance(value, tuple):
        return value
    parts = parse_csv(value)
    if len(parts) != 3:
        raise ValueError("label_color must contain three values: r,g,b")
    try:
        rgb = tuple(int(part) for part in parts)
    except ValueError as exc:
        raise ValueError("label_color values must be integers") from exc
    if any(channel < 0 or channel > 255 for channel in rgb):
        raise ValueError("label_color values must be between 0 and 255")
    return rgb[0], rgb[1], rgb[2]


def clean_optional(value: str | None) -> str | None:
    """Normalize empty CLI strings into ``None``."""

    if value is None:
        return None
    value = value.strip()
    return value or None


def asdict_shallow(cfg: Config) -> dict[str, Any]:
    """Return a simple dict useful for logging or debugging."""

    return {field_name: getattr(cfg, field_name) for field_name in cfg.__dataclass_fields__}
