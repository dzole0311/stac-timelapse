"""Encode rendered PNG frame sequences into HLS with ffmpeg.

The package does not bundle ffmpeg; it must be available on ``PATH`` at runtime.
When ``Config.frame_hold`` is greater than one, this module builds a temporary
held-frame sequence using symlinks where the platform allows them and file
copies where it does not.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .config import Config

LOGGER = logging.getLogger(__name__)


def encode_hls(frames_dir: Path, output_dir: Path, cfg: Config) -> Path:
    """
    Encode a PNG frame sequence into HLS and return ``index.m3u8``.
    """

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required but was not found on PATH")

    frame_source = _prepare_frame_source(frames_dir, output_dir, cfg)
    output_dir.mkdir(parents=True, exist_ok=True)
    playlist = output_dir / "index.m3u8"
    segment_pattern = output_dir / "seg%03d.ts"

    command = [
        ffmpeg,
        "-y",
        "-framerate",
        str(cfg.fps),
        "-i",
        str(frame_source / "frame_%05d.png"),
        "-c:v",
        cfg.video_codec,
        "-crf",
        str(cfg.crf),
        "-preset",
        cfg.preset,
        "-pix_fmt",
        "yuv420p",
        "-hls_time",
        str(cfg.hls_segment_duration),
        "-hls_list_size",
        "0",
        "-hls_playlist_type",
        "vod",
        "-hls_segment_filename",
        str(segment_pattern),
        str(playlist),
    ]

    LOGGER.info("Running ffmpeg: %s", " ".join(command))
    process = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert process.stderr is not None
    for line in process.stderr:
        LOGGER.info("ffmpeg: %s", line.rstrip())
    return_code = process.wait()
    if return_code:
        raise RuntimeError(f"ffmpeg failed with exit code {return_code}")
    return playlist


def _prepare_frame_source(frames_dir: Path, output_dir: Path, cfg: Config) -> Path:
    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        raise RuntimeError(f"No frames found in {frames_dir}")
    if cfg.frame_hold <= 1:
        return frames_dir

    held_dir = output_dir / "_held_frames"
    held_dir.mkdir(parents=True, exist_ok=True)
    for old_frame in held_dir.glob("frame_*.png"):
        old_frame.unlink()

    index = 0
    for frame in frames:
        for _ in range(cfg.frame_hold):
            target = held_dir / f"frame_{index:05d}.png"
            try:
                target.symlink_to(frame.resolve())
            except OSError:
                shutil.copy2(frame, target)
            index += 1
    return held_dir
