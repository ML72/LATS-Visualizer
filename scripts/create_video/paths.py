"""
Where the video pipeline reads and writes.

Everything the renderer produces lands under ``results/`` at the repository
root, which is gitignored:

::

    results/video/20260830-010025/    one render - the mp4s, the timings, SCRIPT.md
    results/video/.manim_cache/       Manim's own output tree, shared by every render

Manim renders each part in a separate process, so the run directory cannot
simply be passed as an argument. ``create_video.py`` chooses it and exports it
as :data:`RUN_DIR_ENV`; the scene base class reads it back through
:func:`run_dir` when it writes a part's timing file.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

#: Repository root. This file is ``<root>/scripts/create_video/paths.py``.
REPO_ROOT = Path(__file__).resolve().parents[2]

RESULTS = REPO_ROOT / "results"
VIDEO_RESULTS = RESULTS / "video"

#: Manim's media directory, shared across renders on purpose: compiling the
#: equations with LaTeX is the slowest part of a cold render, and Manim keys
#: that cache by content, so it stays valid from one run to the next.
MANIM_CACHE = VIDEO_RESULTS / ".manim_cache"

#: Environment variable carrying the run directory into the Manim subprocesses.
RUN_DIR_ENV = "LATS_RUN_DIR"

#: Run directories are named for the moment the render started.
STAMP_FORMAT = "%Y%m%d-%H%M%S"
_STAMP_RE = re.compile(r"^\d{8}-\d{6}$")


def new_run_dir(now: datetime | None = None) -> Path:
    """A fresh timestamped directory for one render."""
    path = VIDEO_RESULTS / (now or datetime.now()).strftime(STAMP_FORMAT)
    path.mkdir(parents=True, exist_ok=True)
    return path


def latest_run_dir() -> Path | None:
    """The most recent render, or ``None`` if nothing has been rendered yet.

    Timestamps sort lexicographically in the order they happened, so the name
    is enough - no need to stat anything.
    """
    if not VIDEO_RESULTS.is_dir():
        return None
    runs = [p for p in VIDEO_RESULTS.iterdir()
            if p.is_dir() and _STAMP_RE.match(p.name)]
    return max(runs, key=lambda p: p.name, default=None)


def run_dir() -> Path:
    """The directory the current process should write into.

    In a Manim subprocess this is whatever ``create_video.py`` exported.
    Rendering a scene by hand - ``manim scripts/create_video/parts/...`` -
    exports nothing, so those timings go to a scratch directory instead of
    landing in, and corrupting, a real render.
    """
    env = os.environ.get(RUN_DIR_ENV)
    path = Path(env) if env else VIDEO_RESULTS / "manual"
    path.mkdir(parents=True, exist_ok=True)
    return path
