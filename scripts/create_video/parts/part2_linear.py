"""
Part 2 - Why a straight line fails.

Three failure modes of linear agents, in order:

1. ReAct commits to one trajectory and cannot back out of it.
2. Each step had alternatives that were sampled once and thrown away.
3. Reflexion retries from scratch, so a correct prefix is paid for every time.

Ends by merging the repeated prefixes into a tree, which is the shape the rest
of the video works with.

Render:  manim -qh scripts/create_video/parts/part2_linear.py Part2Linear
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, SearchTree, chip, cross_mark, section_card, speech_bubble,
)
from create_video.theme import (  # noqa: E402
    ACCENT, BAD, EDGE, FS_BODY, FS_H3, FS_SMALL, FS_TINY, GOOD, INK,
    INK_DIM, INK_FAINT, PRIMARY, SURFACE_2, T_FAST, T_NORM, T_SLOW, TEAL,
    VIOLET, cap_width, mathtex, txt, value_color,
)

NARRATION = {
    "beat_section": [
        "So how does a normal agent choose? Usually, it just walks forwards.",
    ],
    "beat_react": [
        "This is the ReAct pattern, and it is what almost every agent "
        "framework does. Think, act, observe, repeat, in one straight line.",
        "Our agent reads the spec, writes a one-pass merge, runs the tests, "
        "and gets three out of five. It patches the edge case it can see, and "
        "gets three out of five again.",
        "It is stuck, and it would like to go back to that second step and "
        "try something else. A ReAct agent has no way to do that.",
    ],
    "beat_forks": [
        "Rewind to that second step. The model did not have one idea; it had "
        "several. Sort first and sweep. Use an interval tree. Merge "
        "neighbors in one pass.",
        "It sampled one of them, and the other two were never written down. "
        "They are not ranked lower. They simply do not exist any more.",
    ],
    "beat_reflexion": [
        "There is a well-known fix for this, called Reflexion. When a "
        "trajectory fails, the agent writes itself a reflection about why it "
        "failed, and tries the whole task again with that note in context.",
        "It genuinely helps. But look at what it costs. Every attempt starts "
        "from an empty transcript, so the first three steps - which were "
        "perfectly good - get re-derived, and re-paid for, every single time.",
    ],
    "beat_ask": [
        "Which suggests what we actually want. Keep the steps that worked. "
        "Branch only where the decision was, and choose which branch to spend "
        "the next sample on.",
        "That shape has a name. It is a tree.",
    ],
}

#: The linear trajectory, as (short label under the node, node value or None).
TRAJECTORY = [
    ("Read the\nspec", None),
    ("One-pass\nmerge", None),
    ("Run tests\n3 / 5", 0.6),
    ("Patch the\nedge case", None),
    ("Run tests\n3 / 5", 0.6),
]


class Part2Linear(LATSScene):
    """Linear agents commit, discard alternatives, and repeat themselves."""

    PART = 2
    TITLE = "Why a Straight Line Fails"

    def beats(self):
        return [
            self.beat_section,
            self.beat_react,
            self.beat_forks,
            self.beat_reflexion,
            self.beat_ask,
        ]

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _chain(labels, y, x0=-5.15, dx=2.45, radius=0.3, color=PRIMARY,
               label_size=FS_TINY, label_color=INK_DIM):
        """A left-to-right run of nodes joined by arrows.

        Returns ``VGroup(links, nodes, captions)`` with those three groups also
        exposed as attributes, so a caller can animate them independently.
        """
        nodes, captions = VGroup(), VGroup()
        for i, (text, value) in enumerate(labels):
            fill = value_color(value) if value is not None else SURFACE_2
            dot = Circle(radius=radius, stroke_color=color, stroke_width=3,
                         fill_color=fill, fill_opacity=1.0)
            dot.move_to([x0 + i * dx, y, 0])
            nodes.add(dot)
            if text:
                cap = txt(text, size=label_size, color=label_color,
                          line_spacing=0.7)
                cap.next_to(dot, DOWN, buff=0.2)
                captions.add(cap)
        links = VGroup(*[
            Arrow(nodes[i].get_right(), nodes[i + 1].get_left(), buff=0.1,
                  stroke_width=3, color=EDGE, max_tip_length_to_length_ratio=0.14,
                  max_stroke_width_to_length_ratio=6)
            for i in range(len(nodes) - 1)
        ])
        group = VGroup(links, nodes, captions)
        group.links, group.nodes, group.captions = links, nodes, captions
        return group

    # -- 1. Section card ----------------------------------------------------

    def beat_section(self):
        card = section_card(2, "Why a Straight Line Fails",
                            "Commit, discard, repeat")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(3.4)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 2. The linear agent walks into a wall ------------------------------

    def beat_react(self):
        self.set_header("The Straight Line")

        tag = chip("ReAct: think → act → observe → repeat", PRIMARY,
                   size=FS_SMALL)
        tag.move_to([0, 2.1, 0])
        self.play(FadeIn(tag, shift=DOWN * 0.2), run_time=T_NORM)
        self.wait(5.4)

        chain = self._chain(TRAJECTORY, y=0.35)
        self.chain = chain
        self.play(GrowFromCenter(chain.nodes[0]),
                  FadeIn(chain.captions[0], shift=UP * 0.15), run_time=T_NORM)
        for i in range(1, len(chain.nodes)):
            self.play(Create(chain.links[i - 1]), run_time=0.34)
            self.play(GrowFromCenter(chain.nodes[i]),
                      FadeIn(chain.captions[i], shift=UP * 0.15),
                      run_time=0.46)
            self.wait(1.7)
        self.wait(2.2)

        # The dead end: the same score twice, and nowhere left to go.
        mark = cross_mark(scale=1.7).next_to(chain.nodes[-1], RIGHT, buff=0.6)
        repeat = SurroundingRectangle(
            VGroup(chain.nodes[2], chain.captions[2]), color=BAD, buff=0.14,
            corner_radius=0.14, stroke_width=2.5)
        repeat2 = SurroundingRectangle(
            VGroup(chain.nodes[4], chain.captions[4]), color=BAD, buff=0.14,
            corner_radius=0.14, stroke_width=2.5)

        self.play(Create(repeat), Create(repeat2), run_time=T_NORM)
        self.wait(1.8)
        self.play(FadeIn(mark, scale=0.6), run_time=T_NORM)
        self.wait(3.2)

        # It would like to go back to step two. It cannot: draw the move it
        # wants to make, then break it. No caption needed. The ReAct chip goes
        # first, because the arc sweeps through where it sits.
        self.play(FadeOut(tag), run_time=T_FAST)
        back = CurvedArrow(chain.nodes[4].get_top() + UP * 0.12,
                           chain.nodes[1].get_top() + UP * 0.12,
                           angle=0.8, color=BAD, stroke_width=4,
                           tip_length=0.24)
        self.play(Create(back), run_time=T_SLOW)
        self.wait(1.4)
        blocked = cross_mark(scale=2.4).move_to(back.point_from_proportion(0.5))
        self.play(FadeIn(blocked, scale=0.5),
                  Flash(blocked.get_center(), color=BAD, line_length=0.3,
                        flash_radius=0.7), run_time=T_NORM)
        self.play(back.animate.set_stroke(opacity=0.25),
                  Wiggle(back, scale_value=1.02), run_time=T_NORM)
        self.wait(4.6)
        self.play(FadeOut(VGroup(mark, repeat, repeat2, back, blocked)),
                  run_time=T_NORM)

    # -- 3. The alternatives that were never written down -------------------

    def beat_forks(self):
        self.set_header("Every Step Had Alternatives")

        chain = self.chain
        # Dim everything after the decision we are rewinding to.
        self.play(
            VGroup(chain.nodes[2:], chain.captions[2:],
                   chain.links[1:]).animate.set_opacity(0.18),
            run_time=T_NORM)
        self.play(Indicate(chain.nodes[1], color=ACCENT, scale_factor=1.25),
                  run_time=T_NORM)
        self.wait(1.4)

        # Three candidate second steps, laid out in a row so they clear the
        # trajectory and its captions above.
        options = [
            ("sort first,\nthen sweep", GOOD),
            ("build an\ninterval tree", TEAL),
            ("merge neighbors\nin one pass", PRIMARY),
        ]
        cards = VGroup()
        for label, color in options:
            body = txt(label, size=FS_SMALL, color=color, line_spacing=0.75)
            box = RoundedRectangle(
                corner_radius=0.14, width=body.width + 0.74,
                height=body.height + 0.5, stroke_color=color,
                stroke_width=2, fill_color=SURFACE_2, fill_opacity=1.0)
            body.move_to(box.get_center())
            cards.add(VGroup(box, body))
        cards.arrange(RIGHT, buff=0.5)
        cards.move_to([0.35, -1.5, 0])
        # The one actually taken is the approach already on the chain.
        taken = cards[2]

        self.play(LaggedStart(*[FadeIn(c, shift=UP * 0.2) for c in cards],
                              lag_ratio=0.3), run_time=1.6)
        self.wait(6.2)

        ring = SurroundingRectangle(taken, color=ACCENT, corner_radius=0.14,
                                    buff=0.1, stroke_width=3)
        sampled = txt("Sampled", size=FS_TINY, color=ACCENT, weight=MEDIUM)
        sampled.next_to(ring, DOWN, buff=0.2)
        self.play(Create(ring), FadeIn(sampled), run_time=T_NORM)
        self.wait(3.0)

        self.play(FadeOut(cards[0], shift=DOWN * 0.7),
                  FadeOut(cards[1], shift=DOWN * 0.7), run_time=T_SLOW)
        self.wait(5.8)

        self.play(FadeOut(VGroup(chain, taken, ring, sampled)),
                  run_time=T_NORM)

    # -- 4. Reflexion re-derives the prefix every time ----------------------

    def beat_reflexion(self):
        self.set_header("Retrying Is Not the Same as Remembering")

        prefix = [("", None), ("", None), ("", None)]
        suffix_a = [("", 0.6), ("", 0.6)]
        suffix_b = [("", 0.4), ("", 0.4)]
        suffix_c = [("", 0.2), ("", 0.2)]

        # Three attempts stacked on the left; the reflection sits to their
        # right so nothing has to share a row with it.
        rows, ys = VGroup(), [1.55, 0.15, -1.25]
        for y, suffix in zip(ys, (suffix_a, suffix_b, suffix_c)):
            rows.add(self._chain(prefix + suffix, y=y, x0=-5.3, dx=1.28,
                                 radius=0.24))
        labels = VGroup(*[
            txt(f"attempt {i + 1}", size=FS_TINY, color=INK_FAINT)
            for i in range(3)
        ])
        for label, row in zip(labels, rows):
            label.next_to(row.nodes[0], LEFT, buff=0.34)

        self.play(FadeIn(rows[0]), FadeIn(labels[0]), run_time=T_NORM)
        self.wait(1.6)

        method = chip("Reflexion  ·  Shinn et al., 2023", INK_FAINT,
                      size=FS_TINY)
        method.move_to([3.55, 2.15, 0])
        note = speech_bubble(
            "The one-pass merge assumes\nthe input is already sorted.",
            color=VIOLET, width=5.7, tail=False)
        note.move_to([3.55, 0.15, 0])
        note_tag = chip("Reflection", VIOLET, size=FS_TINY)
        note_tag.next_to(note, UP, buff=0.2)
        self.play(FadeIn(method, shift=DOWN * 0.15), run_time=T_FAST)
        self.play(FadeIn(note, shift=LEFT * 0.25), FadeIn(note_tag),
                  run_time=T_NORM)
        self.wait(5.6)

        for i in (1, 2):
            self.play(FadeIn(rows[i]), FadeIn(labels[i]), run_time=T_NORM)
            self.wait(1.2)
        self.wait(3.0)

        # The identical prefix, paid for three times over.
        boxes = VGroup(*[
            SurroundingRectangle(VGroup(row.nodes[0], row.nodes[2]),
                                 color=ACCENT, corner_radius=0.16, buff=0.16,
                                 stroke_width=3)
            for row in rows
        ])
        self.play(LaggedStart(*[Create(b) for b in boxes], lag_ratio=0.25),
                  run_time=1.2)
        cost = mathtex(r"\times\, 3", size=44, color=ACCENT)
        cost.move_to([-2.75, -2.5, 0])
        self.play(FadeIn(cost, shift=UP * 0.2), run_time=T_NORM)
        self.wait(10.4)

        self.play(FadeOut(VGroup(method, note, note_tag, cost, labels)),
                  run_time=T_NORM)
        self.rows, self.boxes = rows, boxes

    # -- 5. Merge the prefixes; you have built a tree -----------------------

    def beat_ask(self):
        self.set_header("So: Keep the Paths")

        rows, boxes = self.rows, self.boxes

        # Slide the three shared prefixes onto one another.
        merged_y = 0.15
        moves = []
        for row, y in zip(rows, [1.55, 0.15, -1.25]):
            dy = merged_y - y
            moves.append(VGroup(row.nodes[:3], row.links[:2]).animate.shift(
                UP * dy))
            moves.append(row.links[2].animate.put_start_and_end_on(
                row.nodes[2].get_right() + UP * dy + RIGHT * 0.1,
                row.nodes[3].get_left() + LEFT * 0.1))
        self.play(FadeOut(boxes), run_time=T_FAST)
        self.play(*moves, run_time=T_SLOW)
        # Only one copy of the prefix survives.
        self.play(FadeOut(VGroup(rows[1].nodes[:3], rows[1].links[:2],
                                 rows[2].nodes[:3], rows[2].links[:2])),
                  run_time=T_NORM)
        self.wait(3.2)

        ltr = VGroup(rows)
        self.wait(2.4)

        # Cross-dissolve into the top-down orientation used from here on.
        tree = SearchTree(origin=[0, 1.95, 0], slot_width=2.3, level_gap=1.2,
                          radius=0.34)
        for key, parent, value in [
            ("s0", None, None), ("p1", "s0", None), ("p2", "p1", None),
            ("a", "p2", 0.75), ("b", "p2", 0.45), ("c", "p2", 0.2),
        ]:
            tree.add_node(key, parent, label="", value=value,
                          kind="root" if parent is None else "normal")
        tree.place()

        name = txt("A tree", size=44, color=ACCENT, weight=MEDIUM)
        name.move_to([0, -3.0, 0])
        self.play(FadeOut(ltr), run_time=T_NORM)
        self.play(FadeIn(tree, shift=UP * 0.2), FadeIn(name, shift=UP * 0.2),
                  run_time=T_SLOW)
        self.wait(4.2)
        self.clear_body(run_time=T_NORM)
        self.drop_header()
