"""
Multi-hop question answering over a small offline corpus.

A ReAct-shaped environment: the agent issues ``search[term]``, reads what comes
back, and eventually commits with ``finish[answer]``. The reward is a match
against a gold answer - see :func:`matches_gold` for how loose that is.

Two things about this task are worth saying out loud in class.

**The reward is an oracle.** Nothing in the environment can tell a good answer
from a bad one; a stored gold string does. Zhou et al. use the same oracle
signal on HotPotQA - and so do the ReAct and Reflexion baselines they compare
against - but it is a real caveat, not a footnote.

**The distractor is the lesson.** The question asks which venue published the
paper that *introduced* the algorithm LATS adapts. The corpus also contains a
2006 paper about the *selection rule* that algorithm uses, published somewhere
else. The mock policy has a recency bias, so it is strongly tempted to answer
with whichever venue it read last. Search is what recovers from that.
"""

from __future__ import annotations

import math
import random
import re
import string
from typing import Any

from ..types import Action, Observation, Proposal
from .base import Task

#: A miniature related-work wiki. Every fact here is checkable against the
#: papers named in it.
CORPUS: list[dict[str, str]] = [
    {
        "title": "Language Agent Tree Search",
        "body": (
            "Language Agent Tree Search, or LATS, was presented at ICML in 2024 by "
            "Zhou, Yan, Shlapentokh-Rothman, Wang and Wang. It adapts Monte Carlo "
            "Tree Search to language agents, adding a language model value "
            "function, real environment feedback, and a reflection step."
        ),
    },
    {
        "title": "Monte Carlo Tree Search",
        "body": (
            "Monte Carlo Tree Search is a planning algorithm that grows a tree of "
            "simulated futures. Remi Coulom introduced it, presenting Efficient "
            "Selectivity and Backup Operators for Monte-Carlo Tree Search at "
            "Computers and Games in 2006."
        ),
    },
    {
        "title": "UCT",
        "body": (
            "UCT is the selection rule most Monte Carlo Tree Search "
            "implementations use. Kocsis and Szepesvari derived it from the UCB1 "
            "bandit algorithm and presented it at ECML in 2006."
        ),
    },
    {
        "title": "AlphaGo",
        "body": (
            "AlphaGo paired Monte Carlo Tree Search with a policy network and a "
            "value network. Silver and colleagues published it in Nature in 2016."
        ),
    },
    {
        "title": "Tree of Thoughts",
        "body": (
            "Tree of Thoughts searches over intermediate reasoning steps. Yao and "
            "colleagues presented it at NeurIPS in 2023. It has no environment, so "
            "it scores states by self-evaluation alone."
        ),
    },
    {
        "title": "Reflexion",
        "body": (
            "Reflexion turns a failed attempt into a written note that is placed "
            "in the next prompt. Shinn and colleagues presented it at NeurIPS in "
            "2023. It reflects, but it does not search."
        ),
    },
    {
        "title": "Reasoning via Planning",
        "body": (
            "Reasoning via Planning, or RAP, runs Monte Carlo Tree Search using "
            "the language model itself as the world model. Hao and colleagues "
            "presented it at EMNLP in 2023."
        ),
    },
    {
        "title": "ReAct",
        "body": (
            "ReAct interleaves reasoning traces with actions taken in an "
            "environment. Yao and colleagues presented it at ICLR in 2023."
        ),
    },
]

QUESTION = (
    "LATS adapts an existing tree search algorithm. At which venue, and in "
    "which year, was the paper that introduced that algorithm presented?"
)

GOLD = "Computers and Games 2006"

#: Search terms the offline policy may issue. A real model would write its own;
#: this keeps the trace reproducible.
TERMS = [t["title"] for t in CORPUS]

#: Matches "... at ICML in 2024", "... in Nature in 2016". Non-greedy so the
#: venue stops at the year rather than swallowing the sentence.
_VENUE_YEAR = re.compile(r"\b(?:at|in) ([A-Z][A-Za-z][A-Za-z ]*?) in (\d{4})\b")

_PUNCT = str.maketrans("", "", string.punctuation)


def normalise(text: str) -> str:
    """Lower-case, drop punctuation and articles, collapse whitespace.

    The standard exact-match normalisation used by HotPotQA-style benchmarks.
    """
    words = text.lower().translate(_PUNCT).split()
    return " ".join(w for w in words if w not in {"a", "an", "the"})


#: Words that carry no venue information, so an answer is not marked wrong for
#: spelling them differently.
_FILLER = {"and", "of", "at", "in", "on", "for", "the", "a", "an"}


def matches_gold(answer: str) -> bool:
    """Is this the gold answer, allowing for how a model chooses to write it?

    Strict string equality is the benchmark convention, and it fails a correct
    answer over a comma: "Computers and Games (CG), 2006" and "Computers and
    Games 2006" name the same venue and year. Requiring every content word of
    the gold answer to appear accepts the extra qualifier while still rejecting
    a different venue - "ECML/PKDD 2006" contains neither "computers" nor
    "games", and an answer that drops the year is missing "2006".

    It is still an oracle, and it can still be fooled by an answer that negates
    itself. It is a teaching environment, not a benchmark harness.
    """
    def content(text: str) -> set[str]:
        return {w for w in normalise(text).split() if w not in _FILLER}

    return content(GOLD) <= content(answer)


def retrieve(query: str) -> dict[str, str] | None:
    """Return the single best-matching document, or None.

    Token overlap, which is all this needs to be: the point of the task is the
    search over trajectories, not the search over documents.
    """
    q = set(normalise(query).split())
    if not q:
        return None
    best, best_score = None, 0.0
    for doc in CORPUS:
        title = set(normalise(doc["title"]).split())
        body = set(normalise(doc["body"]).split())
        score = 2.0 * len(q & title) / len(q | title) + 0.5 * len(q & body) / len(q)
        if score > best_score:
            best, best_score = doc, score
    return best if best_score > 0.2 else None


class MultiHopQATask(Task):
    """Answer a two-hop question by retrieving from a small local corpus."""

    id = "multihop-qa"
    family = "qa"
    title = "Two-hop question answering"
    prompt = QUESTION
    reward_desc = "1 if the answer names the gold venue and year, else 0 (an oracle signal)"

    TEMPERATURE = 0.28

    def __init__(self) -> None:
        self.context = {
            "Tools": ["search[term]", "finish[answer]"],
            "Corpus": [doc["title"] for doc in CORPUS],
        }

    def defaults(self) -> dict[str, Any]:
        return {"lam": 0.5, "simulate": True, "max_depth": 4, "iterations": 8, "n": 3}

    # -- environment --------------------------------------------------------

    def root_data(self) -> dict:
        return {"trail": [], "searched": [], "retrieved": ""}

    def step(self, data: dict, action: Action) -> tuple[dict, Observation]:
        kind = action.payload["kind"]

        if kind == "finish":
            answer = action.payload["answer"]
            correct = matches_gold(answer)
            new = dict(data)
            new["trail"] = list(data["trail"]) + [f"finish[{answer}]"]
            new["answer"] = answer
            return new, Observation(
                text=(
                    f"Answered {answer!r}. "
                    + ("That is the gold answer."
                       if correct else f"The gold answer is {GOLD!r}.")
                ),
                detail={"answer": answer, "gold": GOLD, "exact_match": correct},
                terminal=True,
                reward=1.0 if correct else 0.0,
            )

        term = action.payload["term"]
        doc = retrieve(term)
        text = (
            f"{doc['title']}: {doc['body']}" if doc else f"No document matches {term!r}."
        )
        new = {
            "trail": list(data["trail"]) + [f"search[{term}]"],
            "searched": list(data["searched"]) + [term],
            "retrieved": (data["retrieved"] + "\n" + text).strip(),
        }
        return new, Observation(
            text=text,
            detail={"query": term, "document": doc["title"] if doc else None},
            terminal=False,
            reward=None,
        )

    # -- offline policy -----------------------------------------------------

    def _answer_candidates(self, data: dict) -> list[tuple[str, float]]:
        """Every "<venue> <year>" the agent has actually read, newest first.

        The recency weighting is the policy's bias, and it is the thing the
        search has to overcome: the last venue read is not the right one.
        """
        matches = list(_VENUE_YEAR.finditer(data["retrieved"]))
        seen: dict[str, int] = {}
        for position, m in enumerate(matches):
            seen[f"{m.group(1).strip()} {m.group(2)}"] = position
        if not seen:
            return []
        newest = max(seen.values())
        return [
            (answer, 0.55 + 0.30 * (1.0 if position == newest else 0.35))
            for answer, position in seen.items()
        ]

    def mock_propose(
        self, data: dict, rng: random.Random, n: int, reflections: list[str]
    ) -> list[Proposal]:
        retrieved = data["retrieved"].lower()
        rejected = {r.split("|")[-1].strip() for r in reflections if "|" in r}

        options: list[tuple[Proposal, float]] = []

        for term in TERMS:
            score = 0.40
            if term.lower() in retrieved:
                score += 0.25  # the term was named by something already read
            if term in data["searched"]:
                score -= 0.30
            options.append(
                (
                    Proposal(
                        action=Action(
                            label=f"search[{term}]",
                            text=f"search[{term}]",
                            payload={"kind": "search", "term": term},
                        ),
                        self_eval=round(min(max(score, 0.05), 0.95), 3),
                        rationale=f"look up {term}",
                        signature=f"search:{term}",
                    ),
                    score,
                )
            )

        for answer, score in self._answer_candidates(data):
            if answer in rejected:
                score -= 0.45
            options.append(
                (
                    Proposal(
                        action=Action(
                            label=f"finish[{answer}]",
                            text=f"finish[{answer}]",
                            payload={"kind": "finish", "answer": answer},
                        ),
                        self_eval=round(min(max(score, 0.05), 0.95), 3),
                        rationale=f"commit to {answer}",
                        signature=f"finish:{answer}",
                    ),
                    score,
                )
            )

        if not options:
            return []
        top = max(s for _, s in options)
        weights = [math.exp((s - top) / self.TEMPERATURE) for _, s in options]
        return [
            rng.choices([p for p, _ in options], weights=weights, k=1)[0]
            for _ in range(n)
        ]

    # -- online policy ------------------------------------------------------

    def render(self, data: dict) -> str:
        trail = "\n".join(f"  {t}" for t in data["trail"]) or "  (nothing yet)"
        return (
            f"{QUESTION}\n\nActions so far:\n{trail}\n\n"
            f"What you have read:\n{data['retrieved'] or '  (nothing yet)'}"
        )

    def action_schema(self) -> str:
        return (
            'Return JSON: {"candidates": [{"action": "search[term]" or '
            '"finish[answer]", "self_eval": 0.0-1.0}]}. Search before you '
            "finish; the answer must name a venue and a year."
        )

    def parse_action(self, obj: dict, data: dict) -> Action:
        # ``data`` is unused: a tool call means the same at any node.
        raw = str(obj["action"]).strip()
        match = re.match(r"(search|finish)\[(.*)\]\s*$", raw, re.IGNORECASE)
        if not match:
            raise ValueError(f"not a tool call: {raw!r}")
        kind, arg = match.group(1).lower(), match.group(2).strip()
        payload = {"kind": kind, "term": arg} if kind == "search" else {
            "kind": kind,
            "answer": arg,
        }
        return Action(label=f"{kind}[{arg}]"[:40], text=raw, payload=payload)

    # -- reflection ---------------------------------------------------------

    def reflection_for(self, node_data: dict, observation: Observation | None) -> str:
        answer = (observation.detail or {}).get("answer") if observation else None
        if not answer:
            trail = " then ".join(node_data.get("trail", [])) or "nothing"
            return f"That branch ran {trail} and never committed to an answer."
        # Name the document the wrong answer came from - that is the difference
        # between "wrong" and "wrong for this reason".
        source = next(
            (d["title"] for d in CORPUS if answer.split()[0] in d["body"]), None
        )
        note = f"{answer} is not the gold answer."
        if source:
            note += (
                f" It was read from the {source} entry, which describes a "
                "different paper from the one the question asks about."
            )
        return f"{note} | finish:{answer}"
