#!/usr/bin/env python3
"""
Render the LATS explainer video.

    python scripts/create_video.py                  # draft (854x480, 15 fps), for iterating
    python scripts/create_video.py --quality final  # delivery (1920x1080, 30 fps)
    python scripts/create_video.py --parts 3 5      # re-render two parts, then re-join
    python scripts/create_video.py --join-only      # rebuild full.mp4 and SCRIPT.md only
    python scripts/create_video.py --script-only    # rewrite SCRIPT.md against the last render
    python scripts/create_video.py --timing         # narration length vs. time on screen
    python scripts/create_video.py --check          # report the toolchain and exit

Every render gets its own timestamped directory under ``results/video/``::

    results/video/20260830-010025/
        partial_part1.mp4 ... partial_part6.mp4   one file per section
        full.mp4                                  all six, concatenated
        timing.json                               per-beat timings
        SCRIPT.md                                 narration, cued to those timings
        render.json                               which quality preset produced this

The video carries no sound. ``SCRIPT.md`` is written from the ``NARRATION`` and
``ON_SCREEN`` dicts in the part modules and the timings this render measured, so
it always describes the mp4 sitting beside it. A copy lands at
``results/SCRIPT.md`` too, so the current script is one predictable path rather
than one inside whichever timestamped run happens to be newest.

``--parts``, ``--join-only`` and ``--script-only`` continue the most recent run
instead of starting a new one, so re-rendering one section does not orphan the
other five. ``--run-dir`` picks a different one.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from create_video import render, script, timing  # noqa: E402
from create_video.paths import (  # noqa: E402
    RESULTS, VIDEO_RESULTS, latest_run_dir, new_run_dir,
)


def resolve_run(args: argparse.Namespace) -> Path:
    """Which run directory this invocation works in."""
    if args.run_dir:
        run = Path(args.run_dir).resolve()
        if not run.is_dir():
            raise SystemExit(f"no such run directory: {run}")
        return run

    continues = args.parts or args.join_only or args.script_only or args.timing
    if not continues:
        return new_run_dir()

    run = latest_run_dir()
    if run is None:
        raise SystemExit(
            f"nothing rendered yet - {VIDEO_RESULTS} holds no runs. Start one "
            "with `python scripts/create_video.py`.")
    return run


def check_quality(run: Path, quality: str, continuing: bool) -> None:
    """Warn before dropping a part rendered at one quality into a run of another.

    Mixing is survivable - ``join`` re-encodes when a stream copy fails - but a
    480p section inside an otherwise 1080p video is the kind of mistake that
    survives all the way to a submission, so say it out loud.
    """
    record = run / "render.json"
    if continuing and record.exists():
        try:
            was = json.loads(record.read_text(encoding="utf-8")).get("quality")
        except (json.JSONDecodeError, OSError):
            was = None
        if was and was != quality:
            print(f"  WARNING: {run.name} was rendered at {was!r}; you are "
                  f"adding parts at {quality!r}. Pass --quality {was} to "
                  "match, or start a fresh run.")
    record.write_text(
        json.dumps({"quality": quality,
                    "updated": datetime.now().isoformat(timespec="seconds")},
                   indent=2) + "\n",
        encoding="utf-8")


def write_script(run: Path) -> None:
    """Rewrite SCRIPT.md, if this run has measured timings to cue it against."""
    if not (run / "timing.json").exists():
        print("  no timing.json yet, so no SCRIPT.md - render the parts first.")
        return
    target = script.write(run)
    # A stable path for the current script, beside the runs it came from, so
    # nothing has to work out which timestamped folder is the newest.
    latest = RESULTS / "SCRIPT.md"
    latest.write_text(target.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"\nSCRIPT.md   {target}")
    print(f"            {latest}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quality", choices=sorted(render.QUALITY), default="draft",
                    help="render preset (default: draft)")
    ap.add_argument("--parts", nargs="*", type=int, metavar="N",
                    help="work on these parts only, then re-join everything")
    ap.add_argument("--run-dir", metavar="PATH",
                    help="use this run directory instead of the latest")
    ap.add_argument("--join-only", action="store_true",
                    help="skip rendering; rebuild full.mp4 and SCRIPT.md")
    ap.add_argument("--no-join", action="store_true",
                    help="render the parts but do not build full.mp4")
    ap.add_argument("--script-only", action="store_true",
                    help="rewrite SCRIPT.md from the last render's timings")
    ap.add_argument("--timing", action="store_true",
                    help="report narration length against time on screen")
    ap.add_argument("--cache", action="store_true",
                    help="let Manim reuse cached partial movie files")
    ap.add_argument("--check", action="store_true",
                    help="report the toolchain and exit")
    args = ap.parse_args(argv)

    if args.check:
        return render.check()

    run = resolve_run(args)

    if args.timing:
        return timing.report(run, args.parts or None)

    if args.script_only:
        write_script(run)
        return 0

    wanted = args.parts if args.parts else render.PART_NUMBERS
    unknown = sorted(set(wanted) - set(render.PART_NUMBERS))
    if unknown:
        raise SystemExit(f"no such part(s): {unknown}. "
                         f"Valid parts are {render.PART_NUMBERS}.")

    if not args.join_only:
        print(f"rendering {len(wanted)} part(s) at {args.quality} quality "
              f"into {run}")
        check_quality(run, args.quality, continuing=bool(args.parts or args.run_dir))
        started = time.time()
        for part, stem, scene in render.PARTS:
            if part in wanted:
                produced = render.render_part(
                    part, stem, scene, quality=args.quality,
                    cache=args.cache, run=run)
                render.collect(part, produced, run)
        print(f"rendered in {(time.time() - started) / 60:.1f} min")

    render.merge_timings(run)

    if not args.no_join:
        output = render.join(render.PART_NUMBERS, run)
        seconds = render.duration(output)
        megabytes = output.stat().st_size / 1_048_576
        print(f"\nfull.mp4    {output}")
        if seconds:
            print(f"            {int(seconds // 60)}m {seconds % 60:04.1f}s"
                  f"   {megabytes:.1f} MB")
        # The NeurIPS Education Track asks for anything much over ~40 MB to be
        # hosted at a permanent URL and linked from the submission instead.
        if megabytes > 40:
            print("            note: over ~40 MB - the call for submissions "
                  "asks for files this large to be hosted externally and "
                  "linked.")

    write_script(run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
