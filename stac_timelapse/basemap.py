"""Fetch or generate a basemap image for the configured bounding box.

Two styles are supported:
- ``boundaries``: draws country outlines from Natural Earth 110m GeoJSON using
  matplotlib. Clean, lightweight, works offline after the first fetch.
- ``satellite``: fetches NASA GIBS EPSG:3857 Blue Marble tiles and stitches
  them into a georeferenced image.

Tile and GeoJSON files are cached under ``Config.cache_dir`` so repeated
renders do not re-download anything.
"""

from __future__ import annotations

import io
import json
import logging
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable

import mercantile
import requests
from PIL import Image

from .config import Config
from .matplotlib_env import configure_matplotlib_env

configure_matplotlib_env()

LOGGER = logging.getLogger(__name__)

TILE_SIZE = 256
GIBS_MATRIX_SET = "GoogleMapsCompatible_Level8"
GIBS_URL = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "{layer}/default//{matrix_set}/{z}/{y}/{x}.jpeg"
)

NE_GEOJSON_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector"
    "/master/geojson/ne_110m_admin_0_countries.geojson"
)


def fetch_basemap(cfg: Config) -> Image.Image:
    """Return a basemap image for ``cfg.bbox`` at ``cfg.width`` × ``cfg.height``."""

    if cfg.basemap_style == "boundaries":
        return _fetch_boundary_basemap(cfg)
    return _fetch_satellite_basemap(cfg)


def _fetch_boundary_basemap(cfg: Config) -> Image.Image:
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath
    import numpy as np

    geojson = _get_naturalearth(cfg)
    west, south, east, north = cfg.bbox

    dpi = 100
    figw = cfg.width / dpi
    figh = cfg.height / dpi

    fig, ax = plt.subplots(figsize=(figw, figh), dpi=dpi)
    fig.patch.set_facecolor("#b8d4e8")
    ax.set_position([0, 0, 1, 1])
    ax.set_xlim(west, east)
    ax.set_ylim(south, north)
    ax.set_aspect("auto")
    ax.axis("off")
    ax.set_facecolor("#b8d4e8")

    for feature in geojson["features"]:
        geom = feature["geometry"]
        if geom["type"] == "Polygon":
            _add_polygon_patch(ax, geom["coordinates"])
        elif geom["type"] == "MultiPolygon":
            for rings in geom["coordinates"]:
                _add_polygon_patch(ax, rings)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, bbox_inches=None, pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    image = Image.open(buf).convert("RGBA")
    image = image.resize((cfg.width, cfg.height), Image.Resampling.LANCZOS)
    return image


def _add_polygon_patch(ax, rings) -> None:
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MplPath

    verts = []
    codes = []
    for ring in rings:
        if len(ring) < 2:
            continue
        verts.extend(ring)
        verts.append(ring[0])
        codes.append(MplPath.MOVETO)
        codes.extend([MplPath.LINETO] * (len(ring) - 1))
        codes.append(MplPath.CLOSEPOLY)

    if not verts:
        return

    path = MplPath(verts, codes)
    patch = PathPatch(
        path,
        facecolor="#efefeb",
        edgecolor="#aaaaaa",
        linewidth=0.5,
        antialiased=True,
    )
    ax.add_patch(patch)


def _get_naturalearth(cfg: Config) -> dict:
    cache_file = cfg.cache_path / "naturalearth" / "ne_110m_admin_0_countries.geojson"
    if cache_file.exists():
        return json.loads(cache_file.read_text())

    LOGGER.info("Downloading Natural Earth 110m countries GeoJSON")
    response = requests.get(NE_GEOJSON_URL, timeout=60)
    response.raise_for_status()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_bytes(response.content)
    return response.json()


def _fetch_satellite_basemap(cfg: Config) -> Image.Image:
    zoom = _select_zoom(cfg)
    tiles = list(mercantile.tiles(*cfg.bbox, zooms=[zoom]))
    if not tiles:
        raise RuntimeError(f"No basemap tiles found for bbox={cfg.bbox} zoom={zoom}")

    cache_dir = cfg.cache_path / "gibs" / cfg.basemap_layer / str(zoom)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fetched = _fetch_tiles(tiles, cfg.basemap_layer, cache_dir, cfg)

    xs = sorted({tile.x for tile in tiles})
    ys = sorted({tile.y for tile in tiles})
    x_index = {x: idx for idx, x in enumerate(xs)}
    y_index = {y: idx for idx, y in enumerate(ys)}
    mosaic = Image.new("RGB", (len(xs) * TILE_SIZE, len(ys) * TILE_SIZE))

    for tile, image in fetched.items():
        mosaic.paste(image, (x_index[tile.x] * TILE_SIZE, y_index[tile.y] * TILE_SIZE))

    cropped = _crop_to_bbox(mosaic, cfg.bbox, xs, ys, zoom)
    resized = cropped.resize((cfg.width, cfg.height), Image.Resampling.LANCZOS)
    rgba = resized.convert("RGBA")
    if cfg.basemap_opacity < 1:
        alpha = rgba.getchannel("A").point(lambda value: int(value * cfg.basemap_opacity))
        rgba.putalpha(alpha)
    return rgba


def _fetch_tiles(
    tiles: Iterable[mercantile.Tile],
    layer: str,
    cache_dir: Path,
    cfg: Config,
) -> dict[mercantile.Tile, Image.Image]:
    tile_list = list(tiles)
    results: dict[mercantile.Tile, Image.Image] = {}
    with ThreadPoolExecutor(max_workers=min(cfg.basemap_tile_workers, len(tile_list))) as executor:
        futures = {
            executor.submit(_fetch_tile, tile, layer, cache_dir): tile
            for tile in tile_list
        }
        for future in as_completed(futures):
            tile = futures[future]
            results[tile] = future.result()
    return results


def _fetch_tile(tile: mercantile.Tile, layer: str, cache_dir: Path) -> Image.Image:
    path = cache_dir / str(tile.y) / f"{tile.x}.jpeg"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        url = GIBS_URL.format(
            layer=layer,
            matrix_set=GIBS_MATRIX_SET,
            z=tile.z,
            y=tile.y,
            x=tile.x,
        )
        LOGGER.debug("Fetching GIBS tile %s", url)
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        path.write_bytes(response.content)
    with Image.open(path) as image:
        return image.convert("RGB")


def _select_zoom(cfg: Config) -> int:
    west, south, east, north = cfg.bbox
    west_x, _ = mercantile.xy(west, 0)
    east_x, _ = mercantile.xy(east, 0)
    _, south_y = mercantile.xy(0, _clamp_lat(south))
    _, north_y = mercantile.xy(0, _clamp_lat(north))
    world_meters = 2 * math.pi * 6378137

    x_fraction = abs(east_x - west_x) / world_meters
    y_fraction = abs(north_y - south_y) / world_meters
    target_fraction = max(
        cfg.width / max(x_fraction, 1e-9),
        cfg.height / max(y_fraction, 1e-9),
    )
    zoom = math.ceil(math.log2(target_fraction / TILE_SIZE))
    return max(0, min(cfg.basemap_max_zoom, zoom))


def _crop_to_bbox(
    mosaic: Image.Image,
    bbox: list[float],
    xs: list[int],
    ys: list[int],
    zoom: int,
) -> Image.Image:
    west, south, east, north = bbox
    left_tile = mercantile.Tile(xs[0], ys[0], zoom)
    tile_bounds = mercantile.xy_bounds(left_tile)
    meters_per_pixel = (tile_bounds.right - tile_bounds.left) / TILE_SIZE

    mosaic_left = mercantile.xy_bounds(mercantile.Tile(xs[0], ys[0], zoom)).left
    mosaic_top = mercantile.xy_bounds(mercantile.Tile(xs[0], ys[0], zoom)).top

    bbox_left, bbox_bottom = mercantile.xy(west, _clamp_lat(south))
    bbox_right, bbox_top = mercantile.xy(east, _clamp_lat(north))

    crop_left = int(max(0, math.floor((bbox_left - mosaic_left) / meters_per_pixel)))
    crop_top = int(max(0, math.floor((mosaic_top - bbox_top) / meters_per_pixel)))
    crop_right = int(
        min(mosaic.width, math.ceil((bbox_right - mosaic_left) / meters_per_pixel))
    )
    crop_bottom = int(
        min(mosaic.height, math.ceil((mosaic_top - bbox_bottom) / meters_per_pixel))
    )
    if crop_left >= crop_right or crop_top >= crop_bottom:
        raise RuntimeError(f"Computed invalid basemap crop for bbox={bbox}")
    return mosaic.crop((crop_left, crop_top, crop_right, crop_bottom))


def _clamp_lat(lat: float) -> float:
    return max(-85.05112878, min(85.05112878, lat))
