"""
Game of 24: combine four numbers with + - * / to make exactly 24.

The classic Tree-of-Thoughts benchmark, and the cleanest possible environment -
arithmetic either lands on 24 or it does not, so the reward needs no oracle and
no judge. Zhou et al. use lambda = 0.5 here, and this task keeps that.

What makes it a good LATS example is that a *locally* attractive move is often
globally fatal. The policy in this file scores a move by how tidy its result
looks: whole numbers, small magnitudes, factors of 24. That is a plausible
heuristic and it is frequently wrong, which is exactly the situation the value
function plus backpropagation is there to repair.
"""

from __future__ import annotations

import math
import random
from fractions import Fraction
from itertools import combinations
from typing import Any

from ..types import Action, Observation, Proposal
from .base import Task

TARGET = 24

OPS: list[tuple[str, Any]] = [
    ("+", lambda x, y: x + y),
    ("-", lambda x, y: x - y),
    ("*", lambda x, y: x * y),
    ("/", lambda x, y: None if y == 0 else x / y),
]


def _fmt(x: Fraction) -> str:
    """Render a Fraction the way a person would write it."""
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def legal_moves(numbers: list[Fraction]) -> list[dict]:
    """Every distinct (pair, operator) move available from ``numbers``.

    Subtraction and division are tried both ways round; addition and
    multiplication are not, because ``a + b`` and ``b + a`` are the same move.
    Duplicate results are collapsed so the branching factor reflects distinct
    *states*, not distinct spellings.
    """
    seen: set[tuple[str, tuple[str, ...]]] = set()
    moves: list[dict] = []
    for i, j in combinations(range(len(numbers)), 2):
        a, b = numbers[i], numbers[j]
        rest = [numbers[k] for k in range(len(numbers)) if k not in (i, j)]
        for symbol, fn in OPS:
            for x, y in ((a, b), (b, a)):
                if symbol in "+*" and (x, y) != (a, b):
                    continue
                result = fn(x, y)
                if result is None:
                    continue
                remaining = sorted(rest + [result], key=lambda v: (v.denominator, v))
                key = (symbol, tuple(_fmt(v) for v in remaining))
                if key in seen:
                    continue
                seen.add(key)
                moves.append(
                    {
                        "expr": f"{_fmt(x)} {symbol} {_fmt(y)} = {_fmt(result)}",
                        "label": f"{_fmt(x)} {symbol} {_fmt(y)}",
                        "result": result,
                        "remaining": remaining,
                    }
                )
    return moves


def tidiness(result: Fraction, remaining: list[Fraction]) -> float:
    """How promising a move *looks* - the mock policy's whole worldview.

    Deliberately shallow. It rewards whole numbers, small magnitudes and
    factors of 24, and it never looks more than one step ahead. Compare it
    against the objective reward in any generated trace: the gap between the
    two is the reason LATS backpropagates at all.
    """
    score = 0.45
    if result.denominator != 1:
        score -= 0.30
    else:
        score += 0.15
        value = int(result)
        if value > 0 and (TARGET % value == 0 or value % TARGET == 0):
            score += 0.20
        if 0 < value <= TARGET:
            score += 0.10
    if result < 0:
        score -= 0.20
    if abs(result) > 100:
        score -= 0.15
    if len(remaining) == 1 and remaining[0] == TARGET:
        score = 0.98
    return min(max(score, 0.05), 0.98)


class Game24Task(Task):
    """Reach 24 from four numbers, using each exactly once."""

    id = "game_of_24"
    family = "game"
    title = "Game of 24"
    reward_desc = "1 if the final value is exactly 24 and every number was used once, else 0"

    #: Solvable exactly one interesting way - (11 - 5) * (8 / 2) - and full of
    #: plausible dead ends on the way there. Chosen by sweeping puzzles and
    #: seeds for one where the search has to back up before it succeeds, and
    #: where turning the exploration weight off makes it fail outright.
    NUMBERS = [2, 5, 8, 11]

    #: Softmax temperature for the mock sampler. Low enough that the same
    #: strong move gets drawn more than once - which is what makes the
    #: self-consistency term SC(s) carry any information at all.
    TEMPERATURE = 0.30

    def __init__(self) -> None:
        self.prompt = (
            f"Use {', '.join(str(n) for n in self.NUMBERS)} exactly once each, "
            f"with + - * / and any bracketing, to make {TARGET}."
        )
        self.context = {"Numbers": [str(n) for n in self.NUMBERS]}

    def defaults(self) -> dict[str, Any]:
        # n = 5 and w = 1 are the paper's own defaults, and Game of 24 is one
        # of the tasks it uses them on. Twelve iterations is well short of the
        # paper's budget; it is what fits on a screen.
        return {"lam": 0.5, "simulate": True, "max_depth": 3, "iterations": 12, "n": 5, "seed": 7}

    # -- environment --------------------------------------------------------

    def root_data(self) -> dict:
        return {
            "numbers": [str(Fraction(n)) for n in self.NUMBERS],
            "steps": [],
        }

    @staticmethod
    def _nums(data: dict) -> list[Fraction]:
        return [Fraction(s) for s in data["numbers"]]

    def step(self, data: dict, action: Action) -> tuple[dict, Observation]:
        remaining = [Fraction(s) for s in action.payload["remaining"]]
        steps = list(data["steps"]) + [action.payload["expr"]]
        new = {"numbers": [str(v) for v in remaining], "steps": steps}

        if len(remaining) > 1:
            left = ", ".join(_fmt(v) for v in remaining)
            return new, Observation(
                text=f"{action.payload['expr']}. Left to combine: {left}.",
                detail={"steps": steps, "remaining": [_fmt(v) for v in remaining]},
                terminal=False,
                reward=None,
            )

        final = remaining[0]
        hit = final == TARGET
        return new, Observation(
            text=(
                f"{action.payload['expr']}. Final value {_fmt(final)} - "
                + ("that is 24." if hit else "that is not 24.")
            ),
            detail={
                "steps": steps,
                "final": _fmt(final),
                "target": TARGET,
                "expression": " ; ".join(steps),
            },
            terminal=True,
            reward=1.0 if hit else 0.0,
        )

    # -- offline policy -----------------------------------------------------

    def mock_propose(
        self, data: dict, rng: random.Random, n: int, reflections: list[str]
    ) -> list[Proposal]:
        numbers = self._nums(data)
        if len(numbers) < 2:
            return []
        moves = legal_moves(numbers)
        if not moves:
            return []

        # Anything a reflection has already ruled out is pushed down, which is
        # how a verbal note becomes a change in behaviour rather than a comment.
        blocked = {line.strip() for r in reflections for line in r.split("|")}
        scores = [tidiness(m["result"], m["remaining"]) for m in moves]
        scores = [
            s * (0.25 if m["expr"] in blocked else 1.0) for s, m in zip(scores, moves)
        ]

        top = max(scores)
        weights = [math.exp((s - top) / self.TEMPERATURE) for s in scores]

        out: list[Proposal] = []
        for _ in range(n):
            idx = rng.choices(range(len(moves)), weights=weights, k=1)[0]
            move = moves[idx]
            out.append(
                Proposal(
                    action=Action(
                        label=move["label"],
                        text=move["expr"],
                        payload={
                            "expr": move["expr"],
                            "remaining": [str(v) for v in move["remaining"]],
                        },
                    ),
                    self_eval=round(scores[idx], 3),
                    rationale=(
                        f"leaves {', '.join(_fmt(v) for v in move['remaining'])}"
                    ),
                    # Two samples agree when they leave the same numbers behind.
                    signature=",".join(_fmt(v) for v in move["remaining"]),
                )
            )
        return out

    # -- online policy ------------------------------------------------------

    def render(self, data: dict) -> str:
        done = "\n".join(f"  {s}" for s in data["steps"]) or "  (nothing yet)"
        left = ", ".join(_fmt(v) for v in self._nums(data))
        return f"{self.prompt}\n\nSteps so far:\n{done}\n\nNumbers left: {left}"

    def action_schema(self) -> str:
        return (
            'Return JSON: {"candidates": [{"expr": "a op b = c", "self_eval": '
            "0.0-1.0}]}, one arithmetic step per candidate, using two of the "
            "numbers that are left."
        )

    def parse_action(self, obj: dict) -> Action:
        expr = str(obj["expr"]).strip()
        return Action(label=expr.split("=")[0].strip(), text=expr, payload={"raw": expr})

    # -- reflection ---------------------------------------------------------

    def reflection_for(self, node_data: dict, observation: Observation | None) -> str:
        steps = node_data.get("steps") or []
        if not steps:
            return "That branch produced no arithmetic at all."
        final = (observation.detail or {}).get("final") if observation else None
        trail = " then ".join(steps)
        # The pipe-separated tail is what mock_propose reads back: the exact
        # first move to avoid next time.
        return (
            f"{trail} ends at {final}, not {TARGET}. "
            f"Do not open with that step again. | {steps[0]}"
        )
