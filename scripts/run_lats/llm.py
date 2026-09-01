"""
The two policies: a deterministic offline stand-in, and a real Claude call.

The design rule for the whole submission is that everything must run with
``pip install -r requirements.txt`` and **no API key**. So :class:`MockLLM` is
the default everywhere, and it is honest about what it is: a seeded sampler
over a bank of candidate actions that each task defines for itself.

What is *not* mocked is the environment. The code really runs, the arithmetic
really evaluates, the retrieval really searches. Every reward in every trace
this package writes came out of a real execution - which is the part that
matters, because the reward is what LATS backpropagates.
"""

from __future__ import annotations

import json
import os
import random
import re
from typing import Any

from .tasks.base import Task
from .types import Proposal


class MockLLM:
    """A deterministic policy. Same seed, same trace, byte for byte.

    Sampling happens *with replacement* from the task's candidate bank, which
    is deliberate: the self-consistency term ``SC(s)`` is defined as the share
    of the ``n`` samples that agree, so duplicates are not waste, they are the
    measurement.
    """

    kind = "mock"
    name = "MockLLM"

    def __init__(self, seed: int = 7) -> None:
        self.rng = random.Random(seed)
        self.seed = seed
        self.calls = 0
        self.tokens = 0

    def propose(
        self, task: Task, data: dict, n: int, reflections: list[str]
    ) -> list[Proposal]:
        proposals = task.mock_propose(data, self.rng, n, reflections)
        self.calls += 1
        self.tokens += _estimate_tokens(task, data, reflections, proposals)
        return proposals

    def info(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "model": None,
            "seed": self.seed,
            "calls": self.calls,
            "tokens": self.tokens,
            "tokens_are_estimated": True,
        }


def _estimate_tokens(
    task: Task, data: dict, reflections: list[str], proposals: list[Proposal]
) -> int:
    """A four-characters-per-token estimate of what this call would have cost.

    Rough on purpose, and flagged as an estimate in the trace. It exists so the
    cost axis of the demo is not simply missing when the mock policy is used;
    the shape of the curve is right even though the constant is not.
    """
    prompt = task.render(data) + task.action_schema() + " ".join(reflections)
    completion = " ".join(p.action.text + p.rationale for p in proposals)
    return (len(prompt) + len(completion)) // 4


# ---------------------------------------------------------------------------


SYSTEM = (
    "You are the policy inside a Language Agent Tree Search. You are given the "
    "current state of a partially solved task and you propose several *distinct* "
    "next actions, then grade each one yourself on how likely it is to lead to a "
    "correct solution. Your grade is a prior only - the environment will execute "
    "your action and overrule you. Reply with JSON and nothing else."
)


class ClaudeLLM:
    """The same policy interface, backed by a real model.

    Opt-in: ``pip install anthropic`` and either export ``ANTHROPIC_API_KEY`` or
    run ``ant auth login``. One request per expansion returns all ``n``
    candidates, which keeps a full search down to a handful of calls.

    Traces produced this way are *not* reproducible, and the search will run
    whatever code the model writes. See the warning in the README.
    """

    kind = "claude"

    def __init__(self, model: str = "claude-opus-5", effort: str = "low") -> None:
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise SystemExit(
                "The claude policy needs the Anthropic SDK: pip install anthropic"
            ) from exc

        self.model = model
        self.name = f"Claude ({model})"
        self.effort = effort
        self._anthropic = anthropic
        # Resolves ANTHROPIC_API_KEY, then ANTHROPIC_AUTH_TOKEN, then an
        # `ant auth login` profile - so an unset key is not necessarily an error.
        self.client = anthropic.Anthropic()
        self.calls = 0
        self.tokens = 0

    def propose(
        self, task: Task, data: dict, n: int, reflections: list[str]
    ) -> list[Proposal]:
        notes = ""
        if reflections:
            joined = "\n".join(f"- {r.split('|')[0].strip()}" for r in reflections)
            notes = (
                "\n\nNotes you wrote after earlier attempts failed. Do not repeat "
                f"those mistakes:\n{joined}"
            )
        prompt = (
            f"{task.render(data)}{notes}\n\n"
            f"Propose exactly {n} distinct next actions.\n{task.action_schema()}"
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,
                system=SYSTEM,
                output_config={"effort": self.effort},
                messages=[{"role": "user", "content": prompt}],
            )
        except self._anthropic.APIStatusError as exc:
            raise SystemExit(f"Claude request failed: {exc}") from exc
        except self._anthropic.APIConnectionError as exc:
            raise SystemExit(f"Could not reach the Claude API: {exc}") from exc

        self.calls += 1
        self.tokens += response.usage.input_tokens + response.usage.output_tokens

        if response.stop_reason == "refusal":
            return []

        text = "".join(b.text for b in response.content if b.type == "text")
        return self._parse(task, text, n)

    def _parse(self, task: Task, text: str, n: int) -> list[Proposal]:
        """Turn the reply into proposals, dropping anything malformed.

        A policy that occasionally returns nothing usable is normal; the search
        loop treats an empty expansion as a dead end rather than a crash.
        """
        payload = _first_json_object(text)
        if not payload:
            return []
        out: list[Proposal] = []
        for item in payload.get("candidates", [])[:n]:
            try:
                action = task.parse_action(item)
            except (KeyError, ValueError, TypeError):
                continue
            try:
                self_eval = min(max(float(item.get("self_eval", 0.5)), 0.0), 1.0)
            except (TypeError, ValueError):
                self_eval = 0.5
            out.append(
                Proposal(
                    action=action,
                    self_eval=self_eval,
                    rationale=str(item.get("text", "")),
                    # Two samples agree when they name the same action.
                    signature=re.sub(r"\s+", " ", action.text.strip().lower()),
                )
            )
        return out

    def info(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "model": self.model,
            "effort": self.effort,
            "seed": None,
            "calls": self.calls,
            "tokens": self.tokens,
            "tokens_are_estimated": False,
        }


def _first_json_object(text: str) -> dict | None:
    """Pull the first JSON object out of a reply, fenced or not."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
        start = text.find("{", start + 1)
    return None


def build_policy(kind: str, seed: int, model: str) -> MockLLM | ClaudeLLM:
    """Construct the policy named on the command line."""
    if kind == "mock":
        return MockLLM(seed=seed)
    if kind == "claude":
        if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
            print(
                "note: no ANTHROPIC_API_KEY in the environment; the SDK will fall "
                "back to an `ant auth login` profile if one exists."
            )
        return ClaudeLLM(model=model)
    raise SystemExit(f"unknown policy {kind!r}: expected 'mock' or 'claude'")
