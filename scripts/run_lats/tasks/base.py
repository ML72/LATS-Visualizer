"""
What a task has to provide for LATS to search it.

A task is an *environment*, not a prompt. It owns the state, it executes
actions for real, and it is the only thing allowed to say what a reward is.
The search loop never inspects ``data``; it only ever asks the task.

Two of the methods exist for the two policies:

``mock_propose``   the offline stand-in policy draws candidates from a bank the
                   task defines, so the demo runs with no API key and produces
                   the same trace every time.
``render`` / ``parse_action``
                   the OpenAI-backed policy needs the state as text, and needs
                   to turn a JSON reply back into an :class:`Action`.
"""

from __future__ import annotations

import random
from typing import Any

from ..types import Action, Observation, Proposal


class Task:
    """Base class. Subclasses override everything that raises."""

    #: Stable identifier, used as the trace filename.
    id: str = "task"
    #: One of ``programming`` | ``game`` | ``qa``. Only used for display and
    #: for picking the paper's per-family defaults.
    family: str = "programming"
    title: str = ""
    #: The problem statement shown to the agent and to the viewer.
    prompt: str = ""
    #: One line describing where the objective reward comes from.
    reward_desc: str = ""
    #: Anything the viewer should show alongside the task - the test suite,
    #: the starting numbers, the corpus size.
    context: dict[str, Any] = {}

    def defaults(self) -> dict[str, Any]:
        """Per-task overrides applied on top of :class:`~run_lats.types.Config`."""
        return {}

    # -- the environment ----------------------------------------------------

    def root_data(self) -> dict[str, Any]:
        """Environment state before the agent has done anything."""
        raise NotImplementedError

    def step(self, data: dict, action: Action) -> tuple[dict, Observation]:
        """Execute ``action`` against ``data``. Returns the new state and what
        the environment said back. This is where real work happens: code is
        run, arithmetic is evaluated, documents are retrieved."""
        raise NotImplementedError

    # -- the offline policy -------------------------------------------------

    def mock_propose(
        self, data: dict, rng: random.Random, n: int, reflections: list[str]
    ) -> list[Proposal]:
        """Sample up to ``n`` candidate actions without calling a model."""
        raise NotImplementedError

    # -- the online policy --------------------------------------------------

    def render(self, data: dict) -> str:
        """The current state as text, for a real model's prompt."""
        raise NotImplementedError

    def action_schema(self) -> str:
        """One paragraph telling a real model what JSON to return."""
        raise NotImplementedError

    def parse_action(self, obj: dict, data: dict) -> Action:
        """Turn one JSON object from a real model into an :class:`Action`.

        ``data`` is the state the action would be applied to. Most tasks do not
        need it - a program or a tool call means the same thing wherever it
        appears - but a task whose actions only make sense against the current
        state does, and it is also the only chance to reject a move the model
        invented. Raise :class:`ValueError` to drop the candidate; the search
        treats an expansion that yields nothing as a dead end.
        """
        raise NotImplementedError

    # -- reflection ---------------------------------------------------------

    def reflection_for(self, node_data: dict, observation: Observation | None) -> str:
        """A short note on why this trajectory failed, written from the
        environment's own output rather than invented."""
        if observation is None:
            return "This trajectory ended without any environment feedback."
        return f"That attempt scored {observation.reward}. {observation.text}"

    # -- display ------------------------------------------------------------

    def brief(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "family": self.family,
            "title": self.title,
            "prompt": self.prompt,
            "reward": self.reward_desc,
            "context": self.context,
        }
