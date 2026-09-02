"""
Part 3 - Monte Carlo Tree Search.

Where the tree from Part 2 gets an algorithm: a twenty-year-old one. Covers the
history, the bandit intuition behind the selection rule, and then the four
classical operations animated on a growing tree.

The formulas are deliberately absent here - Part 4 puts them on screen. This
part only has to make you believe that "spend the next sample where the payoff
is both promising and uncertain" is a sensible thing to do.

Render:  manim -qh scripts/create_video/parts/part3_mcts.py Part3MCTS
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, SearchTree, chip, overlay, section_card, strike,
)
from create_video.theme import (  # noqa: E402
    ACCENT, FS_BODY, FS_H3, FS_SMALL, FS_TINY, GOOD, INK, INK_DIM,
    INK_FAINT, PRIMARY, STROKE, SURFACE_2, T_FAST, T_NORM, T_SLOW, TEAL,
    cap_width, txt,
)

NARRATION = {
    "beat_section": [
        "Now we need an algorithm for growing that tree. There is a very good "
        "one, and it is twenty years old.",
    ],
    "beat_history": [
        "Monte Carlo Tree Search was named by Rémi Coulom in 2006. The same "
        "year, Kocsis and Szepesvári gave it the selection rule it still "
        "uses: UCT - upper confidence bounds applied to trees.",
        "Ten years later it was the search algorithm inside AlphaGo. This is "
        "not a new idea; it is a very well-tested one.",
    ],
    "beat_bandit": [
        "The question underneath it is the multi-armed bandit. Three "
        "machines, unknown payouts. You have pulled the first eight times, "
        "averaging point six two; the second, three times; the third, exactly "
        "once.",
        "Which next? The first has the best record - but you have barely "
        "looked at the third. Its point four zero is a single sample, and "
        "could easily be bad luck.",
        "So score each arm by two terms added together: its empirical mean, "
        "plus a bonus that grows as the pull count shrinks.",
        "That sum is an upper confidence bound. A concentration inequality "
        "puts the true mean below it with high probability, so taking the "
        "largest is optimism under uncertainty.",
    ],
    "beat_ops": [
        "Monte Carlo Tree Search turns that into four operations, repeated "
        "until the budget runs out.",
        "Selection. From the root, walk down applying that bandit rule at "
        "each level, until you reach a node that has not been expanded. That "
        "walk is called the tree policy.",
        "Expansion. Add children of that node to the tree.",
        "Simulation, or rollout. From one child, play out to a terminal state "
        "- classically with a cheap random policy - and take the outcome.",
        "Backpropagation. Walk back up the path, incrementing each ancestor's "
        "visit count and folding the outcome into its value.",
        "Then repeat, now with real numbers to select on.",
    ],
    "beat_asymmetric": [
        "Do that a few thousand times and the tree comes out badly "
        "lopsided, which is the point. Nearly all the compute went into the "
        "branch that looked worth it; the hopeless ones were sampled once and "
        "left alone.",
        "Kocsis and Szepesvári also showed that as the number of simulations "
        "grows, the probability of picking a suboptimal action at the root "
        "goes to zero.",
    ],
    "beat_bridge": [
        "But notice what AlphaGo needed. A trained policy network to propose "
        "moves, a trained value network to score positions, and a simulator "
        "it could play out at random millions of times.",
        "For a language agent we have none of the three: no policy network "
        "over arbitrary text, no value network for half-written code, no "
        "cheap simulator.",
    ],
}

ON_SCREEN = {
    "beat_section": "Section card - 3 / Monte Carlo Tree Search.",
    "beat_history": "A timeline: 2006 Coulom names MCTS; 2006 Kocsis and "
                    "Szepesvári derive UCT; 2016 AlphaGo beats Lee Sedol; "
                    "2024 LATS.",
    "beat_bandit": "Three slot machines - Arm A, eight pulls, mean 0.62; Arm "
                   "B, three pulls, 0.55; Arm C, one pull, 0.40. A is ringed "
                   "Best record, C is ringed Barely looked at. Then the "
                   "recipe, captioned as an upper confidence bound.",
    "beat_ops": "The four operations light up one at a time on a rail to the "
                "right while the tree performs each of them: root "
                "highlighted, three children added, a dashed playout "
                "returning r = 0.8, then the value flowing back up. Then a "
                "faster second round.",
    "beat_asymmetric": "The tree grows two more levels down one branch only, "
                       "then everything except that branch dims to almost "
                       "nothing; the UCT convergence result appears "
                       "underneath.",
    "beat_bridge": "Three requirements appear as chips, then each is struck "
                   "through in turn.",
}


class Part3MCTS(LATSScene):
    """The bandit intuition, then the four operations, on a growing tree."""

    PART = 3
    TITLE = "Monte Carlo Tree Search"

    #: Right-hand rail: the four operations, in order.
    OPS = [
        ("Selection", PRIMARY),
        ("Expansion", TEAL),
        ("Simulation", ACCENT),
        ("Backpropagation", GOOD),
    ]

    def beats(self):
        return [
            self.beat_section,
            self.beat_history,
            self.beat_bandit,
            self.beat_ops,
            self.beat_asymmetric,
            self.beat_bridge,
        ]

    # -- 1. Section card ----------------------------------------------------

    def beat_section(self):
        card = section_card(3, "Monte Carlo Tree Search",
                            "A 2006 answer to “where should I look next?”")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(7.6)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 2. Twenty years of history -----------------------------------------

    def beat_history(self):
        self.set_header("MCTS History")

        axis = Line([-5.6, -0.15, 0], [5.6, -0.15, 0], stroke_color=STROKE,
                    stroke_width=3)
        self.play(Create(axis), run_time=T_NORM)

        events = [
            (-4.6, "2006", "Coulom names MCTS", PRIMARY, True),
            (-1.4, "2006",
             "Kocsis and Szepesvári\nderive the UCT rule", PRIMARY, False),
            (1.8, "2016", "AlphaGo beats\nLee Sedol", ACCENT, True),
            (4.8, "2024", "LATS", GOOD, False),
        ]
        marks = VGroup()
        for x, year, label, color, above in events:
            tick = Line([x, -0.33, 0], [x, 0.03, 0], stroke_color=color,
                        stroke_width=4)
            dot = Dot([x, -0.15, 0], radius=0.09, color=color)
            y_label = txt(year, size=FS_H3, color=color, weight=MEDIUM)
            body = txt(label, size=FS_SMALL, color=INK_DIM, line_spacing=0.8)
            stack = VGroup(y_label, body).arrange(DOWN, buff=0.16)
            stack.next_to([x, -0.15, 0], UP if above else DOWN, buff=0.46)
            marks.add(VGroup(tick, dot, stack))

        for mark in marks:
            self.play(FadeIn(mark, shift=UP * 0.15 if mark[2].get_y() > -0.15
                             else DOWN * 0.15), run_time=0.55)
            self.wait(1.9)
        self.wait(13.0)
        self.play(FadeOut(VGroup(axis, marks)), run_time=T_NORM)

    # -- 3. The bandit question ---------------------------------------------

    @staticmethod
    def _machine(name, pulls, mean, x, color):
        """A labelled arm: a little lever box over its record so far."""
        body = RoundedRectangle(corner_radius=0.14, width=1.5, height=1.05,
                                stroke_color=color, stroke_width=3,
                                fill_color=SURFACE_2, fill_opacity=1.0)
        slot = Line(body.get_center() + LEFT * 0.42 + UP * 0.12,
                    body.get_center() + RIGHT * 0.42 + UP * 0.12,
                    stroke_color=INK_FAINT, stroke_width=3)
        lever_arm = Line(body.get_right() + RIGHT * 0.02 + DOWN * 0.1,
                         body.get_right() + RIGHT * 0.02 + UP * 0.3,
                         stroke_color=color, stroke_width=4)
        knob = Dot(lever_arm.get_end(), radius=0.09, color=color)
        tag = txt(name, size=FS_SMALL, color=color, weight=MEDIUM)
        tag.move_to(body.get_center() + DOWN * 0.24)

        stats = VGroup(
            txt(f"{pulls} pull" + ("" if pulls == 1 else "s"),
                size=FS_TINY, color=INK_FAINT),
            txt(f"Mean {mean:.2f}", size=FS_BODY, color=INK, weight=MEDIUM),
        ).arrange(DOWN, buff=0.12)
        machine = VGroup(body, slot, lever_arm, knob, tag)
        stats.next_to(machine, DOWN, buff=0.3)
        group = VGroup(machine, stats)
        group.move_to([x, 0, 0])
        return group

    def beat_bandit(self):
        self.set_header("What Arm to Select?")

        arms = [("Arm A", 8, 0.62, -3.9, PRIMARY),
                ("Arm B", 3, 0.55, 0.0, PRIMARY),
                ("Arm C", 1, 0.40, 3.9, PRIMARY)]
        machines = VGroup(*[self._machine(*a) for a in arms])
        machines.move_to([0, 1.15, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in machines],
                              lag_ratio=0.25), run_time=1.5)
        self.wait(14.0)

        # Best record vs least explored.
        best = SurroundingRectangle(machines[0], color=GOOD, buff=0.16,
                                    corner_radius=0.16, stroke_width=3)
        best_tag = txt("Best record", size=FS_TINY, color=GOOD)
        best_tag.next_to(best, UP, buff=0.16)
        least = SurroundingRectangle(machines[2], color=ACCENT, buff=0.16,
                                     corner_radius=0.16, stroke_width=3)
        least_tag = txt("Barely looked at", size=FS_TINY, color=ACCENT)
        least_tag.next_to(least, UP, buff=0.16)
        self.play(Create(best), FadeIn(best_tag), run_time=T_NORM)
        self.wait(1.6)
        self.play(Create(least), FadeIn(least_tag), run_time=T_NORM)
        self.wait(10.4)

        # The answer, as two quantities added.
        recipe = VGroup(
            chip("How good it looks", GOOD, size=FS_SMALL),
            txt("+", size=FS_H3, color=INK_DIM),
            chip("How little you have looked", PRIMARY, size=FS_SMALL),
            txt("→", size=FS_H3, color=INK_DIM),
            chip("Take the largest", ACCENT, size=FS_SMALL),
        ).arrange(RIGHT, buff=0.3)
        cap_width(recipe, 12.4)
        recipe.move_to([0, -1.85, 0])
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in recipe],
                              lag_ratio=0.2), run_time=1.4)
        self.wait(5.0)

        # Name the thing the recipe is: this row is UCB1, in words.
        gloss = txt("An upper confidence bound: the mean measured so far, "
                    "plus how uncertain it still is", size=FS_SMALL,
                    color=INK_FAINT)
        cap_width(gloss, 11.8)
        gloss.move_to([0, -2.62, 0])
        cite = self.footnote("UCB1  ·  Auer, Cesa-Bianchi and Fischer, 2002")
        self.play(FadeIn(gloss, shift=UP * 0.15), FadeIn(cite),
                  run_time=T_NORM)
        self.wait(10.6)

        self.play(FadeOut(VGroup(machines, best, best_tag, least, least_tag,
                                 recipe, gloss, cite)), run_time=T_NORM)

    # -- 4. The four operations ---------------------------------------------

    def _rail(self):
        """The right-hand list of the four operations."""
        rows = VGroup()
        for name, color in self.OPS:
            tag = chip(name, color, size=FS_SMALL, fill_opacity=0.0)
            tag[0].set_stroke(opacity=0.35)
            tag[1].set_opacity(0.45)
            rows.add(tag)
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.42)
        rows.move_to([4.75, 0.6, 0])
        return rows

    def _light(self, rail, index):
        """Animations that make one rail entry active and dim the others."""
        anims = []
        for i, row in enumerate(rail):
            on = i == index
            anims.append(row[0].animate.set_stroke(opacity=1.0 if on else 0.3)
                         .set_fill(self.OPS[i][1], 0.16 if on else 0.0))
            anims.append(row[1].animate.set_opacity(1.0 if on else 0.4))
        return anims

    def _rollout(self, tree, key, reward, color=ACCENT):
        """A dashed playout from ``key`` down to a terminal reward chip."""
        start = tree.pos(key)
        end = start + DOWN * 1.15
        line = DashedLine(start + DOWN * tree.radius, end, stroke_color=color,
                          stroke_width=3, dash_length=0.12)
        badge = chip(f"r = {reward:.1f}", color, size=FS_TINY)
        badge.next_to(end, DOWN, buff=0.14)
        overlay(badge)
        return VGroup(line, badge)

    def beat_ops(self):
        self.set_header("Core MCTS Operations")

        rail = self._rail()
        self.play(LaggedStart(*[FadeIn(r, shift=LEFT * 0.2) for r in rail],
                              lag_ratio=0.18), run_time=1.1)
        self.wait(2.6)

        tree = SearchTree(origin=[-1.9, 2.2, 0], slot_width=1.65,
                          level_gap=1.42, radius=0.33)
        self.play(*tree.add_node("s0", None, label="", kind="root"),
                  run_time=T_NORM)
        self.wait(0.8)

        # --- round one -----------------------------------------------------
        self.play(*self._light(rail, 0), run_time=T_FAST)
        self.play(*tree.highlight_path(["s0"]), run_time=T_FAST)
        self.wait(8.0)
        self.play(*tree.reset_path(["s0"]), run_time=T_FAST)

        self.play(*self._light(rail, 1), run_time=T_FAST)
        self.play(*tree.add_children("s0", [
            {"key": "a", "label": ""}, {"key": "b", "label": ""},
            {"key": "c", "label": ""},
        ]), run_time=1.1)
        self.wait(2.0)

        self.play(*self._light(rail, 2), run_time=T_FAST)
        roll = self._rollout(tree, "b", 0.8)
        self.play(Create(roll[0]), run_time=T_NORM)
        self.play(FadeIn(roll[1], scale=0.7), run_time=T_FAST)
        self.wait(4.6)

        self.play(*self._light(rail, 3), run_time=T_FAST)
        for key, value in (("b", 0.80), ("s0", 0.80)):
            self.play(tree.set_value(key, value),
                      Flash(tree.pos(key), color=GOOD, line_length=0.16,
                            flash_radius=0.42), run_time=0.55)
            self.wait(0.5)
        self.play(FadeOut(roll), run_time=T_FAST)
        self.wait(6.0)

        # --- round two -----------------------------------------------------
        self.play(*self._light(rail, 0), run_time=T_FAST)
        self.play(*tree.highlight_path(["s0", "b"]), run_time=T_NORM)
        self.wait(2.0)
        self.play(*tree.reset_path(["s0", "b"]), run_time=T_FAST)

        self.play(*self._light(rail, 1), run_time=T_FAST)
        self.play(*tree.add_children("b", [
            {"key": "b1", "label": ""}, {"key": "b2", "label": ""},
        ]), run_time=1.0)

        self.play(*self._light(rail, 2), run_time=T_FAST)
        roll2 = self._rollout(tree, "b1", 0.3, color=ACCENT)
        self.play(Create(roll2[0]), run_time=T_FAST)
        self.play(FadeIn(roll2[1], scale=0.7), run_time=T_FAST)
        self.wait(1.2)

        self.play(*self._light(rail, 3), run_time=T_FAST)
        for key, value in (("b1", 0.30), ("b", 0.55), ("s0", 0.55)):
            self.play(tree.set_value(key, value),
                      Flash(tree.pos(key), color=GOOD, line_length=0.16,
                            flash_radius=0.42), run_time=0.5)
        self.play(FadeOut(roll2), run_time=T_FAST)
        self.wait(1.8)

        self.tree, self.rail = tree, rail

    # -- 5. The tree comes out lopsided -------------------------------------

    def beat_asymmetric(self):
        self.set_header("The Tree Comes Out Lopsided")
        tree, rail = self.tree, self.rail
        self.play(FadeOut(rail), run_time=T_FAST)
        # Two more levels are coming; make room for them first.
        self.play(*tree.rescale(0.76, origin=[-0.3, 2.35, 0]), run_time=T_NORM)

        # Grow the promising branch, and leave the hopeless one alone.
        self.play(*tree.add_children("b1", [
            {"key": "b1a", "label": "", "value": 0.35},
            {"key": "b1b", "label": "", "value": 0.2},
        ]), run_time=0.8)
        self.play(*tree.add_children("b2", [
            {"key": "b2a", "label": "", "value": 0.7},
            {"key": "b2b", "label": "", "value": 0.62},
        ]), run_time=0.8)
        self.play(*tree.add_children("b2a", [
            {"key": "b2a1", "label": "", "value": 0.86},
            {"key": "b2a2", "label": "", "value": 0.64},
        ]), run_time=0.8)
        self.play(tree.set_value("b2", 0.7), tree.set_value("b", 0.66),
                  run_time=T_FAST)

        self.play(*tree.dim_all(except_keys=[
            "s0", "b", "b2", "b2a", "b2a1", "b2a2", "b2b"], opacity=0.22),
            run_time=T_SLOW)
        self.wait(11.0)

        converge = txt("As simulations grow, the root's chance of choosing a "
                       "suboptimal action goes to zero", size=FS_SMALL,
                       color=INK_FAINT)
        cap_width(converge, 11.8)
        converge.move_to([0, -3.0, 0])
        cite = self.footnote("Kocsis and Szepesvári, 2006")
        self.play(FadeIn(converge, shift=UP * 0.15), FadeIn(cite),
                  run_time=T_NORM)
        self.wait(9.8)
        self.play(FadeOut(tree), FadeOut(converge), FadeOut(cite),
                  run_time=T_NORM)

    # -- 6. What AlphaGo had that we do not ---------------------------------

    def beat_bridge(self):
        self.set_header("What Made It Work")

        needs = VGroup(
            chip("A network that proposes moves", PRIMARY, size=FS_BODY),
            chip("A network that scores positions", TEAL, size=FS_BODY),
            chip("A game you can play out at random", ACCENT, size=FS_BODY),
        ).arrange(DOWN, buff=0.62)
        needs.move_to([0, 0.35, 0])
        self.play(LaggedStart(*[FadeIn(n, shift=UP * 0.2) for n in needs],
                              lag_ratio=0.25), run_time=1.4)
        self.wait(9.0)

        # None of the three survive contact with a language agent. Striking
        # them out says so without a caption.
        for need in needs:
            rule = strike(need, width=4)
            self.play(Create(rule), need.animate.set_opacity(0.35),
                      run_time=0.65)
        self.wait(9.4)
        self.clear_body(run_time=T_NORM)
        self.drop_header()
