/**
 * LATS trace visualizer.
 *
 * Loads a trace written by `python scripts/run_lats.py` and replays it one
 * operation at a time: the tree on the left grows as the search grew, the
 * panel on the right shows the arithmetic behind whatever just happened.
 *
 * Traces come from two places. The ones committed in `public/traces/` are
 * served as static files under /traces/ and indexed by `traces-manifest.json`
 * beside that folder; anything the user drops on the window is validated and
 * held in memory for the session.
 *
 * **One app, laid out three ways.** On a desktop the tree and the panel sit
 * side by side, because reading the explanation while watching the tree is the
 * whole point. Narrow and tall - a tablet held upright - stacks them instead.
 * Below about a phone's width there is no honest way to show both at once, so
 * they become two tabs over a shared transport: the tree keeps every pixel it
 * can get, and tapping a node moves you to its detail rather than shrinking
 * both. Which of the three is in play is a separate question from how much
 * room the chrome may take, and the code keeps them separate.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import AppBar from '@mui/material/AppBar'
import Alert from '@mui/material/Alert'
import AlertTitle from '@mui/material/AlertTitle'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import CircularProgress from '@mui/material/CircularProgress'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import Paper from '@mui/material/Paper'
import Snackbar from '@mui/material/Snackbar'
import Stack from '@mui/material/Stack'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import Toolbar from '@mui/material/Toolbar'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
import DarkModeIcon from '@mui/icons-material/DarkModeOutlined'
import HelpOutlineIcon from '@mui/icons-material/HelpOutlineOutlined'
import LightModeIcon from '@mui/icons-material/LightModeOutlined'

import NodeDetail from './components/NodeDetail'
import OperationPanel from './components/OperationPanels'
import Timeline from './components/Timeline'
import TraceHeader from './components/TraceHeader'
import TracePicker, { type Source } from './components/TracePicker'
import TreeView from './components/TreeView'
import Tour, { type TourStop } from './components/Tour'
import { viewAt } from './lib/layout'
import { readTraceFile, validateManifest, validateTrace } from './lib/validate'
import type { Trace } from './types'
import {
  BAD,
  BG,
  EDGE,
  GOOD,
  INK,
  INK_DIM,
  INK_FAINT,
  MONO,
  OP_COLOR,
  PRIMARY,
  STROKE,
  SURFACE,
  alpha,
  useColorMode,
} from './theme'

/** Milliseconds per step at 1x. Slow enough to read the panel. */
const BASE_TICK = 1100

/** Where the bundled traces are served from, relative to the app's base. */
const TRACES = 'traces/'
/** Their index. Beside the folder rather than in it: it is not a trace. */
const MANIFEST = 'traces-manifest.json'

const url = (file: string) => new URL(file, document.baseURI).href

/** Which half of the app a phone is looking at. */
type Pane = 'tree' | 'step'

export default function App() {
  const [sources, setSources] = useState<Source[]>([])
  const [uploaded, setUploaded] = useState<Record<string, Trace>>({})
  const [current, setCurrent] = useState<string | null>(null)
  const [trace, setTrace] = useState<Trace | null>(null)
  const [loading, setLoading] = useState(true)
  const [errors, setErrors] = useState<string[] | null>(null)
  const [warnings, setWarnings] = useState<string[]>([])
  const [notice, setNotice] = useState<string | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)

  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [selected, setSelected] = useState<number | null>(null)
  const [pane, setPane] = useState<Pane>('tree')
  const [dragging, setDragging] = useState(false)
  const dragDepth = useRef(0)

  const [tour, setTour] = useState(0)
  const tourOffered = useRef(false)
  const pickerRef = useRef<HTMLDivElement>(null)
  const headerRef = useRef<HTMLDivElement>(null)
  const timelineRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)

  const { mode, toggle } = useColorMode()

  // Two questions, not one. *Is this a phone-sized screen* decides the chrome:
  // a folded-up header, a scrubber over two rows, an upload button with no
  // room for its label. *Is it too narrow for two columns* decides whether the
  // tree and the panel have to take turns. A handset held sideways answers yes
  // to the first and no to the second - it has width to spare and no height at
  // all - so it gets the small-screen chrome beside a side-by-side layout.
  const slim = useMediaQuery('(max-width: 700px)')
  // Bounded by width too, so that a short desktop window - a laptop with the
  // browser half the screen tall - keeps the layout it has.
  const short = useMediaQuery('(max-height: 560px) and (max-width: 900px)')
  const compact = slim || short
  const tabbed = slim

  const narrow = useMediaQuery('(max-width: 1100px)')
  // A tablet on its side has the width for two columns even though it is under
  // the narrow threshold, and stacking there wastes it.
  const sideways = useMediaQuery('(min-width: 900px) and (min-aspect-ratio: 5/4)')
  const stacked = narrow && !sideways && !compact

  // -- bundled traces ------------------------------------------------------

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(url(MANIFEST))
        if (!res.ok) throw new Error(`${MANIFEST} returned ${res.status}`)
        const manifest = validateManifest(await res.json())
        if (!manifest) throw new Error(`${MANIFEST} is not a trace index`)
        if (cancelled) return
        setSources(
          manifest.traces.map((entry) => ({
            key: `bundled:${entry.file}`,
            label: entry.name,
            kind: 'bundled' as const,
            file: entry.file,
            task: entry.task,
            taskTitle: entry.title,
            note: entry.note,
            solved: entry.solved,
          })),
        )
        if (manifest.traces.length === 0) {
          setBootError(
            `public/${MANIFEST} lists no traces. Run \`python scripts/run_lats.py --publish\` to generate them.`,
          )
          setLoading(false)
        }
      } catch (err) {
        if (cancelled) return
        setBootError(
          `Could not load ${MANIFEST} (${String(err)}). Run \`python scripts/run_lats.py --publish\` from the repository root, then reload. You can still upload a trace by hand.`,
        )
        setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // Select the first bundled trace once the index arrives. The manifest is in
  // reading order, so that is the introductory run, not an arbitrary one.
  useEffect(() => {
    if (!current && sources.length) setCurrent(sources[0].key)
  }, [sources, current])

  // -- loading the selected trace ------------------------------------------

  useEffect(() => {
    if (!current) return
    const source = sources.find((s) => s.key === current)
    if (!source) return

    if (source.kind === 'uploaded') {
      const t = uploaded[source.key]
      if (t) applyTrace(t)
      return
    }

    let cancelled = false
    setLoading(true)
    ;(async () => {
      try {
        const res = await fetch(url(`${TRACES}${source.file}`))
        if (!res.ok) throw new Error(`${source.file} returned ${res.status}`)
        const result = validateTrace(await res.json())
        if (cancelled) return
        if (!result.ok) {
          setErrors([`traces/${source.file} did not validate:`, ...result.errors])
          setLoading(false)
          return
        }
        setWarnings(result.warnings)
        applyTrace(result.trace)
      } catch (err) {
        if (cancelled) return
        setErrors([`Could not load traces/${source.file}: ${String(err)}`])
        setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current, sources])

  function applyTrace(t: Trace) {
    setTrace(t)
    setIndex(0)
    setSelected(null)
    setPlaying(false)
    setPane('tree')
    setLoading(false)
  }

  // -- the first-run tour --------------------------------------------------

  // Once per page load, after a trace has actually rendered - the tour points
  // at panels that do not exist until then. Deliberately not remembered
  // between visits: this is a demo people arrive at cold, and skipping it costs
  // one click.
  useEffect(() => {
    if (!trace || tourOffered.current) return
    // No rAF here: effects already run after the commit that mounted the
    // panels, and a deferred open would be cancelled by StrictMode's second
    // pass in development, which the ref guard would then refuse to retry.
    tourOffered.current = true
    setTour((n) => n + 1)
  }, [trace])

  const closeTour = useCallback(() => setTour(0), [])

  const stops: TourStop[] = useMemo(
    () => [
      {
        id: 'picker',
        title: 'Pick a run',
        body: 'Eleven searches ship with the viewer, grouped by environment: the plain run first, then the ablations that turn one knob off, then the same puzzle under a real model. Or drop a trace of your own on the window.',
        target: pickerRef,
        place: 'bottom',
      },
      {
        id: 'header',
        title: 'What is being searched',
        body: 'The task, and the settings this run used — n samples per expansion, the exploration weight w, the blend λ between the model’s own score and self-consistency. Hover any of them for what it means.',
        target: headerRef,
        place: 'bottom',
      },
      {
        id: 'timeline',
        title: 'Step through it',
        body: 'The strip shows the six operations of one LATS iteration and which are done. Scrub the timeline, or use ← and → to step and space to play. The tree above grows exactly as the search grew.',
        target: timelineRef,
        place: 'top',
      },
      {
        id: 'panel',
        title: 'Read what just happened',
        body: 'Every step is explained here with its own arithmetic — the two halves of UCT fighting over a branch, the samples that collapsed into one child, the reward travelling back up. Click any node in the tree for its full detail.',
        target: panelRef,
        place: 'left',
      },
    ],
    [],
  )

  // -- uploads -------------------------------------------------------------

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return
    const added: Source[] = []
    const traces: Record<string, Trace> = {}
    const problems: string[] = []

    for (const file of Array.from(files)) {
      const result = await readTraceFile(file)
      if (!result.ok) {
        problems.push(`${file.name}:`, ...result.errors.map((e) => `  ${e}`))
        continue
      }
      const key = `uploaded:${file.name}:${Date.now()}:${added.length}`
      traces[key] = result.trace
      added.push({
        key,
        label: result.trace.name || file.name,
        kind: 'uploaded',
        note: `${file.name} · ${result.trace.nodes.length} nodes · ${result.trace.steps.length} steps`,
        solved: result.trace.result?.solved,
      })
      if (result.warnings.length) problems.push(...result.warnings)
    }

    if (added.length) {
      setUploaded((prev) => ({ ...prev, ...traces }))
      setSources((prev) => [...prev, ...added])
      setCurrent(added[added.length - 1].key)
      setNotice(
        added.length === 1 ? `Loaded ${added[0].label}.` : `Loaded ${added.length} traces.`,
      )
    }
    if (problems.length) setErrors(problems)
  }, [])

  // Drag and drop anywhere on the window. The counter guards against the
  // dragleave that fires every time the pointer crosses a child element.
  useEffect(() => {
    const onOver = (e: DragEvent) => {
      e.preventDefault()
    }
    const onEnter = (e: DragEvent) => {
      e.preventDefault()
      dragDepth.current += 1
      if (e.dataTransfer?.types?.includes('Files')) setDragging(true)
    }
    const onLeave = () => {
      dragDepth.current = Math.max(0, dragDepth.current - 1)
      if (dragDepth.current === 0) setDragging(false)
    }
    const onDrop = (e: DragEvent) => {
      e.preventDefault()
      dragDepth.current = 0
      setDragging(false)
      void handleFiles(e.dataTransfer?.files ?? null)
    }
    window.addEventListener('dragover', onOver)
    window.addEventListener('dragenter', onEnter)
    window.addEventListener('dragleave', onLeave)
    window.addEventListener('drop', onDrop)
    return () => {
      window.removeEventListener('dragover', onOver)
      window.removeEventListener('dragenter', onEnter)
      window.removeEventListener('dragleave', onLeave)
      window.removeEventListener('drop', onDrop)
    }
  }, [handleFiles])

  // -- playback ------------------------------------------------------------

  const last = trace ? trace.steps.length - 1 : 0

  useEffect(() => {
    if (!playing || !trace) return
    if (index >= last) {
      setPlaying(false)
      return
    }
    const id = window.setTimeout(() => setIndex((i) => i + 1), BASE_TICK / speed)
    return () => window.clearTimeout(id)
  }, [playing, index, last, speed, trace])

  useEffect(() => {
    // The tour owns the arrow keys while it is up.
    if (tour > 0) return
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      if (target && /INPUT|TEXTAREA|SELECT/.test(target.tagName)) return
      if (e.key === 'ArrowRight') {
        setPlaying(false)
        setIndex((i) => Math.min(i + 1, last))
      } else if (e.key === 'ArrowLeft') {
        setPlaying(false)
        setIndex((i) => Math.max(i - 1, 0))
      } else if (e.key === ' ') {
        e.preventDefault()
        setPlaying((p) => !p)
      } else if (e.key === 'Home') {
        setIndex(0)
      } else if (e.key === 'End') {
        setIndex(last)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [last, tour])

  // -- derived -------------------------------------------------------------

  const view = useMemo(() => (trace ? viewAt(trace, index) : null), [trace, index])
  const selectedNode = useMemo(
    () => trace?.nodes.find((n) => n.id === selected) ?? null,
    [trace, selected],
  )

  const step = view?.step

  // Where a node's detail is going to appear is the other tab on a phone, so
  // picking one has to take you there; nothing else about selection changes.
  const select = useCallback(
    (id: number | null) => {
      setSelected(id)
      if (tabbed && id !== null) setPane('step')
    },
    [tabbed],
  )

  const gap = compact ? 1 : 1.5

  const header = trace && (
    <Box ref={headerRef}>
      <TraceHeader trace={trace} tokens={step?.tokens ?? 0} compact={compact} />
    </Box>
  )

  const tree = trace && view && (
    <TreeView
      key={trace.name}
      trace={trace}
      view={view}
      selected={selected}
      onSelect={select}
      // A phone in landscape has to buy the transport its row out of this one.
      minHeight={compact ? 120 : stacked ? 160 : 280}
    />
  )

  const timeline = trace && (
    <Box ref={timelineRef}>
      <Timeline
        trace={trace}
        index={index}
        playing={playing}
        speed={speed}
        onIndex={setIndex}
        onPlaying={setPlaying}
        onSpeed={setSpeed}
        compact={compact}
        short={short}
      />
    </Box>
  )

  const panel = trace && (
    <Paper
      ref={panelRef}
      elevation={0}
      sx={{
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        ...(tabbed
          ? { width: '100%', flex: 1, minHeight: 0 }
          : stacked
            ? // A share of the column rather than a floor, so the pair always
              // fits the window however short it is.
              { width: '100%', flex: '1 1 0', minHeight: 180 }
            : // Narrower beside a handset in landscape: there the tree is the
              // half that has nowhere else to go.
              { width: compact ? 340 : 436, flexShrink: 0, minHeight: 0 }),
      }}
    >
      {step && (
        <Box
          sx={{
            px: 1.75,
            py: 1.4,
            borderBottom: `1px solid ${STROKE}`,
            borderLeft: `3px solid ${OP_COLOR[step.op]}`,
            bgcolor: alpha(OP_COLOR[step.op], 0.045),
          }}
        >
          <Stack direction="row" spacing={1} sx={{ alignItems: 'baseline' }}>
            <Typography
              variant="subtitle2"
              sx={{ color: OP_COLOR[step.op], textTransform: 'uppercase' }}
            >
              {step.op}
            </Typography>
            <Typography variant="caption" sx={{ color: INK_FAINT, fontFamily: MONO }}>
              step {step.index + 1}
              {step.iteration ? ` · iteration ${step.iteration}` : ''}
            </Typography>
          </Stack>
          <Typography variant="body2" sx={{ mt: 0.4, color: INK }}>
            {step.summary}
          </Typography>
        </Box>
      )}

      <Box sx={{ flex: 1, overflowY: 'auto', p: 1.75, minHeight: 0 }}>
        {step && trace && <OperationPanel trace={trace} step={step} onSelect={select} />}
        {selectedNode && (
          <>
            <Divider sx={{ my: 1.75 }} />
            <NodeDetail
              node={selectedNode}
              state={view?.state(selectedNode.id)}
              onClose={() => setSelected(null)}
            />
          </>
        )}
      </Box>
    </Paper>
  )

  const picker = (
    <TracePicker
      sources={sources}
      current={current}
      disabled={loading}
      onSelect={(key) => setCurrent(key)}
      onUpload={handleFiles}
      compact={compact}
    />
  )

  return (
    <Box
      sx={{
        height: '100vh',
        // Phone browsers count the collapsing address bar as viewport height,
        // which puts the transport under it until you scroll something.
        '@supports (height: 100dvh)': { height: '100dvh' },
        display: 'flex',
        flexDirection: 'column',
        bgcolor: BG,
        overflow: 'hidden',
      }}
    >
      <AppBar
        position="static"
        elevation={0}
        sx={{ bgcolor: SURFACE, borderBottom: `1px solid ${STROKE}` }}
      >
        <Toolbar
          variant="dense"
          sx={{ gap: 1.5, minHeight: compact ? 52 : 58, px: { xs: 1.5, md: 2 } }}
        >
          <Mark />
          <Box sx={{ minWidth: 0 }}>
            {/* Truncated rather than wrapped where the bar is tight, which
                would otherwise push the whole app down a line. Off on a wide
                bar: `overflow: hidden` clips a descender by a pixel. */}
            <Typography
              noWrap={compact || stacked}
              sx={{ fontWeight: 680, color: INK, letterSpacing: '-0.014em', lineHeight: 1.2 }}
            >
              Language Agent Tree Search
            </Typography>
            <Typography
              variant="caption"
              sx={{ color: INK_FAINT, display: { xs: 'none', md: 'block' }, lineHeight: 1.2 }}
            >
              Trace visualizer · Zhou et al., ICML 2024
            </Typography>
          </Box>
          <Box sx={{ flex: 1 }} />
          {/* Wide enough for the picker: it belongs beside the title. On a
              phone it gets a row of its own, below. */}
          {!tabbed && <Box ref={pickerRef}>{picker}</Box>}
          <Tooltip title={mode === 'dark' ? 'Switch to light' : 'Switch to dark'} arrow>
            <IconButton
              size="small"
              onClick={toggle}
              aria-label={mode === 'dark' ? 'switch to light mode' : 'switch to dark mode'}
              sx={{ color: INK_FAINT }}
            >
              {mode === 'dark' ? (
                <LightModeIcon fontSize="small" />
              ) : (
                <DarkModeIcon fontSize="small" />
              )}
            </IconButton>
          </Tooltip>
          <Tooltip title="Show me around" arrow>
            <span>
              <IconButton
                size="small"
                disabled={!trace}
                onClick={() => setTour((n) => n + 1)}
                aria-label="show the tour"
                sx={{ color: INK_FAINT }}
              >
                <HelpOutlineIcon fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        </Toolbar>

        {tabbed && (
          <Box ref={pickerRef} sx={{ px: 1.5, pb: 1 }}>
            {picker}
          </Box>
        )}
      </AppBar>

      {warnings.length > 0 && (
        <Alert
          severity="warning"
          variant="outlined"
          onClose={() => setWarnings([])}
          sx={{ borderRadius: 0, borderLeft: 0, borderRight: 0 }}
        >
          {warnings.map((w, i) => (
            <div key={i}>{w}</div>
          ))}
        </Alert>
      )}

      {/* Everything below the bar fits the window at any size a phone comes
          in. Smaller than that - a tiny browser window, a handset from before
          they got tall, turned sideways - it scrolls rather than folding the
          transport under the tree. */}
      <Box sx={{ flex: 1, minHeight: 0, p: gap, overflowY: compact ? 'auto' : 'hidden' }}>
        {loading && !trace ? (
          <Centered>
            <CircularProgress size={22} />
            <Typography variant="body2" sx={{ color: INK_DIM }}>
              loading traces…
            </Typography>
          </Centered>
        ) : !trace ? (
          <Centered>
            <Typography variant="body2" sx={{ color: INK_DIM, maxWidth: 560, textAlign: 'center' }}>
              {bootError ??
                'No trace loaded. Upload one, or run `python scripts/run_lats.py --publish` to generate the bundled set.'}
            </Typography>
            <Button component="label" variant="outlined" size="small">
              Choose a trace file
              <input
                hidden
                type="file"
                accept="application/json,.json"
                multiple
                onChange={(e) => {
                  void handleFiles(e.target.files)
                  e.target.value = ''
                }}
              />
            </Button>
          </Centered>
        ) : tabbed ? (
          <Stack spacing={1} sx={{ minHeight: '100%' }}>
            {header}
            <Paper elevation={0} sx={{ flexShrink: 0, overflow: 'hidden' }}>
              <Tabs
                value={pane}
                onChange={(_, next: Pane) => setPane(next)}
                variant="fullWidth"
                sx={{ minHeight: 38 }}
              >
                <Tab value="tree" label="Tree" sx={TAB_SX} />
                <Tab
                  value="step"
                  sx={TAB_SX}
                  label={
                    <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
                      <Box
                        sx={{
                          width: 7,
                          height: 7,
                          borderRadius: '50%',
                          bgcolor: step ? OP_COLOR[step.op] : INK_FAINT,
                        }}
                      />
                      <span>Step{selectedNode ? ` · #${selectedNode.id}` : ''}</span>
                    </Stack>
                  }
                />
              </Tabs>
            </Paper>
            {/* Both panes are mounted only one at a time: the tree measures
                itself to lay out, and a hidden pane measures zero. */}
            <Box sx={{ flex: 1, minHeight: 0, display: 'flex' }}>
              {pane === 'tree' ? tree : panel}
            </Box>
            {timeline}
          </Stack>
        ) : (
          <Stack
            direction={stacked ? 'column' : 'row'}
            spacing={gap}
            sx={{ height: '100%', minHeight: 0 }}
          >
            <Stack spacing={gap} sx={{ flex: stacked ? 1.6 : 1, minWidth: 0, minHeight: 0 }}>
              {header}
              {tree}
              {timeline}
            </Stack>
            {panel}
          </Stack>
        )}
      </Box>

      <Tour key={tour} stops={stops} open={tour > 0 && !!trace} onClose={closeTour} />

      <Dialog
        open={errors !== null}
        onClose={() => setErrors(null)}
        maxWidth="sm"
        fullWidth
        fullScreen={compact}
      >
        <DialogTitle sx={{ pb: 1 }}>That file could not be loaded</DialogTitle>
        <DialogContent>
          <Alert severity="error" variant="outlined" sx={{ mb: 1.5 }}>
            <AlertTitle sx={{ fontSize: '0.85rem' }}>
              {errors?.length === 1 ? 'One problem' : `${errors?.length ?? 0} lines`}
            </AlertTitle>
            <Box component="ul" sx={{ m: 0, pl: 2 }}>
              {errors?.map((e, i) => (
                <Typography
                  component="li"
                  key={i}
                  variant="body2"
                  sx={{ fontFamily: MONO, fontSize: '0.75rem', wordBreak: 'break-word' }}
                >
                  {e}
                </Typography>
              ))}
            </Box>
          </Alert>
          <Typography variant="caption" sx={{ color: INK_DIM }}>
            A viewable trace is one of the JSON files written by{' '}
            <code>python scripts/run_lats.py</code>. The format is documented in the
            project README and in <code>scripts/run_lats/trace.py</code>.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setErrors(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={notice !== null}
        autoHideDuration={3500}
        onClose={() => setNotice(null)}
        message={notice}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      />

      {dragging && (
        <Box
          sx={{
            position: 'fixed',
            inset: 0,
            zIndex: 1400,
            display: 'grid',
            placeItems: 'center',
            bgcolor: alpha(BG, 0.9),
            border: `2px dashed ${PRIMARY}`,
          }}
        >
          <Typography variant="h6" sx={{ color: PRIMARY }}>
            Drop a trace .json to view it
          </Typography>
        </Box>
      )}
    </Box>
  )
}

/** Short enough to leave the tree its height, tall enough to hit with a thumb. */
const TAB_SX = { minHeight: 38, py: 0, fontSize: '0.8rem' }

/**
 * The three-node glyph the favicon uses, so the tab and the bar agree.
 *
 * Painted from the tokens rather than the favicon's literals - identical in
 * light, and lifted off the bar in dark. As everywhere a token reaches SVG,
 * the colours go through `style` rather than the `fill` attribute, because a
 * presentation attribute is not a place every browser resolves `var()`.
 */
function Mark() {
  return (
    <Box component="svg" viewBox="0 0 32 32" sx={{ width: 22, height: 22, flexShrink: 0 }}>
      <path
        d="M16 10 L7 20 M16 10 L25 20"
        strokeWidth={2.2}
        style={{ stroke: EDGE, fill: 'none' }}
      />
      <circle cx={16} cy={6} r={4} style={{ fill: PRIMARY }} />
      <circle cx={7} cy={24} r={4} style={{ fill: BAD }} />
      <circle cx={25} cy={24} r={4} style={{ fill: GOOD }} />
    </Box>
  )
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <Stack
      spacing={1.5}
      sx={{ alignItems: 'center', justifyContent: 'center', height: '100%' }}
    >
      {children}
    </Stack>
  )
}
