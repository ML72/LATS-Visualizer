/**
 * One panel per operation: what the algorithm just did, with its arithmetic.
 *
 * These are the reason the viewer exists. A tree that grows is pretty; a tree
 * that grows *and shows you the two terms of UCT fighting over which branch to
 * take* is an explanation. Every number shown here is read from the trace or
 * recomputed from it - none of it is illustrative.
 */

import { useState } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import Divider from '@mui/material/Divider'
import Slider from '@mui/material/Slider'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'

import type {
  BackpropDetail,
  EvaluationDetail,
  ExpansionDetail,
  InitDetail,
  ReflectionDetail,
  SelectionDetail,
  SimulationDetail,
  Step,
  Trace,
  TraceResult,
} from '../types'
import { exploreBonus, num } from '../lib/format'
import {
  ACCENT,
  BAD,
  GOOD,
  INK,
  INK_DIM,
  INK_FAINT,
  MONO,
  PRIMARY,
  STROKE,
  SURFACE_2,
  TEAL,
  VIOLET,
  alpha,
  valueColor,
} from '../theme'

interface PanelProps {
  trace: Trace
  step: Step
  onSelect: (id: number) => void
}

export default function OperationPanel(props: PanelProps) {
  switch (props.step.op) {
    case 'init':
      return <InitPanel {...props} />
    case 'selection':
      // Keyed on the step so the w slider resets to what this step actually
      // used, rather than carrying over the last value someone dragged to.
      return <SelectionPanel key={props.step.index} {...props} />
    case 'expansion':
      return <ExpansionPanel {...props} />
    case 'evaluation':
      return <EvaluationPanel {...props} />
    case 'simulation':
      return <SimulationPanel {...props} />
    case 'backpropagation':
      return <BackpropPanel {...props} />
    case 'reflection':
      return <ReflectionPanel {...props} />
    case 'result':
      return <ResultPanel {...props} />
    default:
      return null
  }
}

// -- shared bits -------------------------------------------------------------

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <Typography
      variant="subtitle2"
      sx={{ color: INK_FAINT, textTransform: 'uppercase', mt: 0.5 }}
    >
      {children}
    </Typography>
  )
}

function NodeChip({
  id,
  label,
  color = PRIMARY,
  onSelect,
}: {
  id: number
  label?: string
  color?: string
  onSelect?: (id: number) => void
}) {
  return (
    <Chip
      size="small"
      label={label ? `#${id} ${label}` : `#${id}`}
      onClick={onSelect ? () => onSelect(id) : undefined}
      sx={{
        bgcolor: alpha(color, 0.14),
        color,
        border: `1px solid ${alpha(color, 0.45)}`,
        fontFamily: MONO,
        maxWidth: '100%',
      }}
    />
  )
}

/** A stacked horizontal bar. Segments are drawn in order, left to right. */
function StackBar({
  segments,
  max,
  height = 14,
}: {
  segments: { value: number; color: string; title: string }[]
  max: number
  height?: number
}) {
  const scale = max > 0 ? 100 / max : 0
  return (
    <Box
      sx={{
        display: 'flex',
        height,
        borderRadius: 0.5,
        overflow: 'hidden',
        bgcolor: alpha(INK_FAINT, 0.12),
        width: '100%',
      }}
    >
      {segments.map((seg, i) => (
        <Tooltip key={i} title={seg.title} arrow>
          <Box
            sx={{
              width: `${Math.max(0, seg.value) * scale}%`,
              bgcolor: seg.color,
              transition: 'width 160ms ease',
            }}
          />
        </Tooltip>
      ))}
    </Box>
  )
}

function Mono({ children }: { children: React.ReactNode }) {
  return (
    <Typography component="span" sx={{ fontFamily: MONO, fontSize: '0.78rem' }}>
      {children}
    </Typography>
  )
}

function Callout({
  color,
  children,
}: {
  color: string
  children: React.ReactNode
}) {
  return (
    <Box
      sx={{
        borderLeft: `3px solid ${color}`,
        bgcolor: alpha(color, 0.07),
        px: 1.25,
        py: 1,
        borderRadius: '0 4px 4px 0',
      }}
    >
      {children}
    </Box>
  )
}

// -- init --------------------------------------------------------------------

function InitPanel({ trace, step }: PanelProps) {
  const detail = step.detail as unknown as InitDetail
  const context = detail.task?.context ?? {}
  return (
    <Stack spacing={1.5}>
      <Typography variant="body2">{detail.task?.prompt}</Typography>
      <Callout color={TEAL}>
        <Typography variant="caption" sx={{ color: TEAL, fontWeight: 700 }}>
          REWARD
        </Typography>
        <Typography variant="body2">{detail.task?.reward}</Typography>
      </Callout>
      {Object.entries(context).map(([heading, lines]) => (
        <Box key={heading}>
          <SectionLabel>{heading}</SectionLabel>
          <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
            {lines.map((line) => (
              <Typography
                component="li"
                key={line}
                sx={{ fontFamily: MONO, fontSize: '0.75rem', color: INK_DIM }}
              >
                {line}
              </Typography>
            ))}
          </Box>
        </Box>
      ))}
      <SectionLabel>Search settings</SectionLabel>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.5 }}>
        <Chip size="small" label={`n = ${trace.config.n}`} />
        <Chip size="small" label={`w = ${trace.config.w}`} />
        <Chip size="small" label={`λ = ${trace.config.lambda}`} />
        <Chip size="small" label={`depth ≤ ${trace.config.max_depth}`} />
        <Chip size="small" label={`${trace.config.iterations} iterations`} />
        {!trace.config.simulate && <Chip size="small" label="no simulation" />}
        {!trace.config.reflect && <Chip size="small" label="no reflection" />}
      </Stack>
    </Stack>
  )
}

// -- 1. selection ------------------------------------------------------------

/**
 * The tug-of-war.
 *
 * Each child gets two stacked bars: V(s) it has earned, and the exploration
 * bonus it is owed for being under-visited. The `w` slider re-runs the
 * arithmetic live - drag it and watch which branch wins change. That is the
 * whole intuition behind the constant, in about four seconds.
 */
function SelectionPanel({ trace, step, onSelect }: PanelProps) {
  const detail = step.detail as unknown as SelectionDetail
  const traceW = trace.config.w
  const [w, setW] = useState(traceW)

  const level = detail.levels?.[detail.levels.length - 1]

  if (detail.exhausted) {
    return (
      <Alert severity="info" variant="outlined">
        Every branch is terminal or at the depth limit, so there is nothing left to
        select. The search stops here.
      </Alert>
    )
  }
  if (!level) {
    return (
      <Typography variant="body2" sx={{ color: INK_DIM }}>
        The root has never been expanded, so selection stops there immediately.
      </Typography>
    )
  }

  const rows = level.children.map((c) => {
    const bonus = exploreBonus(level.parent_visits, c.visits)
    return { ...c, bonus, live: c.exploit + w * bonus }
  })
  const available = rows.filter((r) => r.available)
  const liveMax = Math.max(...rows.map((r) => r.live), 0.001)
  const liveBest = available.length
    ? available.reduce((a, b) => (b.live > a.live ? b : a))
    : null
  const actual = rows.find((r) => r.chosen)
  const flipped = liveBest && actual && liveBest.id !== actual.id

  return (
    <Stack spacing={1.5}>
      <Callout color={PRIMARY}>
        <Mono>UCT(s) = V(s) + w · √( ln N(p) / N(s) )</Mono>
        <Typography variant="caption" sx={{ display: 'block', color: INK_DIM, mt: 0.5 }}>
          Children of node #{level.parent}, which has been visited{' '}
          {level.parent_visits} time{level.parent_visits === 1 ? '' : 's'}.
        </Typography>
      </Callout>

      <Stack spacing={1.1}>
        {rows.map((row) => {
          const isActual = row.chosen
          const isLive = liveBest?.id === row.id
          return (
            <Box key={row.id} sx={{ opacity: row.available ? 1 : 0.45 }}>
              <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', mb: 0.4 }}>
                <NodeChip
                  id={row.id}
                  label={row.label}
                  color={isLive ? ACCENT : PRIMARY}
                  onSelect={onSelect}
                />
                <Box sx={{ flex: 1 }} />
                <Typography
                  sx={{
                    fontFamily: MONO,
                    fontSize: '0.78rem',
                    color: isLive ? ACCENT : INK,
                    fontWeight: isLive ? 700 : 400,
                  }}
                >
                  {num(row.live)}
                </Typography>
              </Stack>
              <StackBar
                max={liveMax}
                segments={[
                  {
                    value: row.exploit,
                    color: alpha(valueColor(row.exploit), 0.95),
                    title: `V(s) = ${num(row.exploit)} — what this branch has earned`,
                  },
                  {
                    value: w * row.bonus,
                    color: alpha(PRIMARY, 0.55),
                    title: `w · √(ln ${level.parent_visits} / ${row.visits}) = ${num(w * row.bonus)} — what it is owed for being under-visited`,
                  },
                ]}
              />
              <Typography
                variant="caption"
                sx={{ color: INK_FAINT, fontFamily: MONO, fontSize: '0.68rem' }}
              >
                {num(row.exploit)} exploit + {num(w * row.bonus)} explore · N ={' '}
                {row.visits}
                {!row.available && ' · closed'}
                {isActual && ' · taken'}
              </Typography>
            </Box>
          )
        })}
      </Stack>

      <Divider />

      <Box>
        <Stack direction="row" spacing={1} sx={{ alignItems: 'baseline' }}>
          <Typography variant="subtitle2" sx={{ color: INK_DIM }}>
            exploration weight w
          </Typography>
          <Typography sx={{ fontFamily: MONO, color: ACCENT }}>{w.toFixed(2)}</Typography>
          {w !== traceW && (
            <Typography variant="caption" sx={{ color: INK_FAINT }}>
              (this run used {traceW})
            </Typography>
          )}
        </Stack>
        <Slider
          size="small"
          min={0}
          max={3}
          step={0.05}
          value={w}
          onChange={(_, v) => setW(v as number)}
          marks={[
            { value: 0, label: '0' },
            { value: traceW, label: 'run' },
            { value: 3, label: '3' },
          ]}
          sx={{ mt: -0.5 }}
        />
        <Typography variant="caption" sx={{ color: flipped ? ACCENT : INK_FAINT }}>
          {flipped
            ? `At w = ${w.toFixed(2)} selection would take #${liveBest!.id} instead of #${actual!.id}.`
            : 'Drag w to see how much exploration it takes to change the answer.'}
        </Typography>
      </Box>
    </Stack>
  )
}

// -- 2. expansion ------------------------------------------------------------

function ExpansionPanel({ step, onSelect }: PanelProps) {
  const detail = step.detail as unknown as ExpansionDetail
  const notes = detail.reflections_in_context ?? []
  return (
    <Stack spacing={1.5}>
      <Typography variant="body2" sx={{ color: INK_DIM }}>
        {detail.n} samples drawn from node #{detail.parent}. Samples that reach the
        same state are one child; how many agreed becomes SC(s).
      </Typography>

      {notes.length > 0 && (
        <Callout color={VIOLET}>
          <Typography variant="caption" sx={{ color: VIOLET, fontWeight: 700 }}>
            {notes.length} REFLECTION{notes.length === 1 ? '' : 'S'} IN CONTEXT
          </Typography>
          {notes.map((note, i) => (
            <Typography key={i} variant="body2" sx={{ mt: 0.5 }}>
              {note.split('|')[0].trim()}
            </Typography>
          ))}
        </Callout>
      )}

      <Stack spacing={1}>
        {detail.children.map((child, i) => (
          <Box
            key={child.id ?? `rejected-${i}`}
            sx={{
              border: `1px solid ${STROKE}`,
              borderRadius: 1,
              p: 1,
              bgcolor: alpha(SURFACE_2, 0.6),
            }}
          >
            {child.rejected ? (
              <Stack spacing={0.5}>
                <Typography variant="body2" sx={{ color: BAD }}>
                  {child.label} — rejected by the environment
                </Typography>
                <Typography variant="caption" sx={{ fontFamily: MONO, color: INK_FAINT }}>
                  {child.rejected}
                </Typography>
              </Stack>
            ) : (
              <Stack spacing={0.6}>
                <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
                  <NodeChip
                    id={child.id!}
                    label={child.label}
                    color={ACCENT}
                    onSelect={onSelect}
                  />
                  <Box sx={{ flex: 1 }} />
                  <Chip
                    size="small"
                    label={`${child.samples}/${detail.n} samples`}
                    sx={{ bgcolor: alpha(TEAL, 0.12), color: TEAL }}
                  />
                </Stack>
                {child.text && (
                  <Typography variant="body2" sx={{ color: INK }}>
                    {child.text}
                  </Typography>
                )}
                {child.observation && (
                  <Stack direction="row" spacing={0.75} sx={{ alignItems: 'flex-start' }}>
                    <Typography variant="caption" sx={{ color: TEAL, fontWeight: 700 }}>
                      ENV
                    </Typography>
                    <Typography variant="caption" sx={{ color: INK_DIM }}>
                      {child.observation}
                    </Typography>
                  </Stack>
                )}
              </Stack>
            )}
          </Box>
        ))}
      </Stack>
    </Stack>
  )
}

// -- 3. evaluation -----------------------------------------------------------

function EvaluationPanel({ step, onSelect }: PanelProps) {
  const detail = step.detail as unknown as EvaluationDetail
  const lam = detail.lam
  return (
    <Stack spacing={1.5}>
      <Callout color={TEAL}>
        <Mono>V(s) = λ · LM(s) + (1 − λ) · SC(s)</Mono>
        <Typography variant="caption" sx={{ display: 'block', color: INK_DIM, mt: 0.5 }}>
          λ = {lam}. LM(s) is the model grading its own idea; SC(s) is how many of
          the samples agreed. Both are computed <em>after</em> the environment has
          replied — that ordering is what separates LATS from Tree of Thoughts.
        </Typography>
      </Callout>

      <Stack spacing={1.1}>
        {detail.scores.map((score) => (
          <Box key={score.id}>
            <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', mb: 0.4 }}>
              <NodeChip
                id={score.id}
                label={score.label}
                color={TEAL}
                onSelect={onSelect}
              />
              <Box sx={{ flex: 1 }} />
              <Typography sx={{ fontFamily: MONO, fontSize: '0.78rem' }}>
                {num(score.value)}
              </Typography>
            </Stack>
            <StackBar
              max={1}
              segments={[
                {
                  value: lam * score.lm,
                  color: alpha(PRIMARY, 0.85),
                  title: `λ·LM = ${lam} × ${num(score.lm)} = ${num(lam * score.lm)}`,
                },
                {
                  value: (1 - lam) * score.sc,
                  color: alpha(TEAL, 0.85),
                  title: `(1−λ)·SC = ${num(1 - lam)} × ${num(score.sc)} = ${num((1 - lam) * score.sc)}`,
                },
              ]}
            />
            <Stack direction="row" spacing={1} sx={{ mt: 0.3 }}>
              <Typography variant="caption" sx={{ color: PRIMARY, fontFamily: MONO }}>
                LM {num(score.lm)}
              </Typography>
              <Typography variant="caption" sx={{ color: TEAL, fontFamily: MONO }}>
                SC {num(score.sc)}
              </Typography>
              {score.reward !== null && score.reward !== undefined && (
                <Typography
                  variant="caption"
                  sx={{ color: valueColor(score.reward), fontFamily: MONO, ml: 'auto' }}
                >
                  environment says {num(score.reward)}
                </Typography>
              )}
            </Stack>
          </Box>
        ))}
      </Stack>

      {detail.scores.some((s) => s.reward !== null && s.reward !== undefined) && (
        <Typography variant="caption" sx={{ color: INK_FAINT }}>
          Where both are present, compare the bar against the environment number.
          The gap between them is exactly what backpropagation is about to correct.
        </Typography>
      )}
    </Stack>
  )
}

// -- 4. simulation -----------------------------------------------------------

function SimulationPanel({ trace, step, onSelect }: PanelProps) {
  const detail = step.detail as unknown as SimulationDetail
  const byId = new Map(trace.nodes.map((n) => [n.id, n]))
  return (
    <Stack spacing={1.5}>
      {detail.skipped ? (
        <Alert severity="info" variant="outlined">
          {step.summary}
        </Alert>
      ) : (
        <Typography variant="body2" sx={{ color: INK_DIM }}>
          Not a random playout: LATS descends by highest value, in the real
          environment, until it reaches a terminal state.
        </Typography>
      )}

      <Stack spacing={0.5}>
        {detail.rollout.map((id, i) => (
          <Stack key={id} direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
            <Typography sx={{ color: INK_FAINT, fontFamily: MONO, width: 16 }}>
              {i === 0 ? '·' : '↓'}
            </Typography>
            <NodeChip
              id={id}
              label={byId.get(id)?.label}
              color={i === detail.rollout.length - 1 ? ACCENT : PRIMARY}
              onSelect={onSelect}
            />
          </Stack>
        ))}
      </Stack>

      {detail.truncated && (
        <Alert severity="warning" variant="outlined">
          This rollout hit the depth limit without the environment declaring a
          terminal state, so it scores zero rather than inheriting a reward it never
          earned.
        </Alert>
      )}

      {detail.observation && (
        <Callout color={TEAL}>
          <Typography variant="caption" sx={{ color: TEAL, fontWeight: 700 }}>
            ENVIRONMENT
          </Typography>
          <Typography variant="body2">{detail.observation}</Typography>
        </Callout>
      )}
    </Stack>
  )
}

// -- 5. backpropagation ------------------------------------------------------

function BackpropPanel({ trace, step, onSelect }: PanelProps) {
  const detail = step.detail as unknown as BackpropDetail
  const byId = new Map(trace.nodes.map((n) => [n.id, n]))
  return (
    <Stack spacing={1.5}>
      <Callout color={GOOD}>
        <Mono>N(s) ← N(s) + 1 &nbsp;&nbsp; V(s) ← ( V(s)·(N(s)−1) + r ) / N(s)</Mono>
        <Typography variant="caption" sx={{ display: 'block', color: INK_DIM, mt: 0.5 }}>
          Reward r = {num(detail.reward)} from node #{detail.leaf}. Section 4.2 of the
          paper prints this rule with subscripts that do not match its own
          pseudocode; Algorithm 1 is the one to follow.
        </Typography>
      </Callout>

      <Stack spacing={0.75}>
        {detail.updates.map((update) => {
          const delta = update.after.value - update.before.value
          return (
            <Stack
              key={update.id}
              direction="row"
             
              spacing={1}
              sx={{ alignItems: 'center', border: `1px solid ${STROKE}`,
                borderRadius: 1,
                px: 1,
                py: 0.6, }}
            >
              <NodeChip
                id={update.id}
                label={byId.get(update.id)?.label}
                color={GOOD}
                onSelect={onSelect}
              />
              <Box sx={{ flex: 1 }} />
              <Typography sx={{ fontFamily: MONO, fontSize: '0.75rem', color: INK_FAINT }}>
                {num(update.before.value)} → {num(update.after.value)}
              </Typography>
              <Typography
                sx={{
                  fontFamily: MONO,
                  fontSize: '0.75rem',
                  color: delta >= 0 ? GOOD : BAD,
                  width: 52,
                  textAlign: 'right',
                }}
              >
                {delta >= 0 ? '+' : ''}
                {num(delta)}
              </Typography>
              <Typography
                sx={{ fontFamily: MONO, fontSize: '0.7rem', color: INK_FAINT, width: 34 }}
              >
                N {update.after.visits}
              </Typography>
            </Stack>
          )
        })}
      </Stack>
      <Typography variant="caption" sx={{ color: INK_FAINT }}>
        Every ancestor now knows something it did not know before. That is the only
        mechanism by which a failure deep in one branch can move the search into a
        different one.
      </Typography>
    </Stack>
  )
}

// -- 6. reflection -----------------------------------------------------------

function ReflectionPanel({ trace, step, onSelect }: PanelProps) {
  const detail = step.detail as unknown as ReflectionDetail
  const byId = new Map(trace.nodes.map((n) => [n.id, n]))
  return (
    <Stack spacing={1.5}>
      <Typography variant="body2" sx={{ color: INK_DIM }}>
        The one operation with no counterpart in AlphaGo-style MCTS. A scalar says{' '}
        <em>how bad</em>; a reflection says <em>why</em>, in words, and those words go
        back into the prompt.
      </Typography>

      <Callout color={VIOLET}>
        <Typography variant="caption" sx={{ color: VIOLET, fontWeight: 700 }}>
          NOTE WRITTEN AFTER NODE #{detail.node} SCORED {num(detail.reward)}
        </Typography>
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          {detail.text}
        </Typography>
      </Callout>

      <SectionLabel>The trajectory it came from</SectionLabel>
      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.5 }}>
        {detail.trajectory.map((id) => (
          <NodeChip
            key={id}
            id={id}
            label={byId.get(id)?.label}
            color={VIOLET}
            onSelect={onSelect}
          />
        ))}
      </Stack>

      <Typography variant="caption" sx={{ color: INK_FAINT }}>
        {detail.total_notes} note{detail.total_notes === 1 ? '' : 's'} now in context
        for every later expansion.
      </Typography>
    </Stack>
  )
}

// -- result ------------------------------------------------------------------

function ResultPanel({ trace, step, onSelect }: PanelProps) {
  const detail = step.detail as unknown as TraceResult
  const byId = new Map(trace.nodes.map((n) => [n.id, n]))
  return (
    <Stack spacing={1.5}>
      <Alert
        severity={detail.solved ? 'success' : 'warning'}
        variant="outlined"
        sx={{ alignItems: 'center' }}
      >
        {detail.solved
          ? `Solved with reward ${num(detail.best_reward)}.`
          : `Not solved — ${detail.stopped_because}.`}
      </Alert>

      <Stack direction="row" sx={{ flexWrap: 'wrap', gap: 0.5 }}>
        <Chip size="small" label={`${detail.iterations_run} iterations`} />
        <Chip size="small" label={`${detail.nodes} nodes`} />
        <Chip
          size="small"
          label={`${trace.policy.tokens.toLocaleString()} tokens${trace.policy.tokens_are_estimated ? ' (est.)' : ''}`}
        />
        <Chip size="small" label={`${trace.policy.calls} policy calls`} />
      </Stack>

      {detail.best_path.length > 0 && (
        <>
          <SectionLabel>Best trajectory</SectionLabel>
          <Stack spacing={0.4}>
            {detail.best_path.map((id, i) => (
              <Stack key={id} direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
                <Typography sx={{ color: INK_FAINT, fontFamily: MONO, width: 16 }}>
                  {i === 0 ? '·' : '↓'}
                </Typography>
                <NodeChip
                  id={id}
                  label={byId.get(id)?.label}
                  color={detail.solved ? GOOD : ACCENT}
                  onSelect={onSelect}
                />
              </Stack>
            ))}
          </Stack>
        </>
      )}

      {detail.reflections.length > 0 && (
        <>
          <SectionLabel>Notes written along the way</SectionLabel>
          <Stack spacing={0.75}>
            {detail.reflections.map((note, i) => (
              <Callout key={i} color={VIOLET}>
                <Typography variant="body2">{note.split('|')[0].trim()}</Typography>
              </Callout>
            ))}
          </Stack>
        </>
      )}
    </Stack>
  )
}
