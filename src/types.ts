/**
 * The `lats-trace/1` schema, in TypeScript.
 *
 * This mirrors `scripts/run_lats/trace.py`. If you change the schema on the Python
 * side, change it here and in `lib/validate.ts` - those three files are the
 * whole contract between the two halves of the demo.
 */

/** The six operations of the paper, plus a bookend at each end. */
export type Op =
  | 'init'
  | 'selection'
  | 'expansion'
  | 'evaluation'
  | 'simulation'
  | 'backpropagation'
  | 'reflection'
  | 'result'

export const OPS: Op[] = [
  'selection',
  'expansion',
  'evaluation',
  'simulation',
  'backpropagation',
  'reflection',
]

/** A node's immutable half. Written once, when the node is created. */
export interface TraceNode {
  id: number
  parent: number | null
  depth: number
  label: string
  action: string | null
  observation: string | null
  detail: Record<string, unknown>
  terminal: boolean
  /** Index of the step at which this node first exists. */
  created_at: number
}

/** A node's mutable half. Snapshotted on every step. */
export interface NodeState {
  visits: number
  value: number
  reward: number | null
  /** LM(s): the model grading its own idea. */
  lm: number | null
  /** SC(s): the share of samples that agreed. */
  sc: number | null
  terminal: boolean
  reflected: boolean
}

export interface Step {
  index: number
  op: Op
  iteration: number
  title: string
  summary: string
  detail: Record<string, unknown>
  /** Nodes this step is about. */
  focus: number[]
  /** The root-to-leaf path this step walked. */
  path: number[]
  tokens: number
  state: Record<string, NodeState>
}

export interface TaskBrief {
  id: string
  family: string
  title: string
  prompt: string
  reward: string
  context: Record<string, string[]>
}

export interface TraceConfig {
  n: number
  w: number
  lambda: number
  iterations: number
  max_depth: number
  simulate: boolean
  reflect: boolean
  reflect_threshold: number
  solved_at: number
  seed: number | null
}

export interface PolicyInfo {
  kind: string
  name: string
  model: string | null
  seed: number | null
  calls: number
  tokens: number
  tokens_are_estimated: boolean
}

export interface TraceResult {
  solved: boolean
  best_reward: number | null
  best_node: number | null
  best_path: number[]
  nodes: number
  iterations_run: number
  stopped_because: string
  reflections: string[]
}

export interface Trace {
  schema: string
  name: string
  generated_by: { package: string; version: string }
  task: TaskBrief
  config: TraceConfig
  policy: PolicyInfo
  result: TraceResult
  nodes: TraceNode[]
  steps: Step[]
}

// -- per-operation `detail` payloads ---------------------------------------

export interface UctEntry {
  id: number
  label: string
  visits: number
  /** V(s), the exploitation half. */
  exploit: number
  /** w * sqrt(ln N(p) / N(s)), the exploration half, at the trace's own w. */
  explore: number
  uct: number
  /** False for a branch that is terminal or at the depth limit. */
  available: boolean
  chosen: boolean
}

export interface UctLevel {
  parent: number
  parent_visits: number
  w: number
  children: UctEntry[]
}

export interface SelectionDetail {
  levels: UctLevel[]
  exhausted: boolean
  target?: number
}

export interface ExpansionChild {
  id: number | null
  label: string
  text?: string
  observation?: string
  detail?: Record<string, unknown>
  terminal?: boolean
  reward?: number | null
  /** How many of the n samples reached this state. */
  samples?: number
  lm?: number
  sc?: number
  value?: number
  rejected: string | null
}

export interface ExpansionDetail {
  parent: number
  n: number
  children: ExpansionChild[]
  reflections_in_context?: string[]
}

export interface EvaluationDetail {
  lam: number
  scores: {
    id: number
    label: string
    lm: number
    sc: number
    value: number
    reward: number | null
  }[]
}

export interface SimulationDetail {
  rollout: number[]
  terminal: number
  truncated: boolean
  skipped?: boolean
  observation: string
}

export interface BackpropDetail {
  reward: number
  leaf: number
  updates: {
    id: number
    before: { visits: number; value: number }
    after: { visits: number; value: number }
  }[]
}

export interface ReflectionDetail {
  node: number
  text: string
  trajectory: number[]
  reward: number
  total_notes: number
}

export interface InitDetail {
  task: TaskBrief
  config: TraceConfig
}

// -- the traces folder index ------------------------------------------------

export interface ManifestEntry {
  file: string
  name: string
  task: string
  title: string
  family: string
  solved: boolean
  best_reward: number | null
  nodes: number
  steps: number
  policy: string
  note?: string
}

export interface Manifest {
  schema: string
  traces: ManifestEntry[]
}
