/**
 * The visual system.
 *
 * Light, because this is a teaching tool: it is read next to a paper, printed,
 * projected in a lit room and screenshotted into slides, and a near-black page
 * survives none of those well.
 *
 * The colour grammar is the one the explainer video uses, re-tuned for paper
 * rather than for a dark canvas. Colour carries meaning here exactly as it does
 * there:
 *
 *     blue    structure / the search algorithm itself
 *     amber   the thing you should be looking at right now
 *     green   high value, success, passing tests
 *     red     low value, failure, dead end
 *     violet  reflection
 *     teal    the environment / external feedback
 *
 * Every hue is picked to clear 4.5:1 against both the page and a card, so a
 * number that carries meaning is never the faint one on the screen.
 */

import { createTheme } from '@mui/material/styles'

/** The page. Cool grey, so a white card lifts off it without a shadow. */
export const BG = '#F4F6F9'
export const SURFACE = '#FFFFFF'
/** Insets and nested blocks: a panel inside a panel. */
export const SURFACE_2 = '#F4F6FA'
export const STROKE = '#E1E6ED'
/** Tree edges. Visible across a large canvas, but never the subject. */
export const EDGE = '#A9B4C4'

export const INK = '#141A24'
export const INK_DIM = '#48566A'
export const INK_FAINT = '#66717F'

export const PRIMARY = '#2563EB'
export const ACCENT = '#B45309'
export const GOOD = '#15803D'
export const BAD = '#DC2626'
export const VIOLET = '#7C3AED'
export const TEAL = '#0F766E'

/** A card's lift. One soft shadow, used everywhere, never stacked. */
export const CARD_SHADOW = '0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)'

/**
 * Stops for mapping a value in [0, 1] onto colour, chosen so that neighbouring
 * node values stay distinguishable in the middle of the range - which is where
 * most of the interesting search happens - and so that every stop is still
 * legible as text, because this ramp colours numbers as well as swatches.
 */
const VALUE_STOPS = ['#C81E1E', '#C2410C', '#A16207', '#4D7C0F', GOOD]

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
  simulation: '#4F46E5',
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
    mode: 'light',
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
    h6: { fontSize: '1.02rem', fontWeight: 650, letterSpacing: '-0.011em' },
    subtitle2: { fontSize: '0.72rem', fontWeight: 650, letterSpacing: '0.055em' },
    body2: { fontSize: '0.845rem', lineHeight: 1.6 },
    caption: { fontSize: '0.72rem', lineHeight: 1.5, color: INK_DIM },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          border: `1px solid ${STROKE}`,
          boxShadow: CARD_SHADOW,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontVariantNumeric: 'tabular-nums' },
        sizeSmall: { height: 21, fontSize: '0.7rem' },
        outlined: { borderColor: STROKE, backgroundColor: SURFACE_2 },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: '#1F2937',
          color: '#F8FAFC',
          fontSize: '0.75rem',
          lineHeight: 1.5,
          maxWidth: 340,
          padding: '6px 9px',
        },
        arrow: { color: '#1F2937' },
      },
    },
    MuiSelect: {
      styleOverrides: {
        // The picker is the control most people need first; give it a real
        // edge rather than the barely-there default.
        outlined: { backgroundColor: SURFACE },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        // The tree canvas and the inspector both scroll; keep those scrollbars
        // quiet rather than letting them draw a grey slab down the page.
        '*::-webkit-scrollbar': { width: 10, height: 10 },
        '*::-webkit-scrollbar-thumb': {
          background: '#CBD3DE',
          borderRadius: 5,
          border: `2px solid ${BG}`,
        },
        '*::-webkit-scrollbar-thumb:hover': { background: '#B3BDCB' },
        '*::-webkit-scrollbar-track': { background: 'transparent' },
      },
    },
  },
})
