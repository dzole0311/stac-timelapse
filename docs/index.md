# stac-timelapse

Takes STAC datasets and produces HLS video streams with a basemap, data layer, colorbar, and timestamp on each frame. Output goes to local disk or directly to S3.

!!! warning "Experimental"
    This project is under active development. APIs and configuration options may change without notice.

```sh
stac-timelapse \
  --use-cmr \
  --cmr-collection-concept-id C2723754864-GES_DISC \
  --cmr-variable precipitation \
  --cmr-date-frequency daily \
  --start 2024-06-01 --end 2024-10-31 \
  --bbox "-180,-70,180,75" \
  --colormap blues --rescale "0,48" \
  --basemap-style boundaries \
  --title "GPM IMERG Global" \
  --out ./gpm-global
```

Output is `gpm-global/index.m3u8` plus `.ts` segments.

## How it works

1. Queries STAC for each requested timestep
2. Fetches a rendered PNG for each timestep
3. Composites a basemap underneath the data (satellite imagery or country boundaries)
4. Draws a colorbar and timestamp label on each frame
5. Encodes the frames into HLS with ffmpeg
6. Optionally uploads the output to S3

## Render modes

Both modes use STAC. The difference is the tiler backend.

**Raster API** (default) renders each STAC item through the Raster API (titiler-pgstac).

**titiler-cmr** renders STAC items through titiler-cmr's xarray or rasterio backends. Useful for collections like GPM IMERG that are served via titiler-cmr.

## Deployment

Runs locally with no AWS dependency. For large renders, a FastAPI + SQS + EC2 deployment is available - see [Getting Started](getting-started.md).

## Requirements

- Python 3.11 or newer
- `ffmpeg` on `PATH`

```sh
pip install stac-timelapse        # local use
pip install stac-timelapse[aws]   # + S3 upload
pip install stac-timelapse[server] # + FastAPI/SQS server
brew install ffmpeg               # macOS
```
