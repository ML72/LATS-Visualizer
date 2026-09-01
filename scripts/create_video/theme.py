"""
Visual design system for the LATS explainer video.

Everything that controls the *look* of the video lives here: the palette, the
type scale, the layout grid, and a handful of small helpers used by every
scene. To restyle the whole video, this is the only file you need to touch.

Design notes
------------
* Dark, low-chroma background. The video is meant to be projected in a lit room
  and to be readable on a laptop; a near-black ground keeps the coloured value
  encodings legible without vibrating.
* Colour carries *meaning*, consistently across all seven parts:

      blue    structure / the search algorithm itself
      amber   the thing you should be looking at right now
      green   high value, success, passing tests
      red     low value, failure, dead end
      violet  reflection (LATS's one genuinely new operation)
      teal    the environment / external feedback

* No raster or vector assets are imported from anywhere. Every icon in this
  video is drawn from Manim primitives (see ``components.py``), so the whole
  production is original work with no third-party asset licensing to track.
"""

from __future__ import annotations

from manim import *

from .texpath import ensure_latex_on_path

# Manim shells out to `latex` and `dvisvgm` for every equation. On Windows,
# MiKTeX is often installed per-user and is missing from the PATH a virtualenv
# sees, so make it reachable before any MathTex is constructed.
ensure_latex_on_path()

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

BG = "#0E1117"          # page background
SURFACE = "#161C25"     # panel fill
SURFACE_2 = "#1F2733"   # raised panel fill
STROKE = "#2E3947"      # panel border / hairlines
EDGE = "#4A5A6E"        # tree edges: quiet, but never invisible

INK = "#EEF2F7"         # primary text
INK_DIM = "#93A1B5"     # secondary text
INK_FAINT = "#5B6879"   # tertiary text, rules, ghosted elements

PRIMARY = "#4EA8FF"     # structure, the algorithm, selected paths
ACCENT = "#FFB547"      # the current focus of attention
GOOD = "#3DD68C"        # high value / success
BAD = "#FF6B6B"         # low value / failure
VIOLET = "#B98CFF"      # reflection
TEAL = "#2DD4BF"        # environment / external feedback

# Ordered stops used to map a value in [0, 1] onto a colour. The stops are
# chosen so that neighbouring node values stay visually distinguishable in the
# middle of the range, which is where most of the interesting search happens.
VALUE_STOPS = ["#F2565B", "#FF8A3D", "#FFC24A", "#A9D95E", GOOD]


def value_color(v: float) -> str:
    """Map a node value in ``[0, 1]`` onto the red-amber-green ramp."""
    v = float(min(max(v, 0.0), 1.0))
    span = len(VALUE_STOPS) - 1
    idx = min(int(v * span), span - 1)
    local = v * span - idx
    return interpolate_color(
        ManimColor(VALUE_STOPS[idx]), ManimColor(VALUE_STOPS[idx + 1]), local
    ).to_hex()


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

def _resolve_font(candidates):
    """Return the first installed font from ``candidates``.

    Open-licensed families are listed first so a machine that has them renders
    identically everywhere; the trailing system fonts are metric-compatible
    fallbacks so the layout does not shift much when they are used instead.
    """
    try:
        import manimpango
        available = set(manimpango.list_fonts())
    except Exception:  # pragma: no cover - manimpango ships with manim
        return candidates[-1]
    for name in candidates:
        if name in available:
            return name
    return candidates[-1]


#: Body / UI face. Open fonts first, then common system fallbacks.
FONT = _resolve_font([
    "Inter", "Source Sans 3", "Source Sans Pro", "Noto Sans", "DejaVu Sans",
    "Liberation Sans", "Segoe UI", "Helvetica Neue", "Arial",
])

#: Monospace face, used for code and for agent transcripts.
FONT_MONO = _resolve_font([
    "JetBrains Mono", "Fira Code", "Source Code Pro", "Noto Sans Mono",
    "DejaVu Sans Mono", "Liberation Mono", "Cascadia Mono", "Consolas",
    "Courier New",
])

# Type scale. Manim font sizes are points against a 1080-pixel-tall frame.
FS_TITLE = 54    # opening title card only
FS_H1 = 40       # section headline
FS_H2 = 31       # on-slide heading
FS_H3 = 26       # panel title
FS_BODY = 23     # body copy
FS_SMALL = 19    # labels, axis ticks
FS_TINY = 15     # footnotes, citations
FS_MONO = 18     # code and transcripts


def txt(s, size=FS_BODY, color=INK, weight=NORMAL, font=None, **kw):
    """Body text with the project's face and defaults applied."""
    return Text(s, font=font or FONT, font_size=size, color=color,
                weight=weight, **kw)


def mono(s, size=FS_MONO, color=INK, **kw):
    """Monospaced text (code, transcripts, tool output)."""
    return Text(s, font=FONT_MONO, font_size=size, color=color, **kw)


def mathtex(s, size=FS_H2, color=INK, **kw):
    """A LaTeX equation at the project's default maths size.

    Named ``mathtex`` rather than ``math`` so it never reads as the
    standard-library module, which several parts also import from.
    """
    return MathTex(s, font_size=size, color=color, **kw)


# ---------------------------------------------------------------------------
# Layout grid
# ---------------------------------------------------------------------------

FRAME_W = config.frame_width     # 14.222 units at 16:9
FRAME_H = config.frame_height    # 8.0 units

MARGIN = 0.6                     # keep everything this far from the frame edge
SAFE_L = -FRAME_W / 2 + MARGIN
SAFE_R = FRAME_W / 2 - MARGIN
SAFE_T = FRAME_H / 2 - MARGIN    # +3.4
SAFE_B = -FRAME_H / 2 + MARGIN   # -3.4

HEADER_Y = 3.25                  # centre line of the slide heading
RULE_Y = 2.86                    # hairline under the heading
BODY_TOP = 2.55                  # highest a body element may reach
BODY_BOTTOM = -3.05              # lowest a body element may reach
FOOTER_Y = -3.58                 # citations / footnotes

#: Vertical centre of the usable body area.
BODY_CY = (BODY_TOP + BODY_BOTTOM) / 2
BODY_W = SAFE_R - SAFE_L
BODY_H = BODY_TOP - BODY_BOTTOM


def body_zone(pad=0.0, top=None, bottom=None, left=None, right=None):
    """An invisible rectangle covering the usable area below the heading.

    Pass ``top`` / ``bottom`` / ``left`` / ``right`` to carve out a sub-region
    (for example the left half of the slide). Use with :func:`fit_in` to
    guarantee a group cannot collide with the header or leave the frame.
    """
    t = BODY_TOP if top is None else top
    b = BODY_BOTTOM if bottom is None else bottom
    lo = SAFE_L if left is None else left
    hi = SAFE_R if right is None else right
    r = Rectangle(width=(hi - lo) - 2 * pad, height=(t - b) - 2 * pad)
    r.move_to([(lo + hi) / 2, (t + b) / 2, 0])
    r.set_opacity(0).set_stroke(width=0)
    return r


def fit_in(mob, region, pad=0.0, max_scale=1.0, center=True):
    """Scale ``mob`` down to fit ``region``, then centre it there.

    Never scales up past ``max_scale``. This is the workhorse that keeps every
    slide inside the safe area no matter how much text a beat carries.
    """
    avail_w = region.width - 2 * pad
    avail_h = region.height - 2 * pad
    if mob.width <= 1e-6 or mob.height <= 1e-6:
        return mob
    factor = min(avail_w / mob.width, avail_h / mob.height, max_scale)
    if factor < 1.0:
        mob.scale(factor)
    if center:
        mob.move_to(region.get_center())
    return mob


def cap_width(mob, width):
    """Shrink ``mob`` if it is wider than ``width``. Never enlarges."""
    if mob.width > width:
        mob.scale(width / mob.width)
    return mob


def cap_height(mob, height):
    """Shrink ``mob`` if it is taller than ``height``. Never enlarges."""
    if mob.height > height:
        mob.scale(height / mob.height)
    return mob


# ---------------------------------------------------------------------------
# Motion
# ---------------------------------------------------------------------------

# One place to tune the overall feel. Keeping these consistent across parts is
# most of what makes a multi-part video look like one piece of work.
T_FAST = 0.4     # micro-transitions: a highlight, a colour change
T_NORM = 0.7     # the default for anything that appears or moves
T_SLOW = 1.1     # a deliberate, "look at this" transition
T_LAG = 0.14     # lag_ratio for staggered LaggedStart groups
