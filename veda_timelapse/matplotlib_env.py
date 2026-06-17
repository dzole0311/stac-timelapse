"""Prepare matplotlib for non-interactive rendering imports.

The package only needs matplotlib for colormap lookup, but matplotlib still
initializes a config/cache directory on import. Setting ``MPLCONFIGDIR`` before
that import keeps generated font caches out of the repository and avoids
warnings on systems where the default user config directory is not writable.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def configure_matplotlib_env() -> None:
    """Set a writable matplotlib config directory if the caller did not."""

    if os.environ.get("MPLCONFIGDIR"):
        return

    path = Path.home() / ".cache" / "veda_timelapse" / "matplotlib"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        path = Path(tempfile.mkdtemp(prefix="veda_timelapse_mpl_"))
    os.environ["MPLCONFIGDIR"] = str(path)
