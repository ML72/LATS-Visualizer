"""
The two policies: a deterministic offline stand-in, and a real OpenAI call.

The design rule for the whole submission is that the default path must run with
**no API key and no network**. So :class:`MockLLM` is the default everywhere,
and it is honest about what it is: a seeded sampler over a bank of candidate
actions that each task defines for itself.

What is *not* mocked is the environment. The code really runs, the arithmetic
really evaluates, the retrieval really searches. Every reward in every trace
this package writes came out of a real execution - which is the part that
matters, because the reward is what LATS backpropagates.

:class:`OpenAILLM` swaps in a real model. It is selected with ``--llm openai``
and is never used unless you ask for it.
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
# The real model
# ---------------------------------------------------------------------------


SYSTEM = (
    "You are the policy inside a Language Agent Tree Search. You are given the "
    "current state of a partially solved task and you propose several *distinct* "
    "next actions, then grade each one yourself on how likely it is to lead to a "
    "correct solution. Your grade is a prior only - the environment will execute "
    "your action and overrule you. Reply with JSON and nothing else."
)


class OpenAILLM:
    """The same interface as :class:`MockLLM`, backed by a real model.

    Needs ``OPENAI_API_KEY``. ``OPENAI_BASE_URL`` points the SDK at a different
    endpoint - a compatible local server, or a gateway - in which case the key
    may not be needed at all.

    One request per expansion returns all ``n`` candidates, which keeps a full
    search down to a handful of calls. Reply parsing is deliberately lenient
    rather than schema-enforced, so ``--model`` is free to name anything the
    endpoint serves.

    Traces produced this way are *not* reproducible, and the search will run
    whatever code the model writes. See the warning in the README.
    """

    kind = "openai"
    #: Used when ``--model`` is not given.
    default_model = "gpt-5"

    def __init__(self, model: str | None = None, effort: str | None = "low") -> None:
        try:
            import openai
        except ImportError as exc:  # pragma: no cover - depends on the environment
            raise SystemExit(
                "The openai policy needs the OpenAI SDK: pip install openai"
            ) from exc

        self.model = model or self.default_model
        self.name = f"OpenAI ({self.model})"
        self.effort = effort
        self.calls = 0
        self.tokens = 0
        self._openai = openai
        # Resolves OPENAI_API_KEY and OPENAI_BASE_URL from the environment.
        try:
            self.client = openai.OpenAI()
        except openai.OpenAIError as exc:
            raise SystemExit(
                f"Could not construct the OpenAI client: {exc}\n"
                "Export OPENAI_API_KEY, or set OPENAI_BASE_URL to an endpoint "
                "that does not need one."
            ) from exc

    # -- the interface the search sees --------------------------------------

    def propose(
        self, task: Task, data: dict, n: int, reflections: list[str]
    ) -> list[Proposal]:
        text, tokens = self._complete(self._prompt(task, data, n, reflections))
        self.calls += 1
        self.tokens += tokens
        return self._parse(task, text, n, data)

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

    # -- the request --------------------------------------------------------

    def _complete(self, prompt: str) -> tuple[str, int]:
        """Send one prompt. Returns the reply text and the tokens it used."""
        request: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "max_completion_tokens": 8000,
        }
        # Only the reasoning models accept reasoning_effort. Rather than keep a
        # list of which ones do - it changes every few months - send it, and
        # drop it for good the first time an endpoint says no.
        if self.effort:
            request["reasoning_effort"] = self.effort

        try:
            response = self._create(request)
        except self._openai.APIStatusError as exc:
            if self.effort and "reasoning_effort" in str(exc):
                self.effort = None
                request.pop("reasoning_effort")
                response = self._create(request)
            else:
                raise SystemExit(f"OpenAI request failed: {exc}") from exc

        usage = response.usage
        tokens = usage.total_tokens if usage else 0

        choice = response.choices[0] if response.choices else None
        if choice is None or getattr(choice.message, "refusal", None):
            return "", tokens
        return choice.message.content or "", tokens

    def _create(self, request: dict[str, Any]):
        try:
            return self.client.chat.completions.create(**request)
        except self._openai.APIConnectionError as exc:
            raise SystemExit(f"Could not reach the OpenAI API: {exc}") from exc

    # -- turning a reply into moves -----------------------------------------

    @staticmethod
    def _prompt(task: Task, data: dict, n: int, reflections: list[str]) -> str:
        notes = ""
        if reflections:
            joined = "\n".join(f"- {r.split('|')[0].strip()}" for r in reflections)
            notes = (
                "\n\nNotes you wrote after earlier attempts failed. Do not repeat "
                f"those mistakes:\n{joined}"
            )
        return (
            f"{task.render(data)}{notes}\n\n"
            f"Propose exactly {n} distinct next actions.\n{task.action_schema()}"
        )

    def _parse(
        self, task: Task, text: str, n: int, data: dict
    ) -> list[Proposal]:
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
                action = task.parse_action(item, data)
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


#: Everything ``--llm`` accepts, in the order it is offered on the command line.
POLICIES = ("mock", "openai")


def build_policy(
    kind: str, seed: int, model: str | None = None
) -> MockLLM | OpenAILLM:
    """Construct the policy named on the command line."""
    if kind == "mock":
        return MockLLM(seed=seed)

    if kind == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            if os.environ.get("OPENAI_BASE_URL"):
                print(
                    "note: no OPENAI_API_KEY in the environment; using "
                    "OPENAI_BASE_URL, which is assumed not to need one."
                )
            else:
                raise SystemExit(
                    "The openai policy needs an API key. Export OPENAI_API_KEY:\n"
                    "    export OPENAI_API_KEY=sk-...       # macOS / Linux\n"
                    "    $env:OPENAI_API_KEY = 'sk-...'     # PowerShell\n"
                    "Or set OPENAI_BASE_URL to a compatible endpoint that does "
                    "not need one."
                )
        return OpenAILLM(model=model)

    raise SystemExit(
        f"unknown policy {kind!r}: expected one of {', '.join(POLICIES)}"
    )
