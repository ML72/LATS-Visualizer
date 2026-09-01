/**
 * Tree layout, and the derived view for one step.
 *
 * The layout is the classic bottom-up tidy pass: leaves are placed left to
 * right in order, and every parent sits at the mean of its children. It is
 * stable - a node's position never depends on which step you are looking at,
 * only on the shape of the finished tree - so scrubbing the timeline grows the
 * tree in place instead of rearranging it under the cursor.
 */

import type { NodeState, Step, Trace, TraceNode } from '../types'

export const NODE_W = 138
export const NODE_H = 50
const GAP_X = 18
const GAP_Y = 78

export interface Placed {
  node: TraceNode
  x: number
  y: number
}

export interface Layout {
  placed: Map<number, Placed>
  order: number[]
  width: number
  height: number
  childrenOf: Map<number, number[]>
}

export function layoutTree(nodes: TraceNode[]): Layout {
  const childrenOf = new Map<number, number[]>()
  const byId = new Map<number, TraceNode>()
  let root: TraceNode | undefined

  for (const node of nodes) {
    byId.set(node.id, node)
    if (node.parent === null) root = root ?? node
    else childrenOf.set(node.parent, [...(childrenOf.get(node.parent) ?? []), node.id])
  }

  const placed = new Map<number, Placed>()
  const order: number[] = []
  let cursor = 0

  // Iterative post-order: a trace can be deeper than it looks and recursion
  // over untrusted input is an avoidable risk.
  if (root) {
    const stack: { id: number; visited: boolean }[] = [{ id: root.id, visited: false }]
    while (stack.length) {
      const frame = stack.pop()!
      const node = byId.get(frame.id)!
      const kids = childrenOf.get(frame.id) ?? []

      if (!frame.visited && kids.length) {
        stack.push({ id: frame.id, visited: true })
        for (let i = kids.length - 1; i >= 0; i--) stack.push({ id: kids[i], visited: false })
        continue
      }

      const y = node.depth * (NODE_H + GAP_Y)
      let x: number
      if (!kids.length) {
        x = cursor * (NODE_W + GAP_X)
        cursor += 1
      } else {
        const xs = kids.map((k) => placed.get(k)!.x)
        x = (Math.min(...xs) + Math.max(...xs)) / 2
      }
      placed.set(node.id, { node, x, y })
      order.push(node.id)
    }
  }

  let maxX = 0
  let maxY = 0
  for (const p of placed.values()) {
    maxX = Math.max(maxX, p.x)
    maxY = Math.max(maxY, p.y)
  }

  return {
    placed,
    order: order.reverse(),
    width: maxX + NODE_W,
    height: maxY + NODE_H,
    childrenOf,
  }
}

// ---------------------------------------------------------------------------

export interface View {
  step: Step
  /** Nodes that exist as of this step. */
  visible: TraceNode[]
  state: (id: number) => NodeState | undefined
  focus: Set<number>
  path: number[]
  /** "parent-child" keys for the edges on this step's path. */
  pathEdges: Set<string>
}

export function viewAt(trace: Trace, index: number): View {
  const step = trace.steps[Math.min(Math.max(index, 0), trace.steps.length - 1)]
  const visible = trace.nodes.filter((n) => n.created_at <= step.index)
  const path = step.path ?? []
  const pathEdges = new Set<string>()
  for (let i = 1; i < path.length; i++) {
    // A path may be recorded root-first or leaf-first; store both directions
    // so edge lookup does not care which.
    pathEdges.add(`${path[i - 1]}-${path[i]}`)
    pathEdges.add(`${path[i]}-${path[i - 1]}`)
  }
  return {
    step,
    visible,
    state: (id) => step.state[String(id)],
    focus: new Set(step.focus ?? []),
    path,
    pathEdges,
  }
}

/** Index of the first step of each iteration, for the timeline's tick marks. */
export function iterationStarts(trace: Trace): { index: number; iteration: number }[] {
  const out: { index: number; iteration: number }[] = []
  let last = -1
  for (const step of trace.steps) {
    if (step.iteration !== last && step.iteration > 0) {
      out.push({ index: step.index, iteration: step.iteration })
      last = step.iteration
    }
  }
  return out
}
