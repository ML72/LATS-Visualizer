"""
Part 7 - Does it work, what does it cost, and where is it going.

Deliberately ordered results -> ablations -> cost -> frontier. Showing the
ablations and the token cost before the follow-up work is the honest ordering:
the parts of LATS that matter most, and the price of running it, are both
things a student should know before being told the idea is everywhere now.

Every number on screen is from the LATS paper (Zhou et al., ICML 2024) except
the follow-up results, which are attributed on screen to their own papers.

Render:  manim -qh scripts/create_video/parts/part7_frontier.py Part7Frontier
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, chip, hbar_chart, section_card,
)
from create_video.theme import (  # noqa: E402
    ACCENT, BAD, FS_BODY, FS_H1, FS_H3, FS_SMALL, FS_TINY, GOOD, INK,
    INK_DIM,
    INK_FAINT, PRIMARY, STROKE, SURFACE_2, T_FAST, T_NORM, T_SLOW, TEAL,
    VIOLET, body_zone, cap_width, fit_in, mathtex, txt,
)

NARRATION = {
    "beat_section": [
        "Two questions are left. Does it actually work, and where has it gone "
        "since.",
    ],
    "beat_results": [
        "On HotPotQA, a multi-hop question answering benchmark, ReAct with "
        "GPT-3.5 scores zero point three two exact match. Reflexion reaches "
        "zero point five one. LATS gets zero point six three, and zero point "
        "seven one with internal reasoning as well.",
        "On HumanEval with GPT-4, it was state of the art at the time.",
    ],
    "beat_ablations": [
        "The more useful table is this one, because it says which pieces are "
        "load-bearing.",
        "Remove the model's value estimate and you fall from zero point six "
        "three to zero point three seven. Swap the tree search for plain "
        "depth-first search and you fall to zero point four two.",
        "Remove reflection - the one genuinely new operation - and you lose "
        "zero point zero five. It helps, and it is the smallest of the three. "
        "Worth saying out loud.",
    ],
    "beat_cost": [
        "It is not free. On HotPotQA, a successful search cost about a "
        "hundred and seventy thousand tokens and sixty-seven expanded "
        "nodes. That is cheaper than the tree-search baselines it was "
        "measured against, and far more expensive than a single ReAct "
        "pass.",
        "It also needs an environment you can rewind, and plenty of real "
        "ones you cannot.",
    ],
    "beat_frontier": [
        "Since 2024 the idea has spread fast. SWE-Search runs tree search over "
        "edits to real repositories. Koh and colleagues ran it on live "
        "websites. And rStar-Math used the search rollouts as training data, "
        "lifting a seven-billion-parameter model from fifty-nine to ninety "
        "percent on MATH.",
        "That last one is the direction to watch: search is moving from "
        "inference time to training time.",
    ],
    "beat_references": [
        "If you want to go further, these are the five papers this was built "
        "from.",
        "Everything you have just seen was made for this track, and the code "
        "that drew it ships with the submission.",
    ],
    "beat_close": [
        "So, to put the whole thing in one screen: a search algorithm from "
        "2006, a language model in every slot that used to need a trained "
        "network, and one new operation that only makes sense because the "
        "agent can read.",
        "It is high impact, it is still moving, and the honest summary is "
        "that the value function is doing most of the work.",
    ],
}

#: HotPotQA exact match, GPT-3.5, n = 5, k = 50 (LATS Tables 2 and 3).
HOTPOT = [
    ("ReAct", 0.32, INK_DIM),
    ("Reflexion", 0.51, TEAL),
    ("RAP", 0.54, TEAL),
    ("LATS", 0.63, GOOD),
    ("LATS, CoT + ReAct", 0.71, GOOD),
]

#: Tokens consumed upon a successful HotPotQA search (LATS Table 9).
TOKEN_COST = [("ToT", 210_215, INK_DIM), ("RAP", 176_500, TEAL),
              ("LATS", 173_290, GOOD)]

#: HumanEval pass@1 with GPT-4 (LATS Table 4).
HUMANEVAL = [
    ("Base model", 80.1, INK_DIM),
    ("Reflexion", 91.0, TEAL),
    ("LATS", 92.7, GOOD),
]

#: HotPotQA ablations, all from LATS 0.63 (LATS Table 8).
ABLATIONS = [
    ("No LLM value estimate", 0.37, BAD),
    ("Depth-first instead of MCTS", 0.42, BAD),
    ("No reflection", 0.58, ACCENT),
    ("Full LATS", 0.63, GOOD),
]

#: (title, venue, one-line claim).
FOLLOW_UPS = [
    ("SWE-Search", "ICLR 2025",
     "Monte Carlo Tree Search over edits to real repositories"),
    ("Tree Search for LM Agents", "Koh et al., 2025",
     "Search on live websites: a 39.7% relative gain on VisualWebArena"),
    ("rStar-Math", "ICML 2025",
     "Search rollouts become training data: 58.8% → 90.0% on MATH"),
    ("And Further Afield", "2025 – 2026",
     "Retrieval, automated ML, and budget-aware variants"),
]

#: The linked papers, shown as the closing card.
#: (authors, short title, venue, arXiv id).
REFERENCES = [
    ("Zhou et al.", "Language Agent Tree Search", "ICML 2024", "2310.04406"),
    ("Yao et al.", "Tree of Thoughts", "NeurIPS 2023", "2305.10601"),
    ("Shinn et al.", "Reflexion", "NeurIPS 2023", "2303.11366"),
    ("Hao et al.", "Reasoning with LM Is Planning with World Model",
     "EMNLP 2023", "2305.14992"),
    ("Koh et al.", "Tree Search for Language Model Agents", "TMLR 2025",
     "2407.01476"),
]


class Part7Frontier(LATSScene):
    """Results, ablations, cost, and the follow-up work."""

    PART = 7
    TITLE = "Does It Work, and Where Is It Going"

    def beats(self):
        return [
            self.beat_section,
            self.beat_results,
            self.beat_ablations,
            self.beat_cost,
            self.beat_frontier,
            self.beat_close,
            self.beat_references,
        ]

    # -- 1. Section card ----------------------------------------------------

    def beat_section(self):
        card = section_card(7, "The frontier",
                            "What it buys, what it costs, and what came next")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(4.4)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 2. Results ---------------------------------------------------------

    def beat_results(self):
        self.set_header("Does It Work?")

        chart = hbar_chart(HOTPOT, max_value=0.8, width=5.4, bar_height=0.4,
                           gap=0.3, label_width=3.0)
        title = txt("HotPotQA — exact match, GPT-3.5", size=FS_SMALL,
                    color=INK_DIM)
        block = VGroup(title, chart).arrange(DOWN, buff=0.6, aligned_edge=LEFT)
        block.move_to([-1.1, 0.6, 0])

        self.play(FadeIn(title), run_time=T_FAST)
        self.play(FadeIn(chart.tracks), FadeIn(chart.labels), run_time=T_NORM)
        self.play(LaggedStart(*[
            AnimationGroup(GrowFromEdge(bar, LEFT), FadeIn(value))
            for bar, value in zip(chart.bars, chart.values)
        ], lag_ratio=0.3), run_time=2.4)
        self.wait(12.6)

        second = hbar_chart(HUMANEVAL, max_value=100, width=4.0,
                            bar_height=0.34, gap=0.26, label_width=2.2,
                            size=FS_TINY)
        second_title = txt("HumanEval — pass@1, GPT-4", size=FS_TINY,
                           color=INK_DIM)
        pair = VGroup(second_title, second).arrange(DOWN, buff=0.42,
                                                    aligned_edge=LEFT)
        pair.move_to([0, -2.35, 0])
        self.play(FadeIn(pair, shift=UP * 0.2), run_time=T_NORM)
        self.wait(5.4)

        self.play(FadeOut(VGroup(block, pair)), run_time=T_NORM)

    # -- 3. Ablations -------------------------------------------------------

    def beat_ablations(self):
        self.set_header("Which Part Is Doing the Work?")

        chart = hbar_chart(ABLATIONS, max_value=0.8, width=6.0,
                           bar_height=0.44, gap=0.36, label_width=4.0)
        chart.move_to([-0.2, 0.55, 0])
        note = txt("HotPotQA exact match — one component removed at a time",
                   size=FS_TINY, color=INK_FAINT)
        note.next_to(chart, UP, buff=0.6)
        note.align_to(chart.labels, LEFT)

        self.play(FadeIn(note), run_time=T_FAST)
        self.play(FadeIn(chart.tracks), FadeIn(chart.labels), run_time=T_NORM)
        self.play(LaggedStart(*[
            AnimationGroup(GrowFromEdge(bar, LEFT), FadeIn(value))
            for bar, value in zip(chart.bars, chart.values)
        ], lag_ratio=0.32), run_time=2.4)
        self.wait(9.4)

        # A dashed line at full-LATS performance. Every bar that stops short of
        # it shows its own shortfall, so no annotation has to say how far.
        track = chart.tracks[0]
        x0 = track.get_left()[0]
        target = x0 + track.width * ABLATIONS[-1][1] / 0.8
        line = DashedLine(
            [target, chart.tracks[-1].get_bottom()[1] - 0.2, 0],
            [target, chart.tracks[0].get_top()[1] + 0.2, 0],
            stroke_color=GOOD, stroke_width=2.5, dash_length=0.12)
        self.play(Create(line), run_time=T_SLOW)
        self.wait(15.6)
        self.play(FadeOut(VGroup(chart, note, line)), run_time=T_NORM)

    # -- 4. The cost --------------------------------------------------------

    def beat_cost(self):
        self.set_header("What It Costs")

        figures = VGroup()
        for value, unit, gloss, color in [
            ("173,290", "Tokens", "Upon a successful search", ACCENT),
            ("66.65", "Nodes", "Expanded, on average", ACCENT),
        ]:
            block = VGroup(
                txt(value, size=46, color=color, weight=BOLD),
                txt(unit, size=FS_BODY, color=INK),
                txt(gloss, size=FS_TINY, color=INK_FAINT),
            ).arrange(DOWN, buff=0.16)
            figures.add(block)
        figures.arrange(RIGHT, buff=2.2, aligned_edge=UP)
        figures.move_to([0, 1.55, 0])

        self.play(LaggedStart(*[FadeIn(f, shift=UP * 0.2) for f in figures],
                              lag_ratio=0.25), run_time=1.3)
        self.wait(2.6)

        # Rather than saying "cheaper than the baselines", show them.
        compare = hbar_chart(TOKEN_COST, max_value=220_000, width=5.0,
                             bar_height=0.32, gap=0.24, label_width=1.4,
                             size=FS_TINY)
        compare_title = txt("Tokens per successful search", size=FS_TINY,
                            color=INK_FAINT)
        pair = VGroup(compare_title, compare).arrange(DOWN, buff=0.4,
                                                      aligned_edge=LEFT)
        pair.move_to([-2.6, -0.85, 0])
        self.play(FadeIn(pair, shift=UP * 0.15), run_time=T_NORM)
        self.wait(7.4)

        limits = VGroup(
            chip("Higher compute than ReAct or Reflexion", BAD,
                 size=FS_SMALL),
            chip("Needs an environment you can rewind", BAD, size=FS_SMALL),
        ).arrange(DOWN, buff=0.34, aligned_edge=LEFT)
        limits_title = txt("Stated limitations", size=FS_TINY, color=INK_FAINT)
        limits_title.next_to(limits, UP, buff=0.4).align_to(limits, LEFT)
        block = VGroup(limits_title, limits)
        block.move_to([3.6, -0.85, 0])
        self.play(FadeIn(block, shift=UP * 0.2), run_time=T_NORM)
        self.wait(9.0)
        self.play(FadeOut(VGroup(figures, pair, block)), run_time=T_NORM)

    # -- 5. Where it has gone -----------------------------------------------

    def beat_frontier(self):
        self.set_header("Where It Has Gone Since")

        cards = VGroup()
        for title, venue, claim in FOLLOW_UPS:
            head = txt(title, size=FS_BODY, color=INK, weight=MEDIUM)
            tag = txt(venue, size=FS_TINY, color=PRIMARY)
            body = txt(claim, size=FS_SMALL, color=INK_DIM)
            cap_width(body, 5.4)
            inner = VGroup(head, tag, body).arrange(DOWN, aligned_edge=LEFT,
                                                    buff=0.18)
            box = RoundedRectangle(
                corner_radius=0.16, width=6.0, height=inner.height + 0.72,
                stroke_color=STROKE, stroke_width=2,
                fill_color=SURFACE_2, fill_opacity=1.0)
            inner.move_to(box.get_center())
            inner.align_to(box, LEFT).shift(RIGHT * 0.36)
            cards.add(VGroup(box, inner))
        cards.arrange_in_grid(rows=2, cols=2, buff=(0.5, 0.45))
        fit_in(cards, body_zone(bottom=-1.7), pad=0.05)

        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in cards],
                              lag_ratio=0.22), run_time=1.8)
        self.wait(16.9)

        # Where it is heading, as a diagram rather than a sentence.
        origin_tag = chip("Search at inference time", INK_FAINT,
                          size=FS_SMALL)
        dest_tag = chip("Search at training time", ACCENT, size=FS_SMALL)
        move = Arrow(ORIGIN, RIGHT * 1.5, buff=0, stroke_width=3,
                     color=ACCENT, max_tip_length_to_length_ratio=0.28)
        shift = VGroup(origin_tag, move, dest_tag).arrange(RIGHT, buff=0.4)
        shift.move_to([0, -2.5, 0])
        self.play(FadeIn(origin_tag), run_time=T_FAST)
        self.play(Create(move), FadeIn(dest_tag, shift=RIGHT * 0.2),
                  run_time=T_SLOW)
        self.wait(6.0)
        self.play(FadeOut(VGroup(cards, shift)), run_time=T_NORM)

    # -- 6. Close -----------------------------------------------------------

    def beat_close(self):
        self.set_header("In One Screen")

        lines = VGroup(
            chip("A search algorithm from 2006", PRIMARY, size=FS_BODY),
            chip("A language model in every slot that needed a trained network",
                 TEAL, size=FS_BODY),
            chip("One new operation, because the agent can read", VIOLET,
                 size=FS_BODY),
        ).arrange(DOWN, buff=0.52)
        lines.move_to([0, 0.35, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in lines],
                              lag_ratio=0.25), run_time=1.5)
        self.wait(24.0)
        self.play(FadeOut(lines), run_time=T_NORM)
        self.drop_header()

    # -- 7. References ------------------------------------------------------

    def beat_references(self):
        """The five linked papers, as the closing card."""
        heading = txt("References", size=FS_H1, color=INK, weight=MEDIUM)
        heading.move_to([0, 2.55, 0])
        rule = Line([-5.6, 2.05, 0], [5.6, 2.05, 0], stroke_color=STROKE,
                    stroke_width=2)

        author_x, title_x, venue_x = -5.4, -3.1, 6.3
        rows, top_y, step = VGroup(), 1.3, 0.72
        for i, (authors, short, venue, arxiv) in enumerate(REFERENCES):
            y = top_y - i * step
            a = txt(authors, size=FS_SMALL, color=INK, weight=MEDIUM)
            a.move_to([author_x, y, 0], aligned_edge=LEFT)
            t = txt(short, size=FS_SMALL, color=INK_DIM)
            cap_width(t, 6.2)
            t.move_to([title_x, y, 0], aligned_edge=LEFT)
            v = txt(f"{venue}  ·  arXiv:{arxiv}", size=FS_TINY,
                    color=INK_FAINT)
            v.move_to([venue_x, y, 0], aligned_edge=RIGHT)
            rows.add(VGroup(a, t, v))

        closing = txt("Original material for the NeurIPS 2026 Education Track",
                      size=FS_TINY, color=INK_FAINT)
        closing.move_to([0, -2.75, 0])

        self.play(FadeIn(heading, shift=UP * 0.2), Create(rule),
                  run_time=T_NORM)
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in rows],
                              lag_ratio=0.2), run_time=1.8)
        self.play(FadeIn(closing), run_time=T_FAST)
        self.wait(9.0)
        self.play(FadeOut(VGroup(heading, rule, rows, closing)),
                  run_time=T_SLOW)
        self.wait(0.8)
