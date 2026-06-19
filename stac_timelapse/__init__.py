"""Tools for turning STAC datasets into HLS video streams."""

from __future__ import annotations

from pathlib import Path

from .config import Config


def run(cfg: Config) -> Path:
    """Run the full pipeline, importing heavy rendering dependencies lazily."""

    from .pipeline import run as _run

    return _run(cfg)

__all__ = ["Config", "run"]
__version__ = "0.1.2"
