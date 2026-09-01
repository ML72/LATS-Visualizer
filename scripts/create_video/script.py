"""
Write the narration script from the part modules plus the measured timings.

The narration itself lives in a ``NARRATION`` dict at the top of each part
module, next to the animation it describes. That is the file to edit; this
module only formats. It is re-run at the end of every render, because the
timestamps come from the render - so ``SCRIPT.txt`` always describes the video
sitting next to it in the run directory.

Timestamps are cue points, not a hard grid: each one marks where a beat's
picture starts. A narrator should read at a natural pace and use them to check
they have not drifted, rather than trying to hit them exactly.
"""

from __future__ import annotations

import importlib
import json
import textwrap
from pathlib import Path

from .timing import (
    PART_MODULES, WORDS_PER_MINUTE, narration_seconds, word_count,
)

WRAP = 78


def clock(seconds: float) -> str:
    return f"{int(seconds // 60):d}:{seconds % 60:04.1f}"


def beat_title(name: str) -> str:
    """``beat_llm_agent`` -> ``LLM AGENT``."""
    stem = name[5:] if name.startswith("beat_") else name
    return stem.replace("_", " ").upper()


def build(run: Path) -> str:
    """Render the script for the video in ``run``. Needs ``timing.json``."""
    timing_path = run / "timing.json"
    if not timing_path.exists():
        raise SystemExit(
            f"{timing_path} is missing - render the parts first so the beat "
            "timings exist (python scripts/create_video.py).")
    timing = json.loads(timing_path.read_text(encoding="utf-8"))

    out: list[str] = []
    add = out.append

    total = timing["total"]
    total_words = 0
    for part in timing["parts"]:
        narration = getattr(
            importlib.import_module(PART_MODULES[part["part"]]),
            "NARRATION", {})
        for beat in part["beats"]:
            total_words += sum(word_count(p)
                               for p in narration.get(beat["name"], []))

    add("=" * WRAP)
    add("LANGUAGE AGENT TREE SEARCH — NARRATION SCRIPT")
    add("=" * WRAP)
    add("")
    add(textwrap.fill(
        "Read this over full.mp4, in this same folder. Timestamps mark where "
        "each beat's picture starts; treat them as cue points to check "
        "against, not a grid to hit. The animation was paced against a read "
        f"of about {WORDS_PER_MINUTE:.0f} words per minute, so if you finish "
        "a beat early, pause rather than pressing on into the next picture.",
        WRAP))
    add("")
    add(f"  runtime      {clock(total)}  ({len(timing['parts'])} parts)")
    add(f"  word count   {total_words}")
    add(f"  target pace  {WORDS_PER_MINUTE:.0f} words per minute")
    add("")
    add(textwrap.fill(
        "A dash in the middle of a sentence is an em dash: pause, do not read "
        "it. Numbers are written the way they should be spoken. Terms are "
        "spelled out on first use so the pronunciation is not in doubt: "
        "\"ReAct\" is ree-ACT, \"UCT\" is spelled out as three letters, "
        "\"HotPotQA\" is hot-pot-Q-A, and \"Szepesvari\" is roughly "
        "SEP-esh-vaa-ree.", WRAP))
    add("")
    add("-" * WRAP)
    add("CONTENTS")
    add("-" * WRAP)
    for part in timing["parts"]:
        start = clock(part["offset"])
        add(f"  {start:>7}   Part {part['part']} — {part['title']}")
    add("")

    for part in timing["parts"]:
        module = importlib.import_module(PART_MODULES[part["part"]])
        narration = getattr(module, "NARRATION", {})

        add("")
        add("=" * WRAP)
        add(f"PART {part['part']} — {part['title'].upper()}")
        add(f"{clock(part['offset'])} – {clock(part['offset'] + part['total'])}"
            f"   ({part['total']:.0f} seconds)")
        add("=" * WRAP)

        for beat in part["beats"]:
            paragraphs = narration.get(beat["name"], [])
            words = sum(word_count(p) for p in paragraphs)
            need = narration_seconds(paragraphs)
            add("")
            add(f"[{clock(beat['absolute_start'])}]  {beat_title(beat['name'])}"
                f"   ({beat['duration']:.0f}s on screen, {words} words)")
            add("")
            if not paragraphs:
                add("    (no narration — let the picture carry it)")
                continue
            for paragraph in paragraphs:
                # The narration source keeps ASCII hyphens so it stays easy to
                # edit; the delivered script gets real em dashes.
                spoken = paragraph.replace(" - ", " — ")
                add(textwrap.fill(spoken, WRAP - 4,
                                  initial_indent="    ",
                                  subsequent_indent="    "))
                add("")
            if need > beat["duration"] + 2.5:
                add(f"    [tight: about {need - beat['duration']:.0f}s more "
                    "narration than picture — read briskly]")
                add("")
            elif beat["duration"] > need + 2.5:
                add(f"    [room: about {beat['duration'] - need:.0f}s of "
                    "picture beyond the words — let it breathe]")
                add("")

    add("")
    add("=" * WRAP)
    add("END")
    add("=" * WRAP)
    return "\n".join(out) + "\n"


def write(run: Path) -> Path:
    """Write ``SCRIPT.txt`` next to the video it narrates."""
    target = run / "SCRIPT.txt"
    target.write_text(build(run), encoding="utf-8")
    return target
