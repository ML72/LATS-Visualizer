"""Manim source for the LATS explainer video.

Submodules
----------
paths       where a render reads and writes, under results/
theme       palette, type scale, layout grid, motion constants
components  reusable mobjects (search tree, panels, icons) and the scene base
texpath     locates a TeX distribution so equations render on Windows
render      the Manim and ffmpeg mechanics behind scripts/create_video.py
timing      narration length against time on screen, per beat
script      writes SCRIPT.txt, the narration cued to a render's timings
preview     a design-system contact sheet, for checking the theme
parts/      one module per section of the finished video

The command line is ``scripts/create_video.py``; nothing here is meant to be
run directly except the Manim scenes in ``parts/`` and ``preview``.
"""

__all__ = ["paths", "theme", "components", "texpath", "render", "timing",
           "script", "preview"]
