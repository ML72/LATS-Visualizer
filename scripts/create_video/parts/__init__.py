"""One module per section of the video.

Each module defines exactly one Manim ``Scene`` subclass, so it renders to a
single mp4. ``scripts/create_video.py`` renders them in order and concatenates
the results.

The narration lives here too, in a ``NARRATION`` dict at the top of each
module, keyed by beat method name - so the words and the picture they describe
sit in the same file. A second dict, ``ON_SCREEN``, describes what the frame shows for each beat.
``create_video.script`` turns those two dicts plus a render's measured timings
into ``SCRIPT.md``.
"""
