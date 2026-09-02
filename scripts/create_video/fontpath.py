"""
Make the fonts bundled with this repository available to Pango.

Manim draws every ``Text`` through Pango, which by default can only see fonts
the operating system has installed. That makes a render machine-dependent: the
type scale in :mod:`create_video.theme` asks for Inter first and falls back
through a list of system faces, so the same source produces different metrics -
and slightly different line breaks - on a machine that happens to lack it.

Dropping the font files in ``create_video/fonts/`` and registering them at
import time fixes that without installing anything. ``manimpango.register_font``
calls the native API (``AddFontResourceEx`` with private scope on Windows,
fontconfig elsewhere), so the face is visible to *this process only*: nothing is
written to the system font directory or the registry, and a process that does
not call it still sees the unmodified system list.

Registration is per-process, and Manim renders each part in a subprocess of its
own, so this has to run on import rather than once from the command line -
:mod:`create_video.theme` calls it before it resolves a face, and every part
module imports the theme.

Set ``LATS_FONT_DIR`` to register from somewhere else instead.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Font files live here unless ``LATS_FONT_DIR`` says otherwise.
FONT_DIR = Path(__file__).resolve().parent / "fonts"

#: Extensions Pango can load: TrueType, OpenType, and TrueType collections.
SUFFIXES = {".ttf", ".otf", ".ttc"}

#: Families registered by this process, filled in by :func:`register_bundled`.
REGISTERED: list[str] = []

_done = False


def font_dir() -> Path:
    override = os.environ.get("LATS_FONT_DIR")
    return Path(override) if override else FONT_DIR


def register_bundled() -> list[str]:
    """Register every bundled font file. Returns the families that appeared.

    Safe to call repeatedly - the work happens once per process. A missing
    directory is not an error: the theme simply falls back to system faces,
    which is what happened before any fonts were bundled.
    """
    global _done
    if _done:
        return REGISTERED

    _done = True
    directory = font_dir()
    if not directory.is_dir():
        return REGISTERED

    try:
        import manimpango
    except ImportError:  # pragma: no cover - manimpango ships with manim
        return REGISTERED

    before = set(manimpango.list_fonts())
    # Sorted, so a collection that carries the real weights is registered
    # before any variable-font sibling and wins the family name.
    for path in sorted(directory.iterdir()):
        if path.suffix.lower() in SUFFIXES:
            manimpango.register_font(str(path))
    REGISTERED.extend(sorted(set(manimpango.list_fonts()) - before))
    _freeze_font_list(manimpango)
    return REGISTERED


def _freeze_font_list(manimpango) -> None:
    """Memoise ``manimpango.list_fonts`` - it looks cached, and is not.

    Manim validates the family name on *every* ``Text`` it builds, by calling
    ``manimpango.list_fonts()`` (``text_mobject.py``). That function reads as
    though it is cached::

        def list_fonts():
            return lru_cache(maxsize=None)(_list_fonts)(tuple(...))

    but the decorator is applied to a fresh wrapper on each call, so the cache
    is thrown away every time and every ``Text`` pays a full font enumeration.

    That is survivable on the system font list (measured here at ~0.5 s per
    call) and is not survivable once private fonts are registered: Windows
    rebuilds its font collection on each enumeration and the call measured
    ~6.4 s. Part 4 rebuilds three number labels per frame while the exploration
    weight sweeps, so an unfixed render went from 74 seconds to over 40 minutes
    and 6 GB of resident memory before it was killed.

    The set of registered fonts cannot change after this module has run, so the
    answer is constant and safe to freeze. A copy is handed out because Manim
    treats the result as its own list.
    """
    families = list(manimpango.list_fonts())
    manimpango.list_fonts = lambda: list(families)


def status() -> str:
    """One line for ``--check``: which bundled families Pango can now see."""
    directory = font_dir()
    if not directory.is_dir():
        return f"no bundled fonts ({directory} does not exist)"
    families = register_bundled()
    if not families:
        return f"no fonts registered from {directory}"
    return f"OK   {', '.join(families)}  from {directory}"
