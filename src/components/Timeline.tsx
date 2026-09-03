/**
 * Transport controls, and the strip of six operations.
 *
 * The operation strip is the same spine the explainer video uses. Whatever
 * else is on screen, it should always be obvious which of the six things the
 * algorithm is doing right now, and which ones it has already done this
 * iteration.
 *
 * On a phone the same parts are dealt into more rows rather than shrunk: the
 * six operations wrap to two rows of three so they keep their real names, and
 * the transport gets a row to itself at a size a thumb can hit. Turned
 * sideways, where rows are the scarce thing, the controls go back onto one
 * line. Everything the desktop layout can do, every one of them can do.
 */

import Box from '@mui/material/Box'
import IconButton from '@mui/material/IconButton'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import Select from '@mui/material/Select'
import Slider from '@mui/material/Slider'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import FirstPageIcon from '@mui/icons-material/FirstPage'
import LastPageIcon from '@mui/icons-material/LastPage'
import NavigateBeforeIcon from '@mui/icons-material/NavigateBefore'
import NavigateNextIcon from '@mui/icons-material/NavigateNext'
import PauseIcon from '@mui/icons-material/Pause'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'

import type { Trace } from '../types'
import { OPS } from '../types'
import { iterationStarts } from '../lib/layout'
import {
  INK,
  INK_DIM,
  INK_FAINT,
  MARK,
  MONO,
  OP_COLOR,
  RAIL,
  STROKE,
  SURFACE_2,
  alpha,
} from '../theme'

interface Props {
  trace: Trace
  index: number
  playing: boolean
  speed: number
  onIndex: (i: number) => void
  onPlaying: (p: boolean) => void
  onSpeed: (s: number) => void
  /** Phone: more rows, bigger targets, no iteration labels under the scrubber. */
  compact?: boolean
  /** ...unless it is a phone on its side, where rows are the scarce thing and
      the controls go back onto one line. */
  short?: boolean
}

export default function Timeline({
  trace,
  index,
  playing,
  speed,
  onIndex,
  onPlaying,
  onSpeed,
  compact,
  short,
}: Props) {
  // Small chrome, but stacked into two rows only where there is height to
  // spend on the second one.
  const stackControls = compact && !short
  /** A thumb needs more of a target than a mouse does. */
  const hit = compact ? 'medium' : 'small'
  const last = trace.steps.length - 1
  const step = trace.steps[Math.min(Math.max(index, 0), last)]
  const marks = iterationStarts(trace).map((m) => ({
    value: m.index,
    // The labels are the first thing to go when there is no room for them:
    // the ticks still say where an iteration starts.
    label:
      compact || !(m.iteration % 2 === 1 || trace.steps.length < 40)
        ? ''
        : String(m.iteration),
  }))

  // Which of the six have already happened in this iteration, so the strip
  // reads as progress through a cycle rather than a static legend.
  const doneThisIteration = new Set(
    trace.steps
      .slice(0, index + 1)
      .filter((s) => s.iteration === step.iteration)
      .map((s) => s.op),
  )

  const buttons = (
    <Stack direction="row" sx={{ flexShrink: 0 }}>
      <Tooltip title="First step  ·  Home">
        <span>
          <IconButton size={hit} disabled={index === 0} onClick={() => onIndex(0)}>
            <FirstPageIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      <Tooltip title="Previous step  ·  ←">
        <span>
          <IconButton
            size={hit}
            disabled={index === 0}
            onClick={() => onIndex(index - 1)}
          >
            <NavigateBeforeIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      <Tooltip title={`${playing ? 'Pause' : 'Play'}  ·  space`}>
        <IconButton
          size={hit}
          color="primary"
          onClick={() => onPlaying(!playing)}
        >
          {playing ? <PauseIcon /> : <PlayArrowIcon />}
        </IconButton>
      </Tooltip>
      <Tooltip title="Next step  ·  →">
        <span>
          <IconButton
            size={hit}
            disabled={index === last}
            onClick={() => onIndex(index + 1)}
          >
            <NavigateNextIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
      <Tooltip title="Last step  ·  End">
        <span>
          <IconButton
            size={hit}
            disabled={index === last}
            onClick={() => onIndex(last)}
          >
            <LastPageIcon fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
    </Stack>
  )

  const scrubber = (
    <Slider
      size="small"
      min={0}
      max={last}
      step={1}
      value={index}
      marks={marks}
      onChange={(_, v) => {
        onPlaying(false)
        onIndex(v as number)
      }}
      sx={{
        flex: 1,
        minWidth: 60,
        mx: 1,
        '& .MuiSlider-markLabel': { fontSize: '0.62rem', color: INK_FAINT, top: 21 },
        '& .MuiSlider-mark': { backgroundColor: MARK, height: 6, width: '1px' },
        '& .MuiSlider-rail': { opacity: 1, backgroundColor: RAIL },
      }}
    />
  )

  const rate = (
    <Select
      size="small"
      value={speed}
      onChange={(e) => onSpeed(Number(e.target.value))}
      sx={{
        flexShrink: 0,
        fontSize: '0.74rem',
        '& .MuiSelect-select': { py: 0.4, color: INK },
      }}
    >
      {[0.5, 1, 2, 4].map((s) => (
        <MenuItem key={s} value={s} sx={{ fontSize: '0.78rem' }}>
          {s}×
        </MenuItem>
      ))}
    </Select>
  )

  return (
    <Paper elevation={0} sx={{ p: compact ? 1 : 1.25, overflow: 'hidden' }}>
      <OpStrip compact={compact}>
        {OPS.map((op) => {
          const isNow = step.op === op
          const done = doneThisIteration.has(op)
          const color = OP_COLOR[op]
          return (
            <Tooltip key={op} title={op} arrow>
              <Box
                sx={{
                  px: 0.5,
                  py: 0.45,
                  borderRadius: 0.75,
                  textAlign: 'center',
                  border: `1px solid ${isNow ? color : STROKE}`,
                  bgcolor: isNow
                    ? alpha(color, 0.13)
                    : done
                      ? alpha(color, 0.055)
                      : SURFACE_2,
                  boxShadow: isNow ? `inset 0 0 0 1px ${alpha(color, 0.35)}` : 'none',
                  transition: 'background-color 140ms ease, border-color 140ms ease',
                  minWidth: 0,
                  // Ignored by the grid, and what makes the flex row equal.
                  flex: 1,
                }}
              >
                <Typography
                  noWrap
                  sx={{
                    fontSize: '0.66rem',
                    fontWeight: isNow ? 700 : 500,
                    letterSpacing: '0.03em',
                    color: isNow ? color : done ? color : INK_FAINT,
                  }}
                >
                  {op}
                </Typography>
              </Box>
            </Tooltip>
          )
        })}
      </OpStrip>

      {stackControls ? (
        <>
          <Stack direction="row" sx={{ alignItems: 'center', minWidth: 0 }}>
            {scrubber}
            <Typography
              sx={{
                flexShrink: 0,
                fontFamily: MONO,
                fontSize: '0.72rem',
                color: INK_DIM,
              }}
            >
              {index + 1}/{last + 1}
              <Box component="span" sx={{ color: INK_FAINT }}>
                {step.iteration ? ` · it ${step.iteration}` : ''}
              </Box>
            </Typography>
          </Stack>
          <Stack direction="row" sx={{ alignItems: 'center' }}>
            {buttons}
            <Box sx={{ flex: 1 }} />
            {rate}
          </Stack>
        </>
      ) : (
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center', minWidth: 0 }}>
          {buttons}
          {scrubber}

          <Stack sx={{ flexShrink: 0, textAlign: 'right', minWidth: compact ? 64 : 96 }}>
            <Typography sx={{ fontFamily: MONO, fontSize: '0.74rem', color: INK_DIM }}>
              {compact ? '' : 'step '}
              {index + 1}/{last + 1}
            </Typography>
            <Typography variant="caption" sx={{ color: INK_FAINT, lineHeight: 1.2 }}>
              iteration {step.iteration || '—'}
            </Typography>
          </Stack>

          {rate}
        </Stack>
      )}
    </Paper>
  )
}

/**
 * The six operations, in one row or in two.
 *
 * A phone gets a grid of three columns, so a name is never shrunk past
 * reading; anything wider keeps the flex row it always had, down to how the
 * browser rounds the leftover pixel between six equal columns.
 */
function OpStrip({
  compact,
  children,
}: {
  compact?: boolean
  children: React.ReactNode
}) {
  if (compact) {
    return (
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
          gap: 0.5,
          mb: 0.9,
        }}
      >
        {children}
      </Box>
    )
  }
  return (
    <Stack direction="row" spacing={0.5} sx={{ mb: 0.9 }}>
      {children}
    </Stack>
  )
}
