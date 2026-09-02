"""
Compare each beat's narration length against how long that beat runs on screen.

The narration is written into a ``NARRATION`` dict in every part module, keyed
by beat method name. Every render writes ``timing_partN.json`` into its run
directory with the measured span of each beat. This module puts the two side by
side so you can see which beats need a longer hold and which are dawdling::

    python scripts/create_video.py --timing         # the latest render
    python scripts/create_video.py --timing 3 4     # just parts 3 and 4

Reading the output
------------------
``need`` is the narration read at :data:`WORDS_PER_MINUTE`, times
:data:`BREATHING_ROOM` to allow for pauses between sentences. ``have`` is what
the animation actually gives it. A beat is flagged when the gap is more than
:data:`TOLERANCE` seconds in either direction:

    SHORT   the narrator will still be talking after the picture has moved on
            -> lengthen a self.wait(), or cut a clause

    LONG    the screen sits still while nobody is speaking
            -> shorten a self.wait(), or say more
"""

from __future__ import annotations

import importlib
import json
import re
from pathlib import Path

#: Delivery pace assumed for the narrator. A measured, technical read.
WORDS_PER_MINUTE = 145.0
#: Multiplier applied on top, covering breaths and sentence gaps.
BREATHING_ROOM = 1.06
#: Beats within this many seconds of target are not flagged.
TOLERANCE = 2.5

#: part number -> module path, in playing order.
PART_MODULES = {
    1: "create_video.parts.part1_agents",
    2: "create_video.parts.part2_linear",
    3: "create_video.parts.part3_mcts",
    4: "create_video.parts.part4_lats",
    5: "create_video.parts.part5_walkthrough",
    6: "create_video.parts.part6_frontier",
}


def word_count(text: str) -> int:
    """Words a narrator actually says. Numerals and hyphenates count once."""
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.\-]*", text))


def narration_seconds(paragraphs) -> float:
    words = sum(word_count(p) for p in paragraphs)
    return words / (WORDS_PER_MINUTE / 60.0) * BREATHING_ROOM


def load_narration(part: int) -> dict:
    module = importlib.import_module(PART_MODULES[part])
    return getattr(module, "NARRATION", {})


def report_part(part: int, run: Path) -> tuple[float, float, int]:
    """Print one part's table. Returns (need, have, flagged)."""
    timing_path = run / f"timing_part{part}.json"
    if not timing_path.exists():
        print(f"part {part}: not in this render ({timing_path.name} missing)")
        return 0.0, 0.0, 0

    timing = json.loads(timing_path.read_text(encoding="utf-8"))
    narration = load_narration(part)

    print(f"\nPart {part} - {timing.get('title', '')}")
    print(f"  {'beat':<24}{'words':>6}{'need':>8}{'have':>8}{'delta':>8}  flag")
    print("  " + "-" * 62)

    total_need = total_have = 0.0
    flagged = 0
    for beat in timing["beats"]:
        paragraphs = narration.get(beat["name"], [])
        words = sum(word_count(p) for p in paragraphs)
        need = narration_seconds(paragraphs)
        have = beat["duration"]
        delta = have - need
        total_need += need
        total_have += have

        flag = ""
        if not paragraphs:
            flag = "no narration"
        elif delta < -TOLERANCE:
            flag = "SHORT"
            flagged += 1
        elif delta > TOLERANCE:
            flag = "LONG"
            flagged += 1
        print(f"  {beat['name']:<24}{words:>6}{need:>8.1f}{have:>8.1f}"
              f"{delta:>+8.1f}  {flag}")

    print("  " + "-" * 62)
    print(f"  {'TOTAL':<24}{'':>6}{total_need:>8.1f}{total_have:>8.1f}"
          f"{total_have - total_need:>+8.1f}")
    return total_need, total_have, flagged


def report(run: Path, parts: list[int] | None = None) -> int:
    """Print the table for every requested part, then the grand total."""
    print(f"timings from {run}")
    grand_need = grand_have = 0.0
    grand_flagged = 0
    for part in parts or sorted(PART_MODULES):
        need, have, flagged = report_part(part, run)
        grand_need += need
        grand_have += have
        grand_flagged += flagged

    print("\n" + "=" * 66)
    print(f"  narration {grand_need / 60:6.2f} min      "
          f"video {grand_have / 60:6.2f} min      "
          f"beats needing attention: {grand_flagged}")
    print("=" * 66)
    return 0
