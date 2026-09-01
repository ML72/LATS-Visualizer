/**
 * The visual system, ported from `scripts/create_video/theme.py`.
 *
 * The video and this viewer are two windows onto the same algorithm, so they
 * use one palette and one colour grammar. Colour carries meaning here exactly
 * as it does there:
 *
 *     blue    structure / the search algorithm itself
 *     amber   the thing you should be looking at right now
 *     green   high value, success, passing tests
 *     red     low value, failure, dead end
 *     violet  reflection
 *     teal    the environment / external feedback
 */

import { createTheme } from '@mui/material/styles'

export const BG = '#0E1117'
export const SURFACE = '#161C25'
export const SURFACE_2 = '#1F2733'
export const STROKE = '#2E3947'
export const EDGE = '#4A5A6E'

export const INK = '#EEF2F7'
export const INK_DIM = '#93A1B5'
export const INK_FAINT = '#5B6879'

export const PRIMARY = '#4EA8FF'
export const ACCENT = '#FFB547'
export const GOOD = '#3DD68C'
export const BAD = '#FF6B6B'
export const VIOLET = '#B98CFF'
export const TEAL = '#2DD4BF'

/**
 * Stops for mapping a value in [0, 1] onto colour, chosen so that neighbouring
 * node values stay distinguishable in the middle of the range - which is where
 * most of the interesting search happens.
 */
const VALUE_STOPS = ['#F2565B', '#FF8A3D', '#FFC24A', '#A9D95E', GOOD]

function mix(a: string, b: string, t: number): string {
  const parse = (hex: string) => [
    parseInt(hex.slice(1, 3), 16),
    parseInt(hex.slice(3, 5), 16),
    parseInt(hex.slice(5, 7), 16),
  ]
  const [r1, g1, b1] = parse(a)
  const [r2, g2, b2] = parse(b)
  const to = (x: number) => Math.round(x).toString(16).padStart(2, '0')
  return `#${to(r1 + (r2 - r1) * t)}${to(g1 + (g2 - g1) * t)}${to(b1 + (b2 - b1) * t)}`
}

/** Map a node value in [0, 1] onto the red-amber-green ramp. */
export function valueColor(v: number): string {
  const clamped = Math.min(Math.max(v, 0), 1)
  const span = VALUE_STOPS.length - 1
  const idx = Math.min(Math.floor(clamped * span), span - 1)
  return mix(VALUE_STOPS[idx], VALUE_STOPS[idx + 1], clamped * span - idx)
}

/** Semi-transparent fill derived from a hex colour. */
export function alpha(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`
}

/** One colour per operation, used by the timeline and the step headers. */
export const OP_COLOR: Record<string, string> = {
  init: INK_FAINT,
  selection: PRIMARY,
  expansion: ACCENT,
  evaluation: TEAL,
  simulation: '#8AB4F8',
  backpropagation: GOOD,
  reflection: VIOLET,
  result: INK,
}

export const MONO =
  '"JetBrains Mono", "Fira Code", "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace'

const SANS =
  'Inter, "Source Sans 3", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'

export const theme = createTheme({
  palette: {
    mode: 'dark',
    background: { default: BG, paper: SURFACE },
    primary: { main: PRIMARY },
    secondary: { main: ACCENT },
    success: { main: GOOD },
    error: { main: BAD },
    warning: { main: ACCENT },
    info: { main: TEAL },
    text: { primary: INK, secondary: INK_DIM, disabled: INK_FAINT },
    divider: STROKE,
  },
  shape: { borderRadius: 8 },
  typography: {
    fontFamily: SANS,
    fontSize: 14,
    h6: { fontSize: '1rem', fontWeight: 600, letterSpacing: 0 },
    subtitle2: { fontSize: '0.78rem', fontWeight: 600, letterSpacing: '0.04em' },
    body2: { fontSize: '0.84rem', lineHeight: 1.55 },
    caption: { fontSize: '0.72rem', color: INK_DIM },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: { backgroundImage: 'none', border: `1px solid ${STROKE}` },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontVariantNumeric: 'tabular-nums' },
        sizeSmall: { height: 20, fontSize: '0.7rem' },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: SURFACE_2,
          border: `1px solid ${STROKE}`,
          fontSize: '0.75rem',
          maxWidth: 340,
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        // The tree canvas and the inspector both scroll; make those scrollbars
        // quiet rather than chrome-coloured slabs over a near-black page.
        '*::-webkit-scrollbar': { width: 10, height: 10 },
        '*::-webkit-scrollbar-thumb': {
          background: STROKE,
          borderRadius: 5,
          border: `2px solid ${BG}`,
        },
        '*::-webkit-scrollbar-track': { background: 'transparent' },
      },
    },
  },
})
