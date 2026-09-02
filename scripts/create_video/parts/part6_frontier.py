"""
Part 6 - Does it work, what does it cost, and where is it going.

Deliberately ordered results -> ablations -> cost -> frontier. Showing the
ablations and the token cost before the follow-up work is the honest ordering:
the parts of LATS that matter most, and the price of running it, are both
things a student should know before being told the idea is everywhere now.

Every number on screen is from the LATS paper (Zhou et al., ICML 2024) except
the follow-up results, which are attributed on screen to their own papers.

Render:  manim -qh scripts/create_video/parts/part6_frontier.py Part6Frontier
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, bullets, chip, hbar_chart, section_card,
)
from create_video.theme import (  # noqa: E402
    ACCENT, BAD, FS_BODY, FS_H1, FS_H3, FS_SMALL, FS_TINY, GOOD, INK,
    INK_DIM, INK_FAINT, PRIMARY, SAFE_L, SAFE_R, STROKE, SURFACE_2, T_FAST,
    T_NORM, T_SLOW, TEAL, body_zone, cap_width, fit_in, txt,
)

NARRATION = {
    "beat_section": [
        "Two questions are left. Does it actually work, and where has it "
        "gone since?",
    ],
    "beat_results": [
        "On HotpotQA, a multi-hop question answering benchmark, ReAct with "
        "GPT-3.5 scores zero point three two exact match. Reflexion reaches "
        "zero point five one. LATS gets zero point six three, and zero point "
        "seven one when chain-of-thought reasoning is added alongside ReAct.",
        "On HumanEval with GPT-4, it was state of the art at the time.",
    ],
    "beat_ablations": [
        "The more useful table is this one, because it says which pieces are "
        "load-bearing.",
        "Remove the model's value estimate and you fall from zero point six "
        "three to zero point three seven. Swap the tree search for plain "
        "depth-first search and you fall to zero point four two.",
        "Remove reflection - the one genuinely new operation - and you lose "
        "only zero point zero five. It helps, and it is the smallest of the "
        "three.",
    ],
    "beat_cost": [
        "It is not free. On HotpotQA, a successful search cost about a "
        "hundred and seventy thousand tokens and sixty-seven expanded nodes - "
        "cheaper than the tree-search baselines it was measured against, and "
        "far more expensive than one ReAct pass.",
        "It also needs an environment you can rewind, and plenty of real ones "
        "you cannot.",
    ],
    "beat_frontier": [
        "Since 2024 the idea has spread fast. SWE-Search runs tree search "
        "over edits to real repositories. Koh and colleagues ran it on live "
        "websites. And rStar-Math used the search rollouts as training data, "
        "lifting a seven-billion-parameter model from fifty-nine to ninety "
        "percent on MATH.",
        "That last one is the direction to watch: search is moving from "
        "inference time to training time.",
    ],
    "beat_close": [
        "So, to put the whole thing in one screen: a search algorithm from "
        "2006, a language model in every slot that used to need a trained "
        "network, and two new operations - evaluation, and reflection.",
        "It is high impact, it is still moving, and the honest summary is "
        "that the value function is doing most of the work.",
    ],
    "beat_references": [
        "If you want to go further, these are the five papers this was built "
        "from.",
        "Everything you have just seen was made for this track, and the code "
        "that drew it ships with the submission.",
    ],
}

ON_SCREEN = {
    "beat_section": "Section card - 6 / The Frontier.",
    "beat_results": "Two benchmarks side by side: HotpotQA exact match on the "
                    "left - ReAct 0.32, Reflexion 0.51, RAP 0.54, LATS 0.63, "
                    "LATS with CoT and ReAct 0.71 - and HumanEval pass@1 on "
                    "the right.",
    "beat_ablations": "The ablation chart - no value estimate 0.37, "
                      "depth-first instead of MCTS 0.42, no reflection 0.58, "
                      "full LATS 0.63 - with a dashed line at the full result "
                      "so each shortfall is visible.",
    "beat_cost": "173,290 tokens and 66.65 nodes, then a token-cost "
                 "comparison against Tree of Thoughts and RAP, then the "
                 "paper's two stated limitations.",
    "beat_frontier": "Four follow-up cards - SWE-Search, Koh et al. on live "
                     "websites, rStar-Math, and And More! - then an arrow "
                     "from Search at inference time to Search at training "
                     "time.",
    "beat_close": "Three summary lines: a search algorithm from 2006; a "
                  "language model in every slot that needed a trained "
                  "network; introduces reflection and evaluation operations.",
    "beat_references": "The five linked papers with venues and arXiv "
                       "identifiers, and the closing line.",
}

#: HotpotQA exact match, GPT-3.5, n = 5, k = 50 (LATS Tables 2 and 3).
HOTPOT = [
    ("ReAct", 0.32, INK_DIM),
    ("Reflexion", 0.51, TEAL),
    ("RAP", 0.54, TEAL),
    ("LATS", 0.63, GOOD),
    ("LATS, CoT + ReAct", 0.71, GOOD),
]

#: Tokens consumed upon a successful HotpotQA search (LATS Table 9).
TOKEN_COST = [("ToT", 210_215, INK_DIM), ("RAP", 176_500, TEAL),
              ("LATS", 173_290, GOOD)]

#: HumanEval pass@1 with GPT-4 (LATS Table 4).
HUMANEVAL = [
    ("Base model", 80.1, INK_DIM),
    ("Reflexion", 91.0, TEAL),
    ("LATS", 92.7, GOOD),
]

#: HotpotQA ablations, all from LATS 0.63 (LATS Table 8).
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
    ("And More!", "2025 – 2026",
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


class Part6Frontier(LATSScene):
    """Results, ablations, cost, and the follow-up work."""

    PART = 6
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
        card = section_card(6, "The Frontier",
                            "What it buys, what it costs, and what came next")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(4.4)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 2. Results ---------------------------------------------------------

    @staticmethod
    def _benchmark(title, rows, max_value, label_width, left, right,
                   top=2.05):
        """A titled bar chart pinned to the top of its own column.

        The two benchmarks have different scales and different numbers of
        bars, so they get a column each rather than being stacked - stacked,
        the second chart arrives underneath the first one's value labels.
        """
        chart = hbar_chart(rows, max_value=max_value, width=3.6,
                           bar_height=0.50, gap=0.36,
                           label_width=label_width, size=FS_SMALL)
        head = txt(title, size=FS_SMALL, color=INK_DIM)
        block = VGroup(head, chart).arrange(DOWN, buff=0.6)
        fit_in(block, body_zone(left=left, right=right, top=top,
                                bottom=-2.9), max_scale=1.0, center=True)
        block.shift(UP * (top - block.get_top()[1]))
        block.head, block.chart = head, chart
        return block

    def beat_results(self):
        self.set_header("Does It Work?")

        # A full track is exact match 1.00 and pass@1 100 - the top of each
        # metric's own range, so a bar's length is the score it carries.
        left = self._benchmark("HotpotQA (exact match, GPT-3.5)", HOTPOT,
                               1.0, 2.4, SAFE_L, -0.3)
        right = self._benchmark("HumanEval (pass@1, GPT-4)", HUMANEVAL,
                                100, 2.0, 0.5, SAFE_R)
        rule = Line([0.1, 2.15, 0], [0.1, -2.85, 0], stroke_color=STROKE,
                    stroke_width=1.6)

        self.play(FadeIn(left.head), run_time=T_FAST)
        self.play(FadeIn(left.chart.tracks), FadeIn(left.chart.labels),
                  run_time=T_NORM)
        self.play(LaggedStart(*[
            AnimationGroup(GrowFromEdge(bar, LEFT), FadeIn(value))
            for bar, value in zip(left.chart.bars, left.chart.values)
        ], lag_ratio=0.3), run_time=2.4)
        self.wait(13.0)

        self.play(Create(rule), run_time=T_FAST)
        self.play(FadeIn(right.head), FadeIn(right.chart.tracks),
                  FadeIn(right.chart.labels), run_time=T_NORM)
        self.play(LaggedStart(*[
            AnimationGroup(GrowFromEdge(bar, LEFT), FadeIn(value))
            for bar, value in zip(right.chart.bars, right.chart.values)
        ], lag_ratio=0.3), run_time=1.6)
        self.wait(4.6)

        self.play(FadeOut(VGroup(left, right, rule)), run_time=T_NORM)

    # -- 3. Ablations -------------------------------------------------------

    def beat_ablations(self):
        self.set_header("Which Part Is Doing the Work?")

        note = txt("Component ablations on HotpotQA exact match",
                   size=FS_H3, color=INK)
        cap_width(note, 11.5)
        note.move_to([0, 2.05, 0])

        chart = hbar_chart(ABLATIONS, max_value=1.0, width=6.6,
                           bar_height=0.56, gap=0.48, label_width=4.0)
        chart.move_to([-0.2, -0.5, 0])
        # The reference line at full-LATS performance lands right beside the
        # 0.58 value label, so the numbers are lifted above it and it is drawn
        # a shade softer: the line reads as a rule, not as a strikethrough.
        chart.values.set_z_index(5)

        self.play(FadeIn(note, shift=DOWN * 0.15), run_time=T_FAST)
        self.play(FadeIn(chart.tracks), FadeIn(chart.labels), run_time=T_NORM)
        self.play(LaggedStart(*[
            AnimationGroup(GrowFromEdge(bar, LEFT), FadeIn(value))
            for bar, value in zip(chart.bars, chart.values)
        ], lag_ratio=0.32), run_time=2.4)
        self.wait(9.4)

        # A dashed line at full-LATS performance. Every bar that stops short of
        # it shows its own shortfall, so no annotation has to say how far.
        plate = chart.tracks[0]
        x0 = plate.get_left()[0]
        target = x0 + plate.width * ABLATIONS[-1][1]
        line = DashedLine(
            [target, chart.tracks[-1].get_bottom()[1] - 0.2, 0],
            [target, chart.tracks[0].get_top()[1] + 0.2, 0],
            stroke_color=GOOD, stroke_width=2.5, dash_length=0.12,
            stroke_opacity=0.75)
        self.play(Create(line), run_time=T_SLOW)
        self.wait(16.4)
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

        # Rather than saying "cheaper than the baselines", show them. No track
        # here: a token count has no ceiling, so a full bar would stand for a
        # number nobody could name. The bars are scaled against the largest of
        # the three and compared with each other.
        compare = hbar_chart(TOKEN_COST, max_value=max(v for _, v, _ in TOKEN_COST),
                             width=5.0, bar_height=0.32, gap=0.24,
                             label_width=1.4, size=FS_TINY, track=False)
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
        self.wait(8.0)
        self.play(FadeOut(VGroup(figures, pair, block)), run_time=T_NORM)

    # -- 5. Where it has gone -----------------------------------------------

    def beat_frontier(self):
        self.set_header("Where LATS Has Gone Since")

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
        self.wait(16.4)

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
        self.wait(5.4)
        self.play(FadeOut(VGroup(cards, shift)), run_time=T_NORM)

    # -- 6. Close -----------------------------------------------------------

    def beat_close(self):
        self.set_header("LATS Summary")

        lines = bullets([
            "A search algorithm from 2006",
            "A language model in every slot that needed a trained network",
            "Introduces reflection and evaluation operations",
        ], color=INK, marker=INK_DIM, size=FS_H3, buff=0.72, width=11.0)
        lines.move_to([0, 0.35, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in lines],
                              lag_ratio=0.25), run_time=1.5)
        self.wait(20.0)
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
