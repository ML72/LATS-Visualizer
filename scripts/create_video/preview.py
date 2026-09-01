"""
Design-system contact sheet.

Renders one still frame per page showing every reusable component at its real
size, so you can check spacing, contrast and collisions after changing
``create_video/theme.py`` without re-rendering fifteen minutes of video.

    manim -ql -s scripts/create_video/preview.py PreviewComponents
    manim -ql -s scripts/create_video/preview.py PreviewTree

``-s`` renders only the final frame; drop it to watch the tree animate.
"""

import sys
from pathlib import Path

# Manim imports a scene file by path, which leaves scripts/ off sys.path.
# Adding it here lets this file render from any working directory.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, SearchTree, agent_glyph, bullets, check_mark, chip,
    code_block, cross_mark, env_glyph, hbar_chart, llm_glyph,
    section_card, speech_bubble, stacked_bar, value_legend,
)
from create_video.theme import (  # noqa: E402
    ACCENT, BAD, BODY_TOP, FS_SMALL, GOOD, INK_DIM, PRIMARY, TEAL, VIOLET,
    body_zone, fit_in, mathtex, txt,
)


class PreviewComponents(LATSScene):
    """Every component except the tree, on one frame."""

    PART = 90
    TITLE = "Component preview"
    WRITE_TIMING = False

    def beats(self):
        return [self.beat_sheet]

    def beat_sheet(self):
        self.set_header("Design system: components", run_time=0.2)

        icons = VGroup(
            agent_glyph(), env_glyph(), llm_glyph(),
            check_mark(scale=1.6), cross_mark(scale=1.6),
        ).arrange(RIGHT, buff=0.6)

        chips = VGroup(
            chip("selection", PRIMARY), chip("evaluation", ACCENT),
            chip("reward", GOOD), chip("dead end", BAD),
            chip("reflection", VIOLET), chip("environment", TEAL),
        ).arrange(RIGHT, buff=0.22)

        left = VGroup(
            icons, chips,
            bullets(["A bullet line, set in the body face",
                     "A second line, to check the leading"], width=5.6),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.42)

        eq = mathtex(r"\mathrm{UCT}(s) = V(s) + w\sqrt{\frac{\ln N(p)}{N(s)}}")
        code = code_block([
            "def merge(intervals):",
            "    out = []",
            "    for a, b in intervals:",
            "        ...",
        ])
        bubble = speech_bubble(
            "The failure was in the sort key, not the merge step.",
            width=5.0, tail=False)
        chart = hbar_chart(
            [("ReAct", 0.32, INK_DIM), ("Reflexion", 0.51, ACCENT),
             ("LATS", 0.63, GOOD)], max_value=0.8, width=3.4)

        right = VGroup(eq, code, bubble, chart).arrange(
            DOWN, aligned_edge=LEFT, buff=0.42)

        sheet = VGroup(left, right).arrange(RIGHT, buff=0.9, aligned_edge=UP)
        fit_in(sheet, body_zone(pad=0.05))
        self.add(sheet)
        self.wait(0.2)


class PreviewTree(LATSScene):
    """The search tree growing, plus the value ramp and the UCT bars."""

    PART = 91
    TITLE = "Component preview: tree"
    WRITE_TIMING = False

    def beats(self):
        return [self.beat_tree]

    def beat_tree(self):
        self.set_header("Design system: search tree", run_time=0.2)

        tree = SearchTree(origin=[-2.6, BODY_TOP - 0.3, 0], slot_width=1.35)
        self.play(*tree.add_node("s0", None, "s0", kind="root"))
        self.play(*tree.add_children("s0", [
            {"key": "a", "label": "a", "value": 0.7, "show_value": True},
            {"key": "b", "label": "b", "value": 0.4, "show_value": True},
            {"key": "c", "label": "c", "value": 0.2, "show_value": True},
        ]))
        self.play(*tree.add_children("a", [
            {"key": "a1", "label": "a1", "value": 0.8, "show_value": True},
            {"key": "a2", "label": "a2", "value": 0.3, "show_value": True},
        ]))
        self.play(*tree.highlight_path(["s0", "a", "a1"]))

        legend = value_legend()
        legend.move_to([-2.6, -3.0, 0])

        bars = VGroup()
        for v, u in [(0.70, 0.18), (0.40, 0.52), (0.20, 0.52)]:
            bars.add(stacked_bar(v, u, height=1.7, scale_max=1.1))
        bars.arrange(RIGHT, buff=0.55, aligned_edge=DOWN)
        bars.move_to([3.9, -0.4, 0])
        caption = txt("exploit + explore", size=FS_SMALL, color=INK_DIM)
        caption.next_to(bars, DOWN, buff=0.35)

        self.play(FadeIn(legend), FadeIn(bars), FadeIn(caption))
        self.wait(0.4)


class PreviewSectionCard(LATSScene):
    """The card that opens each part."""

    PART = 92
    TITLE = "Section card"
    WRITE_TIMING = False

    def beats(self):
        return [self.beat_card]

    def beat_card(self):
        card = section_card(3, "Monte Carlo Tree Search",
                            "A 2006 answer to “where should I look next?”")
        self.add(card)
        self.wait(0.2)
