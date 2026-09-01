"""
The six operations of Language Agent Tree Search.

    selection -> expansion -> evaluation -> simulation -> backpropagation -> reflection

Zhou, Yan, Shlapentokh-Rothman, Wang and Wang, *Language Agent Tree Search
Unifies Reasoning, Acting and Planning in Language Models*, ICML 2024
(arXiv:2310.04406). This file is a from-scratch reading of Algorithm 1; it
vendors nothing.

Two places where the paper has to be read carefully:

**The backup rule.** Section 4.2 prints it with subscripts that do not match
the pseudocode. Algorithm 1 and Section 3.2 carry the correct form, and that is
what :func:`backpropagate` implements::

    N(s) <- N(s) + 1
    V(s) <- ( V_old(s) * (N(s) - 1) + r ) / N(s)

**Simulation is not a random playout.** Classic MCTS rolls out at random; LATS
descends greedily by value, in the real environment, until it reaches a
terminal state. The randomness is replaced by the policy plus real execution.

Everything the search does is announced to a recorder, so a run can be replayed
frame by frame afterwards. The recorder is optional; the algorithm does not
depend on being watched.
"""

from __future__ import annotations

from math import log, sqrt
from typing import Any

from .tasks.base import Task
from .types import Config, Node, Observation, Proposal


def uct(child: Node, parent: Node, w: float) -> float:
    """``UCT(s) = V(s) + w * sqrt( ln N(p) / N(s) )``.

    ``N`` is initialised to 1 rather than 0, so this is finite for a node that
    has never been backed up through. With ``N(p) == 1`` the bonus is exactly
    zero and selection is pure exploitation - which is correct, because a
    parent visited once has no evidence to be uncertain about.
    """
    return child.value + w * sqrt(log(parent.visits) / child.visits)


def exploit_explore(child: Node, parent: Node, w: float) -> tuple[float, float]:
    """The two halves of UCT, kept apart so the demo can draw them as bars."""
    return child.value, w * sqrt(log(parent.visits) / child.visits)


def backpropagate(leaf: Node, reward: float) -> list[dict[str, Any]]:
    """Push ``reward`` from ``leaf`` up to the root, returning what changed."""
    updates: list[dict[str, Any]] = []
    node: Node | None = leaf
    while node is not None:
        before = {"visits": node.visits, "value": round(node.value, 4)}
        node.visits += 1
        node.value = (node.value * (node.visits - 1) + reward) / node.visits
        updates.append(
            {
                "id": node.id,
                "before": before,
                "after": {"visits": node.visits, "value": round(node.value, 4)},
            }
        )
        node = node.parent
    return updates


class NullRecorder:
    """Records nothing. The algorithm runs identically with or without one."""

    def register(self, node: Node) -> None:
        pass

    def emit(self, op: str, **kw: Any) -> None:
        pass


class LATS:
    """One search over one task."""

    def __init__(
        self,
        task: Task,
        config: Config,
        policy: Any,
        recorder: Any | None = None,
    ) -> None:
        self.task = task
        self.cfg = config
        self.policy = policy
        self.rec = recorder or NullRecorder()

        self._next_id = 0
        #: Notes written by the reflection step. Shared across the whole search,
        #: as in the paper - a lesson learned in one branch is available in all
        #: the others.
        self.reflections: list[str] = []
        self.root = self._node(depth=0, data=task.root_data())
        self.rec.register(self.root)

    # -- plumbing -----------------------------------------------------------

    def _node(self, **kw: Any) -> Node:
        node = Node(id=self._next_id, **kw)
        self._next_id += 1
        return node

    def _expandable(self, node: Node) -> bool:
        """Can the search still do useful work anywhere under ``node``?"""
        if node.terminal or node.depth >= self.cfg.max_depth:
            return False
        if not node.children:
            return True
        return any(self._expandable(c) for c in node.children)

    # -- 1. selection -------------------------------------------------------

    def select(self) -> tuple[Node | None, list[Node], list[dict]]:
        """Descend from the root by UCT to a node that has not been expanded.

        Returns the node, the path taken, and one table per level recording
        what every child scored - the raw material for the tug-of-war bars in
        the demo.
        """
        node = self.root
        path = [node]
        levels: list[dict] = []

        while node.children:
            options = [c for c in node.children if self._expandable(c)]
            row = {
                "parent": node.id,
                "parent_visits": node.visits,
                "w": self.cfg.w,
                "children": [
                    self._uct_entry(c, node, c in options) for c in node.children
                ],
            }
            if not options:
                levels.append(row)
                return None, path, levels
            best = max(options, key=lambda c: uct(c, node, self.cfg.w))
            for entry in row["children"]:
                entry["chosen"] = entry["id"] == best.id
            levels.append(row)
            node = best
            path.append(node)

        return node, path, levels

    def _uct_entry(self, child: Node, parent: Node, available: bool) -> dict:
        exploit, explore = exploit_explore(child, parent, self.cfg.w)
        return {
            "id": child.id,
            "label": child.action.label if child.action else "root",
            "visits": child.visits,
            "exploit": round(exploit, 4),
            "explore": round(explore, 4),
            "uct": round(exploit + explore, 4),
            "available": available,
            "chosen": False,
        }

    # -- 2. expansion + 3. evaluation ---------------------------------------

    def expand(self, node: Node) -> tuple[list[Node], list[dict]]:
        """Sample ``n`` actions, execute every one of them, and score the
        states that come back.

        Samples are drawn with replacement, then grouped: two samples that
        reach the same state become one child, and the size of the group is the
        self-consistency score ``SC(s)``. The environment is stepped once per
        group, not once per sample.
        """
        proposals = self.policy.propose(
            self.task, node.data, self.cfg.n, self.reflections
        )
        if not proposals:
            return [], []

        groups: dict[str, list[Proposal]] = {}
        for p in proposals:
            groups.setdefault(p.signature or p.action.text, []).append(p)

        children: list[Node] = []
        records: list[dict] = []
        for group in groups.values():
            head = group[0]
            try:
                data, obs = self.task.step(node.data, head.action)
            except Exception as exc:  # a policy may propose something illegal
                records.append(
                    {"label": head.action.label, "rejected": str(exc), "id": None}
                )
                continue

            child = self._node(
                depth=node.depth + 1,
                parent=node,
                action=head.action,
                observation=obs,
                data=data,
                terminal=obs.terminal or node.depth + 1 >= self.cfg.max_depth,
                reward=obs.reward,
            )
            # V(s) = lambda * LM(s) + (1 - lambda) * SC(s), computed *after* the
            # environment has spoken. That ordering is the paper's stated
            # difference from Tree of Thoughts.
            child.lm_score = sum(p.self_eval for p in group) / len(group)
            child.sc_score = len(group) / len(proposals)
            child.value = (
                self.cfg.lam * child.lm_score + (1 - self.cfg.lam) * child.sc_score
            )
            children.append(child)
            self.rec.register(child)
            records.append(
                {
                    "id": child.id,
                    "label": child.action.label,
                    "text": child.action.text,
                    "observation": obs.text,
                    "detail": obs.detail,
                    "terminal": child.terminal,
                    "reward": obs.reward,
                    "samples": len(group),
                    "lm": round(child.lm_score, 4),
                    "sc": round(child.sc_score, 4),
                    "value": round(child.value, 4),
                    "rejected": None,
                }
            )

        node.children = children
        return children, records

    # -- 4. simulation ------------------------------------------------------

    def simulate(self, start: Node) -> tuple[Node, list[Node], bool]:
        """Descend greedily by value until a terminal state.

        Not a random playout. Expansion happens as needed, and every step is
        executed in the real environment. Returns the node reached, the path
        walked, and whether it ran out of depth instead of finishing.

        A node can be marked terminal for two different reasons - the
        environment said so, or the depth limit did - and only the first is a
        real ending. ``truncated`` reports which one happened, and a truncated
        trajectory scores zero rather than inheriting a reward it never earned.
        """
        node = start
        walked = [node]
        while not node.terminal and node.depth < self.cfg.max_depth:
            if not node.children:
                children, _ = self.expand(node)
                if not children:
                    return node, walked, True
            node = max(node.children, key=lambda c: c.value)
            walked.append(node)
        finished = node.observation is not None and node.observation.terminal
        return node, walked, not finished

    # -- the loop -----------------------------------------------------------

    def run(self) -> dict[str, Any]:
        cfg = self.cfg
        self.rec.emit(
            "init",
            iteration=0,
            title="Root",
            summary=(
                f"{self.task.title}. The search starts from an empty state; "
                f"reward is {self.task.reward_desc}."
            ),
            detail={"task": self.task.brief(), "config": _config_dict(cfg)},
            focus=[self.root.id],
            path=[self.root.id],
        )

        stop = "the iteration budget ran out"
        iteration = 0

        for iteration in range(1, cfg.iterations + 1):
            # 1. selection
            node, path, levels = self.select()
            if node is None:
                self.rec.emit(
                    "selection",
                    iteration=iteration,
                    title="Selection finds nothing left",
                    summary="Every branch is terminal or at the depth limit.",
                    detail={"levels": levels, "exhausted": True},
                    focus=[p.id for p in path],
                    path=[p.id for p in path],
                )
                stop = "the tree was exhausted"
                break

            self.rec.emit(
                "selection",
                iteration=iteration,
                title="Selection",
                summary=_selection_summary(levels, node),
                detail={"levels": levels, "exhausted": False, "target": node.id},
                focus=[node.id],
                path=[p.id for p in path],
            )

            # 2. expansion (which also executes every candidate)
            children, records = self.expand(node)
            if not children:
                node.terminal = True
                self.rec.emit(
                    "expansion",
                    iteration=iteration,
                    title="Expansion",
                    summary="The policy returned nothing usable; this branch is closed.",
                    detail={"parent": node.id, "children": records, "n": cfg.n},
                    focus=[node.id],
                    path=[p.id for p in path],
                )
                continue

            self.rec.emit(
                "expansion",
                iteration=iteration,
                title="Expansion",
                summary=(
                    f"{cfg.n} samples from the policy collapsed to "
                    f"{len(children)} distinct state"
                    f"{'' if len(children) == 1 else 's'}, each executed in the "
                    "environment."
                ),
                detail={
                    "parent": node.id,
                    "children": records,
                    "n": cfg.n,
                    "reflections_in_context": list(self.reflections),
                },
                focus=[c.id for c in children],
                path=[p.id for p in path],
            )

            # 3. evaluation
            self.rec.emit(
                "evaluation",
                iteration=iteration,
                title="Evaluation",
                summary=(
                    f"V(s) = {cfg.lam:g}·LM(s) + {1 - cfg.lam:g}·SC(s), "
                    "scored after the environment replied."
                ),
                detail={
                    "lam": cfg.lam,
                    "scores": [
                        {
                            "id": c.id,
                            "label": c.action.label if c.action else "root",
                            "lm": round(c.lm_score or 0.0, 4),
                            "sc": round(c.sc_score or 0.0, 4),
                            "value": round(c.value, 4),
                            "reward": c.reward,
                        }
                        for c in children
                    ],
                },
                focus=[c.id for c in children],
                path=[p.id for p in path],
            )

            # 4. simulation
            #
            # Expansion has already executed every candidate, so a child may
            # arrive already solving the task. There is nothing to roll out
            # from a finished trajectory, and no reason to pretend the tests
            # were not run - take it and back it up.
            leaf = max(children, key=lambda c: c.value)
            solved_child = next(
                (c for c in children if (c.reward or 0.0) >= cfg.solved_at), None
            )
            truncated = False
            if solved_child is not None:
                leaf = solved_child
                self.rec.emit(
                    "simulation",
                    iteration=iteration,
                    title="Simulation not needed",
                    summary=(
                        f"Expansion already reached a solved terminal state at "
                        f"node {leaf.id}; there is nothing to roll out."
                    ),
                    detail={
                        "rollout": [leaf.id],
                        "terminal": leaf.id,
                        "truncated": False,
                        "skipped": True,
                        "observation": leaf.observation.text if leaf.observation else "",
                    },
                    focus=[leaf.id],
                    path=[p.id for p in path] + [leaf.id],
                )
            elif cfg.simulate:
                leaf, walked, truncated = self.simulate(leaf)
                self.rec.emit(
                    "simulation",
                    iteration=iteration,
                    title="Simulation",
                    summary=(
                        "Greedy descent by value, in the real environment, "
                        + (
                            "ran out of depth."
                            if truncated
                            else f"reached a terminal state after "
                            f"{len(walked) - 1} more step"
                            f"{'' if len(walked) == 2 else 's'}."
                        )
                    ),
                    detail={
                        "rollout": [n.id for n in walked],
                        "terminal": leaf.id,
                        "truncated": truncated,
                        "observation": leaf.observation.text if leaf.observation else "",
                    },
                    focus=[n.id for n in walked],
                    path=[p.id for p in path] + [n.id for n in walked[1:]],
                )
            else:
                self.rec.emit(
                    "simulation",
                    iteration=iteration,
                    title="Simulation skipped",
                    summary=(
                        "Every node in this task is already a complete solution, "
                        "so there is nothing to roll out - the paper skips "
                        "simulation in the programming setting for the same reason."
                    ),
                    detail={
                        "rollout": [leaf.id],
                        "terminal": leaf.id,
                        "truncated": False,
                        "skipped": True,
                        "observation": leaf.observation.text if leaf.observation else "",
                    },
                    focus=[leaf.id],
                    path=[p.id for p in path],
                )

            # 5. backpropagation
            #
            # One trajectory per iteration, as in Algorithm 1. A trajectory
            # that ran out of depth scores zero rather than inheriting a
            # reward it never earned.
            reward = 0.0 if (truncated or leaf.reward is None) else leaf.reward
            leaf.reward = reward
            updates = backpropagate(leaf, reward)
            self.rec.emit(
                "backpropagation",
                iteration=iteration,
                title="Backpropagation",
                summary=(
                    f"Reward {reward:g} flows from node {leaf.id} up to the root, "
                    f"revising {len(updates)} value"
                    f"{'' if len(updates) == 1 else 's'}."
                ),
                detail={"reward": reward, "leaf": leaf.id, "updates": updates},
                focus=[u["id"] for u in updates],
                path=[u["id"] for u in reversed(updates)],
            )

            # 6. reflection
            if cfg.reflect and reward < cfg.reflect_threshold:
                text = self.task.reflection_for(leaf.data, leaf.observation)
                leaf.reflection = text
                self.reflections.append(text)
                self.rec.emit(
                    "reflection",
                    iteration=iteration,
                    title="Reflection",
                    summary=(
                        "The trajectory failed, so the agent writes down why. "
                        "The note joins the context for every later expansion."
                    ),
                    detail={
                        # The pipe-separated tail of a note is a machine-readable
                        # hint for the offline policy; only show the prose.
                        "node": leaf.id,
                        "text": text.split("|")[0].strip(),
                        "trajectory": [n.id for n in leaf.path],
                        "reward": reward,
                        "total_notes": len(self.reflections),
                    },
                    focus=[leaf.id],
                    path=[n.id for n in leaf.path],
                )

            if reward >= cfg.solved_at:
                stop = "a trajectory reached the target reward"
                break

        nodes = list(self.root.descendants())
        scored = [n for n in nodes if n.reward is not None]
        winner = max(scored, key=lambda n: n.reward or 0.0) if scored else None

        result = {
            "solved": bool(winner and (winner.reward or 0.0) >= cfg.solved_at),
            "best_reward": round(winner.reward, 4) if winner else None,
            "best_node": winner.id if winner else None,
            "best_path": [n.id for n in winner.path] if winner else [],
            "nodes": len(nodes),
            "iterations_run": iteration,
            "stopped_because": stop,
            "reflections": list(self.reflections),
        }
        best_reward = result["best_reward"]
        self.rec.emit(
            "result",
            iteration=result["iterations_run"],
            title="Search over",
            summary=(
                f"Solved: reward {best_reward:g} at node {result['best_node']}."
                if result["solved"]
                else (
                    f"Stopped without solving - {stop}. Best reward "
                    + ("none" if best_reward is None else f"{best_reward:g}")
                    + "."
                )
            ),
            detail=result,
            focus=result["best_path"],
            path=result["best_path"],
        )
        return result


def _config_dict(cfg: Config) -> dict[str, Any]:
    return {
        "n": cfg.n,
        "w": cfg.w,
        "lambda": cfg.lam,
        "iterations": cfg.iterations,
        "max_depth": cfg.max_depth,
        "simulate": cfg.simulate,
        "reflect": cfg.reflect,
        "reflect_threshold": cfg.reflect_threshold,
        "solved_at": cfg.solved_at,
        "seed": cfg.seed,
    }


def _selection_summary(levels: list[dict], target: Node) -> str:
    if not levels:
        return "The root has never been expanded, so selection stops there."
    last = levels[-1]
    chosen = next((c for c in last["children"] if c["chosen"]), None)
    if not chosen:
        return f"Descended to node {target.id}."
    return (
        f"{chosen['label']} wins with UCT {chosen['uct']:g} "
        f"= {chosen['exploit']:g} exploit + {chosen['explore']:g} explore."
    )
