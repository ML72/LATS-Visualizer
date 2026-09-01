/** Small formatting helpers, so numbers line up the same way everywhere. */

/** Fixed-width number, with the trailing zeros kept for column alignment. */
export function num(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '--'
  return v.toFixed(digits)
}

/** Compact number for tight spaces: 0.83, 1.4k, 173k. */
export function compact(v: number): string {
  if (Math.abs(v) >= 1e6) return `${(v / 1e6).toFixed(1)}M`
  if (Math.abs(v) >= 1e3) return `${(v / 1e3).toFixed(1)}k`
  return String(v)
}

export function titleOf(op: string): string {
  return op.charAt(0).toUpperCase() + op.slice(1)
}

export function truncate(text: string, max: number): string {
  return text.length <= max ? text : `${text.slice(0, max - 1)}…`
}

/** The paper's exploration bonus, recomputed so the w slider can vary it. */
export function exploreBonus(parentVisits: number, visits: number): number {
  if (visits <= 0 || parentVisits <= 0) return 0
  return Math.sqrt(Math.log(parentVisits) / visits)
}
