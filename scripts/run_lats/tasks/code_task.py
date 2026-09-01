"""
The programming task: write ``merge`` against a visible test suite.

This is the worked example from Part 6 of the explainer video, and the trap is
deliberate. The obvious one-pass solution is a reasonable guess, it passes
three of the five tests, and **it cannot be patched into correctness** - every
refinement of it stays at three. The fix is a different approach, one level up
the tree. That is the whole argument for search in one example.

Following the paper's programming setting, every node here is already a
complete program, so simulation is skipped and the reward backpropagated is the
fraction of tests that pass. The tests are run for real, in a subprocess - see
``sandbox.py``. None of the pass counts in this file are asserted anywhere;
they are whatever the interpreter says they are.
"""

from __future__ import annotations

import ast
import random
import re
from typing import Any

from ..types import Action, Observation, Proposal
from .base import Task
from .sandbox import run_tests

PROMPT = (
    "Write merge(intervals) -> list[list[int]] that merges every pair of "
    "overlapping or touching intervals and returns the result sorted by start."
)

#: The visible test suite. The last two arrive out of order; that is the
#: difficulty, sitting in plain sight.
TESTS = [
    {"call": "merge([[1,3],[2,6]])", "expect": "[[1,6]]"},
    {"call": "merge([[1,4],[5,6]])", "expect": "[[1,4],[5,6]]"},
    {"call": "merge([[1,4],[4,5]])", "expect": "[[1,5]]"},
    {"call": "merge([[3,5],[1,2]])", "expect": "[[1,2],[3,5]]"},
    {"call": "merge([[8,10],[1,3],[2,6]])", "expect": "[[1,6],[8,10]]"},
]

# ---------------------------------------------------------------------------
# The candidate bank the offline policy draws from.
#
# ``weight`` is how often the sampler picks a candidate - a stand-in for the
# model's own likelihood - and ``self_eval`` is the score the model would give
# its own idea before running anything. Both are fiction; that is what makes
# this a *mock* policy. Everything downstream of them is real.
# ---------------------------------------------------------------------------

APPROACHES = [
    {
        "key": "A",
        "label": "one-pass merge",
        "text": "Sweep the list as given and merge each interval into the previous one.",
        "self_eval": 0.70,
        "weight": 0.45,
        "code": """def merge(iv):
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out""",
    },
    {
        "key": "B",
        "label": "sort, then sweep",
        "text": "Sort by start first, then merge each interval into the previous one.",
        "self_eval": 0.62,
        "weight": 0.35,
        "code": """def merge(iv):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a < out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out""",
    },
    {
        "key": "C",
        "label": "interval tree",
        "text": "Insert every interval into a binary tree keyed by start, then walk it in order.",
        "self_eval": 0.35,
        "weight": 0.20,
        "code": """class _N:
    def __init__(self, lo, hi):
        self.lo, self.hi, self.l, self.r = lo, hi, None, None

def merge(iv):
    root = None
    for a, b in iv:
        n = _N(a, b)
        if root is None:
            root = n
            continue
        cur = root
        while True:
            nxt = "l" if a < cur.lo else "r"
            if getattr(cur, nxt) is None:
                setattr(cur, nxt, n)
                break
            cur = getattr(cur, nxt)
    out = []

    def walk(n):
        if n is None:
            return
        walk(n.l)
        out.append([n.lo, n.hi])
        walk(n.r)

    walk(root)
    return out""",
    },
]

#: Refinements, keyed by the approach they refine. The three under A are the
#: point of the example: each is a sensible-looking patch, and none of them
#: gets past three of five, because the approach itself is the bug.
REFINEMENTS: dict[str, list[dict[str, Any]]] = {
    "A": [
        {
            "label": "scan all, not just last",
            "text": "Compare each interval against every interval already emitted, not only the most recent one.",
            "self_eval": 0.78,
            "weight": 0.40,
            "code": """def merge(iv):
    out = []
    for a, b in iv:
        for cur in out:
            if a <= cur[1] and b >= cur[0]:
                cur[0] = min(cur[0], a)
                cur[1] = max(cur[1], b)
                break
        else:
            out.append([a, b])
    return out""",
        },
        {
            "label": "guard the lower bound",
            "text": "Only merge when the new start also falls at or after the previous start.",
            "self_eval": 0.66,
            "weight": 0.35,
            "code": """def merge(iv):
    out = []
    for a, b in iv:
        if out and out[-1][0] <= a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out""",
        },
        {
            "label": "sort the output",
            "text": "Keep the one-pass sweep and sort the result before returning it.",
            "self_eval": 0.59,
            "weight": 0.25,
            "code": """def merge(iv):
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return sorted(out)""",
        },
    ],
    "B": [
        {
            "label": "merge on touch too",
            "text": "Treat intervals that only touch at an endpoint as overlapping: use <= instead of <.",
            "self_eval": 0.64,
            "weight": 0.34,
            "code": """def merge(iv):
    iv = sorted(iv)
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out""",
        },
        {
            "label": "widen both ends",
            "text": "Sort by start, and when merging take the min of the starts and the max of the ends.",
            "self_eval": 0.71,
            "weight": 0.36,
            "code": """def merge(iv):
    iv = sorted(iv, key=lambda p: p[0])
    out = []
    for a, b in iv:
        if out and a < out[-1][1]:
            out[-1] = [min(out[-1][0], a), max(out[-1][1], b)]
        else:
            out.append([a, b])
    return out""",
        },
        {
            "label": "sweep in reverse",
            "text": "Sort descending and merge backwards, extending the start of the open interval.",
            "self_eval": 0.48,
            "weight": 0.30,
            "code": """def merge(iv):
    out = []
    for a, b in sorted(iv, reverse=True):
        if out and b >= out[-1][0]:
            out[-1][0] = min(out[-1][0], a)
        else:
            out.append([a, b])
    return out""",
        },
    ],
    "C": [
        {
            "label": "key on midpoint",
            "text": "Order the intervals by midpoint instead of by start before walking them.",
            "self_eval": 0.44,
            "weight": 0.5,
            "code": """def merge(iv):
    return [list(p) for p in sorted(iv, key=lambda p: (p[0] + p[1]) / 2)]""",
        },
        {
            "label": "merge on insert",
            "text": "Widen a node in place whenever the interval being inserted overlaps it.",
            "self_eval": 0.52,
            "weight": 0.5,
            "code": """def merge(iv):
    out = []
    for a, b in iv:
        for cur in out:
            if a <= cur[1] and b >= cur[0]:
                cur[1] = max(cur[1], b)
                break
        else:
            out.append([a, b])
    return out""",
        },
    ],
}


class MergeIntervalsTask(Task):
    """Write ``merge`` against five visible tests. Reward = fraction passing."""

    id = "merge_intervals"
    family = "programming"
    title = "Write merge_intervals against a visible test suite"
    prompt = PROMPT
    reward_desc = "fraction of the five unit tests that pass, measured by running them"

    def __init__(self) -> None:
        self.context = {
            "Test suite": [f"{t['call']}  ->  {t['expect']}" for t in TESTS],
        }

    def defaults(self) -> dict[str, Any]:
        # The paper uses lambda = 0.8 for programming, and skips simulation
        # there because every node is already a complete program.
        return {"lam": 0.8, "simulate": False, "max_depth": 2, "iterations": 6}

    # -- environment --------------------------------------------------------

    def root_data(self) -> dict:
        return {"approach": None, "code": None}

    def step(self, data: dict, action: Action) -> tuple[dict, Observation]:
        code = action.payload["code"]
        report = run_tests(code, TESTS)
        new = {
            "approach": action.payload.get("approach") or data.get("approach"),
            "code": code,
            "report": report,
        }
        if report["error"]:
            text = f"The program did not run: {report['error']}"
        else:
            text = f"{report['passed']} of {report['total']} tests pass."
        obs = Observation(
            text=text,
            detail={
                "code": code,
                "results": report["results"],
                "passed": report["passed"],
                "total": report["total"],
                "error": report["error"],
            },
            # Every node is a complete program, so every node is scorable; only
            # a perfect score ends the search.
            terminal=report["fraction"] >= 1.0,
            reward=report["fraction"],
        )
        return new, obs

    # -- offline policy -----------------------------------------------------

    def _bank(self, data: dict) -> list[dict]:
        if data.get("approach") is None:
            return APPROACHES
        return REFINEMENTS.get(data["approach"], [])

    def mock_propose(
        self, data: dict, rng: random.Random, n: int, reflections: list[str]
    ) -> list[Proposal]:
        bank = self._bank(data)
        if not bank:
            return []
        # Reflection is not decoration: a note that names ordering pushes the
        # sampler towards candidates whose text mentions sorting, which is a
        # crude stand-in for what a real model does once the note is in its
        # context window.
        hint = any("order" in r.lower() or "sort" in r.lower() for r in reflections)
        weights = [
            c["weight"] * (3.0 if hint and "sort" in c["text"].lower() else 1.0)
            for c in bank
        ]

        out: list[Proposal] = []
        for _ in range(n):
            cand = rng.choices(bank, weights=weights, k=1)[0]
            approach = cand.get("key") or data.get("approach")
            out.append(
                Proposal(
                    action=Action(
                        label=cand["label"],
                        text=cand["text"],
                        payload={"code": cand["code"], "approach": approach},
                    ),
                    self_eval=cand["self_eval"],
                    rationale=cand["text"],
                    signature=f"{approach}:{cand['label']}",
                )
            )
        return out

    # -- online policy ------------------------------------------------------

    def render(self, data: dict) -> str:
        tests = "\n".join(f"  assert {t['call']} == {t['expect']}" for t in TESTS)
        if data.get("code") is None:
            return f"{PROMPT}\n\nTests:\n{tests}\n\nNo program has been written yet."
        report = data.get("report", {})
        fails = [r for r in report.get("results", []) if not r["passed"]]
        detail = "\n".join(
            f"  {r['call']} returned {r['got']}, expected {r['expect']}" for r in fails
        )
        return (
            f"{PROMPT}\n\nTests:\n{tests}\n\nCurrent program:\n{data['code']}\n\n"
            f"It passes {report.get('passed')} of {report.get('total')}.\n"
            f"Failing:\n{detail or '  (none)'}"
        )

    def action_schema(self) -> str:
        return (
            'Return JSON: {"candidates": [{"label": "at most five words", '
            '"text": "one sentence on the idea", "code": "a complete Python '
            'program defining merge(iv)", "self_eval": 0.0-1.0}]}. Each '
            "candidate must be a whole program, not a patch."
        )

    def parse_action(self, obj: dict) -> Action:
        label = str(obj.get("label", "candidate"))[:32]
        return Action(
            label=label,
            text=str(obj.get("text", "")),
            payload={"code": str(obj["code"]), "approach": label},
        )

    # -- reflection ---------------------------------------------------------

    def reflection_for(self, node_data: dict, observation: Observation | None) -> str:
        """Write the note from the test runner's output, not from a template.

        The interesting case is when unsorted input is exactly what separates
        the failures from the passes. That is a fact about the *data*, and
        noticing it is what turns a score into a lesson.
        """
        if observation is None or not observation.detail.get("results"):
            return "That attempt produced no test output at all."
        results = observation.detail["results"]
        failed = [r for r in results if not r["passed"]]
        if not failed:
            return "That attempt passed everything."

        first = failed[0]
        note = (
            f"{first['call']} returned {first['got']}, expected {first['expect']}. "
            f"{len(failed)} of {len(results)} cases fail."
        )
        if _unsorted_input_separates_failures(results):
            note += (
                " Every failing case receives its intervals out of order and "
                "every passing case receives them sorted, so the approach is "
                "assuming an ordering the input does not guarantee. Sort first."
            )
        return note


def _unsorted_input_separates_failures(results: list[dict]) -> bool:
    """True when unsorted input cleanly separates the failures from the passes.

    Read off the test calls themselves, so it stays honest if the suite changes.
    """

    def starts(call: str) -> list[int]:
        match = re.search(r"merge\((\[.*\])\)", call)
        if not match:
            return []
        try:
            return [iv[0] for iv in ast.literal_eval(match.group(1))]
        except (ValueError, SyntaxError, TypeError, IndexError):
            return []

    fails = [starts(r["call"]) for r in results if not r["passed"]]
    passes = [starts(r["call"]) for r in results if r["passed"]]
    if not fails or not passes:
        return False
    return all(s != sorted(s) for s in fails) and all(s == sorted(s) for s in passes)
