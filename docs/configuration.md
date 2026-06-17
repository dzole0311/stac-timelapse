# Configuration

Every option can be set on the `Config` dataclass in Python. Most are also available as CLI flags.

---

## Render mode

Both modes use STAC. The default renders through the VEDA Raster API; the titiler-cmr mode uses titiler-cmr's xarray or rasterio backends instead.

| Option | Default | Description |
|---|---|---|
| `--use-cmr` | off | Use titiler-cmr backend instead of the Raster API |

---

## Raster API mode (default)

| Option | Default | Description |
|---|---|---|
| `--collection` | required | VEDA STAC collection ID |
| `--assets` | | Comma-separated asset names, e.g. `cog_default` |
| `--expression` | | Band math expression |
| `--algorithm` | | Raster API algorithm name |
| `--stac-api` | `https://openveda.cloud/api/stac` | STAC API root |
| `--raster-api` | `https://openveda.cloud/api/raster` | Raster API root |
| `--auth-token` | env `VEDA_TIMELAPSE_TOKEN` | Bearer token for private collections |

---

## titiler-cmr mode

| Option | Default | Description |
|---|---|---|
| `--cmr-collection-concept-id` | required | STAC collection concept ID |
| `--cmr-variable` | required | Variable name |
| `--cmr-backend` | `xarray` | titiler-cmr backend: `xarray` or `rasterio` |
| `--cmr-date-frequency` | `daily` | Cadence: `30min`, `daily`, or `monthly` |
| `--cmr-dry-luminance-threshold` | `230.0` | Pixels brighter than this become transparent |
| `--cmr-tiler-url` | `https://openveda.cloud/api/titiler-cmr` | titiler-cmr service root |

---

## Date and area

| Option | Default | Description |
|---|---|---|
| `--start` | required | Start date or ISO timestamp |
| `--end` | required | End date or ISO timestamp |
| `--bbox` | required | `west,south,east,north` in decimal degrees |

---

## Rendering

| Option | Default | Description |
|---|---|---|
| `--colormap` | `rdbu` | Matplotlib colormap name |
| `--rescale` | `0,3000` | `min,max` data range |
| `--width` | `1920` | Frame width in pixels |
| `--height` | `1080` | Frame height in pixels |
| `--fps` | `10` | Frames per second |
| `--frame-hold` | `1` | Repeat each frame N times |
| `--data-blur-radius` | `0.0` | Gaussian blur on the data layer |
| `--data-opacity` | `0.85` | Data layer opacity (0 to 1) |

---

## Basemap

Two styles are available. `boundaries` draws Natural Earth country outlines with matplotlib and works fully offline after the first GeoJSON fetch. `satellite` fetches and stitches NASA GIBS Blue Marble tiles.

| Option | Default | Description |
|---|---|---|
| `--no-basemap` | off | Disable basemap entirely |
| `--basemap-style` | `boundaries` | `boundaries` for country outlines, `satellite` for NASA GIBS imagery |
| `--basemap-layer` | `BlueMarble_ShadedRelief_Bathymetry` | NASA GIBS layer name (satellite style only) |
| `--basemap-max-zoom` | `8` | Maximum GIBS tile zoom level (satellite style only) |
| `--basemap-tile-workers` | `16` | Parallel tile downloads (satellite style only) |
| `--basemap-opacity` | `1.0` | Basemap opacity (0 to 1) |

---

## Colorbar

| Option | Default | Description |
|---|---|---|
| `--no-colorbar` | off | Disable colorbar |
| `--colorbar-label` | | Unit label, e.g. `NO2 column` |
| `--colorbar-width` | `30` | Width in pixels |
| `--colorbar-height` | `300` | Height in pixels |
| `--colorbar-position` | `bottom-right` | `top-left`, `top-right`, `bottom-left`, or `bottom-right` |
| `--colorbar-ticks` | `5` | Number of tick labels |

---

## Labels

| Option | Default | Description |
|---|---|---|
| `--title` | | Title drawn top-left on every frame |
| `--no-show-date` | off | Hide the date stamp |
| `--date-format` | `%Y-%m-%d` | Python `strftime` format |
| `--font-size` | `36` | Label font size |
| `--label-color` | `255,255,255` | Label color as `r,g,b` |
| `--label-shadow-offset` | `2` | Drop shadow offset in pixels |

---

## Caching and downloads

| Option | Default | Description |
|---|---|---|
| `--cache-dir` | `~/.cache/veda_timelapse` | Cache root for GIBS tiles and downloaded data |
| `--download-retries` | `3` | Retry attempts for failed downloads |
| `--download-timeout` | `180` | Per-request timeout in seconds |

---

## S3 output

When `s3_bucket` is set the HLS output is uploaded to S3 after the local encode. Requires `pip install veda-timelapse[aws]` and standard AWS credentials (`AWS_ACCESS_KEY_ID` / instance role / `~/.aws/credentials`).

| Option | Default | Description |
|---|---|---|
| `--s3-bucket` | | S3 bucket name. If omitted, output stays on local disk |
| `--s3-prefix` | `renders` | Key prefix inside the bucket |
| `--s3-public` | off | Set `ACL=public-read` on uploaded objects |

---

## Encoding

| Option | Default | Description |
|---|---|---|
| `--out` | `./output` | Local output directory (also used as staging area when uploading to S3) |
| `--frames-dir` | | Keep intermediate PNG frames here instead of a temp dir |
| `--hls-segment-duration` | `4` | HLS segment length in seconds |
| `--video-codec` | `libx264` | ffmpeg video codec |
| `--crf` | `18` | ffmpeg CRF quality (lower = better) |
| `--preset` | `slow` | ffmpeg encoding speed preset |
