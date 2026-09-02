"""
Part 2 - Motivation for tree search.

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
    ACCENT, BAD, EDGE, FS_SMALL, FS_TINY, GOOD, INK_DIM, INK_FAINT, PRIMARY,
    SURFACE_2, T_FAST, T_NORM, T_SLOW, TEAL, VIOLET, mathtex, txt,
    value_color,
)

NARRATION = {
    "beat_section": [
        "So how does a normal language agent choose? Almost always, it just "
        "walks forwards.",
    ],
    "beat_react": [
        "This is the ReAct pattern - Yao and colleagues, 2023 - and it is "
        "what almost every agent framework does. Interleave reasoning and "
        "acting: think, act, observe, repeat, in one straight line.",
        "Our agent reads the spec, writes a one-pass merge, runs the tests: "
        "three out of five. It patches the edge case it can see, and gets "
        "three out of five again.",
        "It is stuck. What it wants is to go back to that second decision "
        "and try something else. A ReAct agent has no operation for that: the "
        "transcript is append-only, so the policy always conditions on a "
        "history that can only grow.",
    ],
    "beat_forks": [
        "Rewind to that second step. The model did not have one idea; it had "
        "a distribution over them. Sort first and sweep. Build an interval "
        "tree. Merge neighbors in one pass.",
        "It drew a single sample from that distribution. The other two were "
        "never written down - not ranked lower, never scored at all. They "
        "simply do not exist any more.",
    ],
    "beat_reflexion": [
        "There is a well-known fix, called Reflexion - Shinn and colleagues, "
        "2023. When a trajectory fails the agent writes itself a note about "
        "why, keeps it in memory, and retries the whole task with that note "
        "in context.",
        "It genuinely helps. But every attempt restarts from an empty "
        "transcript, so the first three steps - which were perfectly good - "
        "are re-derived and re-paid for every time.",
        "And the credit assignment is still trajectory-level. The reflection "
        "knows the attempt failed; it does not know which step was at fault.",
    ],
    "beat_ask": [
        "Which tells us what we want. Keep the prefix that worked, branch "
        "only where the decision was, and choose which branch to spend the "
        "next sample on.",
        "Nodes are states, edges are actions, and the prefix is shared "
        "instead of repeated. That shape has a name.",
    ],
}

ON_SCREEN = {
    "beat_section": "Section card - 2 / Motivation for Tree Search.",
    "beat_react": "The ReAct chip, then a five-step chain builds left to "
                  "right. The two 3 / 5 steps are boxed in red, a cross "
                  "appears at the end, and a red curved arrow tries to reach "
                  "back to step two and is broken.",
    "beat_forks": "Everything after step two dims. Three candidate "
                  "approaches appear as cards; the one actually taken is "
                  "ringed and labelled Sampled, and the other two drop off "
                  "the bottom of the frame.",
    "beat_reflexion": "Attempt 1, then a violet reflection note, then "
                      "attempts 2 and 3 stacked beneath it. The identical "
                      "three-step prefix is boxed in all three rows, and a "
                      "large x 3 appears.",
    "beat_ask": "The three shared prefixes slide onto one another and merge "
                "into a single path; the picture cross-dissolves into a "
                "top-down tree captioned Tree.",
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
    TITLE = "Motivation for Tree Search"

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
                  stroke_width=3, color=EDGE,
                  max_tip_length_to_length_ratio=0.14,
                  max_stroke_width_to_length_ratio=6)
            for i in range(len(nodes) - 1)
        ])
        group = VGroup(links, nodes, captions)
        group.links, group.nodes, group.captions = links, nodes, captions
        return group

    # -- 1. Section card ----------------------------------------------------

    def beat_section(self):
        card = section_card(2, "Motivation for Tree Search",
                            "Where does linear search fail?")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(5.6)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 2. The linear agent walks into a wall ------------------------------

    def beat_react(self):
        self.set_header("Basic Linear Search")

        tag = chip("ReAct: Think → Act → Observe → Repeat", PRIMARY,
                   size=FS_SMALL)
        tag.move_to([0, 2.1, 0])
        self.play(FadeIn(tag, shift=DOWN * 0.2), run_time=T_NORM)
        self.wait(8.4)

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
        self.wait(3.4)

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
        self.wait(2.0)

        append = txt("The transcript is append-only", size=FS_SMALL,
                     color=INK_FAINT)
        append.move_to([0, -2.5, 0])
        self.play(FadeIn(append, shift=UP * 0.15), run_time=T_NORM)
        self.wait(8.2)
        self.play(FadeOut(VGroup(mark, repeat, repeat2, back, blocked,
                                 append)), run_time=T_NORM)

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
        self.wait(1.6)

        # Three candidate second steps, laid out in a row so they clear the
        # trajectory and its captions above.
        options = [
            ("Sort first,\nthen sweep", GOOD),
            ("Build an\ninterval tree", TEAL),
            ("Merge neighbors\nin one pass", PRIMARY),
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
        self.wait(6.4)

        ring = SurroundingRectangle(taken, color=ACCENT, corner_radius=0.14,
                                    buff=0.1, stroke_width=3)
        sampled = txt("Sampled", size=FS_TINY, color=ACCENT, weight=MEDIUM)
        sampled.next_to(ring, DOWN, buff=0.2)
        self.play(Create(ring), FadeIn(sampled), run_time=T_NORM)
        self.wait(3.0)

        self.play(FadeOut(cards[0], shift=DOWN * 0.7),
                  FadeOut(cards[1], shift=DOWN * 0.7), run_time=T_SLOW)
        self.wait(7.4)

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
            txt(f"Attempt {i + 1}", size=FS_TINY, color=INK_FAINT)
            for i in range(3)
        ])
        for label, row in zip(labels, rows):
            label.next_to(row.nodes[0], LEFT, buff=0.34)

        self.play(FadeIn(rows[0]), FadeIn(labels[0]), run_time=T_NORM)
        self.wait(1.8)

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
        self.wait(7.4)

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
        self.wait(6.4)

        grain = txt("Credit assignment stays trajectory-level",
                    size=FS_SMALL, color=INK_FAINT)
        grain.move_to([1.2, -2.5, 0])
        self.play(FadeIn(grain, shift=UP * 0.15), run_time=T_NORM)
        self.wait(7.0)

        self.play(FadeOut(VGroup(method, note, note_tag, cost, grain,
                                 labels)), run_time=T_NORM)
        self.rows, self.boxes = rows, boxes

    # -- 5. Merge the prefixes; you have built a tree -----------------------

    def beat_ask(self):
        self.set_header("Let's Keep the Shared Paths")

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
        self.wait(3.6)

        ltr = VGroup(rows)
        self.wait(2.8)

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

        name = txt("Tree", size=44, color=ACCENT, weight=MEDIUM)
        name.move_to([0, -2.85, 0])
        legend = txt("Nodes are states  ·  edges are actions", size=FS_SMALL,
                     color=INK_FAINT)
        legend.next_to(name, DOWN, buff=0.26)
        self.play(FadeOut(ltr), run_time=T_NORM)
        self.play(FadeIn(tree, shift=UP * 0.2), FadeIn(name, shift=UP * 0.2),
                  run_time=T_SLOW)
        self.play(FadeIn(legend), run_time=T_FAST)
        self.wait(7.5)
        self.clear_body(run_time=T_NORM)
        self.drop_header()
