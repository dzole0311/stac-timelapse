"""Composite rendered data, basemaps, labels, and legends with Pillow.

The renderer works entirely in memory on RGBA PNGs so it can combine outputs
from STAC Raster API and titiler-cmr. Matplotlib
is used only for colormap lookup; all layout, text, opacity, and shadow work is
performed by Pillow.
"""

from __future__ import annotations

import io
from datetime import datetime

from .matplotlib_env import configure_matplotlib_env

configure_matplotlib_env()

from matplotlib import cm, colormaps
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import Config


def compose_frame(
    data_png: bytes,
    basemap: Image.Image,
    datetime_str: str,
    cfg: Config,
) -> bytes:
    """
    Composite data, basemap, colorbar, title, and timestamp into a PNG frame.
    """

    base = basemap.convert("RGBA").resize((cfg.width, cfg.height))
    data = Image.open(io.BytesIO(data_png)).convert("RGBA")
    if data.size != base.size:
        data = data.resize(base.size, Image.Resampling.LANCZOS)
    if cfg.data_blur_radius > 0:
        data = data.filter(ImageFilter.GaussianBlur(radius=cfg.data_blur_radius))
    data = _apply_opacity(data, cfg.data_opacity)
    frame = Image.alpha_composite(base, data)

    draw = ImageDraw.Draw(frame)
    font = _load_font(cfg.font_size)
    small_font = _load_font(max(12, int(cfg.font_size * 0.55)))

    margin = max(16, int(min(cfg.width, cfg.height) * 0.025))
    if cfg.title:
        _draw_shadowed_text(
            draw,
            (margin, margin),
            cfg.title,
            font,
            cfg.label_color,
            cfg.label_shadow,
            cfg.label_shadow_offset,
        )
    if cfg.show_date:
        date_label = _format_datetime(datetime_str, cfg.date_format)
        y = cfg.height - margin - _text_size(draw, date_label, font)[1]
        _draw_shadowed_text(
            draw,
            (margin, y),
            date_label,
            font,
            cfg.label_color,
            cfg.label_shadow,
            cfg.label_shadow_offset,
        )

    if cfg.colorbar:
        _draw_colorbar(frame, cfg, small_font, margin)

    output = io.BytesIO()
    frame.save(output, format="PNG")
    return output.getvalue()


def _apply_opacity(image: Image.Image, opacity: float) -> Image.Image:
    if opacity >= 1:
        return image
    image = image.copy()
    alpha = image.getchannel("A").point(lambda value: int(value * opacity))
    image.putalpha(alpha)
    return image


def _draw_colorbar(
    frame: Image.Image,
    cfg: Config,
    font: ImageFont.ImageFont,
    margin: int,
) -> None:
    draw = ImageDraw.Draw(frame)
    bar_w = cfg.colorbar_width
    bar_h = min(cfg.colorbar_height, cfg.height - 2 * margin)
    tick_len = 10
    label_gap = 8
    value_gap = 8
    text_probe = _format_tick(9999)
    value_w = _text_size(draw, text_probe, font)[0]
    total_w = bar_w + tick_len + value_gap + value_w

    if "right" in cfg.colorbar_position:
        x = cfg.width - margin - total_w
    else:
        x = margin
    if "bottom" in cfg.colorbar_position:
        y = cfg.height - margin - bar_h
    else:
        y = margin

    shadow_box = (x - 8, y - 8, x + total_w + 8, y + bar_h + 8)
    draw.rounded_rectangle(shadow_box, radius=4, fill=(0, 0, 0, 90))

    gradient = _colorbar_gradient(cfg.colormap_name, bar_w, bar_h)
    frame.alpha_composite(gradient, (x, y))
    draw.rectangle((x, y, x + bar_w, y + bar_h), outline=(255, 255, 255, 220), width=1)

    min_value, max_value = _parse_rescale(cfg.rescale)
    for idx in range(cfg.colorbar_ticks):
        ratio = idx / (cfg.colorbar_ticks - 1)
        tick_y = y + int((1 - ratio) * bar_h)
        value = min_value + ratio * (max_value - min_value)
        tick_label = _format_tick(value)
        tick_h = _text_size(draw, tick_label, font)[1]
        draw.line(
            (x + bar_w, tick_y, x + bar_w + tick_len, tick_y),
            fill=(255, 255, 255, 230),
            width=1,
        )
        _draw_shadowed_text(
            draw,
            (x + bar_w + tick_len + value_gap, tick_y - tick_h // 2),
            tick_label,
            font,
            cfg.label_color,
            cfg.label_shadow,
            cfg.label_shadow_offset,
        )

    if cfg.colorbar_label:
        label_img = _rotated_label(
            cfg.colorbar_label,
            font,
            cfg.label_color,
            cfg.label_shadow_offset,
        )
        label_x = x - label_img.width - label_gap
        label_y = y + (bar_h - label_img.height) // 2
        frame.alpha_composite(label_img, (max(0, label_x), max(0, label_y)))


def _colorbar_gradient(name: str, width: int, height: int) -> Image.Image:
    cmap = cm.get_cmap(_matplotlib_colormap_name(name))
    image = Image.new("RGBA", (width, height))
    pixels = image.load()
    for row in range(height):
        ratio = 1 - row / max(1, height - 1)
        red, green, blue, alpha = cmap(ratio)
        color = (
            int(red * 255),
            int(green * 255),
            int(blue * 255),
            int(alpha * 255),
        )
        for col in range(width):
            pixels[col, row] = color
    return image


def _matplotlib_colormap_name(name: str) -> str:
    """Resolve Raster API-style lowercase colormap names for Matplotlib."""

    available = list(colormaps)
    if name in available:
        return name
    lowered = name.lower()
    for candidate in available:
        if candidate.lower() == lowered:
            return candidate
    return name


def _rotated_label(
    text: str,
    font: ImageFont.ImageFont,
    color: tuple[int, int, int],
    shadow_offset: int,
) -> Image.Image:
    probe = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(probe)
    text_w, text_h = _text_size(draw, text, font)
    label = Image.new("RGBA", (text_w + 8, text_h + 8), (0, 0, 0, 0))
    label_draw = ImageDraw.Draw(label)
    _draw_shadowed_text(label_draw, (4, 4), text, font, color, True, shadow_offset)
    return label.rotate(90, expand=True)


def _draw_shadowed_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    color: tuple[int, int, int],
    shadow: bool,
    shadow_offset: int,
) -> None:
    if shadow:
        x, y = xy
        brightness = sum(color) / 3
        shadow_fill = (255, 255, 255, 160) if brightness < 128 else (0, 0, 0, 160)
        draw.text(
            (x + shadow_offset, y + shadow_offset),
            text,
            font=font,
            fill=shadow_fill,
        )
    draw.text(xy, text, font=font, fill=(*color, 255))


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in (
        "DejaVuSans.ttf",
        "Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _format_datetime(value: str, date_format: str) -> str:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).strftime(date_format)
    except ValueError:
        return value


def _parse_rescale(value: str | None) -> tuple[float, float]:
    if not value:
        return 0.0, 1.0
    try:
        left, right = value.split(",", 1)
        return float(left), float(right)
    except ValueError:
        return 0.0, 1.0


def _format_tick(value: float) -> str:
    if abs(value) >= 100:
        return f"{value:.0f}"
    if abs(value) >= 10:
        return f"{value:.1f}"
    return f"{value:.2g}"


def _text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]
