"""
Part 1 - Agents, states, and rewards.

Opens with the whole argument as one picture: a straight chain of decisions
that dead-ends, then fans out into a tree. The title sits over that.

Then the vocabulary the rest of the video leans on - the agent/environment
loop, and the fact that for a language agent the *state* is the whole
transcript so far while the *reward* arrives only at the very end.

Also introduces the running example (``merge_intervals``) that Part 6 searches
over, and says out loud that it is worth remembering.

Render:  manim -qh scripts/create_video/parts/part1_agents.py Part1Agents
"""

import sys
from pathlib import Path

# Manim imports a scene file by path, which leaves scripts/ off sys.path.
# Adding it here lets `manim scripts/create_video/parts/<part>.py <Scene>`
# work from any working directory.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manim import *  # noqa: E402

from create_video.components import (  # noqa: E402
    LATSScene, SearchTree, agent_glyph, chip, env_glyph, overlay, panel,
    section_card,
)
from create_video.theme import (  # noqa: E402
    ACCENT, BAD, BG, FS_BODY, FS_H3, FS_SMALL, FS_TINY, GOOD, INK, INK_DIM,
    INK_FAINT, PRIMARY, STROKE, SURFACE_2, TEAL, T_FAST, T_NORM, T_SLOW,
    body_zone, cap_width, fit_in, mathtex, mono, txt,
)

#: Author list for the opening card. Review is single-blind, so real names go
#: on the video. EDIT THIS to include every author before submitting.
AUTHORS = "Michael Li"

#: The venue line under the title.
VENUE = "NeurIPS 2026 Education Track"

NARRATION = {
    "beat_title": [
        "An AI agent that writes code, or browses the web, makes a long chain "
        "of decisions. And almost every agent you have used makes them the "
        "same way: one after another, never going back.",
        "But what if it could go back?",
    ],
    "beat_section": [
        "Start with how an agent works at all. It only takes four words.",
    ],
    "beat_loop": [
        "An agent is anything that sits in a loop with an environment. The "
        "agent takes an action. The environment changes, and hands back an "
        "observation. Then another action, and around we go.",
        "Somewhere in that loop a reward comes back too - a number saying how "
        "well things are going. The agent's whole job is to make that number "
        "large.",
    ],
    "beat_vocab": [
        "So, four words. The environment is the world the agent acts in. An "
        "action is one move in it, and an observation is what comes back.",
        "The state is everything the agent knows right now. And the reward is "
        "the score. If you have seen reinforcement learning, this is that "
        "picture.",
    ],
    "beat_llm_agent": [
        "Now make the agent a language model, and those four words turn into "
        "something concrete.",
        "An action is a piece of text: a thought the model writes down, or a "
        "tool it calls. An observation is whatever that tool prints back - a "
        "test result, an error message.",
        "Here is the task we will use throughout. Write a function that merges "
        "overlapping intervals. Hold on to it, because in a few minutes we are "
        "going to search it properly.",
        "So then, what is the state? It is not a position on a board. It is "
        "the entire transcript so far: the original question, every action the "
        "agent has taken, and every observation it has seen.",
    ],
    "beat_reward": [
        "The reward, though, is stingy. The agent writes a solution, the tests "
        "run, and only then does a single number come back.",
        "So every step before that is a shot in the dark. The agent commits to "
        "it without knowing whether it helped.",
    ],
}

#: The transcript shown in ``beat_llm_agent``: (tag, body, colour, monospace).
TRANSCRIPT = [
    ("Task", "Write merge_intervals(intervals).", INK_DIM, True),
    ("Thought", "One pass, merging each pair of neighbors.", PRIMARY, False),
    ("Action", "run_tests(solution_A)", PRIMARY, True),
    ("Observation", "3 of 5 tests passed", TEAL, False),
    ("Thought", "Which two failed, and why?", PRIMARY, False),
]


class Part1Agents(LATSScene):
    """Agents, states, actions, rewards - and what they mean for an LLM."""

    PART = 1
    TITLE = "Agents, States, and Rewards"

    def beats(self):
        return [
            self.beat_title,
            self.beat_section,
            self.beat_loop,
            self.beat_vocab,
            self.beat_llm_agent,
            self.beat_reward,
        ]

    # -- 1. Title: a straight line that becomes a tree -----------------------

    def beat_title(self):
        """The whole argument as one image, with the title over it.

        A chain of decisions grows straight down and dead-ends; then it fans
        out into a tree. That is the video in eight seconds, and it doubles as
        the backdrop for the title card.
        """
        tree = SearchTree(origin=[0, 3.25, 0], slot_width=1.5, level_gap=1.32,
                          radius=0.28)

        # The linear agent: one decision after another, straight down.
        chain = ["root", "n1", "n2", "n3", "n4"]
        self.play(*tree.add_node("root", None, label="", kind="root"),
                  run_time=0.5)
        for parent, key in zip(chain, chain[1:]):
            self.play(*tree.add_node(key, parent, label=""), run_time=0.42)
        self.play(tree.node("n4").animate.restyle(kind="fail"),
                  Flash(tree.pos("n4"), color=BAD, line_length=0.18,
                        flash_radius=0.5), run_time=T_NORM)
        self.wait(1.6)

        # And then it branches.
        for parent, keys, values in [
            ("n3", ["p"], [0.55]),
            ("n2", ["q"], [0.7]),
            ("q", ["q1", "q2"], [0.85, 0.45]),
            ("n1", ["r"], [0.4]),
            ("r", ["r1"], [0.6]),
            ("root", ["s"], [0.5]),
            ("s", ["s1", "s2"], [0.35, 0.75]),
        ]:
            self.play(*tree.add_children(parent, [
                {"key": k, "label": "", "value": v}
                for k, v in zip(keys, values)
            ]), run_time=0.55)
        self.wait(1.2)

        # Retire the tree to a watermark. A full-width band sits over it so the
        # title reads cleanly: full width means no visible side edges, so it
        # looks like a deliberate plate rather than a box.
        band = Rectangle(width=config.frame_width + 0.2, height=4.5,
                         stroke_width=0, fill_color=BG, fill_opacity=0.9)
        band.move_to(UP * 0.1)
        overlay(band)

        title = txt("Language Agent Tree Search", size=58, color=INK,
                    weight=BOLD)
        cap_width(title, 12.0)
        rule = Line(ORIGIN, RIGHT * 2.6, stroke_color=PRIMARY, stroke_width=4)
        sub = txt("Teaching an Agent to Change Its Mind", size=FS_H3,
                  color=INK_DIM)
        head = VGroup(title, rule, sub).arrange(DOWN, buff=0.4)
        head.move_to(UP * 0.75)

        venue = txt(VENUE, size=FS_BODY, color=PRIMARY, weight=MEDIUM)
        authors = txt(AUTHORS, size=FS_BODY, color=INK_DIM)
        credit = VGroup(venue, authors).arrange(DOWN, buff=0.24)
        credit.next_to(head, DOWN, buff=0.95)
        overlay(head, credit)

        self.play(tree.animate.set_opacity(0.11), FadeIn(band),
                  run_time=T_SLOW)
        self.play(FadeIn(title, shift=UP * 0.25), run_time=T_SLOW)
        self.play(Create(rule), FadeIn(sub, shift=UP * 0.12), run_time=T_NORM)
        self.play(FadeIn(credit), run_time=T_NORM)
        self.wait(3.6)
        self.play(FadeOut(VGroup(head, credit, band)), FadeOut(tree),
                  run_time=T_SLOW)

    # -- 2. Section card ----------------------------------------------------

    def beat_section(self):
        card = section_card(1, "Agents, States, and Rewards",
                            "How an agent works, in four words")
        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in card],
                              lag_ratio=0.18), run_time=T_NORM)
        self.wait(4.2)
        self.play(FadeOut(card), run_time=T_FAST)

    # -- 3. The agent/environment loop --------------------------------------

    def beat_loop(self):
        self.set_header("An Agent Is a Loop")

        agent = agent_glyph(scale=1.45).move_to([-3.5, 0.55, 0])
        env = env_glyph(scale=1.45).move_to([3.5, 0.55, 0])
        agent_cap = txt("Agent", size=FS_H3, color=PRIMARY, weight=MEDIUM)
        agent_cap.next_to(agent, DOWN, buff=0.34)
        env_cap = txt("Environment", size=FS_H3, color=TEAL, weight=MEDIUM)
        env_cap.next_to(env, DOWN, buff=0.34)

        self.play(FadeIn(agent, shift=RIGHT * 0.3),
                  FadeIn(agent_cap, shift=RIGHT * 0.3), run_time=T_NORM)
        self.play(FadeIn(env, shift=LEFT * 0.3),
                  FadeIn(env_cap, shift=LEFT * 0.3), run_time=T_NORM)
        self.wait(1.6)

        # Action: agent -> environment, arcing over the top.
        act = CurvedArrow(agent.get_right() + UP * 0.16 + RIGHT * 0.12,
                          env.get_left() + UP * 0.16 + LEFT * 0.12,
                          angle=-0.62, color=PRIMARY, stroke_width=4,
                          tip_length=0.22)
        act_lab = txt("Action", size=FS_BODY, color=PRIMARY, weight=MEDIUM)
        act_lab.next_to(act, UP, buff=0.14)

        # Observation: environment -> agent, arcing under the bottom.
        obs = CurvedArrow(env.get_left() + DOWN * 0.3 + LEFT * 0.12,
                          agent.get_right() + DOWN * 0.3 + RIGHT * 0.12,
                          angle=-0.62, color=TEAL, stroke_width=4,
                          tip_length=0.22)
        obs_lab = txt("Observation", size=FS_BODY, color=TEAL, weight=MEDIUM)
        obs_lab.next_to(obs, DOWN, buff=0.14)

        self.play(Create(act), FadeIn(act_lab), run_time=T_NORM)
        self.wait(2.2)
        self.play(Create(obs), FadeIn(obs_lab), run_time=T_NORM)
        self.wait(2.6)

        # The loop runs, and runs, and runs.
        for target in (act, obs, act, obs):
            self.play(Indicate(target, color=ACCENT, scale_factor=1.04),
                      run_time=0.52)
        self.wait(2.4)

        reward = chip("Reward", GOOD)
        reward.next_to(obs_lab, DOWN, buff=0.22)
        self.play(FadeIn(reward, shift=LEFT * 0.25), run_time=T_NORM)
        self.play(Circumscribe(reward, color=GOOD, buff=0.12,
                               stroke_width=3, run_time=1.2))
        for target in (act, obs, act, obs):
            self.play(Indicate(target, color=ACCENT, scale_factor=1.04),
                      run_time=0.52)
        self.wait(6.2)

        self.loop = VGroup(agent, env, agent_cap, env_cap, act, act_lab,
                           obs, obs_lab, reward)
        self.loop_parts = {"Environment": env, "Action": act,
                           "Observation": obs, "State": agent,
                           "Reward": reward}

    # -- 4. The four words --------------------------------------------------

    @staticmethod
    def _mini_loop(centre, scale=0.62):
        """A compact, wordless copy of the loop, for the vocabulary beat.

        Built fresh rather than shrinking the big diagram: at this size any
        text in it would be unreadable, so the mini version carries only
        shapes, and the vocabulary rows point at them one at a time.
        """
        agent = agent_glyph(scale=1.3).move_to([-2.5, 0.35, 0])
        env = env_glyph(scale=1.3).move_to([2.5, 0.35, 0])
        act = CurvedArrow(agent.get_right() + UP * 0.12 + RIGHT * 0.1,
                          env.get_left() + UP * 0.12 + LEFT * 0.1,
                          angle=-0.6, color=PRIMARY, stroke_width=4,
                          tip_length=0.2)
        obs = CurvedArrow(env.get_left() + DOWN * 0.26 + LEFT * 0.1,
                          agent.get_right() + DOWN * 0.26 + RIGHT * 0.1,
                          angle=-0.6, color=TEAL, stroke_width=4,
                          tip_length=0.2)
        # The reward rides back with the observation, so it lives on that arc.
        coin = Dot(obs.point_from_proportion(0.5), radius=0.16, color=GOOD)
        group = VGroup(act, obs, agent, env, coin).scale(scale)
        group.move_to(centre)
        group.targets = {"Environment": env, "Action": act,
                         "Observation": obs, "State": agent, "Reward": coin}
        return group

    def beat_vocab(self):
        self.set_header("Four Words")

        # Swap the full diagram for a compact, wordless one so each term can be
        # pointed at the thing it names.
        self.play(FadeOut(self.loop), run_time=T_FAST)
        diagram = self._mini_loop([0, 1.85, 0])
        self.play(FadeIn(diagram), run_time=T_NORM)

        rows = [
            ("Environment", TEAL, "the world the agent acts in",
             diagram.targets["Environment"]),
            ("Action", PRIMARY, "one move in that world",
             diagram.targets["Action"]),
            ("Observation", TEAL, "what the world hands back",
             diagram.targets["Observation"]),
            ("State", ACCENT, "everything the agent knows right now",
             diagram.targets["State"]),
            ("Reward", GOOD, "the score, at the end",
             diagram.targets["Reward"]),
        ]
        entries, targets = VGroup(), []
        for name, color, gloss, target in rows:
            tag = chip(name, color, size=FS_SMALL)
            body = txt(gloss, size=FS_BODY, color=INK_DIM)
            entries.add(VGroup(tag, body))
            targets.append(target)
        widest = max(row[0].width for row in entries)
        for row in entries:
            row[1].next_to(row[0], RIGHT, buff=0.34 + (widest - row[0].width))
        entries.arrange(DOWN, aligned_edge=LEFT, buff=0.42)
        entries.move_to([0, -1.2, 0])

        for row, target in zip(entries, targets):
            self.play(FadeIn(row, shift=RIGHT * 0.22),
                      Indicate(target, color=row[0][0].get_color(),
                               scale_factor=1.14),
                      run_time=0.85)
            self.wait(1.5)
        self.wait(6.0)

        self.play(FadeOut(entries), FadeOut(diagram), run_time=T_NORM)

    # -- 5. What the four words mean for a language agent -------------------

    def beat_llm_agent(self):
        self.set_header("For a Language Agent")

        mapping = VGroup()
        for name, color, gloss in [
            ("Action", PRIMARY, "a piece of text: a thought,\nor a tool call"),
            ("Observation", TEAL, "whatever the tool prints back"),
        ]:
            tag = chip(name, color, size=FS_SMALL)
            body = txt(gloss, size=FS_SMALL, color=INK_DIM, line_spacing=0.8)
            body.next_to(tag, DOWN, buff=0.2, aligned_edge=LEFT)
            mapping.add(VGroup(tag, body))
        mapping.arrange(DOWN, aligned_edge=LEFT, buff=0.5)
        mapping.move_to([-4.55, 0.95, 0])

        self.play(LaggedStart(*[FadeIn(m, shift=UP * 0.2) for m in mapping],
                              lag_ratio=0.25), run_time=1.2)
        self.wait(11.0)

        box = panel(7.6, 3.5, "transcript", accent=STROKE)
        box.move_to([2.15, -0.35, 0])
        self.play(FadeIn(box), run_time=T_NORM)

        # Two fixed columns inside the panel: a tag gutter and a body column.
        tag_x = box[0].get_left()[0] + 0.42
        body_x = tag_x + 1.55
        top_y = box[0].get_top()[1] - 0.62
        rendered = VGroup()
        for i, (tag, body, color, is_code) in enumerate(TRANSCRIPT):
            t = txt(tag, size=FS_TINY, color=color, weight=MEDIUM)
            b = (mono(body, size=FS_TINY, color=INK_DIM) if is_code
                 else txt(body, size=FS_SMALL, color=INK_DIM))
            cap_width(b, 5.1)
            y = top_y - i * 0.6
            t.move_to([tag_x, y, 0], aligned_edge=LEFT)
            b.move_to([body_x, y, 0], aligned_edge=LEFT)
            rendered.add(VGroup(t, b))
        self.rows = rendered

        # The task line is the running example; mark it once, visually.
        self.play(FadeIn(rendered[0], shift=UP * 0.12), run_time=0.42)
        self.play(Circumscribe(rendered[0], color=ACCENT, buff=0.16,
                               stroke_width=3, run_time=1.5))
        self.wait(9.8)
        for row in rendered[1:]:
            self.play(FadeIn(row, shift=UP * 0.12), run_time=0.42)
            self.wait(0.62)
        self.wait(2.2)

        # The punchline: the state is the whole transcript.
        self.play(FadeOut(mapping), run_time=T_FAST)
        brace = Brace(box[0], LEFT, color=ACCENT, buff=0.18)
        state_lab = txt("The state", size=FS_BODY, color=ACCENT, weight=MEDIUM)
        state_lab.next_to(brace, LEFT, buff=0.22)
        self.play(GrowFromCenter(brace), FadeIn(state_lab, shift=RIGHT * 0.2),
                  run_time=T_NORM)
        self.wait(6.2)

        formal = mathtex(r"s \;=\; [\, x,\; a_1 \ldots a_i,\; o_1 \ldots o_i \,]",
                         size=34)
        formal.move_to([0, -2.88, 0])
        gloss = txt("The question, every action, every observation",
                    size=FS_TINY, color=INK_FAINT)
        gloss.next_to(formal, DOWN, buff=0.16)
        self.play(FadeIn(formal, shift=UP * 0.2), run_time=T_NORM)
        self.play(FadeIn(gloss), run_time=T_FAST)
        self.wait(8.6)

        self.transcript = VGroup(box, rendered)
        self.play(FadeOut(VGroup(brace, state_lab, formal, gloss)),
                  run_time=T_NORM)

    # -- 6. The reward is sparse --------------------------------------------

    def beat_reward(self):
        """Collapse the transcript into its steps, and mark every one unknown.

        The picture carries the point: five decisions, each taken blind, and a
        single number at the very end.
        """
        self.set_header("The Reward Comes Last")

        box, rendered = self.transcript

        xs = [-5.0, -3.0, -1.0, 1.0, 3.0]
        dots = VGroup(*[
            Circle(radius=0.26, stroke_color=PRIMARY, stroke_width=3,
                   fill_color=SURFACE_2, fill_opacity=1.0).move_to([x, 0.3, 0])
            for x in xs
        ])
        links = VGroup(*[
            Line(dots[i].get_right(), dots[i + 1].get_left(), buff=0.08,
                 stroke_color=STROKE, stroke_width=2.5)
            for i in range(len(dots) - 1)
        ])

        self.play(FadeOut(box), run_time=T_FAST)
        self.play(LaggedStart(*[
            ReplacementTransform(row, dot)
            for row, dot in zip(rendered, dots)
        ], lag_ratio=0.16), run_time=1.5)
        self.play(Create(links), run_time=T_NORM)
        self.wait(1.2)

        marks = VGroup(*[
            txt("?", size=40, color=ACCENT, weight=BOLD).move_to([x, 1.35, 0])
            for x in xs
        ])
        self.play(LaggedStart(*[FadeIn(m, shift=DOWN * 0.18) for m in marks],
                              lag_ratio=0.18), run_time=1.4)
        self.wait(4.4)

        terminal = Circle(radius=0.34, stroke_color=ACCENT, stroke_width=4,
                          fill_color=ACCENT, fill_opacity=0.22)
        terminal.move_to([5.2, 0.3, 0])
        last_link = Line(dots[-1].get_right(), terminal.get_left(), buff=0.08,
                         stroke_color=STROKE, stroke_width=2.5)
        score = mathtex(r"r \;=\; 0.6", size=38, color=ACCENT)
        score.next_to(terminal, DOWN, buff=0.5)

        self.play(Create(last_link), GrowFromCenter(terminal), run_time=T_NORM)
        self.play(FadeIn(score, shift=UP * 0.2), run_time=T_NORM)
        self.wait(6.6)

        self.clear_body(run_time=T_NORM)
        self.drop_header()
