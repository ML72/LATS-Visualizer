/**
 * Everything about one node, for when the tree card is not enough.
 *
 * The observation `detail` object is task-specific by design, so this renders
 * the shapes it knows - a program and its test results, a chain of arithmetic,
 * a retrieved document - and falls back to formatted JSON for anything else.
 * A new task therefore shows up here usefully without touching this file.
 */

import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import Divider from '@mui/material/Divider'
import IconButton from '@mui/material/IconButton'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import CloseIcon from '@mui/icons-material/Close'

import type { NodeState, TraceNode } from '../types'
import { num } from '../lib/format'
import {
  BAD,
  GOOD,
  INK,
  INK_DIM,
  INK_FAINT,
  MONO,
  STROKE,
  SURFACE,
  SURFACE_2,
  TEAL,
  VIOLET,
  alpha,
  valueColor,
} from '../theme'

interface Props {
  node: TraceNode
  state: NodeState | undefined
  onClose: () => void
}

export default function NodeDetail({ node, state, onClose }: Props) {
  return (
    <Paper elevation={0} sx={{ p: 1.5, bgcolor: SURFACE_2 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mb: 1 }}>
        <Typography variant="subtitle2" sx={{ color: INK, letterSpacing: 0 }}>
          #{node.id} {node.label}
        </Typography>
        <Box sx={{ flex: 1 }} />
        <IconButton size="small" onClick={onClose} aria-label="close node detail">
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>

      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
        <Chip size="small" label={`depth ${node.depth}`} />
        {state && (
          <>
            <Chip
              size="small"
              label={`V ${num(state.value)}`}
              sx={{ color: valueColor(state.value) }}
            />
            <Chip size="small" label={`N ${state.visits}`} />
            {state.lm !== null && <Chip size="small" label={`LM ${num(state.lm)}`} />}
            {state.sc !== null && <Chip size="small" label={`SC ${num(state.sc)}`} />}
            {state.reward !== null && (
              <Chip
                size="small"
                label={`reward ${num(state.reward)}`}
                sx={{
                  bgcolor: alpha(valueColor(state.reward), 0.18),
                  color: valueColor(state.reward),
                }}
              />
            )}
          </>
        )}
        {node.terminal && <Chip size="small" label="terminal" variant="outlined" />}
        {state?.reflected && (
          <Chip
            size="small"
            label="reflected"
            sx={{ bgcolor: alpha(VIOLET, 0.16), color: VIOLET }}
          />
        )}
      </Stack>

      {node.action && (
        <>
          <Label>Action</Label>
          <Typography variant="body2" sx={{ mb: 1 }}>
            {node.action}
          </Typography>
        </>
      )}

      {node.observation && (
        <>
          <Label>Observation</Label>
          <Typography variant="body2" sx={{ color: TEAL, mb: 1 }}>
            {node.observation}
          </Typography>
        </>
      )}

      <DetailBody detail={node.detail} />
    </Paper>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <Typography
      variant="subtitle2"
      sx={{ color: INK_FAINT, textTransform: 'uppercase', fontSize: '0.68rem' }}
    >
      {children}
    </Typography>
  )
}

function Code({ children }: { children: string }) {
  return (
    <Box
      component="pre"
      sx={{
        m: 0,
        mb: 1,
        p: 1,
        maxHeight: 260,
        overflow: 'auto',
        border: `1px solid ${STROKE}`,
        borderRadius: 1,
        bgcolor: SURFACE,
        fontFamily: MONO,
        fontSize: '0.72rem',
        lineHeight: 1.5,
        color: INK,
        whiteSpace: 'pre',
      }}
    >
      {children}
    </Box>
  )
}

interface TestResult {
  call: string
  expect: string
  got: string
  passed: boolean
}

function DetailBody({ detail }: { detail: Record<string, unknown> }) {
  if (!detail || Object.keys(detail).length === 0) return null

  const known = new Set([
    'code',
    'results',
    'passed',
    'total',
    'error',
    'steps',
    'final',
    'target',
    'expression',
    'answer',
    'gold',
    'exact_match',
    'query',
    'document',
    'remaining',
  ])
  const rest = Object.fromEntries(
    Object.entries(detail).filter(([k]) => !known.has(k)),
  )

  return (
    <Stack spacing={0.5}>
      {typeof detail.code === 'string' && (
        <>
          <Label>Program</Label>
          <Code>{detail.code}</Code>
        </>
      )}

      {typeof detail.error === 'string' && detail.error && (
        <Typography variant="caption" sx={{ color: BAD, fontFamily: MONO }}>
          {detail.error}
        </Typography>
      )}

      {Array.isArray(detail.results) && (
        <>
          <Label>
            Tests — {String(detail.passed ?? '?')} of {String(detail.total ?? '?')} pass
          </Label>
          <Stack spacing={0.3} sx={{ mb: 1 }}>
            {(detail.results as TestResult[]).map((r, i) => (
              <Stack key={i} direction="row" spacing={0.75} sx={{ alignItems: 'flex-start' }}>
                <Typography
                  sx={{
                    fontFamily: MONO,
                    fontSize: '0.72rem',
                    color: r.passed ? GOOD : BAD,
                    width: 12,
                    flexShrink: 0,
                  }}
                >
                  {r.passed ? '✓' : '✗'}
                </Typography>
                <Box sx={{ minWidth: 0 }}>
                  <Typography
                    sx={{ fontFamily: MONO, fontSize: '0.7rem', color: INK_DIM }}
                  >
                    {r.call}
                  </Typography>
                  {!r.passed && (
                    <Typography
                      sx={{ fontFamily: MONO, fontSize: '0.7rem', color: BAD }}
                    >
                      got {r.got}, expected {r.expect}
                    </Typography>
                  )}
                </Box>
              </Stack>
            ))}
          </Stack>
        </>
      )}

      {Array.isArray(detail.steps) && (detail.steps as string[]).length > 0 && (
        <>
          <Label>Arithmetic so far</Label>
          <Stack spacing={0.2} sx={{ mb: 1 }}>
            {(detail.steps as string[]).map((s, i) => (
              <Typography key={i} sx={{ fontFamily: MONO, fontSize: '0.74rem' }}>
                {s}
              </Typography>
            ))}
          </Stack>
        </>
      )}

      {detail.final !== undefined && (
        <Typography sx={{ fontFamily: MONO, fontSize: '0.74rem', mb: 1 }}>
          final {String(detail.final)} · target {String(detail.target)}
        </Typography>
      )}

      {typeof detail.query === 'string' && (
        <>
          <Label>Retrieval</Label>
          <Typography sx={{ fontFamily: MONO, fontSize: '0.74rem', mb: 1 }}>
            search[{detail.query}] → {String(detail.document ?? 'no match')}
          </Typography>
        </>
      )}

      {typeof detail.answer === 'string' && (
        <>
          <Label>Answer</Label>
          <Typography sx={{ fontFamily: MONO, fontSize: '0.74rem' }}>
            {detail.answer}
          </Typography>
          <Typography
            sx={{
              fontFamily: MONO,
              fontSize: '0.74rem',
              color: detail.exact_match ? GOOD : BAD,
              mb: 1,
            }}
          >
            gold {String(detail.gold)} · {detail.exact_match ? 'exact match' : 'no match'}
          </Typography>
        </>
      )}

      {Object.keys(rest).length > 0 && (
        <>
          <Divider sx={{ my: 0.5 }} />
          <Label>Other fields</Label>
          <Code>{JSON.stringify(rest, null, 2)}</Code>
        </>
      )}
    </Stack>
  )
}
