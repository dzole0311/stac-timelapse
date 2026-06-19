# Getting Started

!!! warning "Experimental"
    This project is under active development. APIs and configuration options may change without notice.

## Install

Python 3.11 or newer is required. `ffmpeg` must be on `PATH`.

```sh
pip install stac-timelapse           # local rendering only
pip install stac-timelapse[aws]      # + S3 upload
pip install stac-timelapse[server]   # + FastAPI/SQS job server
brew install ffmpeg                  # macOS
apt install ffmpeg                   # Ubuntu / Debian
```

## STAC mode

Queries a STAC catalog and renders through the Raster API.

```sh
stac-timelapse \
  --collection no2-monthly \
  --start 2022-01-01 \
  --end 2022-12-31 \
  --bbox "-74.3,40.4,-73.6,40.9" \
  --assets cog_default \
  --colormap rdbu \
  --rescale "0,75" \
  --colorbar-label "NO2 column" \
  --title "New York NO2 2022" \
  --fps 10 \
  --out ./nyc-no2
```

The playlist is written to `./nyc-no2/index.m3u8`.

Use `--stac-api` and `--raster-api` to point at a different endpoint.

## titiler-cmr mode

Renders STAC collections through titiler-cmr (xarray or rasterio backend) instead of the Raster API.

```sh
stac-timelapse \
  --use-cmr \
  --cmr-collection-concept-id C2723754864-GES_DISC \
  --cmr-variable precipitation \
  --cmr-date-frequency daily \
  --start 2024-06-01 \
  --end 2024-10-31 \
  --bbox "-180,-70,180,75" \
  --rescale "0,48" \
  --colormap blues \
  --basemap-style boundaries \
  --colorbar-label "Precipitation (mm/day)" \
  --title "GPM IMERG Global Jun-Oct 2024" \
  --out ./gpm-imerg-global
```

## Python API

```python
from stac_timelapse import Config, run

cfg = Config(
    use_cmr=True,
    cmr_collection_concept_id="C2723754864-GES_DISC",
    cmr_variable="precipitation",
    cmr_date_frequency="daily",
    datetime_start="2024-06-01",
    datetime_end="2024-10-31",
    bbox=[-180.0, -70.0, 180.0, 75.0],
    rescale="0,48",
    colormap_name="blues",
    basemap_style="boundaries",
    colorbar_label="Precipitation (mm/day)",
    title="GPM IMERG Global Jun-Oct 2024",
    output_dir="./gpm-imerg-global",
)

playlist = run(cfg)
print(playlist)
```

## Upload to S3

Set `s3_bucket` (and optionally `s3_prefix`) on `Config`. The pipeline runs as normal and then uploads the m3u8 and segments to S3, returning the S3 URL.

```python
cfg = Config(
    ...,
    s3_bucket="my-bucket",
    s3_prefix="renders/gpm-global",
    output_dir="./tmp-output",
)

s3_url = run(cfg)  # returns s3://my-bucket/renders/gpm-global/index.m3u8
```

Requires `pip install stac-timelapse[aws]` and AWS credentials available in the environment.

## EC2 deployment

For large or automated renders, run the job server on EC2. The same Docker image serves both the API and the worker - set `CMD` to select which process to start.

**Prerequisites:** an SQS queue and an S3 bucket. The EC2 instance role needs `sqs:*` on the queue and `s3:PutObject` on the bucket.

```sh
docker build -t stac-timelapse .

# API server (accepts job submissions)
docker run -p 8000:8000 \
  -e SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/veda-jobs \
  -e S3_BUCKET=my-bucket \
  stac-timelapse

# Worker (polls SQS, runs renders, uploads to S3)
docker run \
  -e SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/veda-jobs \
  -e S3_BUCKET=my-bucket \
  stac-timelapse python server/worker.py
```

Submit a job:

```sh
curl -X POST http://<ec2-host>:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"config": {"use_cmr": true, "cmr_collection_concept_id": "C2723754864-GES_DISC", "cmr_variable": "precipitation", "cmr_date_frequency": "daily", "datetime_start": "2024-06-01", "datetime_end": "2024-10-31", "bbox": [-180, -70, 180, 75], "colormap_name": "blues", "rescale": "0,48", "output_dir": "/tmp/render"}}'
```

Poll for completion:

```sh
curl http://<ec2-host>:8000/jobs/<job_id>
# {"job_id": "...", "status": "done", "s3_prefix": "jobs/<job_id>"}
```

Job status is determined by S3: `index.m3u8` present means done, `error.json` present means failed, neither means still running.

## Play the output locally

```sh
cd gpm-imerg-global
python -m http.server 8080
```

Open `http://localhost:8080/index.m3u8` in [HLS.js demo](https://hlsjs.video-dev.org/demo/) or VLC.

## Visualize on a globe or map

To render the HLS output on an interactive 2D/3D map, see [hls-streaming-layer](https://github.com/dzole0311/hls-streaming-layer), a glue library for streaming HLS video on Mapbox GL in 2D and globe projections. Point it at the `index.m3u8` produced by stac-timelapse.

More map integration examples are coming soon.
