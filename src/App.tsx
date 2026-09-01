/**
 * LATS trace viewer.
 *
 * Loads a trace written by `python scripts/run_lats.py` and replays it one
 * operation at a time: the tree on the left grows as the search grew, the
 * panel on the right shows the arithmetic behind whatever just happened.
 *
 * Traces come from two places. The ones committed in `public/traces/` are
 * served as static files under /traces/, and anything the user drops on the
 * window is validated and held in memory for the session.
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
import Paper from '@mui/material/Paper'
import Snackbar from '@mui/material/Snackbar'
import Stack from '@mui/material/Stack'
import Toolbar from '@mui/material/Toolbar'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'

import NodeDetail from './components/NodeDetail'
import OperationPanel from './components/OperationPanels'
import Timeline from './components/Timeline'
import TraceHeader from './components/TraceHeader'
import TracePicker, { type Source } from './components/TracePicker'
import TreeView from './components/TreeView'
import { layoutTree, viewAt } from './lib/layout'
import { readTraceFile, validateManifest, validateTrace } from './lib/validate'
import type { Trace } from './types'
import {
  BG,
  INK,
  INK_DIM,
  INK_FAINT,
  MONO,
  OP_COLOR,
  PRIMARY,
  STROKE,
  SURFACE,
  alpha,
} from './theme'

/** Milliseconds per step at 1x. Slow enough to read the panel. */
const BASE_TICK = 1100

/** Where the bundled traces are served from, relative to the app's base. */
const TRACES = 'traces/'

const url = (file: string) => new URL(file, document.baseURI).href

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
  const [dragging, setDragging] = useState(false)
  const dragDepth = useRef(0)

  const narrow = useMediaQuery('(max-width: 1100px)')

  // -- bundled traces ------------------------------------------------------

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(url(`${TRACES}manifest.json`))
        if (!res.ok) throw new Error(`manifest.json returned ${res.status}`)
        const manifest = validateManifest(await res.json())
        if (!manifest) throw new Error('manifest.json is not a trace index')
        if (cancelled) return
        setSources(
          manifest.traces.map((entry) => ({
            key: `bundled:${entry.file}`,
            label: entry.name,
            kind: 'bundled' as const,
            file: entry.file,
            note: entry.note,
            solved: entry.solved,
          })),
        )
        if (manifest.traces.length === 0) {
          setBootError(
            'public/traces/manifest.json lists no traces. Run `python scripts/run_lats.py --publish` to generate them.',
          )
          setLoading(false)
        }
      } catch (err) {
        if (cancelled) return
        setBootError(
          `Could not load traces/manifest.json (${String(err)}). Run \`python scripts/run_lats.py --publish\` from the repository root, then reload. You can still upload a trace by hand.`,
        )
        setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  // Select the first bundled trace once the index arrives.
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
    setLoading(false)
  }

  // -- uploads -------------------------------------------------------------

  const handleFiles = useCallback(
    async (files: FileList | null) => {
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
          added.length === 1
            ? `Loaded ${added[0].label}.`
            : `Loaded ${added.length} traces.`,
        )
      }
      if (problems.length) setErrors(problems)
    },
    [],
  )

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
  }, [last])

  // -- derived -------------------------------------------------------------

  const layout = useMemo(() => (trace ? layoutTree(trace.nodes) : null), [trace])
  const view = useMemo(() => (trace ? viewAt(trace, index) : null), [trace, index])
  const selectedNode = useMemo(
    () => trace?.nodes.find((n) => n.id === selected) ?? null,
    [trace, selected],
  )

  const step = view?.step

  return (
    <Box
      sx={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: BG,
        overflow: 'hidden',
      }}
    >
      <AppBar position="static" elevation={0} sx={{ bgcolor: SURFACE, borderBottom: `1px solid ${STROKE}` }}>
        <Toolbar variant="dense" sx={{ gap: 1.5, minHeight: 54 }}>
          <Typography sx={{ fontWeight: 700, color: INK, letterSpacing: '-0.01em' }}>
            Language Agent Tree Search
          </Typography>
          <Typography variant="caption" sx={{ color: INK_FAINT, display: { xs: 'none', md: 'block' } }}>
            trace viewer
          </Typography>
          <Box sx={{ flex: 1 }} />
          <TracePicker
            sources={sources}
            current={current}
            disabled={loading}
            onSelect={(key) => setCurrent(key)}
            onUpload={handleFiles}
          />
        </Toolbar>
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

      <Box sx={{ flex: 1, minHeight: 0, p: 1.25 }}>
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
        ) : (
          <Stack
            direction={narrow ? 'column' : 'row'}
            spacing={1.25}
            sx={{ height: '100%', minHeight: 0 }}
          >
            <Stack spacing={1.25} sx={{ flex: 1, minWidth: 0, minHeight: 0 }}>
              <TraceHeader trace={trace} tokens={step?.tokens ?? 0} />
              {layout && view && (
                <TreeView
                  trace={trace}
                  layout={layout}
                  view={view}
                  selected={selected}
                  onSelect={setSelected}
                />
              )}
              <Timeline
                trace={trace}
                index={index}
                playing={playing}
                speed={speed}
                onIndex={setIndex}
                onPlaying={setPlaying}
                onSpeed={setSpeed}
              />
            </Stack>

            <Paper
              elevation={0}
              sx={{
                width: narrow ? '100%' : 430,
                flexShrink: 0,
                display: 'flex',
                flexDirection: 'column',
                minHeight: narrow ? 320 : 0,
              }}
            >
              {step && (
                <Box
                  sx={{
                    px: 1.5,
                    py: 1.25,
                    borderBottom: `1px solid ${STROKE}`,
                    borderLeft: `3px solid ${OP_COLOR[step.op]}`,
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
                  <Typography variant="body2" sx={{ mt: 0.4 }}>
                    {step.summary}
                  </Typography>
                </Box>
              )}

              <Box sx={{ flex: 1, overflowY: 'auto', p: 1.5, minHeight: 0 }}>
                {step && (
                  <OperationPanel trace={trace} step={step} onSelect={setSelected} />
                )}
                {selectedNode && (
                  <>
                    <Divider sx={{ my: 1.5 }} />
                    <NodeDetail
                      node={selectedNode}
                      state={view?.state(selectedNode.id)}
                      onClose={() => setSelected(null)}
                    />
                  </>
                )}
              </Box>
            </Paper>
          </Stack>
        )}
      </Box>

      <Dialog open={errors !== null} onClose={() => setErrors(null)} maxWidth="sm" fullWidth>
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
            <code>python scripts/run_lats.py</code>. The format is documented in
            the project README and in <code>scripts/run_lats/trace.py</code>.
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
            bgcolor: alpha(BG, 0.86),
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
