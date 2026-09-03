/** The task being searched, and how this particular run was configured. */

import { useState } from 'react'
import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import Collapse from '@mui/material/Collapse'
import IconButton from '@mui/material/IconButton'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'

import type { Trace } from '../types'
import { num } from '../lib/format'
import { ACCENT, GOOD, INK, INK_DIM, INK_FAINT, MONO, TEAL, alpha } from '../theme'

export default function TraceHeader({
  trace,
  tokens,
  compact,
}: {
  trace: Trace
  /** Tokens spent as of the current step, not the total for the run. */
  tokens: number
  /**
   * Phone: the prompt and the settings fold away behind the title, because on
   * a screen this size every line they take comes out of the tree.
   */
  compact?: boolean
}) {
  const { config: cfg, result, policy } = trace
  const [open, setOpen] = useState(false)

  const solved = (
    <Chip
      size="small"
      label={result.solved ? 'solved' : 'not solved'}
      sx={{
        bgcolor: alpha(result.solved ? GOOD : ACCENT, 0.16),
        color: result.solved ? GOOD : ACCENT,
        fontWeight: 700,
      }}
    />
  )

  const spent = (
    <Tooltip
      title={
        policy.tokens_are_estimated
          ? 'Estimated at four characters per token: the offline policy makes no API calls, so there is nothing to measure.'
          : 'Reported by the API.'
      }
    >
      <Typography sx={{ fontFamily: MONO, fontSize: '0.75rem', color: TEAL }}>
        {tokens.toLocaleString()} tokens{policy.tokens_are_estimated ? '*' : ''}
      </Typography>
    </Tooltip>
  )

  const settings = (
    <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.5, mt: 1 }}>
      <Meta label="n" value={String(cfg.n)} title="samples per expansion" />
      <Meta label="w" value={String(cfg.w)} title="exploration weight in UCT" />
      <Meta
        label="λ"
        value={String(cfg.lambda)}
        title="weight on the model's own evaluation, against self-consistency"
      />
      <Meta label="depth" value={`≤ ${cfg.max_depth}`} title="hard depth limit" />
      {!cfg.simulate && <Meta label="simulation" value="off" title="the paper skips it in the programming setting" />}
      {!cfg.reflect && <Meta label="reflection" value="off" title="ablation" />}
      <Meta
        label="best"
        value={num(result.best_reward)}
        title={`stopped because ${result.stopped_because}`}
      />
      <Meta
        label="policy"
        value={policy.kind === 'mock' ? `mock · seed ${policy.seed}` : (policy.model ?? policy.name)}
        title={
          policy.kind === 'mock'
            ? 'Deterministic offline sampler. The environment is real; the policy is not.'
            : 'Sampled from a real model.'
        }
      />
    </Stack>
  )

  if (compact) {
    return (
      <Paper elevation={0} sx={{ px: 1.25, py: 0.6 }}>
        <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', minWidth: 0 }}>
          <Typography
            noWrap
            sx={{ fontWeight: 650, fontSize: '0.9rem', color: INK, flex: 1, minWidth: 0 }}
          >
            {trace.task.title}
          </Typography>
          {solved}
          {spent}
          <IconButton
            size="small"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? 'hide the task and its settings' : 'show the task and its settings'}
            sx={{ flexShrink: 0, color: INK_FAINT, p: 0.25 }}
          >
            <ExpandMoreIcon
              fontSize="small"
              sx={{
                transform: open ? 'rotate(180deg)' : 'none',
                transition: 'transform 160ms ease',
              }}
            />
          </IconButton>
        </Stack>
        <Collapse in={open} unmountOnExit>
          <Typography variant="body2" sx={{ color: INK_DIM, mt: 0.5 }}>
            {trace.task.prompt}
          </Typography>
          {settings}
        </Collapse>
      </Paper>
    )
  }

  return (
    <Paper elevation={0} sx={{ px: 1.5, py: 1.25 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'baseline', flexWrap: 'wrap' }}>
        <Typography variant="h6" sx={{ color: INK }}>
          {trace.task.title}
        </Typography>
        {solved}
        <Box sx={{ flex: 1 }} />
        {spent}
      </Stack>

      <Typography variant="body2" sx={{ color: INK_DIM, mt: 0.25 }}>
        {trace.task.prompt}
      </Typography>

      {settings}
    </Paper>
  )
}

function Meta({
  label,
  value,
  title,
}: {
  label: string
  value: string
  title: string
}) {
  return (
    <Tooltip title={title} arrow>
      <Chip
        size="small"
        variant="outlined"
        label={
          <>
            <Box component="span" sx={{ color: INK_FAINT }}>
              {label}
            </Box>{' '}
            <Box component="span" sx={{ fontFamily: MONO }}>
              {value}
            </Box>
          </>
        }
      />
    </Tooltip>
  )
}
