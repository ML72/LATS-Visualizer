"""
Part 5 - The math, and the intuition behind it.

Three equations, one per operation that has one:

    selection        UCT(s) = V(s) + w * sqrt( ln N(p) / N(s) )
    evaluation       V(s)   = lambda * LM(s) + (1 - lambda) * SC(s)
    backpropagation  V(s)  <- ( V(s) * (N(s) - 1) + r ) / N(s)

and then reflection, which has none - which is the point of the fourth beat.

The centrepiece is the exploration sweep: two stacked bars per child, and a
slider on w that flips which child wins. The numbers on screen are computed
from the formula at render time (see :data:`CHILDREN` and :func:`_uct`), so if
you edit them the picture stays honest.

Render:  manim -qh scripts/create_video/parts/part5_math.py Part5Math
"""

import sys
from math import log, sqrt
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, SearchTree, chip, overlay, section_card, speech_bubble,
)
from create_video.theme import (  # noqa: E402
    ACCENT, EDGE, FS_BODY, FS_H3, FS_SMALL, FS_TINY, GOOD, INK, INK_DIM,
    INK_FAINT, PRIMARY, STROKE, SURFACE_2, T_FAST, T_NORM, T_SLOW, TEAL,
    VIOLET, cap_width, mathtex, txt,
)

NARRATION = {
    "beat_section": [
        "Time for the equations. There are three of them, they are all short, "
        "and each one is just a sentence written in symbols.",
    ],
    "beat_uct": [
        "Selection first. At every level, LATS scores each child with this, and "
        "takes the largest.",
        "The first term is the value: how good we currently think this branch "
        "is. On its own, that is pure greed - always go where things already "
        "look best.",
        "The second term is the correction. At the bottom of that fraction is "
        "how often we have visited this child: fewer visits, bigger term. A "
        "bonus for being under-explored.",
        "And w decides how much that bonus is worth. Watch what happens when we "
        "turn it up.",
        "At w equals zero, child A wins on value alone. As w grows, child C - "
        "looked at exactly once - overtakes it, because we do not yet know "
        "whether its low score was real or bad luck. The default is w equals "
        "one.",
    ],
    "beat_value": [
        "Which raises the obvious question: where does V come from? In AlphaGo "
        "a trained network produced it. Here, there is no network.",
        "So LATS builds it from two things it can get for free. LM of s is the "
        "model reading its own transcript and grading it. SC of s is "
        "self-consistency: of the actions sampled here, how many agreed with "
        "this one. Lambda decides the mix.",
        "But the part that actually matters is when this is computed. Tree of "
        "Thoughts scores a step as soon as it is proposed. LATS takes the step "
        "in the real environment first, sees what happened, and only then "
        "grades it.",
        "The paper is explicit that this is the distinction, and the ablations "
        "back it up: remove the value estimate and performance falls further "
        "than for any other change.",
    ],
    "beat_backup": [
        "Third equation. A trajectory has finished and produced a reward, and "
        "now every node on the path back to the root needs updating.",
        "This looks like the most technical of the three, and it is the least. "
        "Multiply the old average by the old count, add the new sample, divide "
        "by the new count. It is a running average.",
        "So a node with a single visit worth zero point eight gets a second "
        "visit worth zero point three, and becomes zero point five five. That "
        "number then flows up to its parent, and on to the root.",
        "This is what makes the next selection smarter than the last one.",
    ],
    "beat_reflect": [
        "And the sixth operation has no equation at all.",
        "Reflection is a prompt. Its output is a sentence, and that sentence "
        "gets pasted into the context of the next attempt. There is nothing to "
        "differentiate and nothing to tune.",
        "It is also the one operation on this list that nobody could have "
        "written down in 2006, because it only makes sense when your agent "
        "reads.",
    ],
}

#: (name, V(s), N(s)) for the three children in the exploration sweep.
CHILDREN = [("Child A", 0.72, 8), ("Child B", 0.55, 3), ("Child C", 0.40, 1)]
#: N(p), the parent's visit count.
PARENT_VISITS = 12


def _bonus(visits: int) -> float:
    """The exploration term, without the weight: sqrt( ln N(p) / N(s) )."""
    return sqrt(log(PARENT_VISITS) / visits)


def _uct(value: float, visits: int, w: float) -> float:
    return value + w * _bonus(visits)


class Part5Math(LATSScene):
    """UCT, the value blend, the backup rule - and the one with no equation."""

    PART = 5
    TITLE = "The Math, and the Intuition"

    def beats(self):
        return [
            self.beat_section,
            self.beat_uct,
            self.beat_value,
            self.beat_backup,
            self.beat_reflect,
        ]

    # -- 1. Section card ----------------------------------------------------

    def beat_section(self):
        card = section_card(5, "The Math", "Three short equations, and one "
                                            "operation that has none")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(9.0)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 2. Selection: UCT --------------------------------------------------

    def beat_uct(self):
        self.set_header("Selection")

        eq = MathTex(r"\mathrm{UCT}(s)", "=", "V(s)", "+",
                     r"w\,\sqrt{\dfrac{\ln N(p)}{N(s)}}",
                     font_size=54, color=INK)
        eq.move_to([0, 1.15, 0])
        self.play(Write(eq), run_time=1.6)
        self.wait(3.2)

        # Term one: exploitation. Both captions share a baseline so the pair
        # reads as one row rather than a staircase.
        caption_y = -0.05
        box_v = SurroundingRectangle(eq[2], color=GOOD, buff=0.14,
                                     corner_radius=0.1, stroke_width=3)
        lab_v = txt("How good we think it is", size=FS_BODY, color=GOOD)
        lab_v.move_to([box_v.get_center()[0] - 0.95, caption_y, 0])
        tick_v = Line(box_v.get_bottom(), [lab_v.get_center()[0],
                                           lab_v.get_top()[1] + 0.16, 0],
                      stroke_color=GOOD, stroke_width=2)
        self.play(Create(box_v), Create(tick_v),
                  FadeIn(lab_v, shift=UP * 0.15), run_time=T_NORM)
        self.wait(6.4)

        # Term two: exploration.
        box_u = SurroundingRectangle(eq[4], color=PRIMARY, buff=0.14,
                                     corner_radius=0.1, stroke_width=3)
        lab_u = txt("How little we have looked", size=FS_BODY, color=PRIMARY)
        lab_u.move_to([box_u.get_center()[0] + 0.95, caption_y, 0])
        tick_u = Line(box_u.get_bottom(), [lab_u.get_center()[0],
                                           lab_u.get_top()[1] + 0.16, 0],
                      stroke_color=PRIMARY, stroke_width=2)
        self.play(Create(box_u), Create(tick_u),
                  FadeIn(lab_u, shift=UP * 0.15), run_time=T_NORM)
        self.wait(1.4)
        self.play(Indicate(eq[4][-4:], color=ACCENT, scale_factor=1.15),
                  run_time=T_SLOW)
        self.wait(8.2)
        self.play(FadeOut(VGroup(tick_v, tick_u)), run_time=T_FAST)

        self.play(FadeOut(VGroup(box_v, box_u, lab_v, lab_u)), run_time=T_FAST)
        self.play(eq.animate.scale(0.62).move_to([0, 2.28, 0]), run_time=T_NORM)

        # --- the tug of war ------------------------------------------------
        w_tracker = ValueTracker(0.0)
        base_y, max_h, scale_max = -2.45, 3.9, 2.45
        xs = [-3.55, -0.85, 1.85]
        bar_w = 1.05

        def columns():
            group = VGroup()
            totals = [_uct(v, n, w_tracker.get_value()) for _, v, n in CHILDREN]
            best = int(np.argmax(totals))
            for i, ((name, value, visits), x) in enumerate(zip(CHILDREN, xs)):
                vh = max_h * value / scale_max
                uh = max_h * (w_tracker.get_value() * _bonus(visits)) / scale_max
                lower = Rectangle(width=bar_w, height=max(vh, 0.001),
                                  stroke_width=0, fill_color=GOOD,
                                  fill_opacity=0.95)
                lower.move_to([x, base_y + vh / 2, 0])
                upper = Rectangle(width=bar_w, height=max(uh, 0.001),
                                  stroke_width=0, fill_color=PRIMARY,
                                  fill_opacity=0.95)
                upper.move_to([x, base_y + vh + uh / 2, 0])
                total = txt(f"{totals[i]:.2f}", size=FS_SMALL,
                            color=ACCENT if i == best else INK_DIM,
                            weight=MEDIUM)
                total.move_to([x, base_y + vh + uh + 0.28, 0])
                col = VGroup(lower, upper, total)
                if i == best:
                    crown = Triangle(color=ACCENT, fill_color=ACCENT,
                                     fill_opacity=1.0, stroke_width=0)
                    crown.scale(0.13).rotate(PI)
                    crown.move_to([x, base_y + vh + uh + 0.72, 0])
                    col.add(crown)
                group.add(col)
            return group

        # Rebuilt every frame as w changes. An updater rather than
        # always_redraw() so there is a single handle to fade out at the end -
        # always_redraw's mobject cannot be removed cleanly mid-scene.
        bars = columns()
        bars.add_updater(lambda m: m.become(columns()))
        baseline = Line([-4.9, base_y, 0], [3.6, base_y, 0],
                        stroke_color=STROKE, stroke_width=2)

        captions = VGroup()
        for (name, value, visits), x in zip(CHILDREN, xs):
            cap = VGroup(
                txt(name, size=FS_SMALL, color=INK),
                mathtex(rf"V = {value:.2f}\;\;\; N = {visits}", size=FS_SMALL,
                        color=INK_DIM),
            ).arrange(DOWN, buff=0.14)
            cap.move_to([x, base_y - 0.55, 0])
            captions.add(cap)

        readout = VGroup(
            mathtex(r"w \;=", size=42, color=ACCENT),
            DecimalNumber(0.0, num_decimal_places=2, font_size=42,
                          color=ACCENT),
        ).arrange(RIGHT, buff=0.24)
        readout[1].add_updater(lambda d: d.set_value(w_tracker.get_value()))
        readout.move_to([5.05, 1.0, 0])

        legend = VGroup(
            VGroup(Square(0.22, stroke_width=0, fill_color=PRIMARY,
                          fill_opacity=1),
                   txt("Explore", size=FS_TINY, color=INK_DIM)
                   ).arrange(RIGHT, buff=0.18),
            VGroup(Square(0.22, stroke_width=0, fill_color=GOOD,
                          fill_opacity=1),
                   txt("Exploit", size=FS_TINY, color=INK_DIM)
                   ).arrange(RIGHT, buff=0.18),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.22)
        legend.move_to([5.05, -0.15, 0])

        self.play(Create(baseline), FadeIn(captions), run_time=T_NORM)
        self.add(bars)
        self.play(FadeIn(readout), FadeIn(legend), run_time=T_NORM)
        self.wait(6.4)

        self.play(w_tracker.animate.set_value(1.0), run_time=6.0,
                  rate_func=linear)
        self.wait(3.4)
        self.play(w_tracker.animate.set_value(0.0), run_time=2.4,
                  rate_func=linear)
        self.play(w_tracker.animate.set_value(1.0), run_time=3.4,
                  rate_func=linear)
        self.wait(3.6)

        default = txt("The paper's default\nis w = 1", size=FS_SMALL,
                      color=INK_FAINT, line_spacing=0.8)
        default.move_to([5.05, -1.55, 0])
        self.play(FadeIn(default), run_time=T_FAST)
        self.wait(6.5)

        bars.clear_updaters()
        readout[1].clear_updaters()
        self.play(FadeOut(VGroup(eq, baseline, captions, readout, bars,
                                 legend, default)), run_time=T_NORM)

    # -- 3. Evaluation: where V comes from ----------------------------------

    def beat_value(self):
        self.set_header("Evaluation")

        eq = MathTex("V(s)", "=", r"\lambda", r"\cdot\,\mathrm{LM}(s)", "+",
                     r"(1-\lambda)", r"\cdot\,\mathrm{SC}(s)",
                     font_size=52, color=INK)
        eq.move_to([0, 1.85, 0])
        self.play(Write(eq), run_time=1.5)
        self.wait(9.4)

        cards = VGroup()
        for part, title, gloss, color in [
            (3, "LM(s)", "The model reads its own transcript\nand grades it",
             TEAL),
            (6, "SC(s)", "Of the actions sampled here,\nhow many agreed "
                         "with this one", PRIMARY),
        ]:
            head = txt(title, size=FS_H3, color=color, weight=MEDIUM)
            body = txt(gloss, size=FS_SMALL, color=INK_DIM, line_spacing=0.8)
            cards.add(VGroup(head, body).arrange(DOWN, buff=0.22))
        cards.arrange(RIGHT, buff=1.5, aligned_edge=UP)
        cards.move_to([0, 0.45, 0])

        box_lm = SurroundingRectangle(eq[3], color=TEAL, buff=0.1,
                                      corner_radius=0.1, stroke_width=3)
        box_sc = SurroundingRectangle(eq[6], color=PRIMARY, buff=0.1,
                                      corner_radius=0.1, stroke_width=3)
        self.play(Create(box_lm), FadeIn(cards[0], shift=UP * 0.15),
                  run_time=T_NORM)
        self.wait(8.6)
        self.play(Create(box_sc), FadeIn(cards[1], shift=UP * 0.15),
                  run_time=T_NORM)
        self.wait(6.4)

        lam = txt("λ = 0.5 for question answering,   λ = 0.8 for code and web",
                  size=FS_SMALL, color=INK_FAINT)
        lam.move_to([0, -1.1, 0])
        self.play(FadeIn(lam), run_time=T_FAST)
        self.wait(4.2)

        self.play(FadeOut(VGroup(cards, box_lm, box_sc, lam)), run_time=T_NORM)
        self.play(eq.animate.scale(0.66).move_to([0, 2.3, 0]), run_time=T_NORM)

        # The distinction from Tree of Thoughts: when the score is taken.
        def pipeline(labels, y, color, dim=False):
            boxes = VGroup()
            for text, c in labels:
                body = txt(text, size=FS_SMALL,
                           color=INK_FAINT if dim else c)
                box = RoundedRectangle(
                    corner_radius=0.12, width=body.width + 0.6,
                    height=0.66, stroke_color=INK_FAINT if dim else c,
                    stroke_width=2, fill_color=SURFACE_2, fill_opacity=1.0)
                body.move_to(box.get_center())
                boxes.add(VGroup(box, body))
            boxes.arrange(RIGHT, buff=0.5)
            arrows = VGroup(*[
                Arrow(boxes[i].get_right(), boxes[i + 1].get_left(), buff=0.08,
                      stroke_width=2.5, color=EDGE,
                      max_tip_length_to_length_ratio=0.32)
                for i in range(len(boxes) - 1)
            ])
            group = VGroup(arrows, boxes)
            group.move_to([0.2, y, 0])
            return group

        tot = pipeline([("Propose a step", INK_DIM), ("Score it", INK_DIM)],
                       0.95, INK_DIM, dim=True)
        lats = pipeline([("Propose a step", PRIMARY),
                         ("Run it for real", TEAL),
                         ("See what happened", TEAL),
                         ("Score it", GOOD)], -1.05, PRIMARY)

        # Left-align the two rows on a common start, so the two extra steps
        # LATS takes read as extra rather than as a different layout. The row
        # labels sit above each row: beside them they run off the left edge.
        tot.align_to(lats, LEFT)
        tag_tot = txt("Tree of Thoughts", size=FS_SMALL, color=INK_FAINT)
        tag_tot.next_to(tot, UP, buff=0.2).align_to(tot, LEFT)
        tag_lats = txt("LATS", size=FS_SMALL, color=INK, weight=MEDIUM)
        tag_lats.next_to(lats, UP, buff=0.2).align_to(lats, LEFT)

        self.play(FadeIn(tag_tot), FadeIn(tot), run_time=T_NORM)
        self.wait(3.0)
        self.play(FadeIn(tag_lats), FadeIn(lats), run_time=T_NORM)
        self.wait(1.6)
        ring = SurroundingRectangle(VGroup(lats[1][1], lats[1][2]),
                                    color=ACCENT, corner_radius=0.14,
                                    buff=0.14, stroke_width=3)
        self.play(Create(ring), run_time=T_NORM)
        self.wait(8.3)

        self.wait(9.6)
        self.play(FadeOut(VGroup(eq, tot, lats, tag_tot, tag_lats, ring)),
                  run_time=T_NORM)

    # -- 4. Backpropagation: a running average ------------------------------

    def beat_backup(self):
        self.set_header("Backpropagation")

        eq = MathTex("V(s)", r"\;\leftarrow\;",
                     r"\frac{V(s)\,\bigl(N(s)-1\bigr)\;+\;r}{N(s)}",
                     font_size=52, color=INK)
        eq.move_to([0, 1.75, 0])
        self.play(Write(eq), run_time=1.5)
        self.wait(8.4)

        plain = txt("Old average × old count,  plus the new sample,  "
                    "divided by the new count", size=FS_BODY, color=INK_DIM)
        cap_width(plain, 12.0)
        plain.move_to([0, 0.62, 0])
        self.play(FadeIn(plain, shift=UP * 0.15), run_time=T_NORM)
        self.wait(2.4)

        running = chip("A running average", ACCENT, size=FS_BODY)
        running.move_to([0, -0.28, 0])
        self.play(FadeIn(running, scale=0.9), run_time=T_NORM)
        self.wait(6.4)

        worked = MathTex(r"\frac{0.80 \times 1 \;+\; 0.30}{2}", "=", "0.55",
                         font_size=48, color=INK)
        worked[2].set_color(ACCENT)
        worked.move_to([0, -1.75, 0])
        self.play(FadeIn(worked, shift=UP * 0.2), run_time=T_NORM)
        self.wait(7.8)

        self.play(FadeOut(VGroup(plain, running, worked)), run_time=T_NORM)
        self.play(eq.animate.scale(0.6).move_to([-4.15, 1.45, 0]),
                  run_time=T_NORM)

        # The update travelling up a path.
        tree = SearchTree(origin=[1.9, 2.15, 0], slot_width=1.95,
                          level_gap=1.5, radius=0.38)
        tree.add_node("s0", None, label="", value=0.80, show_value=True)
        for spec in ({"key": "x", "label": "", "value": 0.35},
                     {"key": "y", "label": "", "value": 0.80}):
            tree.add_node(spec["key"], "s0", label="", value=spec["value"],
                          show_value=True)
        for spec in ({"key": "y1", "label": "", "value": 0.80},
                     {"key": "y2", "label": "", "value": None}):
            tree.add_node(spec["key"], "y", label="", value=spec["value"],
                          show_value=spec["value"] is not None)
        tree.place()
        self.play(FadeIn(tree), run_time=T_NORM)

        reward = chip("r = 0.30", ACCENT, size=FS_SMALL)
        reward.next_to(tree.node("y1"), DOWN, buff=0.3)
        overlay(reward)
        self.play(FadeIn(reward, shift=UP * 0.2), run_time=T_NORM)
        self.wait(1.4)

        for key, value in (("y1", 0.55), ("y", 0.55), ("s0", 0.55)):
            self.play(tree.set_value(key, value),
                      Flash(tree.pos(key), color=ACCENT, line_length=0.18,
                            flash_radius=0.46), run_time=0.7)
            self.wait(0.45)
        self.wait(3.6)

        self.wait(6.4)
        self.play(FadeOut(VGroup(eq, tree, reward)), run_time=T_NORM)

    # -- 5. Reflection: no equation -----------------------------------------

    def beat_reflect(self):
        self.set_header("Reflection")

        slot = DashedVMobject(
            RoundedRectangle(corner_radius=0.16, width=7.2, height=1.3,
                             stroke_color=INK_FAINT, stroke_width=2),
            num_dashes=52)
        slot.move_to([0, 1.85, 0])
        empty = txt("No equation", size=FS_H3, color=INK_FAINT)
        empty.move_to(slot.get_center())
        self.play(Create(slot), FadeIn(empty), run_time=T_NORM)
        self.wait(4.4)

        bubble = speech_bubble(
            "Attempt 1 failed on the input [[3, 5], [1, 2]].\n"
            "The one-pass merge assumed the list was sorted.\n"
            "Sort by interval start first, then merge.",
            color=VIOLET, width=8.0, size=FS_BODY, tail=False)
        bubble.move_to([0, -0.5, 0])
        tag = chip("Output of the reflection prompt", VIOLET, size=FS_TINY)
        tag.next_to(bubble, UP, buff=0.2)
        self.play(FadeIn(bubble, shift=UP * 0.2), FadeIn(tag), run_time=T_NORM)
        self.wait(6.4)

        arrow = Arrow(bubble.get_bottom() + DOWN * 0.06,
                      [0, -2.6, 0], buff=0.1, stroke_width=3, color=VIOLET,
                      max_tip_length_to_length_ratio=0.22)
        dest = txt("Pasted into the context of every later attempt",
                   size=FS_BODY, color=INK)
        dest.move_to([0, -2.95, 0])
        self.play(Create(arrow), FadeIn(dest, shift=UP * 0.15), run_time=T_NORM)
        self.wait(7.3)

        self.wait(6.0)
        self.clear_body(run_time=T_NORM)
        self.drop_header()
