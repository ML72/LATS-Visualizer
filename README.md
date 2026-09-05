# Language Agent Tree Search (LATS) Visualizer

A trace generator and visualizer for *Language Agent Tree Search* (LATS; Zhou, Yan,
Shlapentokh-Rothman, Wang and Wang, ICML 2024,
[arXiv:2310.04406](https://arxiv.org/abs/2310.04406)). `scripts/run_lats.py` searches a real
environment and records what it did as an **execution trace**; the web app at the root of this
repository replays that trace one operation at a time, the tree growing as the
search grows, with the logic and arithmetic behind each operation visualized as well.

> **The default path runs offline with no API key.** The default policy is a
> seeded stand-in, so the same command always writes the same trace, byte for
> byte. `--llm openai` swaps in a real model when you want one.
> What is *not* mocked is the environment: the candidate programs are executed,
> the arithmetic is evaluated, the documents are retrieved. Every reward in
> every bundled trace came out of a real execution.

---

## Quick start

```
# The viewer - this alone needs no Python
npm install
npm run dev                       # open the URL specified

# The search
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt   # only the real model and the video need these

python scripts/run_lats.py        # search run, saved in results/lats_traces/
```

The viewer opens on the traces committed in `public/traces/`, so it has something
to show before you have run anything. The default `--llm mock` policy imports
nothing beyond the standard library, so a search runs before you install anything.

---

## The search

```
python scripts/run_lats.py                     # every bundled preset
python scripts/run_lats.py --list              # tasks and presets
python scripts/run_lats.py --task game-of-24   # one task, its own defaults
python scripts/run_lats.py --task game-of-24 --w 0 --seed 3 --name game-of-24_greedy
python scripts/run_lats.py --publish           # refresh public/traces/
```

| flag            | meaning                                                         | paper's value                                           |
| --------------- | --------------------------------------------------------------- | ------------------------------------------------------- |
| `--n`           | samples per expansion                                           | 5                                                       |
| `--w`           | exploration weight in UCT                                       | 1                                                       |
| `--lambda`      | weight on the model's self-evaluation, against self-consistency | 0.5 (HotpotQA, Game of 24) · 0.8 (programming, WebShop) |
| `--iterations`  | search iterations                                               | 30–50 trajectories                                      |
| `--max-depth`   | hard depth limit                                                | 6–7                                                     |
| `--seed`        | seed for the offline policy                                     | —                                                       |
| `--no-simulate` | skip simulation                                                 | the paper does this for programming                     |
| `--no-reflect`  | skip reflection                                                 | ablation                                                |
| `--llm`         | `mock` (default) or `openai`                                    | —                                                       |

Task defaults are applied first and command-line flags override them, so
`--task merge-intervals` picks up λ = 0.8 and no simulation without being told.

Each run writes into its own timestamped directory under `results/lats-traces/`,
laid out exactly like `public/` so the two can be diffed file for file. Drop any of
those files onto the viewer window to step through it.

**A trace name is `<policy>_<task>_<variant>`**, where `-` joins the words of one
phrase and `_` joins the phrases: `mock_game-of-24_no-value` reads as the offline
policy, on Game of 24, with the value function ablated. The policy prefix comes
from `--llm` rather than from anything you type, so a trace cannot be mislabelled.

`--publish` regenerates the offline set in `public/traces/` and leaves anything
else there alone, so a published OpenAI trace survives it. To add one:

```
python scripts/run_lats.py --task game-of-24-hard --llm openai --publish \
    --note "what this trace is for; the picker shows it under the name"
```

`--promote results/lats-traces/<run>/traces/<trace>.json` publishes a run you
already have, without searching again — a real-model run costs money and minutes,
and deciding after the fact that it is worth shipping should not mean paying twice.

### The four environments

**`merge-intervals`** — write `merge(intervals)` against five visible tests. Reward
is the fraction that pass, measured by running them in a child process. Following
the paper's programming setting, every node is already a complete program, so
simulation is skipped and the test-pass rate is what gets backpropagated. The
example is a trap: the obvious one-pass sweep looks best to the model and caps at
three of five, and every refinement of it caps there too. The approach itself is
the bug, and the fix is a different branch.

**`game-of-24`** — make 24 from `2, 5, 8, 11`, each number used once. Reward is 1 or
0 and needs no oracle: the arithmetic either lands on 24 or it does not. The policy
scores a move by how *tidy* the result looks, which is a plausible heuristic and
frequently wrong. That gap is what backpropagation exists to close.

**`game-of-24-hard`** — the same environment on `6, 9, 9, 10`, chosen by sweeping
every four-number puzzle for the one that punishes a value function hardest. Every
solution ends `9 + 15`, and the only ways to reach 15 are a fraction or
`9 * 10 = 90` — a number far past the target. The heuristic's **twelve best-looking
first moves are all dead ends**, and the trap is sharpest at rank five: `6 + 9 = 15`
makes exactly the number every solution needs and still loses, because it spends
the 9 the last step requires. Five first moves do work, so the search can find one;
it has to get through everything that looks better first.

**`multihop-qa`** — a ReAct-shaped loop (`search[term]`, `finish[answer]`) over a
small corpus. The question asks which venue published the paper that *introduced*
the algorithm LATS adapts; the corpus also holds a 2006 paper about the selection
*rule* that algorithm uses, published elsewhere, and the policy has a recency bias
that walks straight into it.

### The traces the viewer ships with

The picker groups them by environment and, inside an environment, puts the offline
policy before a real model and a run that worked before one that did not. The
`mock_` set is reproducible and needs no key; `python scripts/run_lats.py --publish`
regenerates it byte for byte. The rest came out of a real model and are **not**
reproducible — a rerun gives a different tree, which is exactly why they are checked
in rather than regenerated.

| trace                            | policy | solved | nodes | steps | what it is for                                            |
| -------------------------------- | ------ | ------ | ----- | ----- | ---------------------------------------------------------- |
| `mock_game-of-24`                | mock   | yes    | 45    | 31    | all six operations, including a real rollout              |
| `mock_game-of-24_no-value`       | mock   | yes\*  | 68    | 74    | ablation: λ = 0, self-consistency only                    |
| `mock_game-of-24_greedy`         | mock   | **no** | 64    | 74    | ablation: w = 0, exploitation only                        |
| `mock_merge-intervals`           | mock   | yes    | 5     | 13    | the programming setting, simulation skipped               |
| `mock_multihop-qa`               | mock   | yes    | 14    | 13    | two-hop retrieval with a distractor                       |
| `mock_multihop-qa_no-reflection` | mock   | yes    | 14    | 12    | ablation: reflection off                                  |
| `mock_game-of-24-hard`           | mock   | **no** | 75    | 98    | the hard puzzle, and why more search does not help        |
| `openai_game-of-24`              | gpt-5  | yes    | 16    | 7     | the short one: a strong policy needs no search at all     |
| `openai_multihop-qa`             | gpt-5  | yes    | 13    | 13    | the whole loop: wrong commit, reflection, recovery        |
| `openai_game-of-24-hard`         | gpt-5  | **no** | 110   | 98    | correct search over a tree that cannot contain the answer |
| `openai_game-of-24-hard_wide`    | gpt-5  | yes    | 151   | 49    | the same, with `--n 12`: one winning move gets proposed   |

> \* `mock_game-of-24_no-value` is solved only in the bookkeeping sense. A winning node
> is *built* on iteration 1, as a by-product of a rollout, and selection never walks
> back into it: all twelve iterations backpropagate a reward of 0 and the run stops on
> its budget, not on a solution. The final `solved` flag comes from a scan over every
> node that carries a reward — a search can contain an answer it never noticed.

Three things the set is arranged to show.

**Reflection matters least.** Turning it off changes nothing on `multihop-qa`, which
matches the paper's own ablation, where reflection is the smallest of its three
(−0.05 exact match against −0.26 for the value function and −0.21 for the search).

**Which term dominates is a property of the task, not a law.** On Game of 24 the
ordering is *reversed* from the paper's HotpotQA result. Removing exploration
(`w = 0`) breaks the search outright. Removing the model's self-evaluation
(`λ = 0`) leaves a search that still reaches a solution but can no longer recognise
one: it builds the winning node and walks past it, and spends every iteration it has
backpropagating zeros.

**Search cannot repair the policy — but sample width can.** Read the three
`game-of-24-hard` traces in order. A naive arithmetic heuristic and a frontier
reasoning model fail the same way: both expand the root into five tidy-looking
moves, and neither set contains any of the five moves that can reach 24. Selection,
backpropagation and reflection then run flawlessly over a tree with no solution in
it. `openai_game-of-24-hard_wide` moves exactly one knob — `--n 12` instead of 5 —
and `9 * 10 = 90` finally appears among the root's children. It is the *least*
attractive of the twelve, and it sits at the bottom of the exploitation column for
seven iterations until the exploration bonus reaches 1.44, the largest term on the
board, and carries selection into the branch nothing liked. Reward 1.

### The real-model policy

The OpenAI SDK is in `requirements.txt`, so the only thing to supply is a key. Put
it in a `.env` file at the repository root — gitignored, and read automatically — or
export it:

```
cp .env.example .env                    # then fill in OPENAI_API_KEY

export OPENAI_API_KEY=sk-...            # or macOS / Linux
$env:OPENAI_API_KEY = 'sk-...'          # or PowerShell

python scripts/run_lats.py --task game-of-24-hard --llm openai
```

Anything already exported wins over `.env`, and only the variable *names* are ever
printed. One request per expansion returns all `n` candidates, which keeps a full
search down to a handful of calls. `--model` overrides the default of `gpt-5`;
`OPENAI_BASE_URL` points the client at a compatible endpoint instead.

The environment keeps the last word. On `game-of-24` a step the model invented, one
using a number that is not on the board, is rejected before it reaches the tree, and
the result is recomputed rather than taken from the reply.

> **Two warnings.** Traces produced this way are not reproducible. And on
> `merge-intervals` the environment executes whatever program the model wrote.
> That runs in a separate process with a timeout, which bounds a runaway loop —
> it is **not** a sandbox and does not contain hostile code. The offline policy
> only ever proposes programs written in `code_task.py`, so this applies to
> `--llm openai` alone.

### Adding your own task

Subclass `run_lats.tasks.base.Task`, implement `root_data`, `step` and
`mock_propose`, and register it in `scripts/run_lats/tasks/__init__.py`. The search
loop, the trace writer and the viewer are all task-agnostic — nothing else changes.
`render`, `action_schema` and `parse_action` are needed only for `--llm openai`;
`parse_action` receives the state the action applies to, so it can reject one the
model invented.

---

## The viewer

```
npm run dev              # dev server with hot reload
npm run build            # static bundle into dist/
npm run preview          # serve that bundle
npm run lint             # oxlint
npx tsc -b               # typecheck only
```

React 19 · TypeScript · Vite · MUI. Nothing is loaded from a remote host.

- **Replays a trace one operation at a time.** Play, scrub, `←`/`→` to step, space
to pause, `Home`/`End` to jump. The tree grows as the search grew; node fill is the
value ramp and the ring is the objective reward.
- **Frames the step, not the whole tree.** The tree is laid out from the nodes that
exist at the current step and the camera follows the operation being explained, so a
forty-five node search stays readable from its first step. Pan or zoom and the
camera hands over; the crosshair gives it back, and the arrows button fits the whole
tree. Zooming out gives up detail one piece at a time — the full card, then a name
held at a fixed size and truncated, then a bare value-coloured tile.
- **Shows the arithmetic behind each operation.** Selection draws the UCT tug-of-war
as stacked bars — exploitation against the exploration bonus — with a live `w`
slider; drag it and the winning branch can flip. Evaluation draws
`V(s) = λ·LM(s) + (1−λ)·SC(s)` the same way. Backpropagation lists every ancestor's
value before and after.
- **Opens any node** for the full action, the environment's reply, the program and
its per-test results, the arithmetic so far, or the retrieved document.
- **Takes your own traces.** Drop a `.json` anywhere on the window, or use the
Upload button. Uploaded traces stay in the browser; nothing is sent anywhere. A
rejected file gets every problem found, not just the first, each with a path into
the document.
- **Reads in the dark too.** The moon in the app bar swaps to a dark ground and the
choice is remembered, but it is never guessed from the operating system. Dark is not
an inversion — the hues and the value ramp are re-picked for a dark card, so the
same 4.5:1 promise holds in both.
- **Fits a phone.** Above about 1100px the tree and the panel sit side by side.
Narrow and upright stacks them. On a handset they become two tabs over a shared
transport, and the six operations wrap to two rows of three rather than shrink past
reading.

**Changing it.** `src/theme.ts` holds both palettes, the type scale and the value
ramp; the light one mirrors `scripts/create_video/theme.py`, so change them together
or the video and the viewer stop matching. A new colour belongs in the `Token` union
and in both palettes — a literal in a component is a colour that cannot follow the
mode, and one reaching SVG has to go through `style` rather than a `fill` attribute.
A new operation needs an entry in `Op` and `OPS` in `types.ts`, a colour in
`OP_COLOR`, a `case` in `OperationPanel`, and an entry in `VALID_OPS` in
`lib/validate.ts`. A new task's node detail needs nothing: `NodeDetail.tsx` formats
keys it does not recognise as JSON.

---

## The video

`scripts/create_video.py` renders an 18-minute Manim explainer of the algorithm in
six parts, from source.

```
python scripts/create_video.py                  # draft (854x480), for iterating
python scripts/create_video.py --quality final  # delivery (1920x1080, 30 fps)
python scripts/create_video.py --parts 3 5      # re-render two parts, then re-join
python scripts/create_video.py --check          # report the toolchain
```

Rendering needs `requirements.txt`, plus **ffmpeg** and a **LaTeX** distribution on
`PATH`; `--check` reports what it can find. Every render gets its own timestamped
directory under `results/video/`, holding one file per part, the concatenated
`full.mp4`, per-beat timings, and `SCRIPT.md`.

**The video carries no sound.** The narration lives in a `NARRATION` dict at the top
of each part module, next to the animation it describes, with an `ON_SCREEN` dict
beside it. `SCRIPT.md` is generated from those two dicts plus the timings the render
actually measured, so the script always describes the mp4 sitting beside it.
`--timing` compares words against screen time, beat by beat.

**The type is bundled, not installed.** `create_video/fonts/` holds Inter and
JetBrains Mono, and `create_video/fontpath.py` registers them with Pango on import -
privately, for the rendering process only. On Windows, MiKTeX is usually installed
per-user and is missing from the PATH a virtualenv sees; `create_video/texpath.py`
finds it and prepends it automatically, and `LATS_TEX_BIN` overrides the search.

---

## The trace format

`lats-trace/1`. Written by `scripts/run_lats/trace.py`, typed in `src/types.ts`,
validated in `src/lib/validate.ts` — those three files are the whole contract.

```
{
  "schema": "lats-trace/1",
  "name":   "mock_game-of-24",
  "generated_by": { "package", "version" },
  "task":   { "id", "family", "title", "prompt", "reward", "context" },
  "config": { "n", "w", "lambda", "iterations", "max_depth", "simulate",
              "reflect", "reflect_threshold", "solved_at", "seed" },
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

`op` is one of the six operations plus a bookend at each end: `init`, `selection`,
`expansion`, `evaluation`, `simulation`, `backpropagation`, `reflection`, `result`.
`detail` is per-operation — `selection` carries the UCT table at every level
descended, `backpropagation` every before/after pair, and so on.

---

## Where this follows the paper, and where it does not

**Follows.** The six operations and their order.
`UCT(s) = V(s) + w·√(ln N(p) / N(s))` with `N` initialised to 1.
`V(s) = λ·LM(s) + (1 − λ)·SC(s)`, computed *after* the environment has replied — the
paper's stated difference from Tree of Thoughts. Simulation as a greedy
value-guided descent in the real environment, not a random playout. Per-family λ.
Skipping simulation in the programming setting and backpropagating the fraction of
tests passed.

**The backup rule.** Section 4.2 prints it with subscripts that do not match the
paper's own pseudocode. `scripts/run_lats/search.py` follows Algorithm 1 and
Section 3.2:

```
N(s) ← N(s) + 1
V(s) ← ( V_old(s)·(N(s) − 1) + r ) / N(s)
```

Appendix C also reports depth `d = 7` while Appendix D.1 says a maximum depth limit
of 6.

**Deliberate departures.** Smaller — `n = 3` or `5` and 6–12 iterations against the
paper's 30–50 trajectories, because the traces have to fit on a screen; each is a
flag you can turn back up. A two-level programming tree, where a node's children
refine its parent's program, so every node stays a complete program and skipping
simulation stays faithful while the tree still branches visibly. One backup per
iteration, short-circuiting to a candidate that has already solved the task. And a
stand-in policy: `MockLLM` samples from a bank of candidate actions each task
defines, with seeded weights. It is fiction, and it is labelled as such in every
trace (`"policy": {"kind": "mock"}`); token counts under it are estimates, flagged
with `tokens_are_estimated`.

**Honest caveats.** The QA reward is an oracle — a stored gold string, not something
the environment can determine. The paper uses the same oracle signal on HotpotQA, as
do the ReAct and Reflexion baselines it is compared against, but it is a real
caveat. And `tasks/sandbox.py` bounds runtime; it does not contain hostile code.

---

## Reproducing

`python scripts/run_lats.py --publish` is deterministic. Same seeds, same traces,
byte for byte — the manifest carries no timestamp, so regenerating the committed set
produces no diff. Every number in the tables above is printed by that command; none
are typed in by hand.

## Licensing and originality

All material here is original work. `scripts/run_lats/` is a from-scratch reading of
the paper's Algorithm 1 — it vendors nothing from the authors' repository, from
LangGraph, or from any agent framework. The video imports no external image, icon or
font. The viewer depends on React, MUI and Vite, all MIT licensed, and loads no
font, script or image from a remote host. See [LICENSE](LICENSE).
