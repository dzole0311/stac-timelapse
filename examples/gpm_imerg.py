"""
GPM IMERG daily precipitation over the Atlantic hurricane belt, Aug-Sep 2024.
Renders through titiler-cmr using the CMR collection concept ID.
"""
from stac_timelapse import Config, run

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
