"""
Part 4 - LATS: Monte Carlo Tree Search for language agents.

The substitution table is the spine of this part: each thing AlphaGo needed a
trained network for, LATS gets by prompting the language model it already has,
or by asking the real environment. Then the row with no AlphaGo counterpart at
all - reflection - and the six operations that result.

Render:  manim -qh scripts/create_video/parts/part4_lats.py Part4LATS
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, chip, section_card, speech_bubble,
)
from create_video.theme import (  # noqa: E402
    ACCENT, EDGE, FS_BODY, FS_H3, FS_SMALL, FS_TINY, GOOD, INK, INK_DIM,
    INK_FAINT, PRIMARY, T_FAST, T_NORM, TEAL, VIOLET, cap_width, mathtex,
    txt,
)

NARRATION = {
    "beat_section": [
        "Language Agent Tree Search is, in one line, Monte Carlo Tree Search "
        "for language agents. The interesting part is what it puts in place of "
        "the pieces we do not have.",
    ],
    "beat_swap": [
        "AlphaGo needed a policy network to propose moves. LATS asks the "
        "language model to write down several candidate next actions - five, by "
        "default. That is the policy.",
        "AlphaGo needed a value network to score a position. LATS asks the same "
        "model to grade the transcript so far, and blends that with how often "
        "it independently proposed the same step.",
        "And AlphaGo needed to play the game out cheaply, at random. LATS "
        "still plays out to the end, but greedily - always following its "
        "best-looking child - and in the real environment. It runs the code, "
        "loads the page, makes the query. The feedback is real, which is why "
        "the value estimate is worth anything.",
    ],
    "beat_reflection": [
        "Then there is a fourth row, and this one has no AlphaGo counterpart.",
        "When a trajectory fails, LATS asks the model to write a short note "
        "about why it failed, in words. That note goes into the context of "
        "every later attempt.",
        "A number tells you a branch was bad. A sentence tells you what was "
        "wrong with it. The paper calls this a semantic gradient, and it is the "
        "part of LATS that could only exist because the agent is a language "
        "model.",
    ],
    "beat_six": [
        "Put it together and you get six operations instead of four. The "
        "classic four, plus evaluation, because nobody hands us a score - and "
        "reflection, because failures are worth reading, not just counting.",
    ],
}


class Part4LATS(LATSScene):
    """The AlphaGo-to-LATS substitution, reflection, and the six operations."""

    PART = 4
    TITLE = "LATS: Tree Search for Language Agents"

    #: (AlphaGo requirement, LATS answer, gloss, colour).
    SWAPS = [
        ("Policy network", "The LLM proposes",
         "Sample n candidate actions at each step", PRIMARY),
        ("Value network", "The LLM scores",
         "Grade the transcript, and blend in self-consistency", TEAL),
        ("Random playout", "The real environment",
         "Play out greedily — but run the code, load the page, and make "
         "the query for real", ACCENT),
    ]

    #: The six operations, in the order the paper performs them.
    OPS = [
        ("Selection", PRIMARY), ("Expansion", PRIMARY),
        ("Evaluation", TEAL), ("Simulation", ACCENT),
        ("Backpropagation", GOOD), ("Reflection", VIOLET),
    ]

    def beats(self):
        return [
            self.beat_section,
            self.beat_swap,
            self.beat_reflection,
            self.beat_six,
        ]

    # -- 1. Section card ----------------------------------------------------

    def beat_section(self):
        card = section_card(4, "LATS", "Monte Carlo Tree Search, with an "
                                       "LLM in every empty slot")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(12.4)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 2. The substitution table ------------------------------------------

    def beat_swap(self):
        self.set_header("The Same Algorithm, Three Substitutions")

        left_x, right_x, arrow_x = -4.6, 2.1, -1.75
        ys = [1.2, -0.1, -1.4]

        head_l = txt("AlphaGo, 2016", size=FS_H3, color=INK_DIM,
                     weight=MEDIUM).move_to([left_x, 2.15, 0])
        head_r = txt("LATS, 2024", size=FS_H3, color=INK, weight=MEDIUM)
        head_r.move_to([right_x, 2.15, 0])

        lefts, rights, arrows = VGroup(), VGroup(), VGroup()
        for (need, answer, gloss, color), y in zip(self.SWAPS, ys):
            tag = chip(need, INK_FAINT, size=FS_BODY, fill_opacity=0.05)
            tag.move_to([left_x, y, 0])
            lefts.add(tag)

            answer_tag = chip(answer, color, size=FS_BODY)
            note = txt(gloss, size=FS_TINY, color=INK_DIM)
            cap_width(note, 5.6)
            block = VGroup(answer_tag, note).arrange(DOWN, buff=0.16)
            block.move_to([right_x, y, 0])
            rights.add(block)

            arrows.add(Arrow([arrow_x - 0.55, y, 0], [arrow_x + 0.55, y, 0],
                             buff=0, stroke_width=3, color=EDGE,
                             max_tip_length_to_length_ratio=0.28))

        self.play(FadeIn(head_l, shift=DOWN * 0.15), run_time=T_FAST)
        self.play(LaggedStart(*[FadeIn(t, shift=RIGHT * 0.2) for t in lefts],
                              lag_ratio=0.2), run_time=1.0)
        self.wait(1.4)
        self.play(FadeIn(head_r, shift=DOWN * 0.15), run_time=T_FAST)

        holds = [11.4, 13.4, 19.6]
        for i, hold in enumerate(holds):
            self.play(Create(arrows[i]),
                      FadeIn(rights[i], shift=RIGHT * 0.25), run_time=T_NORM)
            self.wait(hold)

        self.swap_group = VGroup(head_l, head_r, lefts, rights, arrows)
        self.swap_geometry = (left_x, right_x, arrow_x)

    # -- 3. The row with no counterpart -------------------------------------

    def beat_reflection(self):
        self.set_header("One Row Has No Counterpart")

        left_x, right_x, arrow_x = self.swap_geometry
        y = -2.7

        blank = DashedVMobject(
            RoundedRectangle(corner_radius=0.13, width=2.9, height=0.56,
                             stroke_color=INK_FAINT, stroke_width=2),
            num_dashes=26)
        blank.move_to([left_x, y, 0])
        nothing = txt("Nothing", size=FS_SMALL, color=INK_FAINT)
        nothing.move_to(blank.get_center())
        arrow = Arrow([arrow_x - 0.55, y, 0], [arrow_x + 0.55, y, 0],
                      buff=0, stroke_width=3, color=EDGE,
                      max_tip_length_to_length_ratio=0.28)
        answer = chip("Reflection", VIOLET, size=FS_BODY)
        gloss = txt("Write down why the attempt failed, in words",
                    size=FS_TINY, color=INK_DIM)
        block = VGroup(answer, gloss).arrange(DOWN, buff=0.16)
        block.move_to([right_x, y, 0])

        self.play(FadeIn(blank), FadeIn(nothing), run_time=T_NORM)
        self.wait(1.6)
        self.play(Create(arrow), FadeIn(block, shift=RIGHT * 0.25),
                  run_time=T_NORM)
        self.wait(3.6)

        row = VGroup(blank, nothing, arrow, block)
        self.play(FadeOut(self.swap_group), FadeOut(row), run_time=T_NORM)

        # A scalar versus a sentence.
        scalar = VGroup(
            txt("What a number tells you", size=FS_SMALL, color=INK_DIM),
            mathtex(r"r = 0.6", size=44, color=ACCENT),
            txt("This branch was mediocre", size=FS_SMALL, color=INK_FAINT),
        ).arrange(DOWN, buff=0.32)
        scalar.move_to([-3.55, 0.0, 0])

        sentence_note = speech_bubble(
            "The one-pass merge assumed the input\n"
            "was already sorted. Sort by start\n"
            "first, then merge.",
            color=VIOLET, width=5.4, tail=False)
        sentence = VGroup(
            txt("What a sentence tells you", size=FS_SMALL, color=INK_DIM),
            sentence_note,
            txt("And what to do instead", size=FS_SMALL, color=INK_FAINT),
        ).arrange(DOWN, buff=0.32)
        sentence.move_to([3.05, 0.0, 0])
        # Align the two column headings on one line, whatever the heights are.
        top = 1.95
        scalar.shift(UP * (top - scalar.get_top()[1]))
        sentence.shift(UP * (top - sentence.get_top()[1]))

        self.play(FadeIn(scalar, shift=UP * 0.2), run_time=T_NORM)
        self.wait(2.6)
        self.play(FadeIn(sentence, shift=UP * 0.2), run_time=T_NORM)
        self.wait(9.6)

        quote = txt("“a semantic gradient signal more useful than a scalar "
                    "value”", size=FS_H3, color=VIOLET)
        cap_width(quote, 11.8)
        quote.move_to([0, -1.85, 0])
        cite = txt("Zhou et al., 2024", size=FS_TINY, color=INK_FAINT)
        cite.next_to(quote, DOWN, buff=0.2)
        self.play(FadeIn(quote, shift=UP * 0.2), FadeIn(cite), run_time=T_NORM)
        self.wait(11.4)
        self.play(FadeOut(VGroup(scalar, sentence, quote, cite)),
                  run_time=T_NORM)

    # -- 4. Six operations --------------------------------------------------

    def beat_six(self):
        self.set_header("Six Operations")

        radius = 2.15
        centre = np.array([0.0, -0.28, 0.0])
        tags, angles = VGroup(), []
        for i, (name, color) in enumerate(self.OPS):
            angle = PI / 2 - i * TAU / len(self.OPS)
            angles.append(angle)
            tag = chip(name, color, size=FS_SMALL)
            tag.move_to(centre + radius * np.array(
                [np.cos(angle) * 1.62, np.sin(angle), 0.0]))
            tags.add(tag)

        arcs = VGroup()
        for i in range(len(tags)):
            a, b = tags[i], tags[(i + 1) % len(tags)]
            start = a.get_center()
            end = b.get_center()
            direction = end - start
            unit = direction / np.linalg.norm(direction)
            arcs.add(Arrow(start + unit * (a.width * 0.34 + 0.22),
                           end - unit * (b.width * 0.34 + 0.22),
                           buff=0, stroke_width=2.5, color=EDGE,
                           max_tip_length_to_length_ratio=0.16))

        core = txt("LATS", size=34, color=INK, weight=BOLD).move_to(centre)
        sub = txt("Repeat until solved, or out of budget",
                  size=FS_TINY, color=INK_FAINT)
        sub.next_to(core, DOWN, buff=0.22)

        self.play(LaggedStart(*[FadeIn(t, scale=0.85) for t in tags],
                              lag_ratio=0.14), run_time=1.5)
        self.play(LaggedStart(*[Create(a) for a in arcs], lag_ratio=0.1),
                  run_time=1.2)
        self.play(FadeIn(core), FadeIn(sub), run_time=T_NORM)
        self.wait(3.2)

        # Call out the two that classical MCTS does not have.
        news = VGroup(
            SurroundingRectangle(tags[2], color=TEAL, corner_radius=0.14,
                                 buff=0.1, stroke_width=3),
            SurroundingRectangle(tags[5], color=VIOLET, corner_radius=0.14,
                                 buff=0.1, stroke_width=3),
        )
        label = txt("New in LATS", size=FS_BODY, color=INK, weight=MEDIUM)
        label.move_to([0, -3.05, 0])
        self.play(Create(news[0]), Create(news[1]),
                  FadeIn(label, shift=UP * 0.2), run_time=T_NORM)
        self.wait(6.0)

        self.clear_body(run_time=T_NORM)
        self.drop_header()
