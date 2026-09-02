"""
Write the narration script from the part modules plus the measured timings.

The narration itself lives in a ``NARRATION`` dict at the top of each part
module, next to the animation it describes, and what the frame shows lives in
an ``ON_SCREEN`` dict beside it. Those are the files to edit; this module only
formats. It is re-run at the end of every render, because the timestamps come
from the render - so ``SCRIPT.md`` always describes the video sitting next to
it in the run directory.

Markdown rather than plain text, so the script is readable in an editor, on
GitHub, and in any Markdown previewer without losing the structure.

Timestamps are cue points, not a hard grid: each one marks where a beat's
picture starts. A narrator should read at a natural pace and use them to check
they have not drifted, rather than trying to hit them exactly.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from .timing import (
    PART_MODULES, WORDS_PER_MINUTE, narration_seconds, word_count,
)

#: Terms a narrator can trip over, and how they are meant to sound. Only
#: entries that are actually spoken belong here.
PRONUNCIATION = [
    ("ReAct", "ree-ACT"),
    ("UCT", "spelled out, three letters"),
    ("HotpotQA", "hot-pot-Q-A"),
    ("HumanEval", "HUMAN-e-val"),
    ("Rémi Coulom", "RAY-mee koo-LOM"),
    ("Szepesvári", "roughly SEP-esh-vaa-ree"),
    ("SWE-Search", "SWEE-search"),
    ("rStar-Math", "R-star-math"),
    ("λ", "say “lambda”"),
    ("w", "say “w”, not “weight”"),
]


def clock(seconds: float) -> str:
    return f"{int(seconds // 60):d}:{seconds % 60:04.1f}"


#: Beat stems whose plain-English heading is not just the method name.
BEAT_NAMES = {
    "llm_agent": "LLM agent",
    "uct": "UCT",
    "iter1": "Iteration 1",
    "iter2": "Iteration 2",
}


def beat_title(name: str) -> str:
    """``beat_llm_agent`` -> ``LLM agent``."""
    stem = name[5:] if name.startswith("beat_") else name
    if stem in BEAT_NAMES:
        return BEAT_NAMES[stem]
    words = stem.replace("_", " ")
    return words[:1].upper() + words[1:]


def anchor(part: dict) -> str:
    """The GitHub-style heading anchor for a part, for the contents table."""
    text = f"part-{part['part']}--{part['title']}".lower()
    keep = [c if (c.isalnum() or c in " -") else "" for c in text]
    return "#" + "".join(keep).replace(" ", "-")


def spoken(paragraph: str) -> str:
    """The narration source keeps ASCII hyphens; delivery gets em dashes."""
    return paragraph.replace(" - ", " — ")


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
    total_beats = 0
    for part in timing["parts"]:
        narration = getattr(
            importlib.import_module(PART_MODULES[part["part"]]),
            "NARRATION", {})
        for beat in part["beats"]:
            total_beats += 1
            total_words += sum(word_count(p)
                               for p in narration.get(beat["name"], []))

    add("# Language Agent Tree Search — Narration Script")
    add("")
    add("Read this over `full.mp4`, in this same folder. **The video carries "
        "no sound**, so this is the whole audio track.")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| **Runtime** | {clock(total)} |")
    add(f"| **Parts** | {len(timing['parts'])} |")
    add(f"| **Beats** | {total_beats} |")
    add(f"| **Word count** | {total_words:,} |")
    add(f"| **Target pace** | {WORDS_PER_MINUTE:.0f} words per minute |")
    add("")
    add("## How to read it")
    add("")
    add("- Each timestamp marks where that beat's **picture** starts. They "
        "are cue points to check yourself against, not a grid to hit.")
    add("- Every beat lists how long it is on screen and how many words it "
        "carries, paced at "
        f"{WORDS_PER_MINUTE:.0f} words per minute. If you finish early, "
        "pause and let the animation land rather than pressing on into the "
        "next picture.")
    add("- **On screen** lines are stage directions, not narration. Only the "
        "quoted blocks are spoken.")
    add("- A dash inside a sentence is an em dash: pause, do not read it. "
        "Numbers are written the way they should be spoken.")
    add("")
    add("## Pronunciation")
    add("")
    add("| written | spoken |")
    add("|---|---|")
    for term, say in PRONUNCIATION:
        add(f"| {term} | {say} |")
    add("")
    add("## Contents")
    add("")
    add("| start | part | runtime |")
    add("|---|---|---|")
    for part in timing["parts"]:
        add(f"| `{clock(part['offset'])}` | "
            f"[Part {part['part']} — {part['title']}]({anchor(part)}) | "
            f"{part['total']:.0f} s |")
    add("")

    for part in timing["parts"]:
        module = importlib.import_module(PART_MODULES[part["part"]])
        narration = getattr(module, "NARRATION", {})
        on_screen = getattr(module, "ON_SCREEN", {})

        add("---")
        add("")
        add(f"## Part {part['part']} — {part['title']}")
        add("")
        add(f"`{clock(part['offset'])} – "
            f"{clock(part['offset'] + part['total'])}` · "
            f"{part['total']:.0f} seconds · {len(part['beats'])} beats")
        add("")

        for beat in part["beats"]:
            paragraphs = narration.get(beat["name"], [])
            words = sum(word_count(p) for p in paragraphs)
            need = narration_seconds(paragraphs)

            add(f"### `{clock(beat['absolute_start'])}` "
                f"{beat_title(beat['name'])}")
            add("")
            add(f"*{beat['duration']:.0f} s on screen · {words} words*")
            add("")
            if beat["name"] in on_screen:
                add(f"**On screen.** {on_screen[beat['name']]}")
                add("")
            if not paragraphs:
                add("*No narration — let the picture carry it.*")
                add("")
                continue
            for paragraph in paragraphs:
                add(f"> {spoken(paragraph)}")
                add("")
            if need > beat["duration"] + 2.5:
                add(f"*Tight: about {need - beat['duration']:.0f} s more "
                    "narration than picture — read briskly.*")
                add("")
            elif beat["duration"] > need + 2.5:
                add(f"*Room: about {beat['duration'] - need:.0f} s of picture "
                    "beyond the words — let it breathe.*")
                add("")

    add("---")
    add("")
    add("*Generated by `scripts/create_video.py` from the `NARRATION` and "
        "`ON_SCREEN` dicts in `scripts/create_video/parts/`, cued to the "
        "timings this render measured.*")
    return "\n".join(out) + "\n"


def write(run: Path) -> Path:
    """Write ``SCRIPT.md`` next to the video it narrates."""
    target = run / "SCRIPT.md"
    target.write_text(build(run), encoding="utf-8")
    return target
