"""
Part 5 - LATS in action.

One task, worked end to end: write ``merge_intervals`` against a visible test
suite. The trap is deliberate. The obvious one-pass solution is genuinely
reasonable, passes three of five tests, and cannot be patched into correctness -
the fix is a different approach, one level up the tree.

That is the whole argument of the video in a single example: a linear agent
loses not because it is not clever enough, but because the only useful move is
backwards.

The UCT numbers shown on screen are computed from the formula at render time
(see :func:`_uct`), so editing the values keeps the arithmetic honest.

Render:  manim -qh scripts/create_video/parts/part5_walkthrough.py Part5Walkthrough
"""

import sys
from math import log, sqrt
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, SearchTree, check_mark, chip, code_block, cross_mark,
    overlay, panel, section_card, speech_bubble,
)
from create_video.theme import (  # noqa: E402
    ACCENT, BAD, EDGE, FS_BODY, FS_H3, FS_MONO, FS_SMALL, FS_TINY, GOOD,
    INK, INK_DIM, INK_FAINT, PRIMARY, STROKE, SURFACE_2, T_FAST, T_NORM,
    T_SLOW, TEAL, VIOLET, cap_width, mathtex, mono, txt,
)

NARRATION = {
    "beat_section": [
        "Now let's run the whole algorithm on that same task: "
        "merge_intervals.",
    ],
    "beat_task": [
        "Here it is in full. Five tests, and we can see all of them. The "
        "first three take a sorted list. The last two do not, and that is "
        "the whole difficulty, sitting in plain sight.",
        "The reward is simply the fraction of tests that pass. This is exactly "
        "how LATS handles programming tasks.",
    ],
    "beat_iter1": [
        "Expansion. The model samples three candidate approaches from the "
        "root.",
        "Evaluation. It grades its own three ideas. Merging neighbors in one "
        "pass looks best - and honestly, it is a reasonable guess.",
        "Selection takes it, and simulation runs it for real: three of five. "
        "The two unsorted tests fail.",
        "Backpropagation writes that zero point six into the node and up to "
        "the root. The model's own optimistic zero point seven has just been "
        "overruled by the test runner - which is why the value estimate has "
        "to be grounded in the environment.",
    ],
    "beat_reflect": [
        "And because that trajectory failed, reflection fires. The model reads "
        "its own failed transcript and writes down why.",
        "This note is now part of the context for everything that follows.",
    ],
    "beat_iter2": [
        "Selection again, and the numbers have moved. A is worth zero point "
        "six over two visits; B still carries the model's zero point six two "
        "over one. B's exploration bonus is the square root of log two, about "
        "zero point eight three - enough to win.",
        "Expansion, and the new solution differs from the failed one by exactly "
        "one line. Simulation: five out of five. Reward one. Search over.",
    ],
    "beat_counterfactual": [
        "So what would a linear agent have done here? It would have kept "
        "patching: handle this input, special-case that one - and stayed at "
        "three of five, because the approach itself was the bug.",
        "LATS did not out-think it. It went back up one level and spent its "
        "next sample somewhere else. Not smarter; just able to go back.",
    ],
}

ON_SCREEN = {
    "beat_section": "Section card - 5 / LATS in Action.",
    "beat_task": "The signature, then all five test assertions. A brace marks "
                 "the first three Sorted input and the last two Unsorted "
                 "input. Then r = fraction of tests that pass.",
    "beat_iter1": "Three children are expanded from the root and listed; each "
                  "gets a value - A 0.70, B 0.62, C 0.35. A is selected and "
                  "its code runs against the suite: three ticks, two crosses, "
                  "r = 0.60. Then 0.60 flashes back into A and the root.",
    "beat_reflect": "The reflection the model wrote, in a violet bubble, then "
                    "an arrow down to Added to the context of every later "
                    "attempt.",
    "beat_iter2": "A table of Child, V, N and UCT - A is 0.60 with two "
                  "visits, B is 0.62 with one - and B wins on UCT. Then the "
                  "new code, with the added sorted() line highlighted and "
                  "captioned One line different. Five ticks, r = 1.00, and a "
                  "green Solved node.",
    "beat_counterfactual": "Two runs side by side. The linear agent patches, "
                           "patches, and gives up; LATS goes back to the root "
                           "and solves it. A green curved arrow marks the "
                           "backward move, and the linear run dims away.",
}

#: (key, label, one-line description, the model's own value estimate).
CANDIDATES = [
    ("A", "Merge neighbors in one pass", 0.70),
    ("B", "Sort by start, then sweep", 0.62),
    ("C", "Build an interval tree", 0.35),
]

#: The visible test suite. ``passes_a`` records whether approach A passes.
TESTS = [
    ("merge([[1,3],[2,6]])", "[[1,6]]", True),
    ("merge([[1,4],[5,6]])", "[[1,4],[5,6]]", True),
    ("merge([[1,4],[4,5]])", "[[1,5]]", True),
    ("merge([[3,5],[1,2]])", "[[1,2],[3,5]]", False),
    ("merge([[8,10],[1,3],[2,6]])", "[[1,6],[8,10]]", False),
]

#: Approach A: correct only if the input happens to arrive sorted.
CODE_A = [
    "out = []",
    "for a, b in iv:",
    "    if out and a <= out[-1][1]:",
    "        out[-1][1] = max(out[-1][1], b)",
    "    else:",
    "        out.append([a, b])",
    "return out",
]

#: Approach B: the same sweep, with one line in front of it.
CODE_B = ["iv = sorted(iv)"] + CODE_A


def _uct(value: float, visits: int, parent_visits: int, w: float = 1.0) -> float:
    return value + w * sqrt(log(parent_visits) / visits)


class Part5Walkthrough(LATSScene):
    """One task, searched end to end, then compared against a linear agent."""

    PART = 5
    TITLE = "LATS in Action"

    #: Where the tree lives, and where the side panel lives.
    TREE_ORIGIN = [-3.95, 2.35, 0]
    PANEL_CENTRE = [3.15, -0.15, 0]
    PANEL_SIZE = (6.3, 4.7)

    def beats(self):
        return [
            self.beat_section,
            self.beat_task,
            self.beat_iter1,
            self.beat_reflect,
            self.beat_iter2,
            self.beat_counterfactual,
        ]

    # -- helpers ------------------------------------------------------------

    def _test_rows(self, size=FS_TINY):
        """The five assertions, as a left-aligned monospace block."""
        rows = VGroup()
        for call, expect, _ in TESTS:
            rows.add(mono(f"{call} == {expect}", size=size, color=INK_DIM))
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.24)
        return rows

    def _side_panel(self, title):
        box = panel(self.PANEL_SIZE[0], self.PANEL_SIZE[1], title,
                    accent=STROKE)
        box.move_to(self.PANEL_CENTRE)
        overlay(box)
        return box

    # -- 1. Section card ----------------------------------------------------

    def beat_section(self):
        card = section_card(5, "LATS in Action", "One task, start to finish")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(5.0)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 2. The task and its tests ------------------------------------------

    def beat_task(self):
        self.set_header("The Task")

        spec = mono("merge_intervals(iv)  →  merge every pair that overlaps",
                    size=FS_BODY, color=INK)
        cap_width(spec, 11.5)
        spec.move_to([0, 2.15, 0])
        self.play(FadeIn(spec, shift=UP * 0.2), run_time=T_NORM)
        self.wait(2.0)

        rows = self._test_rows(size=FS_SMALL)
        rows.move_to([-0.7, -0.45, 0])
        tag = txt("The test suite", size=FS_SMALL, color=INK_DIM)
        tag.next_to(rows, UP, buff=0.5).align_to(rows, LEFT)
        self.play(FadeIn(tag), run_time=T_FAST)
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.2) for r in rows],
                              lag_ratio=0.2), run_time=1.6)
        self.wait(4.6)

        # Brace against the block's full width, not the union of the braced
        # rows: the rows have ragged right edges, and a Brace fitted to that
        # union would sit on top of whichever row is widest.
        def span(first, last):
            top = rows[first].get_top()[1]
            bottom = rows[last].get_bottom()[1]
            box = Rectangle(width=rows.width, height=top - bottom)
            box.move_to([rows.get_center()[0], (top + bottom) / 2, 0])
            return box.set_opacity(0).set_stroke(width=0)

        sorted_note = txt("Sorted input", size=FS_TINY, color=INK_FAINT)
        unsorted_note = txt("Unsorted input", size=FS_TINY, color=ACCENT)
        brace_top = Brace(span(0, 2), RIGHT, color=INK_FAINT, buff=0.32)
        brace_bot = Brace(span(3, 4), RIGHT, color=ACCENT, buff=0.32)
        sorted_note.next_to(brace_top, RIGHT, buff=0.22)
        unsorted_note.next_to(brace_bot, RIGHT, buff=0.22)
        self.play(GrowFromCenter(brace_top), FadeIn(sorted_note),
                  run_time=T_NORM)
        self.play(GrowFromCenter(brace_bot), FadeIn(unsorted_note),
                  run_time=T_NORM)
        self.wait(4.2)

        reward = mathtex(r"r \;=\; \text{fraction of tests that pass}",
                         size=FS_H3, color=GOOD)
        reward.move_to([0, -2.75, 0])
        self.play(FadeIn(reward, shift=UP * 0.2), run_time=T_NORM)
        self.wait(4.8)

        self.play(FadeOut(VGroup(spec, rows, tag, brace_top, brace_bot,
                                 sorted_note, unsorted_note, reward)),
                  run_time=T_NORM)

    # -- 3. First iteration -------------------------------------------------

    def beat_iter1(self):
        self.set_header("Iteration 1")

        tree = SearchTree(origin=self.TREE_ORIGIN, slot_width=1.6,
                          level_gap=1.55, radius=0.36)
        self.tree = tree
        self.play(*tree.add_node("root", None, label="", kind="root"),
                  run_time=T_NORM)

        # Expansion.
        step = chip("Expansion", TEAL, size=FS_SMALL).move_to([3.15, 2.3, 0])
        self.step_chip = step
        self.play(FadeIn(step), run_time=T_FAST)
        note = self.footnote("The paper samples five children per step; "
                             "three here, so the tree fits on screen.")
        self.play(*tree.add_children("root", [
            {"key": key, "label": key} for key, _, _ in CANDIDATES
        ]), FadeIn(note), run_time=1.3)
        self.expansion_note = note

        # Fixed columns inside the right-hand half: key, description, and a
        # right-aligned score column that must not run past the frame edge.
        key_x, desc_x, score_right = 0.5, 1.15, 6.3
        listing, rows_y = VGroup(), [1.0, 0.35, -0.3]
        for (key, description, _), y in zip(CANDIDATES, rows_y):
            tag_key = txt(key, size=FS_BODY, color=PRIMARY, weight=BOLD)
            tag_key.move_to([key_x, y, 0], aligned_edge=LEFT)
            body = txt(description, size=FS_SMALL, color=INK_DIM)
            cap_width(body, 3.5)
            body.move_to([desc_x, y, 0], aligned_edge=LEFT)
            listing.add(VGroup(tag_key, body))
        self.play(LaggedStart(*[FadeIn(m, shift=RIGHT * 0.2) for m in listing],
                              lag_ratio=0.25), run_time=1.4)
        self.wait(3.4)

        # Evaluation.
        self.play(Transform(step, chip("Evaluation", TEAL, size=FS_SMALL)
                            .move_to(step.get_center())), run_time=T_FAST)
        scores = VGroup()
        for y, (key, _, value) in zip(rows_y, CANDIDATES):
            score = mathtex(rf"V = {value:.2f}", size=FS_SMALL, color=INK)
            score.move_to([score_right, y, 0], aligned_edge=RIGHT)
            scores.add(score)
        self.play(LaggedStart(*[FadeIn(s) for s in scores], lag_ratio=0.25),
                  run_time=1.1)
        for key, _, value in CANDIDATES:
            self.play(tree.set_value(key, value), run_time=0.3)
        self.wait(7.4)

        # Selection and simulation.
        self.play(Transform(step, chip("Selection", PRIMARY, size=FS_SMALL)
                            .move_to(step.get_center())), run_time=T_FAST)
        self.play(*tree.highlight_path(["root", "A"]), run_time=T_NORM)
        self.play(FadeOut(VGroup(listing[1], listing[2], scores[1], scores[2])),
                  run_time=T_FAST)
        self.play(VGroup(listing[0], scores[0]).animate.move_to([3.15, 2.3, 0]),
                  FadeOut(step), run_time=T_NORM)

        run_tag = chip("Simulation — run it for real", ACCENT, size=FS_SMALL)
        run_tag.move_to([3.15, 1.55, 0])
        code = code_block(CODE_A, size=FS_MONO - 1)
        code.next_to(run_tag, DOWN, buff=0.4).align_to([0.35, 0, 0], LEFT)
        self.play(FadeIn(run_tag), run_time=T_FAST)
        self.play(FadeIn(code, shift=UP * 0.15), run_time=T_NORM)
        self.wait(2.2)

        marks = VGroup()
        for i, (_, _, passes) in enumerate(TESTS):
            glyph = (check_mark(scale=0.85) if passes
                     else cross_mark(scale=0.85))
            glyph.move_to([0.75 + i * 0.75, -2.35, 0])
            marks.add(glyph)
        label = txt("Tests", size=FS_TINY, color=INK_FAINT)
        label.next_to(marks, LEFT, buff=0.4)
        self.play(FadeIn(label), run_time=T_FAST)
        self.play(LaggedStart(*[FadeIn(m, scale=0.6) for m in marks],
                              lag_ratio=0.32), run_time=1.6)
        score = mathtex(r"r \;=\; 0.60", size=FS_H3, color=ACCENT)
        score.next_to(marks, DOWN, buff=0.42)
        self.play(FadeIn(score, shift=UP * 0.15), run_time=T_NORM)
        self.wait(2.4)

        # Backpropagation.
        back = chip("Backpropagation", GOOD, size=FS_SMALL)
        back.move_to([-3.95, -2.75, 0])
        self.play(FadeIn(back), run_time=T_FAST)
        for key, value in (("A", 0.60), ("root", 0.60)):
            self.play(tree.set_value(key, value),
                      Flash(tree.pos(key), color=GOOD, line_length=0.18,
                            flash_radius=0.5), run_time=0.65)
        self.wait(8.1)

        self.play(FadeOut(VGroup(run_tag, code, marks, label, score, back,
                                 listing[0], scores[0],
                                 self.expansion_note)), run_time=T_NORM)
        self.play(*tree.reset_path(["root", "A"]), run_time=T_FAST)

    # -- 4. Reflection ------------------------------------------------------

    def beat_reflect(self):
        self.set_header("The Trajectory Failed, so Reflection Fires")

        note = speech_bubble(
            "Two failures shared a shape: the input\n"
            "was not sorted. A single left-to-right\n"
            "pass cannot merge intervals that arrive\n"
            "out of order.",
            color=VIOLET, width=6.4, size=FS_SMALL, tail=False)
        note.move_to(self.PANEL_CENTRE + np.array([0, 0.55, 0]))
        tag = chip("Reflection", VIOLET, size=FS_TINY)
        tag.next_to(note, UP, buff=0.22)
        self.play(FadeIn(note, shift=UP * 0.2), FadeIn(tag), run_time=T_NORM)
        self.wait(5.6)

        into = txt("Added to the context of every later attempt",
                   size=FS_SMALL, color=INK_DIM)
        into.next_to(note, DOWN, buff=0.55)
        arrow = Arrow(note.get_bottom() + DOWN * 0.04,
                      into.get_top() + UP * 0.04, buff=0.08,
                      stroke_width=3, color=VIOLET,
                      max_tip_length_to_length_ratio=0.3)
        self.play(Create(arrow), FadeIn(into), run_time=T_NORM)
        self.wait(4.4)
        self.play(FadeOut(VGroup(note, tag, arrow, into)), run_time=T_NORM)

    # -- 5. Second iteration ------------------------------------------------

    def beat_iter2(self):
        self.set_header("Iteration 2")

        tree = self.tree
        parent_visits = 2
        stats = [("A", 0.60, 2), ("B", 0.62, 1), ("C", 0.35, 1)]

        header = VGroup(
            txt("Child", size=FS_TINY, color=INK_FAINT),
            mathtex(r"V", size=FS_TINY, color=INK_FAINT),
            mathtex(r"N", size=FS_TINY, color=INK_FAINT),
            mathtex(r"\mathrm{UCT}", size=FS_TINY, color=INK_FAINT),
        )
        cols = [0.75, 2.35, 3.55, 5.05]
        top_y = 1.85
        for cell, x in zip(header, cols):
            cell.move_to([x, top_y, 0])

        rows, values = VGroup(), []
        for i, (key, value, visits) in enumerate(stats):
            uct = _uct(value, visits, parent_visits)
            values.append(uct)
            y = top_y - 0.62 - i * 0.62
            cells = VGroup(
                txt(key, size=FS_SMALL, color=PRIMARY, weight=BOLD),
                mathtex(f"{value:.2f}", size=FS_SMALL, color=INK),
                mathtex(f"{visits}", size=FS_SMALL, color=INK),
                mathtex(f"{uct:.2f}", size=FS_SMALL, color=INK),
            )
            for cell, x in zip(cells, cols):
                cell.move_to([x, y, 0])
            rows.add(cells)

        best = int(np.argmax(values))
        self.play(FadeIn(header), run_time=T_FAST)
        self.play(LaggedStart(*[FadeIn(r, shift=RIGHT * 0.15) for r in rows],
                              lag_ratio=0.25), run_time=1.3)
        self.wait(2.4)
        ring = SurroundingRectangle(rows[best], color=ACCENT, buff=0.18,
                                    corner_radius=0.12, stroke_width=3)
        self.play(Create(ring), *tree.highlight_path(["root", "B"]),
                  run_time=T_NORM)
        self.wait(10.6)

        self.play(FadeOut(VGroup(header, rows, ring)), run_time=T_NORM)

        # Expansion: the same sweep with one line in front of it.
        code = code_block(CODE_B, size=FS_MONO - 1,
                          highlight={0: GOOD})
        code.move_to(self.PANEL_CENTRE + np.array([0, 0.75, 0]))
        code.align_to([0.35, 0, 0], LEFT)
        one_line = txt("One line different", size=FS_TINY, color=GOOD)
        one_line.next_to(code[0], RIGHT, buff=0.55)
        self.play(FadeIn(code, shift=UP * 0.15), run_time=T_NORM)
        self.play(FadeIn(one_line), Indicate(code[0], color=GOOD,
                                             scale_factor=1.08),
                  run_time=T_NORM)
        self.wait(2.6)

        marks = VGroup()
        for i in range(len(TESTS)):
            glyph = check_mark(scale=0.85)
            glyph.move_to([0.75 + i * 0.75, -1.85, 0])
            marks.add(glyph)
        label = txt("Tests", size=FS_TINY, color=INK_FAINT)
        label.next_to(marks, LEFT, buff=0.4)
        self.play(FadeIn(label), run_time=T_FAST)
        self.play(LaggedStart(*[FadeIn(m, scale=0.6) for m in marks],
                              lag_ratio=0.3), run_time=1.5)
        score = mathtex(r"r \;=\; 1.00", size=FS_H3, color=GOOD)
        score.next_to(marks, DOWN, buff=0.42)
        self.play(FadeIn(score, shift=UP * 0.15), run_time=T_NORM)

        self.play(*tree.add_children("B", [
            {"key": "B1", "label": "", "value": 1.0, "kind": "success"},
        ]), run_time=T_NORM)
        done = chip("Solved", GOOD, size=FS_SMALL)
        done.next_to(tree.node("B1"), DOWN, buff=0.34)
        self.play(FadeIn(done, scale=0.85), run_time=T_NORM)
        self.wait(4.0)

        self.play(FadeOut(VGroup(code, one_line, marks, label, score, done,
                                 tree)), run_time=T_NORM)

    # -- 6. What a linear agent would have done -----------------------------

    def beat_counterfactual(self):
        self.set_header("The Same Task, Without the Tree")

        def run(title, color, steps, y):
            tag = txt(title, size=FS_SMALL, color=color, weight=MEDIUM)
            nodes, caps = VGroup(), VGroup()
            for i, (label, value) in enumerate(steps):
                fill = (GOOD if value == 1.0 else
                        BAD if value is None else ACCENT)
                dot = Circle(radius=0.27, stroke_color=fill, stroke_width=3,
                             fill_color=SURFACE_2, fill_opacity=1.0)
                dot.move_to([-3.5 + i * 1.75, y, 0])
                nodes.add(dot)
                cap = txt(label, size=FS_TINY, color=INK_DIM,
                          line_spacing=0.7)
                cap.next_to(dot, DOWN, buff=0.2)
                caps.add(cap)
            links = VGroup(*[
                Arrow(nodes[i].get_right(), nodes[i + 1].get_left(), buff=0.08,
                      stroke_width=2.5, color=EDGE,
                      max_tip_length_to_length_ratio=0.3)
                for i in range(len(nodes) - 1)
            ])
            tag.move_to([-5.6, y, 0])
            return VGroup(tag, links, nodes, caps)

        linear = run("Linear agent", INK_DIM, [
            ("3 / 5", 0.6), ("Patch\n3 / 5", 0.6), ("Patch\n3 / 5", 0.6),
            ("Give up", None),
        ], y=1.5)
        lats = run("LATS", GOOD, [
            ("3 / 5", 0.6), ("Back to\nthe root", 0.6),
            ("Sort first\n5 / 5", 1.0),
        ], y=-1.05)

        self.play(FadeIn(linear), run_time=T_NORM)
        self.wait(7.6)
        self.play(FadeIn(lats), run_time=T_NORM)
        self.wait(3.4)

        # The backward move is the whole difference; draw it and let it stand.
        arrow = CurvedArrow(lats[2][0].get_top() + UP * 0.1,
                            lats[2][1].get_top() + UP * 0.1,
                            angle=-1.1, color=GOOD, stroke_width=4,
                            tip_length=0.22)
        self.play(Create(arrow), run_time=T_SLOW)
        self.play(Flash(arrow.point_from_proportion(0.5), color=GOOD,
                        line_length=0.22, flash_radius=0.55), run_time=T_NORM)
        self.wait(3.6)

        # Dim the losing run right down: the surviving picture is the point.
        self.play(linear.animate.set_opacity(0.18), run_time=T_SLOW)
        self.wait(5.4)

        self.clear_body(run_time=T_NORM)
        self.drop_header()
