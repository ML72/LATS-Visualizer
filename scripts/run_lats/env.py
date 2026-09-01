"""
Read ``.env``, so a key does not have to be exported by hand every session.

Deliberately tiny and standard-library only. This is the only configuration the
project has, and taking on a dependency to parse ``KEY=value`` would be out of
proportion to the job. It is not a shell: no interpolation, no multi-line
values, no command substitution.

Anything already exported wins, so ``OPENAI_API_KEY=... python scripts/run_lats.py``
still overrides the file.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_env(path: Path) -> list[str]:
    """Set any variable named in ``path`` that is not already set.

    Returns the *names* it set - never the values - so a caller can report what
    it found without putting a secret on the terminal.

    Understands ``KEY=value``, an optional ``export`` prefix, surrounding single
    or double quotes, ``#`` comment lines, and blank lines.
    """
    if not path.is_file():
        return []

    loaded: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].lstrip()

        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not key:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]

        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
