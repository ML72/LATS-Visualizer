"""
Rendering mechanics: run Manim on one part, collect the mp4, join the parts.

The command line lives in ``scripts/create_video.py``; this module is the
machinery it drives. Every path comes from :mod:`create_video.paths`, so a
render writes only into ``results/`` and never into the tracked tree.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .fontpath import status as font_status
from .paths import MANIM_CACHE, REPO_ROOT, RUN_DIR_ENV
from .texpath import latex_status

PARTS_DIR = Path(__file__).resolve().parent / "parts"

#: (part number, module stem, scene class). Rendered and joined in this order.
PARTS: list[tuple[int, str, str]] = [
    (1, "part1_agents", "Part1Agents"),
    (2, "part2_linear", "Part2Linear"),
    (3, "part3_mcts", "Part3MCTS"),
    (4, "part4_lats", "Part4LATS"),
    (5, "part5_walkthrough", "Part5Walkthrough"),
    (6, "part6_frontier", "Part6Frontier"),
]

PART_NUMBERS = [p for p, _, _ in PARTS]

#: Manim flags per quality preset. ``dir`` is the folder Manim writes into.
QUALITY = {
    "draft": {"flags": ["-ql"], "dir": "480p15",
              "note": "854x480 at 15 fps"},
    "medium": {"flags": ["-qm"], "dir": "720p30",
               "note": "1280x720 at 30 fps"},
    "final": {"flags": ["-r", "1920,1080", "--fps", "30"], "dir": "1080p30",
              "note": "1920x1080 at 30 fps"},
}


def partial_path(run: Path, part: int) -> Path:
    return run / f"partial_part{part}.mp4"


def ffmpeg() -> str:
    """Locate ffmpeg. Manim bundles none, so it must be on PATH."""
    found = shutil.which("ffmpeg")
    if found is None:
        sys.exit("ffmpeg not found on PATH. Install it, or add it to PATH, "
                 "then re-run.")
    return found


def render_part(part: int, stem: str, scene: str, *, quality: str,
                cache: bool, run: Path) -> Path:
    """Render one part with Manim and return the mp4 it produced.

    Manim renders in its own process, so the run directory is handed over in
    the environment - that is how :class:`~create_video.components.LATSScene`
    knows where to drop ``timing_partN.json``.
    """
    preset = QUALITY[quality]
    module = (PARTS_DIR / f"{stem}.py").relative_to(REPO_ROOT).as_posix()

    cmd = [sys.executable, "-m", "manim", *preset["flags"],
           "--media_dir", str(MANIM_CACHE)]
    if not cache:
        cmd.append("--disable_caching")
    cmd += [module, scene]

    print(f"  part {part}: {scene} ({preset['note']}) ...", flush=True)
    started = time.time()
    result = subprocess.run(
        cmd, cwd=REPO_ROOT, env={**os.environ, RUN_DIR_ENV: str(run)})
    if result.returncode != 0:
        sys.exit(f"manim failed on part {part} ({scene}).")

    produced = MANIM_CACHE / "videos" / stem / preset["dir"] / f"{scene}.mp4"
    if not produced.exists():
        sys.exit(f"expected {produced} but it is not there.")
    print(f"    done in {time.time() - started:.0f}s", flush=True)
    return produced


def collect(part: int, produced: Path, run: Path) -> Path:
    """Copy a rendered part into the run directory under its stable name."""
    run.mkdir(parents=True, exist_ok=True)
    target = partial_path(run, part)
    shutil.copy2(produced, target)
    return target


def join(parts: list[int], run: Path) -> Path:
    """Concatenate the partials into ``full.mp4``.

    Manim writes every part with identical codec settings for a given quality
    preset, so a stream copy is enough and is effectively instant. If a part is
    missing, say which one rather than producing a truncated video.
    """
    missing = [p for p in parts if not partial_path(run, p).exists()]
    if missing:
        sys.exit(
            f"cannot join: {run.name} has no "
            f"{', '.join(f'partial_part{p}.mp4' for p in missing)} - render "
            "those parts first (python scripts/create_video.py --parts "
            f"{' '.join(str(m) for m in missing)}).")

    listing = run / "_concat.txt"
    listing.write_text(
        "".join(f"file '{partial_path(run, p).as_posix()}'\n" for p in parts),
        encoding="utf-8",
    )
    output = run / "full.mp4"
    cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
           "-i", str(listing), "-c", "copy", str(output)]
    if subprocess.run(cmd).returncode != 0:
        # A stream copy can fail if the parts were rendered at different
        # qualities. Re-encoding always works, it is just slower.
        print("  stream copy failed; re-encoding instead "
              "(are the parts all the same quality?)")
        cmd = [ffmpeg(), "-y", "-loglevel", "error", "-f", "concat", "-safe",
               "0", "-i", str(listing), "-c:v", "libx264", "-preset", "medium",
               "-crf", "18", "-pix_fmt", "yuv420p", str(output)]
        if subprocess.run(cmd).returncode != 0:
            sys.exit("ffmpeg could not join the parts.")
    listing.unlink(missing_ok=True)
    return output


def merge_timings(run: Path) -> Path:
    """Fold the per-part timing files into one, with absolute start times."""
    combined, offset = [], 0.0
    for part, _, _ in PARTS:
        path = run / f"timing_part{part}.json"
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        for beat in payload["beats"]:
            beat["absolute_start"] = round(offset + beat["start"], 3)
            beat["absolute_end"] = round(offset + beat["end"], 3)
        payload["offset"] = round(offset, 3)
        combined.append(payload)
        offset += payload["total"]

    out = run / "timing.json"
    out.write_text(json.dumps({"total": round(offset, 3), "parts": combined},
                              indent=2), encoding="utf-8")
    return out


def duration(path: Path) -> float:
    """Length of a video in seconds, or 0.0 if ffprobe is not available."""
    probe = shutil.which("ffprobe")
    if probe is None:
        return 0.0
    result = subprocess.run(
        [probe, "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def check() -> int:
    """Report the toolchain a render needs."""
    print("toolchain")
    print(f"  python   {sys.version.split()[0]}")
    try:
        import manim
        print(f"  manim    {manim.__version__}")
    except ImportError:
        print("  manim    NOT INSTALLED  (pip install -r requirements.txt)")
    print(f"  ffmpeg   {shutil.which('ffmpeg') or 'NOT FOUND'}")
    print(f"  latex    {latex_status()}")
    print(f"  fonts    {font_status()}")
    try:
        from .theme import FONT, FONT_MONO
        print(f"  faces    body {FONT!r}   mono {FONT_MONO!r}")
    except Exception as exc:  # pragma: no cover - needs manim installed
        print(f"  faces    could not resolve ({exc})")
    print(f"\n  cache    {MANIM_CACHE}")
    return 0
