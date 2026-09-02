/**
 * Turn an untrusted file into a `Trace`, or into a list of reasons why not.
 *
 * Anything can be dropped on this app, so the failure path matters as much as
 * the success path. The rules are:
 *
 *   - never throw at the caller; return a result object
 *   - report *every* problem found, not just the first
 *   - say what was expected and what was there, with a path like
 *     `steps[4].state["7"]`, so a malformed trace is fixable rather than
 *     merely rejected
 *
 * The checks go beyond "the keys exist". A trace whose steps reference nodes
 * that were never declared would render as an empty tree with no explanation,
 * so referential integrity is checked here where it can still be explained.
 */

import type { Manifest, Op, Trace } from '../types'

export const SUPPORTED_SCHEMA = 'lats-trace/1'

/** How many problems to report before giving up; a truncated list still helps. */
const MAX_ERRORS = 12

/** Anything bigger than this is refused before it is parsed. */
export const MAX_BYTES = 64 * 1024 * 1024

export type ParseResult =
  | { ok: true; trace: Trace; warnings: string[] }
  | { ok: false; errors: string[] }

const VALID_OPS = new Set<Op>([
  'init',
  'selection',
  'expansion',
  'evaluation',
  'simulation',
  'backpropagation',
  'reflection',
  'result',
])

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function describe(v: unknown): string {
  if (v === null) return 'null'
  if (Array.isArray(v)) return `an array of ${v.length}`
  return typeof v
}

/** Validate a parsed JSON value against the trace schema. */
export function validateTrace(raw: unknown): ParseResult {
  const errors: string[] = []
  const warnings: string[] = []
  const fail = (msg: string) => {
    if (errors.length < MAX_ERRORS) errors.push(msg)
  }

  if (!isObject(raw)) {
    return {
      ok: false,
      errors: [
        `A trace must be a JSON object; this file contains ${describe(raw)}.`,
      ],
    }
  }

  // -- schema tag ----------------------------------------------------------
  const schema = raw.schema
  if (typeof schema !== 'string') {
    fail(
      `Missing "schema". A trace written by run_lats starts with "schema": "${SUPPORTED_SCHEMA}".`,
    )
  } else if (schema !== SUPPORTED_SCHEMA) {
    const family = schema.split('/')[0]
    if (family === 'lats-trace') {
      warnings.push(
        `This trace declares "${schema}" but the viewer implements ${SUPPORTED_SCHEMA}. Loading it anyway; some panels may be empty.`,
      )
    } else if (family === 'lats-trace-manifest') {
      fail(
        'This is the traces index (traces-manifest.json), not a trace. Pick one of the individual trace files instead.',
      )
    } else {
      fail(`Unknown schema "${schema}"; expected "${SUPPORTED_SCHEMA}".`)
    }
  }

  // -- required sections ---------------------------------------------------
  for (const key of ['task', 'config', 'result', 'policy'] as const) {
    if (!isObject(raw[key])) {
      fail(`Missing or malformed "${key}" (found ${describe(raw[key])}).`)
    }
  }
  if (!Array.isArray(raw.nodes) || raw.nodes.length === 0) {
    fail(`"nodes" must be a non-empty array (found ${describe(raw.nodes)}).`)
  }
  if (!Array.isArray(raw.steps) || raw.steps.length === 0) {
    fail(`"steps" must be a non-empty array (found ${describe(raw.steps)}).`)
  }
  if (errors.length) return { ok: false, errors }

  // -- nodes ---------------------------------------------------------------
  const nodes = raw.nodes as unknown[]
  const ids = new Set<number>()
  let roots = 0

  nodes.forEach((node, i) => {
    if (!isObject(node)) {
      fail(`nodes[${i}] is ${describe(node)}, expected an object.`)
      return
    }
    if (typeof node.id !== 'number' || !Number.isInteger(node.id)) {
      fail(`nodes[${i}].id must be an integer (found ${describe(node.id)}).`)
      return
    }
    if (ids.has(node.id)) fail(`Duplicate node id ${node.id} at nodes[${i}].`)
    ids.add(node.id)

    if (typeof node.depth !== 'number') {
      fail(`nodes[${i}].depth must be a number (found ${describe(node.depth)}).`)
    }
    if (node.parent === null) {
      roots += 1
    } else if (typeof node.parent !== 'number') {
      fail(
        `nodes[${i}].parent must be a node id or null (found ${describe(node.parent)}).`,
      )
    }
  })

  // Parents are checked after the whole set is known, so forward references
  // are fine and only genuinely dangling ones are reported.
  nodes.forEach((node, i) => {
    if (!isObject(node)) return
    if (typeof node.parent === 'number' && !ids.has(node.parent)) {
      fail(`nodes[${i}] has parent ${node.parent}, which is not a node in this trace.`)
    }
  })

  if (roots === 0) fail('No root node: exactly one node must have "parent": null.')
  if (roots > 1) fail(`${roots} nodes have "parent": null; a trace has exactly one root.`)

  // -- steps ---------------------------------------------------------------
  const steps = raw.steps as unknown[]
  steps.forEach((step, i) => {
    if (!isObject(step)) {
      fail(`steps[${i}] is ${describe(step)}, expected an object.`)
      return
    }
    if (typeof step.op !== 'string' || !VALID_OPS.has(step.op as Op)) {
      fail(
        `steps[${i}].op is ${JSON.stringify(step.op)}; expected one of ${[...VALID_OPS].join(', ')}.`,
      )
    }
    if (!isObject(step.state)) {
      fail(`steps[${i}].state must be an object of node id to node state.`)
      return
    }
    for (const key of Object.keys(step.state)) {
      if (!ids.has(Number(key))) {
        fail(`steps[${i}].state["${key}"] refers to a node that is not declared.`)
        break
      }
    }
    for (const key of ['focus', 'path'] as const) {
      if (step[key] !== undefined && !Array.isArray(step[key])) {
        fail(`steps[${i}].${key} must be an array of node ids.`)
      }
    }
  })

  if (errors.length) return { ok: false, errors }

  // -- soft checks: loadable, but worth saying out loud --------------------
  const trace = raw as unknown as Trace
  const declared = (raw.result as Record<string, unknown>)?.nodes
  if (typeof declared === 'number' && declared !== nodes.length) {
    warnings.push(
      `result.nodes says ${declared} but the trace carries ${nodes.length} nodes.`,
    )
  }
  const unseen = trace.nodes.filter((n) => n.created_at >= trace.steps.length)
  if (unseen.length) {
    warnings.push(
      `${unseen.length} node(s) declare a created_at past the end of the trace and will never appear.`,
    )
  }

  return { ok: true, trace, warnings }
}

/** Read and validate a dropped or chosen file. Never rejects. */
export async function readTraceFile(file: File): Promise<ParseResult> {
  if (file.size > MAX_BYTES) {
    return {
      ok: false,
      errors: [
        `${file.name} is ${(file.size / 1e6).toFixed(1)} MB; the viewer accepts files up to ${MAX_BYTES / 1e6} MB.`,
      ],
    }
  }
  if (file.size === 0) {
    return { ok: false, errors: [`${file.name} is empty.`] }
  }
  if (!/\.json$/i.test(file.name)) {
    return {
      ok: false,
      errors: [
        `${file.name} is not a .json file. Traces are the JSON files written by "python scripts/run_lats.py".`,
      ],
    }
  }

  let text: string
  try {
    text = await file.text()
  } catch (err) {
    return { ok: false, errors: [`Could not read ${file.name}: ${String(err)}`] }
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(text)
  } catch (err) {
    // SyntaxError messages carry a character offset; turning it into a
    // line and column is the difference between a fixable report and a shrug.
    const message = err instanceof Error ? err.message : String(err)
    const at = /position (\d+)/.exec(message)
    let where = ''
    if (at) {
      const upto = text.slice(0, Number(at[1]))
      const line = upto.split('\n').length
      const col = upto.length - upto.lastIndexOf('\n')
      where = ` (line ${line}, column ${col})`
    }
    return {
      ok: false,
      errors: [`${file.name} is not valid JSON${where}: ${message}`],
    }
  }

  return validateTrace(parsed)
}

/** Validate the traces-folder index. A missing or broken one is not fatal. */
export function validateManifest(raw: unknown): Manifest | null {
  if (!isObject(raw) || !Array.isArray(raw.traces)) return null
  const traces = raw.traces.filter(
    (t): t is Manifest['traces'][number] =>
      isObject(t) && typeof t.file === 'string' && typeof t.name === 'string',
  )
  return { schema: String(raw.schema ?? ''), traces }
}
