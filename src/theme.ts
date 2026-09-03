/**
 * The visual system.
 *
 * Light by default, because this is a teaching tool: it is read next to a
 * paper, printed, projected in a lit room and screenshotted into slides, and a
 * near-black page survives none of those well. A dark ground is offered as a
 * choice - the same room that wants a projector at noon wants a dim screen at
 * midnight - and the choice is remembered, but it is never guessed from the
 * operating system.
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
 * Every hue is picked to clear 4.5:1 against both the page and a card, in
 * either mode, so a number that carries meaning is never the faint one on the
 * screen.
 *
 * **How the two modes are wired.** Every token below is emitted twice as a CSS
 * custom property, once under `:root` and once under `:root[data-theme=dark]`,
 * and the names exported from this file are `var(...)` references rather than
 * literals. Switching mode is therefore one attribute on `<html>`: nothing
 * re-renders to change colour, and no component needs to know which mode it is
 * in. The price is that a token is no longer a number JavaScript can do
 * arithmetic on, so the two derivations that used to be hex maths - `alpha` and
 * the value ramp - are written as `color-mix` instead, which the browser
 * resolves against whichever mode is live.
 *
 * MUI's own palette is the exception: it derives hover states and disabled
 * greys by decomposing the colours it is given, so `makeTheme` is handed the
 * literal hex for the current mode and is rebuilt when the mode changes.
 */

import { createContext, useContext } from 'react'
import { createTheme } from '@mui/material/styles'

export type Mode = 'light' | 'dark'

/**
 * One name per token. Everything the app paints with is here: a colour
 * hard-coded in a component is a colour that cannot follow the mode.
 */
type Token =
  | 'bg'
  | 'surface'
  | 'surface2'
  | 'stroke'
  | 'edge'
  | 'ink'
  | 'inkDim'
  | 'inkFaint'
  | 'primary'
  | 'accent'
  | 'good'
  | 'bad'
  | 'violet'
  | 'teal'
  | 'indigo'
  | 'rail'
  | 'mark'
  | 'scrim'
  | 'ring'
  | 'tooltip'
  | 'tooltipInk'
  | 'thumb'
  | 'thumbHover'
  | 'shadow'
  | 'v0'
  | 'v1'
  | 'v2'
  | 'v3'
  | 'v4'

type Palette = Record<Token, string>

/** Cool grey page, so a white card lifts off it without a shadow. */
const LIGHT: Palette = {
  bg: '#F4F6F9',
  surface: '#FFFFFF',
  /** Insets and nested blocks: a panel inside a panel. */
  surface2: '#F4F6FA',
  stroke: '#E1E6ED',
  /** Tree edges. Visible across a large canvas, but never the subject. */
  edge: '#A9B4C4',

  ink: '#141A24',
  inkDim: '#48566A',
  inkFaint: '#66717F',

  primary: '#2563EB',
  accent: '#B45309',
  good: '#15803D',
  bad: '#DC2626',
  violet: '#7C3AED',
  teal: '#0F766E',
  indigo: '#4F46E5',

  rail: '#DDE3EB',
  mark: '#C4CCD8',
  scrim: 'rgba(15, 23, 42, 0.55)',
  ring: '#F59E0B',
  tooltip: '#1F2937',
  tooltipInk: '#F8FAFC',
  thumb: '#CBD3DE',
  thumbHover: '#B3BDCB',

  /** A card's lift. One soft shadow, used everywhere, never stacked. */
  shadow: '0 1px 2px rgba(16, 24, 40, 0.04), 0 1px 3px rgba(16, 24, 40, 0.06)',

  /**
   * Stops for mapping a value in [0, 1] onto colour, chosen so that
   * neighbouring node values stay distinguishable in the middle of the range -
   * which is where most of the interesting search happens - and so that every
   * stop is still legible as text, because this ramp colours numbers as well
   * as swatches.
   */
  v0: '#C81E1E',
  v1: '#C2410C',
  v2: '#A16207',
  v3: '#4D7C0F',
  v4: '#15803D',
}

/**
 * The same grammar on a dark ground. Not an inversion: the hues are re-picked
 * for a dark card the way the light ones were picked for paper, and the value
 * ramp is lifted with them, because a red that clears 4.5:1 on white clears
 * about 3:1 on near-black.
 */
const DARK: Palette = {
  bg: '#10141B',
  surface: '#181D26',
  surface2: '#212734',
  stroke: '#2C3442',
  edge: '#5D6C82',

  ink: '#E8EDF4',
  inkDim: '#AEB9C9',
  inkFaint: '#8492A6',

  primary: '#6BA6FF',
  accent: '#EFB13B',
  good: '#4FC97E',
  bad: '#F87171',
  violet: '#A78BFA',
  teal: '#3ECFC0',
  indigo: '#8B8CF6',

  rail: '#2E3743',
  mark: '#46525F',
  scrim: 'rgba(2, 4, 8, 0.68)',
  ring: '#F0B429',
  tooltip: '#2C3442',
  tooltipInk: '#E8EDF4',
  thumb: '#39434F',
  thumbHover: '#4A5766',

  shadow: '0 1px 2px rgba(0, 0, 0, 0.45), 0 1px 3px rgba(0, 0, 0, 0.30)',

  v0: '#F2777A',
  v1: '#F0A05A',
  v2: '#E3C74F',
  v3: '#A6D45C',
  v4: '#4FC97E',
}

const PALETTES: Record<Mode, Palette> = { light: LIGHT, dark: DARK }

const cssName = (token: Token) =>
  `--lats-${token.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}`

const ref = (token: Token) => `var(${cssName(token)})`

const block = (palette: Palette) =>
  Object.fromEntries(
    (Object.keys(palette) as Token[]).map((token) => [cssName(token), palette[token]]),
  )

export const BG = ref('bg')
export const SURFACE = ref('surface')
export const SURFACE_2 = ref('surface2')
export const STROKE = ref('stroke')
export const EDGE = ref('edge')

export const INK = ref('ink')
export const INK_DIM = ref('inkDim')
export const INK_FAINT = ref('inkFaint')

export const PRIMARY = ref('primary')
export const ACCENT = ref('accent')
export const GOOD = ref('good')
export const BAD = ref('bad')
export const VIOLET = ref('violet')
export const TEAL = ref('teal')

/** The transport slider's own greys, which are neither stroke nor ink. */
export const RAIL = ref('rail')
export const MARK = ref('mark')
/** The tour's scrim, and the ring it draws on it. */
export const SCRIM = ref('scrim')
export const RING = ref('ring')

export const CARD_SHADOW = ref('shadow')

const VALUE_STOPS: Token[] = ['v0', 'v1', 'v2', 'v3', 'v4']

/** Trim a percentage to something readable: 4.5%, not 4.5000%. */
const pct = (fraction: number) => `${Number((fraction * 100).toFixed(4))}%`

/** Map a node value in [0, 1] onto the red-amber-green ramp. */
export function valueColor(v: number): string {
  const clamped = Math.min(Math.max(v, 0), 1)
  const span = VALUE_STOPS.length - 1
  const idx = Math.min(Math.floor(clamped * span), span - 1)
  const t = clamped * span - idx
  // `color-mix(in srgb, A x%, B)` is the same linear ramp the hex maths used to
  // walk, except the browser re-runs it whenever the mode changes.
  return `color-mix(in srgb, ${ref(VALUE_STOPS[idx])} ${pct(1 - t)}, ${ref(
    VALUE_STOPS[idx + 1],
  )})`
}

/** Semi-transparent fill derived from any colour, token or literal. */
export function alpha(color: string, a: number): string {
  return `color-mix(in srgb, ${color} ${pct(a)}, transparent)`
}

/** One colour per operation, used by the timeline and the step headers. */
export const OP_COLOR: Record<string, string> = {
  init: INK_FAINT,
  selection: PRIMARY,
  expansion: ACCENT,
  evaluation: TEAL,
  simulation: ref('indigo'),
  backpropagation: GOOD,
  reflection: VIOLET,
  result: INK,
}

export const MONO =
  '"JetBrains Mono", "Fira Code", "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace'

const SANS =
  'Inter, "Source Sans 3", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'

export function makeTheme(mode: Mode) {
  const hex = PALETTES[mode]
  return createTheme({
    palette: {
      mode,
      background: { default: hex.bg, paper: hex.surface },
      primary: { main: hex.primary },
      secondary: { main: hex.accent },
      success: { main: hex.good },
      error: { main: hex.bad },
      warning: { main: hex.accent },
      info: { main: hex.teal },
      text: { primary: hex.ink, secondary: hex.inkDim, disabled: hex.inkFaint },
      divider: hex.stroke,
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
            backgroundColor: ref('tooltip'),
            color: ref('tooltipInk'),
            fontSize: '0.75rem',
            lineHeight: 1.5,
            maxWidth: 340,
            padding: '6px 9px',
          },
          arrow: { color: ref('tooltip') },
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
          // Both modes are always defined; `data-theme` on <html> picks one.
          ':root': block(LIGHT),
          ":root[data-theme='dark']": block(DARK),
          // Without this a phone rubber-bands the whole app shell whenever a
          // drag on the tree canvas runs past its edge.
          body: { overscrollBehavior: 'none' },
          // The tree canvas and the inspector both scroll; keep those
          // scrollbars quiet rather than letting them draw a grey slab down
          // the page.
          '*::-webkit-scrollbar': { width: 10, height: 10 },
          '*::-webkit-scrollbar-thumb': {
            background: ref('thumb'),
            borderRadius: 5,
            border: `2px solid ${BG}`,
          },
          '*::-webkit-scrollbar-thumb:hover': { background: ref('thumbHover') },
          '*::-webkit-scrollbar-track': { background: 'transparent' },
        },
      },
    },
  })
}

// -- the mode itself ---------------------------------------------------------

/** Matches the key read by the inline script in `index.html`. */
const STORED = 'lats-theme'

/** The remembered choice, or light. Never the operating system's preference. */
export function storedMode(): Mode {
  try {
    const saved = localStorage.getItem(STORED)
    if (saved === 'light' || saved === 'dark') return saved
  } catch {
    // A browser with storage denied still gets a working viewer, in light.
  }
  return 'light'
}

/**
 * Put the mode on the document: the `data-theme` attribute the token blocks key
 * off, `color-scheme` so native scrollbars and form controls follow, and the
 * colour a phone paints its address bar with.
 */
export function applyMode(mode: Mode) {
  const root = document.documentElement
  root.setAttribute('data-theme', mode)
  root.style.colorScheme = mode
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute('content', PALETTES[mode].surface)
  try {
    localStorage.setItem(STORED, mode)
  } catch {
    // Not being able to remember the choice is no reason to refuse to make it.
  }
}

export const ColorModeContext = createContext<{ mode: Mode; toggle: () => void }>({
  mode: 'light',
  toggle: () => {},
})

export const useColorMode = () => useContext(ColorModeContext)
