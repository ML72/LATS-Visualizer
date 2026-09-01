#!/usr/bin/env python3
"""
Run Language Agent Tree Search and write a trace the viewer can replay.

    python scripts/run_lats.py                      # every bundled preset
    python scripts/run_lats.py --list               # what can be run
    python scripts/run_lats.py --task game_of_24    # one task, its own defaults
    python scripts/run_lats.py --task game_of_24 --w 0 --seed 3 --name greedy
    python scripts/run_lats.py --publish            # refresh public/traces/

Traces land in a timestamped directory under ``results/lats_traces/``, which is
gitignored::

    results/lats_traces/20260901-041530/
        game_of_24.json ...     one file per trace
        manifest.json           an index of what this run produced

Drop any of those onto the viewer to step through it. ``--publish`` writes into
``public/traces/`` instead - that is the committed set the viewer loads on
startup, so use it when you mean to change what ships.

With the default ``--llm mock`` policy this needs no API key and no network,
and the same seed always produces the same trace, byte for byte. ``--llm openai``
swaps in a real model, reading ``OPENAI_API_KEY`` from the environment; see the
README before using it.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_lats import LATS, Config, TASKS  # noqa: E402
from run_lats.llm import POLICIES, OpenAILLM, build_policy  # noqa: E402
from run_lats.trace import TraceRecorder  # noqa: E402

ROOT = SCRIPTS.parent
#: Generated runs. Gitignored, one timestamped directory each.
TRACE_RESULTS = ROOT / "results" / "lats_traces"
#: The committed set the viewer serves as static files.
PUBLIC_TRACES = ROOT / "public" / "traces"

MANIFEST_SCHEMA = "lats-trace-manifest/1"

#: The traces that ship with the viewer. Two of them are ablations, which is
#: the point: the interesting thing about a knob is what happens when you turn
#: it.
PRESETS: list[dict] = [
    {
        "name": "merge_intervals",
        "task": "merge_intervals",
        "note": (
            "The programming setting. Every node is a complete program and the "
            "reward is the fraction of tests it passes, so simulation is skipped. "
            "The one-pass approach looks best to the model and caps at three of "
            "five; the fix is a different branch, not a better patch."
        ),
        "overrides": {},
    },
    {
        "name": "game_of_24",
        "task": "game_of_24",
        "note": (
            "All six operations, including simulation: the tree descends greedily "
            "by value, in the real environment, until one number is left. Solved "
            "on the fifth iteration, after four dead ends."
        ),
        "overrides": {},
    },
    {
        "name": "game_of_24_no_value",
        "task": "game_of_24",
        "note": (
            "Ablation: lambda = 0, so V(s) is self-consistency alone and the "
            "model's own judgement is thrown away. It still gets there, but it "
            "needs every iteration it has and half again as many nodes."
        ),
        "overrides": {"lam": 0.0},
    },
    {
        "name": "game_of_24_greedy",
        "task": "game_of_24",
        "note": (
            "Ablation: w = 0, so UCT collapses to pure exploitation and selection "
            "never leaves the branch it liked first. It grows a larger tree than "
            "the full search and never finds 24 at all."
        ),
        "overrides": {"w": 0.0},
    },
    {
        "name": "multihop_qa",
        "task": "multihop_qa",
        "note": (
            "Two-hop retrieval. The corpus holds a tempting near-miss answer, and "
            "the policy has a recency bias that walks straight into it; the second "
            "iteration backs out and finds the right document."
        ),
        "overrides": {},
    },
    {
        "name": "multihop_qa_no_reflection",
        "task": "multihop_qa",
        "note": (
            "Ablation: reflection off. Identical outcome, one step shorter - which "
            "is the paper's own finding. Reflection is the smallest of its three "
            "ablations; the value function and the search structure matter more."
        ),
        "overrides": {"reflect": False},
    },
]


def build_config(task, args: argparse.Namespace) -> Config:
    """Task defaults first, then anything given explicitly on the command line."""
    cfg = replace(Config(), **task.defaults())
    explicit = {
        "n": args.n,
        "w": args.w,
        "lam": getattr(args, "lambda"),
        "iterations": args.iterations,
        "max_depth": args.max_depth,
        "seed": args.seed,
    }
    cfg = replace(cfg, **{k: v for k, v in explicit.items() if v is not None})
    if args.no_simulate:
        cfg = replace(cfg, simulate=False)
    if args.no_reflect:
        cfg = replace(cfg, reflect=False)
    return cfg


def run_one(
    task_id: str,
    cfg: Config,
    *,
    name: str,
    out: Path,
    llm: str,
    model: str | None,
    quiet: bool = False,
) -> dict:
    """Search one task, write its trace, and return its manifest entry."""
    if task_id not in TASKS:
        raise SystemExit(
            f"unknown task {task_id!r}. Known: {', '.join(sorted(TASKS))}"
        )
    task = TASKS[task_id]()
    policy = build_policy(llm, cfg.seed, model)
    recorder = TraceRecorder(task, cfg, policy)
    result = LATS(task, cfg, policy, recorder).run()
    recorder.write(out, result, name=name)

    if not quiet:
        status = "solved" if result["solved"] else "not solved"
        print(
            f"  {name:<32} {status:<10} "
            f"reward {result['best_reward']}  "
            f"{result['nodes']} nodes  {len(recorder.steps)} steps"
        )
    return {
        "file": out.name,
        "name": name,
        "task": task_id,
        "title": task.title,
        "family": task.family,
        "solved": result["solved"],
        "best_reward": result["best_reward"],
        "nodes": result["nodes"],
        "steps": len(recorder.steps),
        "policy": policy.info()["kind"],
    }


def display(path: Path) -> str:
    """Repo-relative when it can be, absolute when the target is elsewhere."""
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_manifest(folder: Path) -> list[dict]:
    path = folder / "manifest.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("traces", [])
    except (json.JSONDecodeError, OSError):
        return []


def write_manifest(folder: Path, entries: list[dict]) -> Path:
    """An index of a trace folder, so the viewer knows what is there.

    Deliberately free of timestamps: regenerating ``public/traces/`` with the
    same seeds should produce no diff at all.
    """
    path = folder / "manifest.json"
    payload = {"schema": MANIFEST_SCHEMA, "traces": entries}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def preset_order(entries: list[dict]) -> list[dict]:
    """Bundled traces in their curated order; anything hand-run after them."""
    order = {p["name"]: i for i, p in enumerate(PRESETS)}
    return sorted(entries, key=lambda e: (order.get(e["name"], 999), e["name"]))


def destination(args: argparse.Namespace) -> Path:
    """Where this invocation's traces go.

    ``--publish`` targets the committed folder the viewer serves; everything
    else gets a fresh timestamped directory, so two runs never clobber each
    other and you can diff one against the next.
    """
    if args.publish:
        PUBLIC_TRACES.mkdir(parents=True, exist_ok=True)
        return PUBLIC_TRACES
    folder = TRACE_RESULTS / datetime.now().strftime("%Y%m%d-%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def report(folder: Path, count: int, args: argparse.Namespace) -> None:
    """Say where the traces went, and what to do with them."""
    print(f"\nwrote {count} trace(s) and manifest.json to {display(folder)}/")
    if args.publish:
        print("that is the set the viewer loads on startup - "
              "`npm run dev` to see it.")
    else:
        print("drop one onto the viewer (`npm run dev`) to step through it, "
              "or re-run with --publish to make it part of the bundled set.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--task", help="run one task instead of every bundled preset")
    p.add_argument("--list", action="store_true",
                   help="list tasks and presets, then exit")
    p.add_argument("--publish", action="store_true",
                   help="write into public/traces/, the set the viewer ships with")
    p.add_argument("--out", type=Path,
                   help="write the trace here instead (single-task runs)")
    p.add_argument("--name",
                   help="name recorded inside the trace, and its filename")

    g = p.add_argument_group("search")
    g.add_argument("--n", type=int, help="samples per expansion (paper: 5)")
    g.add_argument("--w", type=float, help="exploration weight in UCT (paper: 1)")
    g.add_argument("--lambda", type=float, dest="lambda",
                   help="weight on LLM self-evaluation")
    g.add_argument("--iterations", type=int, help="search iterations")
    g.add_argument("--max-depth", type=int, dest="max_depth", help="depth limit")
    g.add_argument("--seed", type=int, help="seed for the mock policy")
    g.add_argument("--no-simulate", action="store_true",
                   help="skip the simulation step")
    g.add_argument("--no-reflect", action="store_true",
                   help="skip the reflection step")

    m = p.add_argument_group("policy")
    m.add_argument("--llm", default="mock", choices=list(POLICIES),
                   help="mock is deterministic and offline (default); "
                        "openai calls a real model")
    m.add_argument("--model", default=None,
                   help="model id for --llm openai "
                        f"(default: {OpenAILLM.default_model})")

    p.add_argument("-q", "--quiet", action="store_true")
    args = p.parse_args(argv)

    if args.list:
        print("tasks:")
        for task_id, cls in sorted(TASKS.items()):
            print(f"  {task_id:<20} {cls.title}")
        print("\npresets (written by a bare `python scripts/run_lats.py`):")
        for preset in PRESETS:
            extra = (
                ", ".join(f"{k}={v}" for k, v in preset["overrides"].items())
                or "task defaults"
            )
            print(f"  {preset['name']:<32} {preset['task']}  [{extra}]")
        return 0

    if args.out and not args.task:
        raise SystemExit("--out applies to a single-task run; add --task.")

    if args.task:
        task = TASKS.get(args.task)
        if task is None:
            raise SystemExit(
                f"unknown task {args.task!r}. Known: {', '.join(sorted(TASKS))}"
            )
        name = args.name or args.task
        out = args.out or destination(args) / f"{name}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        if not args.quiet:
            print(f"running {args.task} with the {args.llm} policy")
        entry = run_one(
            args.task,
            build_config(task(), args),
            name=name,
            out=out,
            llm=args.llm,
            model=args.model,
            quiet=args.quiet,
        )
        # Keep the folder's index in step with what is on disk, so a hand-run
        # trace shows up in the picker next to the bundled ones.
        kept = [e for e in read_manifest(out.parent) if e["file"] != entry["file"]]
        write_manifest(out.parent, preset_order(kept + [entry]))
        if not args.quiet:
            report(out.parent, 1, args)
        return 0

    folder = destination(args)
    if not args.quiet:
        print(f"running {len(PRESETS)} presets with the {args.llm} policy\n")
    entries = []
    for preset in PRESETS:
        task = TASKS[preset["task"]]()
        cfg = replace(build_config(task, args), **preset["overrides"])
        entry = run_one(
            preset["task"],
            cfg,
            name=preset["name"],
            out=folder / f"{preset['name']}.json",
            llm=args.llm,
            model=args.model,
            quiet=args.quiet,
        )
        entry["note"] = preset["note"]
        entries.append(entry)

    write_manifest(folder, entries)
    if not args.quiet:
        report(folder, len(entries), args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
