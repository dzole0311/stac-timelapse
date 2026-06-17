# Examples

## GPM IMERG precipitation - daily

Daily precipitation from GPM IMERG over the Atlantic hurricane belt, June through October 2024. Rendered through titiler-cmr using the CMR collection concept ID, overlaid on a country boundary basemap.

<video controls width="100%" style="border-radius:6px">
  <source src="../media/gpm_precipitation.mp4" type="video/mp4">
</video>

**CLI**

```sh
veda-timelapse \
  --use-cmr \
  --cmr-collection-concept-id C2723754864-GES_DISC \
  --cmr-variable precipitation \
  --cmr-date-frequency daily \
  --start 2024-06-01 \
  --end 2024-10-31 \
  --bbox "-100,5,-40,35" \
  --width 960 \
  --height 540 \
  --rescale "0,48" \
  --colormap blues \
  --fps 4 \
  --basemap \
  --basemap-style boundaries \
  --data-opacity 0.75 \
  --colorbar-label "Precipitation (mm/day)" \
  --title "GPM IMERG Atlantic Jun-Oct 2024" \
  --out ./gpm-imerg
```

**Python**

```python
from veda_timelapse import Config, run

cfg = Config(
    use_cmr=True,
    cmr_collection_concept_id="C2723754864-GES_DISC",
    cmr_variable="precipitation",
    cmr_date_frequency="daily",
    datetime_start="2024-06-01",
    datetime_end="2024-10-31",
    bbox=[-100.0, 5.0, -40.0, 35.0],
    width=960,
    height=540,
    rescale="0,48",
    colormap_name="blues",
    fps=4,
    basemap=True,
    basemap_style="boundaries",
    data_opacity=0.75,
    colorbar_label="Precipitation (mm/day)",
    title="GPM IMERG Atlantic Jun-Oct 2024",
    output_dir="./gpm-imerg",
)

print(run(cfg))
```

153 frames, one per day. Output at `./gpm-imerg/index.m3u8`.

---

## GPM IMERG precipitation - global

Daily precipitation from GPM IMERG at global scale, June through October 2024.

<video controls width="100%" style="border-radius:6px">
  <source src="../media/gpm_imerg_global.mp4" type="video/mp4">
</video>

**CLI**

```sh
veda-timelapse \
  --use-cmr \
  --cmr-collection-concept-id C2723754864-GES_DISC \
  --cmr-variable precipitation \
  --cmr-date-frequency daily \
  --start 2024-06-01 \
  --end 2024-10-31 \
  --bbox "-180,-70,180,75" \
  --width 1920 \
  --height 960 \
  --rescale "0,48" \
  --colormap blues \
  --cmr-dry-luminance-threshold 255.0 \
  --fps 6 \
  --basemap \
  --basemap-style boundaries \
  --data-opacity 0.85 \
  --colorbar-label "Precipitation (mm/day)" \
  --label-color "20,20,20" \
  --title "GPM IMERG Global Jun-Oct 2024" \
  --out ./gpm-imerg-global
```

**Python**

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
    width=1920,
    height=960,
    rescale="0,48",
    colormap_name="blues",
    cmr_dry_luminance_threshold=255.0,
    fps=6,
    basemap=True,
    basemap_style="boundaries",
    data_opacity=0.85,
    colorbar_label="Precipitation (mm/day)",
    label_color=(20, 20, 20),
    title="GPM IMERG Global Jun–Oct 2024",
    output_dir="./gpm-imerg-global",
)

print(run(cfg))
```

153 frames, one per day. Output at `./gpm-imerg-global/index.m3u8`.
