"""Hurricane Beryl MODIS thermal infrared timelapse.

MODIS Aqua Band 31 (11µm thermal IR): cold = high cloud tops = intense convection.
16 daily frames showing the storm's Atlantic-to-Gulf track and landfall.
"""

from stac_timelapse.config import Config
from stac_timelapse.pipeline import run

cfg = Config(
    collection_id="modis_mosaic-cyclone-beryl",
    assets=["cog_default"],
    bbox=[-102.8, 6.2, -13.3, 49.1],
    datetime_start="2024-06-26",
    datetime_end="2024-07-11",
    width=960,
    height=540,
    rescale="5000,30000",
    colormap_name="bupu_r",
    fps=4,
    basemap=True,
    data_opacity=0.75,
    output_dir="/tmp/beryl_hls",
)

result = run(cfg)
print(f"HLS output: {result}")
