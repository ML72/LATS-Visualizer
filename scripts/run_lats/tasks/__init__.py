"""The environments LATS can be pointed at.

Adding one means writing a :class:`~run_lats.tasks.base.Task` subclass and
putting it in :data:`TASKS`. Nothing else in the package needs to change - the
search loop, the trace writer and the browser demo are all task-agnostic.
"""

from __future__ import annotations

from .base import Task
from .code_task import MergeIntervalsTask
from .game24 import Game24Task
from .qa import MultiHopQATask

#: Everything ``scripts/run_lats.py`` can run, keyed by the name used on the command
#: line and as the trace filename.
TASKS: dict[str, type[Task]] = {
    MergeIntervalsTask.id: MergeIntervalsTask,
    Game24Task.id: Game24Task,
    MultiHopQATask.id: MultiHopQATask,
}

__all__ = ["TASKS", "Task", "MergeIntervalsTask", "Game24Task", "MultiHopQATask"]
