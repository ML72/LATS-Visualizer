"""
Reusable Mobjects and scene scaffolding for the LATS explainer video.

Nothing here is specific to a single part of the video; each of the six parts
in ``create_video/parts/`` composes these pieces. Two things matter most:

``LATSScene``
    The base class every part inherits. It sets the background, owns the slide
    header, provides ``clear_body()`` so a beat can tear down cleanly, and runs
    the part as a list of *beats* so you can render one beat at a time while
    iterating (see ``LATS_BEATS`` below).

``SearchTree``
    The animated tree used from Part 3 onwards. It handles layout, growth,
    re-layout when a level gets wider, path highlighting, and value recolouring,
    so the parts can talk about the algorithm rather than about geometry.

All icons are drawn from Manim primitives. The project imports no external
image, icon, or font files, so there is no third-party asset licensing to
track.
"""

from __future__ import annotations

import json
import os

from manim import *

from .paths import run_dir
from .theme import (
    ACCENT, BAD, BG, BODY_TOP, EDGE, FOOTER_Y, FS_BODY, FS_H1, FS_H2,
    FS_MONO, FS_SMALL, FS_TINY, GOOD, HEADER_Y, INK, INK_DIM, INK_FAINT,
    PRIMARY, RULE_Y, SAFE_L, SAFE_R, STROKE, SURFACE, SURFACE_2, T_FAST,
    T_LAG, T_NORM, TEAL, VIOLET, cap_width, mono, txt, value_color,
)

# ---------------------------------------------------------------------------
# Stacking order
# ---------------------------------------------------------------------------
#
# Manim renders a frame by flattening every mobject family and sorting it by
# ``z_index`` (a stable sort, so equal indices keep their insertion order).
# Relying on insertion order alone is fragile here: ``Scene.play`` promotes the
# mobject of every animation to the top level, so animating, say, a node's
# circle would lift that circle above its own label and hide it. Assigning
# explicit indices makes the layering independent of what is being animated.

Z_EDGE = 0      # tree edges
Z_NODE = 1      # node discs
Z_LABEL = 2     # node labels and value badges
Z_OVERLAY = 20  # panels and callouts that must sit above the tree


def overlay(*mobs: Mobject) -> Mobject:
    """Lift mobjects above the search tree. Returns the first argument."""
    for m in mobs:
        m.set_z_index(Z_OVERLAY)
    return mobs[0] if mobs else None


# ---------------------------------------------------------------------------
# Scene scaffolding
# ---------------------------------------------------------------------------


class LATSScene(Scene):
    """Base class for every part of the video.

    Subclasses set :attr:`PART`, :attr:`TITLE` and implement :meth:`beats`,
    which returns the ordered list of bound methods that make up the part.

    While iterating on a part you rarely want to re-render all of it. Set the
    ``LATS_BEATS`` environment variable to a comma-separated list of beat
    indices (0-based) or beat method names to render only those::

        LATS_BEATS=2,3 manim -ql scripts/create_video/parts/part4_lats.py Part4LATS

    A full render also writes ``timing_partN.json`` into the run directory
    (see :mod:`create_video.paths`), recording the wall-clock span of each
    beat. ``create_video.py`` folds those files into ``timing.json``, which is
    what the timestamps in ``SCRIPT.md`` are calibrated against. A
    ``LATS_BEATS`` render deliberately writes no timing file, so experimenting
    with one beat cannot corrupt the script.
    """

    PART: int = 0
    TITLE: str = ""
    #: Preview and scratch scenes set this False so they do not write a
    #: timing file into the run directory alongside the real parts.
    WRITE_TIMING: bool = True

    def setup(self) -> None:
        self.camera.background_color = BG
        self.header: VGroup | None = None
        self._persistent: list[Mobject] = []
        self._marks: list[dict] = []

    # -- beat plumbing ------------------------------------------------------

    def beats(self) -> list:
        """Ordered list of bound beat methods. Overridden by each part."""
        raise NotImplementedError

    def construct(self) -> None:
        all_beats = self.beats()
        wanted = os.environ.get("LATS_BEATS", "").strip()
        if wanted:
            keys = {k.strip() for k in wanted.split(",") if k.strip()}
            selected = [
                (i, b) for i, b in enumerate(all_beats)
                if str(i) in keys or b.__name__ in keys
            ]
        else:
            selected = list(enumerate(all_beats))
        self._partial = bool(wanted)

        for i, beat in selected:
            start = self.renderer.time
            beat()
            self._marks.append({
                "index": i,
                "name": beat.__name__,
                "start": round(start, 3),
                "end": round(self.renderer.time, 3),
                "duration": round(self.renderer.time - start, 3),
            })
        self._write_timing()

    def _write_timing(self) -> None:
        if not self.WRITE_TIMING:
            return
        # A LATS_BEATS render covers only some of the part, so its timings are
        # not the part's timings. Writing them would silently corrupt
        # SCRIPT.md with a runtime measured over two beats out of six.
        if getattr(self, "_partial", False):
            return
        out_dir = run_dir()
        payload = {
            "part": self.PART,
            "title": self.TITLE,
            "total": round(self.renderer.time, 3),
            "beats": self._marks,
        }
        path = out_dir / f"timing_part{self.PART}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # -- header -------------------------------------------------------------

    def set_header(self, text: str, run_time: float = T_NORM) -> None:
        """Show or replace the persistent slide heading and its hairline."""
        label = txt(text, size=FS_H2, color=INK, weight=MEDIUM)
        cap_width(label, SAFE_R - SAFE_L)
        label.move_to([SAFE_L + label.width / 2, HEADER_Y, 0])
        rule = Line([SAFE_L, RULE_Y, 0], [SAFE_R, RULE_Y, 0],
                    stroke_color=STROKE, stroke_width=2)
        group = VGroup(label, rule)

        if self.header is None:
            self.header = group
            self.play(FadeIn(label, shift=RIGHT * 0.25),
                      Create(rule), run_time=run_time)
        else:
            old_label = self.header[0]
            self.header = VGroup(label, self.header[1])
            self.play(LaggedStart(FadeOut(old_label, shift=UP * 0.22),
                                  FadeIn(label, shift=UP * 0.22),
                                  lag_ratio=1.0),
                      run_time=run_time + 0.25)

    def drop_header(self, run_time: float = T_FAST) -> None:
        if self.header is not None:
            self.play(FadeOut(self.header), run_time=run_time)
            self.header = None

    # -- teardown -----------------------------------------------------------

    def keep(self, *mobs: Mobject) -> None:
        """Mark mobjects as surviving :meth:`clear_body`."""
        self._persistent.extend(mobs)

    def unkeep(self, *mobs: Mobject) -> None:
        for m in mobs:
            if m in self._persistent:
                self._persistent.remove(m)

    def clear_body(self, keep=(), run_time: float = T_NORM,
                   shift=None) -> None:
        """Fade out everything except the header and anything marked kept."""
        survivors = set(self._persistent) | set(keep)
        if self.header is not None:
            survivors.add(self.header)
            survivors.update(self.header.submobjects)
        doomed = [m for m in self.mobjects if m not in survivors]
        if not doomed:
            return
        kw = {"shift": shift} if shift is not None else {}
        self.play(*[FadeOut(m, **kw) for m in doomed], run_time=run_time)

    # -- convenience --------------------------------------------------------

    def footnote(self, text: str, color: str = INK_FAINT) -> Text:
        """A right-aligned citation line pinned to the bottom of the frame."""
        t = txt(text, size=FS_TINY, color=color)
        cap_width(t, SAFE_R - SAFE_L)
        t.move_to([SAFE_R - t.width / 2, FOOTER_Y, 0])
        return t



# ---------------------------------------------------------------------------
# Cards, panels and small parts
# ---------------------------------------------------------------------------


def section_card(number: int, title: str, subtitle: str = "") -> VGroup:
    """The full-frame card that opens each part of the video.

    Returns ``VGroup(number, rule, title[, subtitle])`` so a scene can stagger
    the pieces in rather than fading the whole card at once.
    """
    num = txt(f"{number:02d}", size=76, color=PRIMARY, weight=BOLD)
    rule = Line(ORIGIN, RIGHT * 1.7, stroke_color=PRIMARY, stroke_width=3)
    name = txt(title, size=FS_H1, color=INK, weight=MEDIUM)
    cap_width(name, 11.5)

    stack = VGroup(num, rule, name).arrange(DOWN, buff=0.40)
    if subtitle:
        sub = txt(subtitle, size=FS_BODY, color=INK_DIM)
        cap_width(sub, 10.5)
        sub.next_to(name, DOWN, buff=0.34)
        stack.add(sub)
    # Sit a touch above the optical centre: the heavy numeral reads low.
    stack.move_to(UP * 0.12)
    return stack


def panel(width: float, height: float, title: str = "",
          accent: str = STROKE, fill: str = SURFACE,
          title_color: str | None = None) -> VGroup:
    """A rounded container with an optional small title above its top-left.

    Returns ``VGroup(box)`` or ``VGroup(box, title)``. The box is always
    ``group[0]``, so callers can position content relative to ``group[0]``.
    """
    box = RoundedRectangle(
        corner_radius=0.16, width=width, height=height,
        stroke_color=accent, stroke_width=2,
        fill_color=fill, fill_opacity=1.0,
    )
    if not title:
        return VGroup(box)
    label = txt(title, size=FS_SMALL, color=title_color or INK_DIM,
                weight=MEDIUM)
    label.next_to(box.get_corner(UL), UR, buff=0.0)
    label.shift(RIGHT * 0.06 + UP * 0.16)
    return VGroup(box, label)


def chip(text: str, color: str = PRIMARY, size: float = FS_SMALL,
         fill_opacity: float = 0.14, pad_x: float = 0.26,
         pad_y: float = 0.14) -> VGroup:
    """A small rounded pill: a label in a tinted capsule."""
    label = txt(text, size=size, color=color, weight=MEDIUM)
    box = RoundedRectangle(
        corner_radius=0.13,
        width=label.width + 2 * pad_x,
        height=label.height + 2 * pad_y,
        stroke_color=color, stroke_width=1.6,
        fill_color=color, fill_opacity=fill_opacity,
    )
    label.move_to(box.get_center())
    return VGroup(box, label)


def bullet(text: str, color: str = INK, marker: str = PRIMARY,
           size: float = FS_BODY, width: float = 9.0) -> VGroup:
    """One bullet: a small square marker plus a line of text."""
    dot = Square(side_length=0.11, stroke_width=0,
                 fill_color=marker, fill_opacity=1.0)
    dot.rotate(PI / 4)
    label = txt(text, size=size, color=color)
    cap_width(label, width)
    label.next_to(dot, RIGHT, buff=0.32)
    dot.align_to(label, UP).shift(DOWN * (label.height / 2 - 0.055))
    return VGroup(dot, label)


def bullets(lines, color: str = INK, marker: str = PRIMARY,
            size: float = FS_BODY, buff: float = 0.42,
            width: float = 9.0) -> VGroup:
    """A left-aligned stack of :func:`bullet` items."""
    group = VGroup(*[bullet(t, color, marker, size, width) for t in lines])
    group.arrange(DOWN, aligned_edge=LEFT, buff=buff)
    return group


def code_block(lines, width: float | None = None, size: float = FS_MONO,
               highlight: dict | None = None, line_buff: float = 0.19,
               ) -> VGroup:
    """A left-aligned monospace block. ``highlight`` maps line index -> colour."""
    highlight = highlight or {}
    rendered = VGroup(*[
        mono(line if line else " ", size=size,
             color=highlight.get(i, INK if line.strip() else INK_FAINT))
        for i, line in enumerate(lines)
    ])
    rendered.arrange(DOWN, aligned_edge=LEFT, buff=line_buff)

    # Put the indentation back. A leading space carries no ink, so it is not in
    # the line's bounding box, and ``aligned_edge=LEFT`` therefore lines every
    # row up on its first visible glyph - which flattens a Python block flush
    # left and shows code that would not run. Shifting by the measured
    # character advance restores it; the face is monospaced, so one advance is
    # the width of any glyph.
    indents = [len(line) - len(line.lstrip(" ")) for line in lines]
    if any(indents):
        advance = mono("xx", size=size).width - mono("x", size=size).width
        for row, indent in zip(rendered, indents):
            if indent:
                row.shift(RIGHT * indent * advance)

    if width is not None:
        cap_width(rendered, width)
    return rendered


def labelled_arrow(start, end, label: str, color: str = INK_DIM,
                   size: float = FS_SMALL, above: bool = True,
                   buff: float = 0.14) -> VGroup:
    """An arrow with a caption riding above or below it."""
    arrow = Arrow(start, end, buff=0.0, stroke_width=3, color=color,
                  max_tip_length_to_length_ratio=0.09,
                  max_stroke_width_to_length_ratio=6)
    cap = txt(label, size=size, color=color)
    cap.next_to(arrow, UP if above else DOWN, buff=buff)
    return VGroup(arrow, cap)


def divider(y: float, x0: float = SAFE_L, x1: float = SAFE_R,
            color: str = STROKE) -> Line:
    return Line([x0, y, 0], [x1, y, 0], stroke_color=color, stroke_width=1.6)


# ---------------------------------------------------------------------------
# Icons, drawn from primitives (no external assets)
# ---------------------------------------------------------------------------


def agent_glyph(color: str = PRIMARY, scale: float = 1.0) -> VGroup:
    """A small robot head: the agent."""
    head = RoundedRectangle(corner_radius=0.16, width=1.0, height=0.82,
                            stroke_color=color, stroke_width=3,
                            fill_color=SURFACE_2, fill_opacity=1.0)
    eye_l = Dot(radius=0.075, color=color)
    eye_l.move_to(head.get_center() + LEFT * 0.21 + UP * 0.07)
    eye_r = Dot(radius=0.075, color=color)
    eye_r.move_to(head.get_center() + RIGHT * 0.21 + UP * 0.07)
    mouth = Line(head.get_center() + LEFT * 0.19 + DOWN * 0.21,
                 head.get_center() + RIGHT * 0.19 + DOWN * 0.21,
                 stroke_color=color, stroke_width=3)
    stem = Line(head.get_top(), head.get_top() + UP * 0.16,
                stroke_color=color, stroke_width=3)
    bulb = Dot(radius=0.06, color=color).move_to(head.get_top() + UP * 0.2)
    return VGroup(head, eye_l, eye_r, mouth, stem, bulb).scale(scale)


def env_glyph(color: str = TEAL, scale: float = 1.0) -> VGroup:
    """A browser/terminal window: the environment."""
    frame = RoundedRectangle(corner_radius=0.11, width=1.35, height=0.98,
                             stroke_color=color, stroke_width=3,
                             fill_color=SURFACE_2, fill_opacity=1.0)
    bar = Line(frame.get_left() + UP * 0.26, frame.get_right() + UP * 0.26,
               stroke_color=color, stroke_width=2)
    dots = VGroup(*[Dot(radius=0.036, color=color) for _ in range(3)])
    dots.arrange(RIGHT, buff=0.075)
    dots.move_to(frame.get_corner(UL) + RIGHT * 0.24 + DOWN * 0.13)
    rows = VGroup(
        Line(ORIGIN, RIGHT * 0.78, stroke_color=INK_FAINT, stroke_width=2.5),
        Line(ORIGIN, RIGHT * 0.55, stroke_color=INK_FAINT, stroke_width=2.5),
        Line(ORIGIN, RIGHT * 0.66, stroke_color=INK_FAINT, stroke_width=2.5),
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.135)
    rows.move_to(frame.get_center() + DOWN * 0.14)
    return VGroup(frame, bar, dots, rows).scale(scale)


def llm_glyph(color: str = PRIMARY, label: str = "LLM",
              scale: float = 1.0) -> VGroup:
    """A labelled block standing in for the language model."""
    box = RoundedRectangle(corner_radius=0.13, width=1.18, height=0.72,
                           stroke_color=color, stroke_width=3,
                           fill_color=SURFACE_2, fill_opacity=1.0)
    text = txt(label, size=FS_SMALL, color=color, weight=BOLD)
    text.move_to(box.get_center())
    return VGroup(box, text).scale(scale)


def speech_bubble(text: str, color: str = VIOLET, width: float = 5.2,
                  size: float = FS_SMALL, tail: bool = True,
                  tail_dir=DOWN) -> VGroup:
    """A rounded speech bubble. Used for reflections.

    ``text`` is set at ``size`` and is only scaled down as a last resort, so
    break long reflections across lines with ``\\n`` rather than relying on
    ``width`` to shrink them into illegibility.
    """
    body = txt(text, size=size, color=INK, line_spacing=0.85)
    cap_width(body, width - 0.7)
    box = RoundedRectangle(
        corner_radius=0.17,
        width=max(body.width + 0.7, 1.4),
        height=body.height + 0.62,
        stroke_color=color, stroke_width=2,
        fill_color=SURFACE_2, fill_opacity=1.0,
    )
    body.move_to(box.get_center())
    parts = [box, body]
    if tail:
        anchor = box.get_edge_center(tail_dir)
        side = RIGHT if abs(tail_dir[1]) > 0.5 else UP
        point = Polygon(
            anchor + side * 0.22,
            anchor - side * 0.06,
            anchor + tail_dir * 0.26,
            stroke_width=0, fill_color=SURFACE_2, fill_opacity=1.0,
        )
        edge = VGroup(
            Line(anchor + side * 0.22, anchor + tail_dir * 0.26,
                 stroke_color=color, stroke_width=2),
            Line(anchor + tail_dir * 0.26, anchor - side * 0.06,
                 stroke_color=color, stroke_width=2),
        )
        parts = [box, point, edge, body]
    return VGroup(*parts)


def strike(mob: Mobject, color: str = BAD, overhang: float = 0.14,
           width: float = 3.0) -> Line:
    """A rule drawn across ``mob``, for striking something out.

    Reads as a deletion where a caption would otherwise have to say so.
    """
    line = Line(mob.get_left() + LEFT * overhang,
                mob.get_right() + RIGHT * overhang,
                stroke_color=color, stroke_width=width)
    line.set_z_index(Z_OVERLAY)
    return line


def check_mark(color: str = GOOD, scale: float = 1.0) -> VGroup:
    """A tick, drawn as two strokes."""
    v = VMobject(stroke_color=color, stroke_width=6)
    v.set_points_as_corners([
        LEFT * 0.18 + DOWN * 0.02, DOWN * 0.16 + LEFT * 0.02,
        RIGHT * 0.22 + UP * 0.2,
    ])
    return VGroup(v).scale(scale)


def cross_mark(color: str = BAD, scale: float = 1.0) -> VGroup:
    """An x, drawn as two strokes."""
    a = Line(LEFT * 0.17 + UP * 0.17, RIGHT * 0.17 + DOWN * 0.17,
             stroke_color=color, stroke_width=6)
    b = Line(LEFT * 0.17 + DOWN * 0.17, RIGHT * 0.17 + UP * 0.17,
             stroke_color=color, stroke_width=6)
    return VGroup(a, b).scale(scale)


# ---------------------------------------------------------------------------
# Bars and charts
# ---------------------------------------------------------------------------


def _format_value(v: float) -> str:
    """Render a bar's value the way a reader expects to see it.

    Benchmark scores want two decimals, percentages one, and token counts want
    thousands separators and no decimal point at all.
    """
    if v >= 1000:
        return f"{v:,.0f}"
    if v >= 10:
        return f"{v:.1f}"
    return f"{v:.2f}"


def hbar_chart(rows, max_value: float, width: float = 6.4,
               bar_height: float = 0.34, gap: float = 0.24,
               label_width: float = 3.1, size: float = FS_SMALL,
               track: bool = True) -> VGroup:
    """A horizontal bar chart.

    ``rows`` is a sequence of ``(label, value, colour)``. Returns a VGroup whose
    ``bars`` / ``labels`` / ``values`` attributes expose the pieces so a scene
    can animate them individually.

    ``max_value`` is what a full-width bar means, so it has to be a number the
    reader can name: the top of the metric's range (1.0 for a rate, 100 for a
    percentage). Padding it to a round number above the data silently inflates
    every bar. Where no such ceiling exists - token counts, say - pass
    ``track=False`` and scale against the largest value in ``rows``; without a
    track behind them the bars read as lengths to compare rather than as
    fractions of something.
    """
    bars, labels, value_labels, tracks = VGroup(), VGroup(), VGroup(), VGroup()
    for i, (name, value, color) in enumerate(rows):
        y = -i * (bar_height + gap)

        label = txt(name, size=size, color=INK_DIM)
        cap_width(label, label_width)
        label.move_to([-label.width / 2 - 0.28, y, 0])
        labels.add(label)

        if track:
            plate = RoundedRectangle(
                corner_radius=bar_height / 2, width=width, height=bar_height,
                stroke_width=0, fill_color=SURFACE_2, fill_opacity=1.0,
            )
            plate.move_to([width / 2, y, 0])
            tracks.add(plate)

        length = max(width * value / max_value, bar_height)
        bar = RoundedRectangle(
            corner_radius=bar_height / 2, width=length, height=bar_height,
            stroke_width=0, fill_color=color, fill_opacity=1.0,
        )
        bar.move_to([length / 2, y, 0])
        bars.add(bar)

        vl = txt(_format_value(value), size=size, color=color, weight=MEDIUM)
        vl.move_to([length + 0.36 + vl.width / 2, y, 0])
        value_labels.add(vl)

    group = VGroup(tracks, bars, labels, value_labels)
    group.tracks, group.bars = tracks, bars
    group.labels, group.values = labels, value_labels
    return group


def stacked_bar(v_value: float, u_value: float, height: float = 2.1,
                width: float = 0.62, scale_max: float = 1.0) -> VGroup:
    """Two stacked segments: exploitation ``V(s)`` under exploration bonus.

    Used for the UCT tug-of-war. Returns a group with ``.v_part``, ``.u_part``
    and ``.total`` (the summed height in scene units).
    """
    vh = max(height * v_value / scale_max, 0.001)
    uh = max(height * u_value / scale_max, 0.001)
    v_part = Rectangle(width=width, height=vh, stroke_width=0,
                       fill_color=GOOD, fill_opacity=0.92)
    u_part = Rectangle(width=width, height=uh, stroke_width=0,
                       fill_color=PRIMARY, fill_opacity=0.92)
    v_part.move_to([0, vh / 2, 0])
    u_part.move_to([0, vh + uh / 2, 0])
    group = VGroup(v_part, u_part)
    group.v_part, group.u_part = v_part, u_part
    group.total = vh + uh
    return group


# ---------------------------------------------------------------------------
# The animated search tree
# ---------------------------------------------------------------------------


class TreeNode(VGroup):
    """One node of the search tree: a circle, a label, and optional badges.

    The visual encodes two quantities at a glance: the *fill* is the node's
    value on the red-amber-green ramp, and the ring thickens when the node sits
    on the currently selected path.
    """

    def __init__(self, key: str, label: str | None = None,
                 value: float | None = None,
                 visits: int | None = None, radius: float = 0.33,
                 kind: str = "normal", show_value: bool = False):
        # ``label=None`` falls back to the key; ``label=""`` draws no label.
        super().__init__()
        self.key = key
        self.value = value
        self.visits = visits
        self.radius = radius
        self.kind = kind

        self.circle = Circle(
            radius=radius,
            stroke_color=self._stroke_color(), stroke_width=3,
            fill_color=self._fill_color(), fill_opacity=self._fill_opacity(),
        )
        self.label = txt(key if label is None else label,
                         size=FS_SMALL, color=self._label_color(),
                         weight=MEDIUM)
        cap_width(self.label, radius * 1.62)
        self.label.move_to(self.circle.get_center())
        self.circle.set_z_index(Z_NODE)
        self.label.set_z_index(Z_LABEL)
        self.add(self.circle, self.label)

        self.badge = None
        if show_value and value is not None:
            self.badge = self._make_badge()
            self.add(self.badge)

    # -- appearance ---------------------------------------------------------

    def _fill_color(self) -> str:
        if self.kind == "ghost":
            return SURFACE
        if self.value is None:
            return SURFACE_2
        return value_color(self.value)

    def _fill_opacity(self) -> float:
        return 0.55 if self.kind == "ghost" else 1.0

    def _label_color(self) -> str:
        """Dark ink on a saturated fill, light ink on the dark surface.

        The value ramp is deliberately light and mid-saturation, so white text
        on top of it is low contrast; near-black is much more readable and
        keeps the node legible when it is only a few percent of frame height.
        """
        if self.kind == "ghost":
            return INK_FAINT
        return BG if self.value is not None else INK

    def _stroke_color(self) -> str:
        return {
            "root": PRIMARY,
            "ghost": INK_FAINT,
            "success": GOOD,
            "fail": BAD,
        }.get(self.kind, STROKE if self.value is None else self._fill_color())

    def _make_badge(self) -> VGroup:
        """The ``V = 0.62`` plate under a node.

        It carries its own background so it stays readable where it crosses the
        edges running down to the node's children.
        """
        t = txt(f"{self.value:.2f}", size=FS_TINY, color=INK_DIM)
        plate = RoundedRectangle(
            corner_radius=0.05, width=t.width + 0.14, height=t.height + 0.09,
            stroke_width=0, fill_color=BG, fill_opacity=0.92,
        )
        t.move_to(plate.get_center())
        badge = VGroup(plate, t)
        badge.set_z_index(Z_LABEL)
        badge.next_to(self.circle, DOWN, buff=0.09)
        return badge

    def restyle(self, value=None, kind=None, visits=None) -> None:
        """Update the node in place (call inside an ``.animate`` context)."""
        if value is not None:
            self.value = value
        if kind is not None:
            self.kind = kind
        if visits is not None:
            self.visits = visits
        self.circle.set_fill(self._fill_color(), self._fill_opacity())
        self.circle.set_stroke(self._stroke_color(), 3)
        self.label.set_color(self._label_color())
        if self.badge is not None and self.value is not None:
            new = txt(f"{self.value:.2f}", size=FS_TINY, color=INK_DIM)
            new.move_to(self.badge[1].get_center())
            self.badge[1].become(new)

    # -- geometry -----------------------------------------------------------
    #
    # A node's *anchor* is the centre of its circle, not the centre of the
    # VGroup: when a value badge hangs below the circle it drags the group's
    # bounding box down, and edges must still meet the circle. Everything
    # positional therefore goes through these two helpers.

    @property
    def anchor(self) -> np.ndarray:
        return self.circle.get_center()

    def move_anchor_to(self, point) -> "TreeNode":
        """Place the node so its *circle* is centred on ``point``."""
        self.shift(np.asarray(point, dtype=float) - self.anchor)
        return self

    def dim(self, opacity: float = 0.3) -> None:
        self.set_opacity(opacity)


class SearchTree(VGroup):
    """A laid-out, animatable search tree.

    Nodes are addressed by string keys. The layout is a standard tidy layered
    tree: depth sets the row, and each subtree is allotted a horizontal slot
    proportional to its leaf count, so siblings never collide and parents sit
    centred over their children.

    Typical use::

        tree = SearchTree(origin=[0, 2.0, 0])
        self.play(*tree.add_node("root", None, "s0", kind="root"))
        self.play(*tree.add_node("a", "root", "A"))
        self.play(*tree.relayout())          # settle after a level widens
        self.play(*tree.highlight_path(["root", "a"]))
    """

    def __init__(self, origin=None, level_gap: float = 1.28,
                 slot_width: float = 1.5, radius: float = 0.33,
                 edge_color: str = EDGE):
        super().__init__()
        self.origin = np.array(origin if origin is not None
                               else [0.0, BODY_TOP - 0.35, 0.0], dtype=float)
        self.level_gap = level_gap
        self.slot_width = slot_width
        self.radius = radius
        self.edge_color = edge_color

        self.nodes: dict[str, TreeNode] = {}
        self.parents: dict[str, str | None] = {}
        self.children: dict[str, list[str]] = {}
        self.edges: dict[str, Line] = {}          # child key -> edge to parent
        self.node_layer = VGroup()
        self.edge_layer = VGroup()
        self.add(self.edge_layer, self.node_layer)

    # -- layout -------------------------------------------------------------

    def _leaf_count(self, key: str) -> int:
        kids = self.children.get(key, [])
        if not kids:
            return 1
        return sum(self._leaf_count(k) for k in kids)

    def _depth(self, key: str) -> int:
        d, cur = 0, self.parents.get(key)
        while cur is not None:
            d += 1
            cur = self.parents.get(cur)
        return d

    def layout(self) -> dict:
        """Compute target positions for every node."""
        roots = [k for k, p in self.parents.items() if p is None]
        positions: dict[str, np.ndarray] = {}
        cursor = 0.0
        for root in roots:
            span = self._leaf_count(root)
            self._place(root, cursor, span, positions)
            cursor += span
        if positions:
            xs = [p[0] for p in positions.values()]
            shift = (min(xs) + max(xs)) / 2
            for key in positions:
                positions[key][0] -= shift
                positions[key] += self.origin
        return positions

    def _place(self, key: str, offset: float, span: float,
               out: dict) -> None:
        x = (offset + span / 2) * self.slot_width
        y = -self._depth(key) * self.level_gap
        out[key] = np.array([x, y, 0.0])
        cursor = offset
        for child in self.children.get(key, []):
            child_span = self._leaf_count(child)
            self._place(child, cursor, child_span, out)
            cursor += child_span

    def _edge_between(self, parent_key: str, child_key: str,
                      positions: dict) -> Line:
        p, c = positions[parent_key], positions[child_key]
        direction = c - p
        norm = np.linalg.norm(direction)
        if norm < 1e-6:
            direction, norm = np.array([0.0, -1.0, 0.0]), 1.0
        unit = direction / norm
        line = Line(p + unit * self.radius, c - unit * self.radius,
                    stroke_color=self.edge_color, stroke_width=2.5)
        line.set_z_index(Z_EDGE)
        return line

    # -- mutation -----------------------------------------------------------

    def add_node(self, key: str, parent: str | None, label: str | None = None,
                 value: float | None = None, kind: str = "normal",
                 show_value: bool = False, run_time: float = T_NORM) -> list:
        """Register a node and return animations that introduce it.

        Existing nodes are moved to their new positions in the same call, so a
        single ``self.play(*tree.add_node(...))`` both grows and settles.
        """
        node = TreeNode(key, label, value=value, radius=self.radius,
                        kind=kind, show_value=show_value)
        self.nodes[key] = node
        self.parents[key] = parent
        self.children.setdefault(key, [])
        if parent is not None:
            self.children.setdefault(parent, []).append(key)

        anims = self._reposition_existing(exclude={key})
        positions = self.layout()
        node.move_anchor_to(positions[key])
        self.node_layer.add(node)

        if parent is not None:
            edge = self._edge_between(parent, key, positions)
            self.edges[key] = edge
            self.edge_layer.add(edge)
            anims.append(Create(edge, run_time=run_time))
        anims.append(GrowFromCenter(node, run_time=run_time))
        return anims

    def add_children(self, parent: str, specs, run_time: float = T_NORM,
                     lag: float = T_LAG) -> list:
        """Add several children at once; they appear staggered.

        ``specs`` is a sequence of dicts accepted by :meth:`add_node` minus
        ``parent`` (keys: ``key``, ``label``, ``value``, ``kind``,
        ``show_value``).
        """
        for spec in specs:
            key = spec["key"]
            node = TreeNode(key, spec.get("label"),
                            value=spec.get("value"), radius=self.radius,
                            kind=spec.get("kind", "normal"),
                            show_value=spec.get("show_value", False))
            self.nodes[key] = node
            self.parents[key] = parent
            self.children.setdefault(key, [])
            self.children.setdefault(parent, []).append(key)

        new_keys = [s["key"] for s in specs]
        anims = self._reposition_existing(exclude=set(new_keys))
        positions = self.layout()

        births = []
        for key in new_keys:
            node = self.nodes[key]
            node.move_anchor_to(positions[key])
            self.node_layer.add(node)
            edge = self._edge_between(parent, key, positions)
            self.edges[key] = edge
            self.edge_layer.add(edge)
            births.append(AnimationGroup(Create(edge), GrowFromCenter(node),
                                         lag_ratio=0.35))
        anims.append(LaggedStart(*births, lag_ratio=lag, run_time=run_time))
        return anims

    def _reposition_existing(self, exclude: set) -> list:
        """Animations that slide already-placed nodes and edges into place."""
        positions = self.layout()
        anims = []
        for key, node in self.nodes.items():
            if key in exclude:
                continue
            target = positions.get(key)
            if target is None:
                continue
            if np.linalg.norm(node.anchor - target) > 1e-4:
                anims.append(node.animate.move_anchor_to(target))
        for key, edge in self.edges.items():
            if key in exclude:
                continue
            parent = self.parents.get(key)
            if parent is None:
                continue
            new_edge = self._edge_between(parent, key, positions)
            anims.append(edge.animate.put_start_and_end_on(
                new_edge.get_start(), new_edge.get_end()))
        return anims

    def relayout(self, run_time: float = T_NORM) -> list:
        """Animations that settle every node and edge onto the current layout."""
        anims = self._reposition_existing(exclude=set())
        return [AnimationGroup(*anims, run_time=run_time)] if anims else []

    def place(self) -> "SearchTree":
        """Snap everything onto the current layout *now*, with no animation.

        ``add_node`` and ``add_children`` only *return* the animations that
        shuffle the already-placed nodes aside to make room. That is what you
        want when the tree grows on screen — but if you build a finished tree
        in one go and simply fade it in, those animations are never played and
        the earlier nodes stay where they were, leaving the tree visibly
        lopsided. Call this once after building such a tree.
        """
        positions = self.layout()
        for key, node in self.nodes.items():
            node.move_anchor_to(positions[key])
        for key, edge in self.edges.items():
            parent = self.parents.get(key)
            if parent is None:
                continue
            target = self._edge_between(parent, key, positions)
            edge.put_start_and_end_on(target.get_start(), target.get_end())
        return self

    def rescale(self, factor: float, origin=None,
                run_time: float = T_NORM) -> list:
        """Shrink (or grow) the whole tree and settle it onto the new layout.

        A tree that is about to gain two more levels will not fit the frame at
        its current spacing. Rather than scaling the finished VGroup - which
        would desynchronise it from the layout maths - this scales the layout
        *parameters* and the node radii together, so every later
        :meth:`add_children` lands correctly at the new size.
        """
        self.slot_width *= factor
        self.level_gap *= factor
        self.radius *= factor
        if origin is not None:
            self.origin = np.asarray(origin, dtype=float)

        positions = self.layout()
        anims = []
        for key, node in self.nodes.items():
            anims.append(node.animate
                         .scale(factor, about_point=node.anchor)
                         .move_anchor_to(positions[key]))
        for key, edge in self.edges.items():
            parent = self.parents.get(key)
            if parent is None:
                continue
            new_edge = self._edge_between(parent, key, positions)
            anims.append(edge.animate.put_start_and_end_on(
                new_edge.get_start(), new_edge.get_end()))
        return [AnimationGroup(*anims, run_time=run_time)] if anims else []

    # -- queries ------------------------------------------------------------

    def path_to(self, key: str) -> list:
        """Keys from the root down to ``key``, inclusive."""
        chain, cur = [], key
        while cur is not None:
            chain.append(cur)
            cur = self.parents.get(cur)
        return list(reversed(chain))

    def node(self, key: str) -> TreeNode:
        return self.nodes[key]

    def pos(self, key: str) -> np.ndarray:
        """Centre of the node's circle (not of its bounding box)."""
        return self.nodes[key].anchor

    # -- emphasis -----------------------------------------------------------

    def highlight_path(self, keys, color: str = ACCENT, width: float = 6.0,
                       run_time: float = T_NORM) -> list:
        """Thicken the edges and rings along a root-to-node path."""
        anims = []
        for i, key in enumerate(keys):
            node = self.nodes[key]
            anims.append(node.circle.animate.set_stroke(color, width))
            if i > 0 and key in self.edges:
                anims.append(self.edges[key].animate.set_stroke(color, 5))
        return [AnimationGroup(*anims, run_time=run_time)] if anims else []

    def reset_path(self, keys, run_time: float = T_FAST) -> list:
        anims = []
        for i, key in enumerate(keys):
            node = self.nodes[key]
            anims.append(node.circle.animate.set_stroke(
                node._stroke_color(), 3))
            if i > 0 and key in self.edges:
                anims.append(self.edges[key].animate.set_stroke(
                    self.edge_color, 2.5))
        return [AnimationGroup(*anims, run_time=run_time)] if anims else []

    def set_value(self, key: str, value: float, run_time: float = T_FAST):
        """Animation that recolours a node to a new value."""
        node = self.nodes[key]
        node.value = value
        target = node.copy()
        target.value = value
        target.restyle(value=value)
        return Transform(node, target, run_time=run_time)

    def dim_all(self, except_keys=(), opacity: float = 0.28,
                run_time: float = T_FAST) -> list:
        keep = set(except_keys)
        anims = [n.animate.set_opacity(opacity)
                 for k, n in self.nodes.items() if k not in keep]
        anims += [e.animate.set_stroke(opacity=opacity)
                  for k, e in self.edges.items() if k not in keep]
        return [AnimationGroup(*anims, run_time=run_time)] if anims else []


def value_legend(width: float = 3.0, height: float = 0.2) -> VGroup:
    """A small red-to-green ramp with end labels, explaining node colour."""
    steps = 40
    strip = VGroup()
    for i in range(steps):
        seg = Rectangle(width=width / steps, height=height, stroke_width=0,
                        fill_color=value_color(i / (steps - 1)),
                        fill_opacity=1.0)
        seg.move_to([(i + 0.5) * width / steps - width / 2, 0, 0])
        strip.add(seg)
    lo = txt("low value", size=FS_TINY, color=INK_FAINT)
    hi = txt("high value", size=FS_TINY, color=INK_FAINT)
    lo.next_to(strip, LEFT, buff=0.2)
    hi.next_to(strip, RIGHT, buff=0.2)
    return VGroup(strip, lo, hi)
