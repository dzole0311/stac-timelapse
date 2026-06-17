# veda-timelapse

**Docs:** https://dzole0311.github.io/veda-timelapse/

Generate GLS video streams from STAC collections. Composites a basemap, data layer, colorbar, and timestamp into PNG frames, then encodes them to `index.m3u8`.

Two render modes:

- **STAC** -- renders VEDA STAC collections through the VEDA Raster API
- **CMR** -- renders CMR granules through titiler-cmr (e.g. GPM IMERG)

## Requirements

Python 3.11 or newer. `ffmpeg` must be on `PATH`:

```sh
brew install ffmpeg        # macOS
apt-get install ffmpeg     # Debian/Ubuntu
```

Install the package:

```sh
pip install veda-timelapse
```

## Quick start

**CMR mode (GPM IMERG global precipitation):**

```python
from veda_timelapse import Config, run

cfg = Config(
    use_cmr=True,
    cmr_collection_concept_id="C2723754864-GES_DISC",
    cmr_variable="precipitation",
    cmr_date_frequency="daily",
    datetime_start="2024-06-01",
    datetime_end="2024-10-31",
    bbox=[-180.0, -70.0, 180.0, 75.0],
    width=1920, height=960,
    rescale="0,48",
    colormap_name="blues",
    cmr_dry_luminance_threshold=255.0,
    basemap=True, basemap_style="boundaries",
    colorbar_label="Precipitation (mm/day)",
    title="GPM IMERG Global Jun-Oct 2024",
    output_dir="./gpm-global",
)

playlist = run(cfg)
print(playlist)
```

**STAC mode (CLI):**

```sh
veda-timelapse \
  --collection no2-monthly \
  --start 2022-01-01 \
  --end 2022-12-31 \
  --bbox "-74.3,40.4,-73.6,40.9" \
  --assets cog_default \
  --colormap rdbu \
  --rescale "0,75" \
  --colorbar-label "NO2 column" \
  --title "New York City NO2 2022" \
  --out ./nyc-no2
```

## S3 upload

Add `s3_bucket` to upload the HLS output to S3 after encoding:

```python
cfg = Config(
    ...,
    s3_bucket="my-bucket",
    s3_prefix="renders/my-job",
)
```

Requires `pip install veda-timelapse[aws]` and standard AWS credentials.

## Docs

```sh
mkdocs serve
```
