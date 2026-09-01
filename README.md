# Language Agent Tree Search (LATS) Visualizer

Teaching materials for the **NeurIPS 2026 Education Track** on *Language Agent
Tree Search* (LATS; Zhou, Yan, Shlapentokh-Rothman, Wang and Wang, ICML 2024,
[arXiv:2310.04406]).

Three pieces, joined by one file format. `scripts/run_lats.py` searches a real
environment and records what it did as a **trace**; the web app at the root of
this repository replays that trace one operation at a time; the video explains
the algorithm the trace is a recording of.

| | what it is | time on task |
|---|---|---|
| **the web app** (repository root) | a viewer that steps through a trace: the tree grows as the search grew, and a panel shows the arithmetic behind each operation | ~10 min, click |
| **`scripts/run_lats.py`** | a from-scratch LATS implementation searching four real environments, offline or against a real model | ~45 min, read and modify |
| **`scripts/create_video.py`** | a 16½-minute Manim explainer in seven parts, rendered from source, with a narration script generated to match it | ~16 min, watch |

> **The default path runs offline with no API key.** The default policy is a
> seeded stand-in, so the same command always writes the same trace, byte for
> byte. `--llm openai` swaps in a real model when you want one.
> What is *not* mocked is the environment: the candidate programs are executed,
> the arithmetic is evaluated, the documents are retrieved. Every reward in
> every bundled trace came out of a real execution.

[arXiv:2310.04406]: https://arxiv.org/abs/2310.04406

---

## Quick start

```bash
# the viewer - this alone needs no Python
npm install
npm run dev                       # open the URL it prints

# the search
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt   # only the video needs these

python scripts/run_lats.py        # a search run, into results/lats_traces/
```

The viewer opens on the traces committed in `public/traces/`, so it has
something to show before you have run anything. The default `--llm mock` policy
imports nothing beyond the standard library, so a search runs before you install
anything; `requirements.txt` is what the video and the real-model backends
need.

Rendering the video additionally needs **ffmpeg** and a **LaTeX** distribution
on `PATH`. `python scripts/create_video.py --check` reports what it can find.

---

## Layout

```
.
├── index.html  package.json  vite.config.ts  tsconfig*.json
├── src/                      the trace viewer (React 19 · TypeScript · Vite · MUI)
│   ├── App.tsx               state, loading, playback, drag-and-drop
│   ├── theme.ts              the palette, shared with the video
│   ├── types.ts              the lats-trace/1 schema in TypeScript
│   ├── lib/                  validation, tidy tree layout, formatting
│   └── components/           tree, timeline, operation panels, node detail
├── public/traces/            the traces the viewer ships with
├── scripts/
│   ├── run_lats.py           CLI: run a search, write a trace
│   ├── run_lats/             the implementation
│   │   ├── types.py          actions, observations, nodes, config
│   │   ├── search.py         the six operations
│   │   ├── llm.py            the two policies: offline mock, and OpenAI
│   │   ├── trace.py          the trace format and its writer
│   │   ├── env.py            reads .env, so a key need not be exported
│   │   └── tasks/            the four environments, and a subprocess runner
│   ├── create_video.py       CLI: render the video, write SCRIPT.txt
│   └── create_video/         Manim source
│       ├── paths.py          where a render reads and writes
│       ├── theme.py          palette, type scale, layout grid, motion
│       ├── components.py     the animated search tree, panels, icons
│       ├── render.py         the Manim and ffmpeg mechanics
│       ├── timing.py         narration length against time on screen
│       ├── script.py         writes SCRIPT.txt from the narration and timings
│       └── parts/            one module per section, narration included
├── results/                  everything generated — gitignored
│   ├── lats_traces/<stamp>/  one directory per search run
│   └── video/<stamp>/        one directory per render
└── requirements.txt
```

Generated output never lands in the tracked tree. The one exception is
deliberate: `public/traces/` holds the traces the viewer ships with, and
`python scripts/run_lats.py --publish` is how you regenerate them.

---

## The search

```bash
python scripts/run_lats.py                     # every bundled preset
python scripts/run_lats.py --list              # tasks and presets
python scripts/run_lats.py --task game_of_24   # one task, its own defaults
python scripts/run_lats.py --task game_of_24 --w 0 --seed 3 --name greedy
python scripts/run_lats.py --publish           # refresh public/traces/
```

Each run writes into its own timestamped directory under
`results/lats_traces/`, alongside a `manifest.json` indexing what it produced.
Drop any of those files onto the viewer window to step through it.

**Every trace is named for the policy that produced it** — `mock_game_of_24`,
`openai_game_of_24_hard` — and the prefix comes from `--llm` rather than from
anything you type, so a trace cannot be mislabelled. Which policy wrote a trace
is the first thing you want to know about it and the easiest thing to lose
track of once a few are sitting in a folder.

`--publish` regenerates the offline set in `public/traces/` and leaves anything
else there alone, so a published OpenAI trace survives it. To add one:

```bash
python scripts/run_lats.py --task game_of_24_hard --llm openai --publish \
    --note "what this trace is for; the picker shows it under the name"
```

| flag | meaning | paper's value |
|---|---|---|
| `--n` | samples per expansion | 5 |
| `--w` | exploration weight in UCT | 1 |
| `--lambda` | weight on the model's self-evaluation, against self-consistency | 0.5 (HotPotQA, Game of 24) · 0.8 (programming, WebShop) |
| `--iterations` | search iterations | 30–50 trajectories |
| `--max-depth` | hard depth limit | 6–7 |
| `--seed` | seed for the offline policy | — |
| `--no-simulate` | skip simulation | the paper does this for programming |
| `--no-reflect` | skip reflection | ablation |
| `--llm` | `mock` (default) or `openai` | — |

Task defaults are applied first and command-line flags override them, so
`--task merge_intervals` picks up λ = 0.8 and no simulation without being told.

### The four environments

**`merge_intervals`** — write `merge(intervals)` against five visible tests.
Reward is the fraction that pass, measured by running them in a child process.
Following the paper's programming setting, every node is already a complete
program, so simulation is skipped and the test-pass rate is what gets
backpropagated. The example is a trap: the obvious one-pass sweep looks best to
the model and caps at three of five, and every refinement of it caps there too.
The approach itself is the bug, and the fix is a different branch.

**`game_of_24`** — make 24 from `2, 5, 8, 11`, each number used once. Reward is
1 or 0 and needs no oracle: the arithmetic either lands on 24 or it does not.
The policy scores a move by how *tidy* the result looks, which is a plausible
heuristic and frequently wrong. That gap is what backpropagation exists to
close.

**`game_of_24_hard`** — the same environment on 6, 9, 9, 10, chosen by sweeping
every four-number puzzle for the one that punishes a value function hardest.
Every solution ends `9 + 15`, and the only ways to reach 15 are a fraction or
`9 * 10 = 90` — a number far past the target. The heuristic's **twelve
best-looking first moves are all dead ends**, and the trap is sharpest at rank
five: `6 + 9 = 15` makes exactly the number every solution needs and still
loses, because it spends the 9 the last step requires. Five first moves do
work, so the search can find one; it has to get through everything that looks
better first.

Deliberately not one of the famous hard puzzles (3-3-8-8, 1-3-4-6, 1-5-5-5) —
a capable model has those memorised and answers from recall instead of
searching, which teaches nothing.

**`multihop_qa`** — a ReAct-shaped loop (`search[term]`, `finish[answer]`) over
a small corpus. The question asks which venue published the paper that
*introduced* the algorithm LATS adapts; the corpus also holds a 2006 paper about
the selection *rule* that algorithm uses, published elsewhere, and the policy
has a recency bias that walks straight into it.

### The traces the viewer ships with

Every trace is named for the policy that wrote it. The offline set is
reproducible and needs no key — `python scripts/run_lats.py --publish`
regenerates it byte for byte:

| trace | solved | nodes | steps | what it is for |
|---|---|---|---|---|
| `mock_merge_intervals` | yes | 5 | 13 | the programming setting, simulation skipped |
| `mock_game_of_24` | yes | 45 | 31 | all six operations, including a real rollout |
| `mock_game_of_24_no_value` | yes | 68 | 74 | ablation: λ = 0, self-consistency only |
| `mock_game_of_24_greedy` | **no** | 64 | 74 | ablation: w = 0, exploitation only |
| `mock_game_of_24_hard` | **no** | 75 | 98 | the hard puzzle, and why more search does not help |
| `mock_multihop_qa` | yes | 14 | 13 | two-hop retrieval with a distractor |
| `mock_multihop_qa_no_reflection` | yes | 14 | 12 | ablation: reflection off |

The rest came out of a real model. They are **not** reproducible — a rerun
gives a different tree — which is exactly why they are checked in rather than
regenerated:

| trace | model | solved | nodes | steps | what it is for |
|---|---|---|---|---|---|
| `openai_game_of_24` | gpt-5 | yes | 16 | 7 | the short one: a strong policy needs no search at all |
| `openai_multihop_qa` | gpt-5 | yes | 13 | 13 | the whole loop in thirteen steps: wrong commit, reflection, recovery |
| `openai_game_of_24_hard` | gpt-5 | **no** | 110 | 98 | the long one: sixteen iterations of correct search over a tree that cannot contain the answer |
| `openai_game_of_24_hard_wide` | gpt-5 | yes | 151 | 49 | the same, with `--n 12`: one winning move gets proposed, and the search finds it |

Three things worth saying to a class.

**Reflection matters least.** Turning it off changes nothing on `multihop_qa`,
which matches the paper's own ablation, where reflection is the smallest of its
three (−0.05 exact match against −0.26 for the value function and −0.21 for the
search).

**Which term dominates is a property of the task, not a law.** On Game of 24 the
ordering is *reversed* from the paper's HotPotQA result: removing exploration
(`w = 0`) breaks the search outright while removing the model's self-evaluation
(`λ = 0`) only makes it slower.

**Search cannot repair the policy — but sample width can.** Read the three
`game_of_24_hard` traces in order. `mock_game_of_24_hard` and
`openai_game_of_24_hard` are the same puzzle, and a naive arithmetic heuristic
and a frontier reasoning model fail it the same way: both expand the root into
five tidy-looking moves, and neither set contains any of the five moves that can
reach 24. Selection, backpropagation and reflection then run flawlessly for
sixteen iterations over a tree with no solution in it.

`openai_game_of_24_hard_wide` moves exactly one knob — `--n 12` instead of 5 —
and `9 * 10 = 90` finally appears among the root's children. It is the *least*
attractive of the twelve, and it sits at the bottom of the exploitation column
for seven iterations while the search works through `6*9`, `9/9`, `6+10`,
`10-9`, `10-6` and `6+9`, each returning 0 and each marked down. On iteration
eight the exploration bonus reaches 1.44, the largest term on the board, and
carries selection into the branch nothing liked. Reward 1.

Same model, same puzzle, same search: what changed was how much the policy was
asked to propose. That is the clearest thing in this repository, and it is worth
a whole class on its own.

### The real-model policy

The OpenAI SDK is in `requirements.txt`, so the only thing to supply is a key.
Put it in a `.env` file at the repository root — gitignored, and read
automatically — or export it:

```bash
cp .env.example .env                    # then fill in OPENAI_API_KEY

export OPENAI_API_KEY=sk-...            # or macOS / Linux
$env:OPENAI_API_KEY = 'sk-...'          # or PowerShell

python scripts/run_lats.py --task game_of_24_hard --llm openai
```

Anything already exported wins over `.env`, and only the variable *names* are
ever printed.

One request per expansion returns all `n` candidates, which keeps a full search
down to a handful of calls. `--model` overrides the default of `gpt-5`;
`reasoning_effort` is sent only while the endpoint accepts it, so naming a
non-reasoning model works without any extra flag. `OPENAI_BASE_URL` points the
client at a compatible endpoint instead — a local server or a gateway — in which
case the key may not be needed at all.

The environment keeps the last word. On `game_of_24` a step the model invented,
one using a number that is not on the board, is rejected before it reaches the
tree, and the result is recomputed rather than taken from the reply: `2 * 11 =
21` is accepted as the move and still lands on 22.

> **Two warnings.** Traces produced this way are not reproducible. And on
> `merge_intervals` the environment executes whatever program the model wrote.
> That runs in a separate process with a timeout, which bounds a runaway loop —
> it is **not** a sandbox and does not contain hostile code. The offline policy
> only ever proposes programs written in `code_task.py`, so this applies to
> `--llm openai` alone.

### Adding your own task

Subclass `run_lats.tasks.base.Task`, implement `root_data`, `step` and
`mock_propose`, and register it in `scripts/run_lats/tasks/__init__.py`. The
search loop, the trace writer and the viewer are all task-agnostic — nothing
else changes. `render`, `action_schema` and `parse_action` are needed only for
`--llm openai`; `parse_action` receives the state the action applies to, so it
can reject one the model invented.

---

## The viewer

```bash
npm run dev              # dev server with hot reload
npm run build            # static bundle into dist/
npm run preview          # serve that bundle
npm run lint             # oxlint
npx tsc -b               # typecheck only
```

React 19 · TypeScript · Vite · MUI. Nothing is loaded from a remote host. The
palette is ported from `scripts/create_video/theme.py`, so the viewer and the
video read as one piece of work: blue for the algorithm, amber for whatever you
should be looking at, green for high value, red for failure, violet for
reflection, teal for the environment.

- **Replays a trace one operation at a time.** Play, scrub, `←`/`→` to step,
  space to pause, `Home`/`End` to jump. The tree grows as the search grew; node
  fill is the value ramp and the ring is the objective reward.
- **Shows the arithmetic behind each operation.** Selection draws the UCT
  tug-of-war as stacked bars — exploitation against the exploration bonus —
  with a live `w` slider; drag it and the winning branch can flip. Evaluation
  draws `V(s) = λ·LM(s) + (1−λ)·SC(s)` the same way. Backpropagation lists every
  ancestor's value before and after.
- **Opens any node** for the full action, the environment's reply, the program
  and its per-test results, the arithmetic so far, or the retrieved document.
- **Takes your own traces.** Drop a `.json` anywhere on the window, or use the
  Upload button. Uploaded traces stay in the browser; nothing is sent anywhere.
  A rejected file gets every problem found, not just the first, each with a path
  into the document.

`public/traces/` is Vite's static directory, so those traces are served at
`/traces/` in development and copied into `dist/traces/` by a build.

**Changing it.** `src/theme.ts` holds the palette, the type scale and the value
ramp; it mirrors `scripts/create_video/theme.py`, so change them together or the
video and the viewer stop matching. A new operation needs an entry in `Op` and
`OPS` in `types.ts`, a colour in `OP_COLOR`, a `case` in `OperationPanel`, and
an entry in `VALID_OPS` in `lib/validate.ts`. A new task's node detail needs
nothing: `NodeDetail.tsx` formats keys it does not recognise as JSON.

---

## The video

```bash
python scripts/create_video.py                  # draft (854x480), for iterating
python scripts/create_video.py --quality final  # delivery (1920x1080, 30 fps)
python scripts/create_video.py --parts 3 5      # re-render two parts, then re-join
python scripts/create_video.py --script-only    # rewrite SCRIPT.txt only
python scripts/create_video.py --timing         # narration length vs. screen time
python scripts/create_video.py --check          # report the toolchain
```

| part | title | starts | runtime |
|---|---|---|---|
| 1 | Agents, States, and Rewards | 0:00 | 2:17 |
| 2 | Why a Straight Line Fails | 2:17 | 1:48 |
| 3 | Monte Carlo Tree Search | 4:06 | 2:18 |
| 4 | LATS: Tree Search for Language Agents | 6:25 | 1:53 |
| 5 | The Math, and the Intuition | 8:19 | 3:25 |
| 6 | LATS in Action | 11:44 | 2:11 |
| 7 | Does It Work, and Where Is It Going | 13:55 | 2:32 |

A single worked example — writing `merge_intervals` against a visible test suite
— is introduced in Part 1 and searched end to end in Part 6. At `final` quality
the delivered `full.mp4` is 1920x1080 H.264, about 25 MB, which is under the
~40 MB above which the call for submissions asks for external hosting.

> **Before submitting:** set `AUTHORS` at the top of
> `scripts/create_video/parts/part1_agents.py`. Review is single-blind, so every
> author's real name belongs on the title card; it currently reads `Michael Li`
> alone.

Every render gets its own timestamped directory under `results/video/`:

```
results/video/20260830-010025/
    partial_part1.mp4 … partial_part7.mp4   one file per section
    full.mp4                                all seven, concatenated
    timing.json                             per-beat timings
    SCRIPT.txt                              the narration, cued to those timings
    render.json                             which quality preset produced this
```

**The video carries no sound.** The narration lives in a `NARRATION` dict at the
top of each part module, next to the animation it describes, and
`SCRIPT.txt` is generated from those dicts plus the timings the render actually
measured — so the script always describes the mp4 sitting beside it. `--timing`
compares the two, beat by beat, and flags anything where the words and the
picture have drifted apart.

`--parts`, `--join-only` and `--script-only` continue the most recent run rather
than starting a new one, so re-rendering one section does not orphan the other
six; `--run-dir` picks a different one. Adding a part at a quality the run was
not rendered at is warned about rather than silently joined.

Manim's scratch tree lives in `results/video/.manim_cache/` and is shared across
renders on purpose — compiling the equations with LaTeX is the slowest part of a
cold render, and that cache is keyed by content.

> On Windows, MiKTeX is usually installed per-user and is missing from the PATH
> a virtualenv sees, which makes every equation fail. `create_video/texpath.py`
> finds it and prepends it automatically; set `LATS_TEX_BIN` to override the
> search.

---

## The trace format

`lats-trace/1`. Written by `scripts/run_lats/trace.py`, typed in
`src/types.ts`, validated in `src/lib/validate.ts` — those three files are the
whole contract.

```jsonc
{
  "schema": "lats-trace/1",
  "name":   "game_of_24",
  "task":   { "id", "family", "title", "prompt", "reward", "context" },
  "config": { "n", "w", "lambda", "iterations", "max_depth", "simulate",
              "reflect", "solved_at", "seed" },
  "policy": { "kind", "name", "model", "seed", "calls", "tokens",
              "tokens_are_estimated" },
  "result": { "solved", "best_reward", "best_node", "best_path", "nodes",
              "iterations_run", "stopped_because", "reflections" },

  "nodes": [{ "id", "parent", "depth", "label", "action", "observation",
              "detail", "terminal", "created_at" }],

  "steps": [{ "index", "op", "iteration", "title", "summary", "detail",
              "focus", "path", "tokens", "state" }]
}
```

The split between `nodes` and `steps` is the design. A node's parent, action and
observation never change, so they are written once. Its visits, value and reward
change constantly, so **every step carries a full snapshot of them** in `state`.
That costs a few kilobytes and buys a viewer that can jump to any step without
replaying the ones before it — and a file you can read in an editor and follow.

`op` is one of the six operations plus a bookend at each end: `init`,
`selection`, `expansion`, `evaluation`, `simulation`, `backpropagation`,
`reflection`, `result`. `detail` is per-operation — `selection` carries the UCT
table at every level descended, `backpropagation` every before/after pair, and
so on.

---

## Where this follows the paper, and where it does not

**Follows.** The six operations and their order. `UCT(s) = V(s) + w·√(ln N(p) /
N(s))` with `N` initialised to 1. `V(s) = λ·LM(s) + (1 − λ)·SC(s)`, computed
*after* the environment has replied — the paper's stated difference from Tree of
Thoughts. Simulation as a greedy value-guided descent in the real environment,
not a random playout. Per-family λ. Skipping simulation in the programming
setting and backpropagating the fraction of tests passed.

**The backup rule.** Section 4.2 prints it with subscripts that do not match the
paper's own pseudocode. `scripts/run_lats/search.py` follows Algorithm 1 and
Section 3.2:

```
N(s) ← N(s) + 1
V(s) ← ( V_old(s)·(N(s) − 1) + r ) / N(s)
```

That discrepancy is worth showing a class. So is §C reporting depth `d = 7`
while §D.1 says "maximum depth limit of 6".

**Deliberate departures.** Smaller — `n = 3` or `5` and 6–12 iterations against
the paper's 30–50 trajectories, because the traces have to fit on a screen; each
is a flag you can turn back up. A two-level programming tree, where a node's
children refine its parent's program, so every node stays a complete program and
skipping simulation stays faithful while the tree still branches visibly. One
backup per iteration, short-circuiting to a candidate that has already solved
the task. And a stand-in policy: `MockLLM` samples from a bank of candidate
actions each task defines, with seeded weights. It is fiction, and it is
labelled as such in every trace (`"policy": {"kind": "mock"}`); token counts
under it are estimates, flagged with `tokens_are_estimated`.

**Honesty notes for teaching.** The QA reward is an oracle — a stored gold
string, not something the environment can determine. The paper uses the same
oracle signal on HotPotQA, as do the ReAct and Reflexion baselines it is
compared against, but it is a real caveat. And `tasks/sandbox.py` bounds
runtime; it does not contain hostile code.

---

## Reproducing

`python scripts/run_lats.py --publish` is deterministic. Same seeds, same
traces, byte for byte — the manifest carries no timestamp, so regenerating the
committed set produces no diff. Every number in the tables above is printed by
that command; none are typed in by hand.

## Licensing and originality

All material here is original work created for the NeurIPS 2026 Education Track.
`scripts/run_lats/` is a from-scratch reading of the paper's Algorithm 1 — it
vendors nothing from the authors' repository, from LangGraph, or from any agent
framework. The video imports no external image, icon or font. The viewer depends
on React, MUI and Vite, all MIT licensed, and loads no font, script or image
from a remote host. See [LICENSE](LICENSE).
