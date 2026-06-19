"""
GPM IMERG daily precipitation — global, Jun–Oct 2024.

Boundaries basemap so no-data land areas render as light colour with country
outlines only, making global coverage gaps immediately visible.
"""
from stac_timelapse import Config, run

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
