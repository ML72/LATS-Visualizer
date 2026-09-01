"""
Make a TeX distribution visible to Manim.

Manim shells out to ``latex`` and ``dvisvgm`` to typeset every ``MathTex``.
On Windows in particular, MiKTeX is frequently installed per-user and is *not*
added to the ``PATH`` seen by a virtual environment's Python, which makes every
equation in the video fail with ``FileNotFoundError: [WinError 2]``.

Importing :mod:`create_video.theme` calls :func:`ensure_latex_on_path` once, which
looks in the usual install locations and prepends the first one that contains
both binaries. If LaTeX is already on ``PATH`` this is a no-op, so the module
is harmless on Linux and macOS.

Set ``LATS_TEX_BIN`` to point at a TeX ``bin`` directory to override the search.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

#: Directories searched, in order, when ``latex`` is not already on PATH.
#: ``*`` is expanded with :meth:`pathlib.Path.glob`.
_CANDIDATES = [
    # MiKTeX, per-user install (the default for a normal MiKTeX setup)
    r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin\x64",
    r"%LOCALAPPDATA%\Programs\MiKTeX\miktex\bin",
    # MiKTeX, machine-wide install
    r"C:\Program Files\MiKTeX\miktex\bin\x64",
    r"C:\Program Files\MiKTeX\miktex\bin",
    r"C:\Program Files (x86)\MiKTeX\miktex\bin",
    # TeX Live on Windows
    r"C:\texlive\*\bin\windows",
    r"C:\texlive\*\bin\win32",
    # TeX Live / MacTeX on Unix
    "/usr/local/texlive/*/bin/*",
    "/Library/TeX/texbin",
    "/usr/local/bin",
]

#: Binaries Manim needs in order to render LaTeX.
_REQUIRED = ("latex", "dvisvgm")


def _has_tex(directory: Path) -> bool:
    """True if ``directory`` holds every binary Manim needs."""
    for name in _REQUIRED:
        if not (directory / name).exists() and not (directory / f"{name}.exe").exists():
            return False
    return True


def find_tex_bin() -> Path | None:
    """Return a directory containing ``latex`` and ``dvisvgm``, or ``None``."""
    override = os.environ.get("LATS_TEX_BIN")
    if override:
        p = Path(os.path.expandvars(override))
        return p if _has_tex(p) else None

    for raw in _CANDIDATES:
        pattern = os.path.expandvars(raw)
        if "*" in pattern:
            # Path.glob needs a concrete anchor, so split at the first wildcard.
            head, _, tail = pattern.partition("*")
            anchor = Path(head).parent if not Path(head).is_dir() else Path(head)
            try:
                matches = sorted(anchor.glob(Path(head).name + "*" + tail))
            except (OSError, ValueError):
                continue
            for m in matches:
                if m.is_dir() and _has_tex(m):
                    return m
        else:
            p = Path(pattern)
            if p.is_dir() and _has_tex(p):
                return p
    return None


def ensure_latex_on_path(verbose: bool = False) -> str | None:
    """Prepend a TeX ``bin`` directory to ``PATH`` if LaTeX is not reachable.

    Returns the directory that was added, or ``None`` if nothing was needed or
    nothing was found.
    """
    if shutil.which("latex") and shutil.which("dvisvgm"):
        return None

    found = find_tex_bin()
    if found is None:
        return None

    os.environ["PATH"] = str(found) + os.pathsep + os.environ.get("PATH", "")
    if verbose:
        print(f"[lats] added TeX binaries to PATH: {found}")
    return str(found)


def latex_status() -> str:
    """A one-line human-readable summary, used by ``scripts/create_video.py --check``."""
    ensure_latex_on_path()
    latex = shutil.which("latex")
    dvisvgm = shutil.which("dvisvgm")
    if latex and dvisvgm:
        return f"OK   latex={latex}  dvisvgm={dvisvgm}"
    missing = [n for n, p in (("latex", latex), ("dvisvgm", dvisvgm)) if not p]
    return (
        f"MISSING {', '.join(missing)} - equations will fail to render. "
        "Install MiKTeX or TeX Live, or set LATS_TEX_BIN to its bin directory."
    )
