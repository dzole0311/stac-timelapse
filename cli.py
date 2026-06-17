"""Command line interface for veda-timelapse.

The CLI mirrors the ``Config`` dataclass and supports STAC and CMR render modes.
STAC is the default; CMR bypasses STAC collection lookup and validates its own
required fields at runtime.
"""

from __future__ import annotations

import logging
from typing import Any

import click

from veda_timelapse import Config, run
from veda_timelapse.config import clean_optional, parse_bbox, parse_csv, parse_rgb


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--stac-api", default=Config.stac_api, show_default=True)
@click.option("--raster-api", default=Config.raster_api, show_default=True)
@click.option("--auth-token", envvar="VEDA_TIMELAPSE_TOKEN")
@click.option(
    "-c",
    "--collection",
    "--collection-id",
    "collection_id",
    default="",
    help="STAC collection id.",
)
@click.option("-s", "--start", "datetime_start", required=True, help="Start date/time.")
@click.option("-e", "--end", "datetime_end", required=True, help="End date/time.")
@click.option(
    "-b",
    "--bbox",
    required=True,
    help="west,south,east,north in EPSG:4326.",
)
@click.option("--assets", default="", help="Comma-separated asset names.")
@click.option("--expression", help="Raster expression or band math.")
@click.option("--colormap", "--colormap-name", "colormap_name", default=Config.colormap_name)
@click.option(
    "--rescale",
    default=Config.rescale,
    help="min,max range. Pass an empty string to request percentile stretch.",
)
@click.option("--algorithm", help="Raster API algorithm name.")
@click.option("--use-cmr", is_flag=True, help="Render through titiler-cmr.")
@click.option("--cmr-tiler-url", default=Config.cmr_tiler_url, show_default=True)
@click.option("--cmr-collection-concept-id", default=Config.cmr_collection_concept_id)
@click.option("--cmr-variable", default=Config.cmr_variable)
@click.option(
    "--cmr-backend",
    default=Config.cmr_backend,
    show_default=True,
    type=click.Choice(["xarray", "rasterio"]),
)
@click.option(
    "--cmr-date-frequency",
    default=Config.cmr_date_frequency,
    show_default=True,
    type=click.Choice(["30min", "daily", "monthly"]),
)
@click.option(
    "--cmr-dry-luminance-threshold",
    default=Config.cmr_dry_luminance_threshold,
    show_default=True,
    type=float,
)
@click.option("--cache-dir", default=Config.cache_dir, show_default=True)
@click.option("--download-retries", default=Config.download_retries, show_default=True, type=int)
@click.option("--download-timeout", default=Config.download_timeout, show_default=True, type=int)
@click.option("--width", default=Config.width, show_default=True, type=int)
@click.option("--height", default=Config.height, show_default=True, type=int)
@click.option("--fps", default=Config.fps, show_default=True, type=int)
@click.option("--frame-hold", default=Config.frame_hold, show_default=True, type=int)
@click.option("--data-blur-radius", default=Config.data_blur_radius, show_default=True, type=float)
@click.option("--basemap/--no-basemap", default=Config.basemap, show_default=True)
@click.option(
    "--basemap-style",
    default=Config.basemap_style,
    show_default=True,
    type=click.Choice(["boundaries", "satellite"]),
)
@click.option("--basemap-layer", default=Config.basemap_layer, show_default=True)
@click.option("--basemap-max-zoom", default=Config.basemap_max_zoom, show_default=True, type=int)
@click.option(
    "--basemap-tile-workers",
    default=Config.basemap_tile_workers,
    show_default=True,
    type=int,
)
@click.option(
    "--basemap-opacity",
    default=Config.basemap_opacity,
    show_default=True,
    type=click.FloatRange(0, 1),
)
@click.option(
    "--data-opacity",
    default=Config.data_opacity,
    show_default=True,
    type=click.FloatRange(0, 1),
)
@click.option("--colorbar/--no-colorbar", default=Config.colorbar, show_default=True)
@click.option("--colorbar-label", default=Config.colorbar_label)
@click.option("--colorbar-width", default=Config.colorbar_width, show_default=True, type=int)
@click.option("--colorbar-height", default=Config.colorbar_height, show_default=True, type=int)
@click.option("--colorbar-ticks", default=Config.colorbar_ticks, show_default=True, type=int)
@click.option(
    "--colorbar-position",
    default=Config.colorbar_position,
    show_default=True,
    type=click.Choice(["top-left", "top-right", "bottom-left", "bottom-right"]),
)
@click.option("--title", default=Config.title)
@click.option("--show-date/--no-show-date", default=Config.show_date, show_default=True)
@click.option("--date-format", default=Config.date_format, show_default=True)
@click.option("--font-size", default=Config.font_size, show_default=True, type=int)
@click.option("--label-color", default="255,255,255", show_default=True)
@click.option("--label-shadow/--no-label-shadow", default=Config.label_shadow, show_default=True)
@click.option(
    "--label-shadow-offset",
    default=Config.label_shadow_offset,
    show_default=True,
    type=int,
)
@click.option(
    "-o",
    "--out",
    "--output-dir",
    "output_dir",
    default=Config.output_dir,
    show_default=True,
)
@click.option("--frames-dir", help="Directory for intermediate PNG frames.")
@click.option(
    "--hls-segment-duration",
    default=Config.hls_segment_duration,
    show_default=True,
    type=int,
)
@click.option("--video-codec", default=Config.video_codec, show_default=True)
@click.option("--crf", default=Config.crf, show_default=True, type=int)
@click.option("--preset", default=Config.preset, show_default=True)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging.")
def main(**kwargs: Any) -> None:
    """Render a VEDA/STAC collection into an HLS video stream."""

    verbose = kwargs.pop("verbose")
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )

    try:
        cfg = Config(
            stac_api=kwargs["stac_api"],
            raster_api=kwargs["raster_api"],
            auth_token=clean_optional(kwargs["auth_token"]),
            collection_id=kwargs["collection_id"],
            datetime_start=kwargs["datetime_start"],
            datetime_end=kwargs["datetime_end"],
            bbox=parse_bbox(kwargs["bbox"]),
            assets=parse_csv(kwargs["assets"]),
            expression=clean_optional(kwargs["expression"]),
            colormap_name=kwargs["colormap_name"],
            rescale=clean_optional(kwargs["rescale"]),
            algorithm=clean_optional(kwargs["algorithm"]),
            use_cmr=kwargs["use_cmr"],
            cmr_tiler_url=kwargs["cmr_tiler_url"],
            cmr_collection_concept_id=kwargs["cmr_collection_concept_id"],
            cmr_variable=kwargs["cmr_variable"],
            cmr_backend=kwargs["cmr_backend"],
            cmr_date_frequency=kwargs["cmr_date_frequency"],
            cmr_dry_luminance_threshold=kwargs["cmr_dry_luminance_threshold"],
            cache_dir=kwargs["cache_dir"],
            download_retries=kwargs["download_retries"],
            download_timeout=kwargs["download_timeout"],
            width=kwargs["width"],
            height=kwargs["height"],
            fps=kwargs["fps"],
            frame_hold=kwargs["frame_hold"],
            data_blur_radius=kwargs["data_blur_radius"],
            basemap=kwargs["basemap"],
            basemap_style=kwargs["basemap_style"],
            basemap_layer=kwargs["basemap_layer"],
            basemap_max_zoom=kwargs["basemap_max_zoom"],
            basemap_tile_workers=kwargs["basemap_tile_workers"],
            basemap_opacity=kwargs["basemap_opacity"],
            data_opacity=kwargs["data_opacity"],
            colorbar=kwargs["colorbar"],
            colorbar_label=kwargs["colorbar_label"],
            colorbar_width=kwargs["colorbar_width"],
            colorbar_height=kwargs["colorbar_height"],
            colorbar_position=kwargs["colorbar_position"],
            colorbar_ticks=kwargs["colorbar_ticks"],
            title=kwargs["title"],
            show_date=kwargs["show_date"],
            date_format=kwargs["date_format"],
            font_size=kwargs["font_size"],
            label_color=parse_rgb(kwargs["label_color"]),
            label_shadow=kwargs["label_shadow"],
            label_shadow_offset=kwargs["label_shadow_offset"],
            output_dir=kwargs["output_dir"],
            frames_dir=clean_optional(kwargs["frames_dir"]),
            hls_segment_duration=kwargs["hls_segment_duration"],
            video_codec=kwargs["video_codec"],
            crf=kwargs["crf"],
            preset=kwargs["preset"],
        )
        playlist = run(cfg)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(str(playlist))


if __name__ == "__main__":
    main()
