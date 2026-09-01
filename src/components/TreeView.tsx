/**
 * The search tree.
 *
 * An SVG the user can pan and zoom, drawing only the nodes that exist as of
 * the current step so the tree grows as the timeline advances. Node fill is
 * the value ramp, the ring is the objective reward when there is one, and the
 * current step's path is drawn in amber over the top.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import IconButton from '@mui/material/IconButton'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import AddIcon from '@mui/icons-material/Add'
import RemoveIcon from '@mui/icons-material/Remove'
import CenterFocusStrongIcon from '@mui/icons-material/CenterFocusStrong'

import type { Trace } from '../types'
import type { Layout, View } from '../lib/layout'
import { NODE_H, NODE_W } from '../lib/layout'
import { num, truncate } from '../lib/format'
import {
  ACCENT,
  BG,
  EDGE,
  GOOD,
  INK,
  INK_DIM,
  INK_FAINT,
  MONO,
  PRIMARY,
  STROKE,
  SURFACE,
  VIOLET,
  alpha,
  valueColor,
} from '../theme'

const PAD = 44

interface Props {
  trace: Trace
  layout: Layout
  view: View
  selected: number | null
  onSelect: (id: number | null) => void
}

interface Camera {
  x: number
  y: number
  scale: number
}

export default function TreeView({ trace, layout, view, selected, onSelect }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 900, h: 520 })
  const [camera, setCamera] = useState<Camera | null>(null)
  const drag = useRef<{ x: number; y: number; cam: Camera } | null>(null)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => {
      const { width, height } = entry.contentRect
      if (width > 0 && height > 0) setSize({ w: width, h: height })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const fit = useCallback((): Camera => {
    const w = layout.width + PAD * 2
    const h = layout.height + PAD * 2
    const scale = Math.min(size.w / w, size.h / h, 1.35)
    return {
      x: (size.w - layout.width * scale) / 2,
      y: (size.h - layout.height * scale) / 2,
      scale,
    }
  }, [layout.width, layout.height, size.w, size.h])

  // Re-fit when the trace changes, but leave the camera alone while the user
  // scrubs the timeline - nothing is more annoying than a view that jumps.
  useEffect(() => {
    setCamera(fit())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trace.name, size.w, size.h])

  const cam = camera ?? fit()

  const zoomBy = (factor: number, cx = size.w / 2, cy = size.h / 2) => {
    setCamera((prev) => {
      const c = prev ?? fit()
      const scale = Math.min(Math.max(c.scale * factor, 0.12), 3)
      const k = scale / c.scale
      return { scale, x: cx - (cx - c.x) * k, y: cy - (cy - c.y) * k }
    })
  }

  const visibleIds = useMemo(
    () => new Set(view.visible.map((n) => n.id)),
    [view.visible],
  )

  const edges = useMemo(() => {
    const out: { key: string; d: string; onPath: boolean }[] = []
    for (const node of view.visible) {
      if (node.parent === null) continue
      if (!visibleIds.has(node.parent)) continue
      const parent = layout.placed.get(node.parent)
      const child = layout.placed.get(node.id)
      if (!parent || !child) continue
      const x1 = parent.x + NODE_W / 2
      const y1 = parent.y + NODE_H
      const x2 = child.x + NODE_W / 2
      const y2 = child.y
      const mid = (y1 + y2) / 2
      out.push({
        key: `${node.parent}-${node.id}`,
        d: `M ${x1} ${y1} C ${x1} ${mid}, ${x2} ${mid}, ${x2} ${y2}`,
        onPath: view.pathEdges.has(`${node.parent}-${node.id}`),
      })
    }
    return out
  }, [view.visible, view.pathEdges, visibleIds, layout])

  const dimmed = view.focus.size > 0

  return (
    <Paper
      ref={wrapRef}
      elevation={0}
      sx={{
        position: 'relative',
        flex: 1,
        minHeight: 280,
        overflow: 'hidden',
        bgcolor: BG,
        cursor: drag.current ? 'grabbing' : 'grab',
      }}
      onPointerDown={(e) => {
        drag.current = { x: e.clientX, y: e.clientY, cam }
        ;(e.target as Element).setPointerCapture?.(e.pointerId)
      }}
      onPointerMove={(e) => {
        const d = drag.current
        if (!d) return
        setCamera({
          scale: d.cam.scale,
          x: d.cam.x + (e.clientX - d.x),
          y: d.cam.y + (e.clientY - d.y),
        })
      }}
      onPointerUp={() => {
        drag.current = null
      }}
      onPointerLeave={() => {
        drag.current = null
      }}
      onWheel={(e) => {
        const rect = wrapRef.current?.getBoundingClientRect()
        zoomBy(
          e.deltaY < 0 ? 1.12 : 1 / 1.12,
          e.clientX - (rect?.left ?? 0),
          e.clientY - (rect?.top ?? 0),
        )
      }}
    >
      <svg width="100%" height="100%" style={{ display: 'block', touchAction: 'none' }}>
        <g transform={`translate(${cam.x} ${cam.y}) scale(${cam.scale})`}>
          {edges.map((edge) => (
            <path
              key={edge.key}
              d={edge.d}
              fill="none"
              stroke={edge.onPath ? ACCENT : EDGE}
              strokeWidth={edge.onPath ? 2.4 : 1.4}
              opacity={edge.onPath ? 0.95 : dimmed ? 0.35 : 0.6}
            />
          ))}

          {view.visible.map((node) => {
            const placed = layout.placed.get(node.id)
            const state = view.state(node.id)
            if (!placed || !state) return null

            const focused = view.focus.has(node.id)
            const onPath = view.path.includes(node.id)
            const isSelected = selected === node.id
            const color = valueColor(state.value)
            const solved =
              state.reward !== null && state.reward >= trace.config.solved_at
            const opacity = !dimmed || focused || onPath ? 1 : 0.42

            return (
              <g
                key={node.id}
                transform={`translate(${placed.x} ${placed.y})`}
                opacity={opacity}
                style={{ cursor: 'pointer' }}
                onClick={(e) => {
                  e.stopPropagation()
                  onSelect(isSelected ? null : node.id)
                }}
              >
                <title>
                  {`#${node.id} ${node.label}\nV ${num(state.value)}  N ${state.visits}` +
                    (state.reward !== null ? `  reward ${num(state.reward)}` : '') +
                    (node.observation ? `\n${node.observation}` : '')}
                </title>

                <rect
                  width={NODE_W}
                  height={NODE_H}
                  rx={8}
                  fill={alpha(color, 0.16)}
                  stroke={isSelected ? INK : focused ? ACCENT : color}
                  strokeWidth={isSelected ? 2.4 : focused ? 2.2 : 1.4}
                />

                {/* A value bar along the bottom edge: the same number as the
                    fill, but readable at a glance across the whole tree. */}
                <rect
                  x={1}
                  y={NODE_H - 4}
                  width={Math.max(0, (NODE_W - 2) * Math.min(state.value, 1))}
                  height={3}
                  rx={1.5}
                  fill={color}
                />

                <text
                  x={9}
                  y={18}
                  fill={INK}
                  fontSize={11.5}
                  fontFamily="inherit"
                  fontWeight={600}
                >
                  {truncate(node.label, 19)}
                </text>
                <text x={9} y={34} fill={INK_DIM} fontSize={10.5} fontFamily={MONO}>
                  {`V ${num(state.value)}  N ${state.visits}`}
                </text>

                {state.reward !== null && (
                  <>
                    <rect
                      x={NODE_W - 40}
                      y={26}
                      width={33}
                      height={15}
                      rx={7.5}
                      fill={alpha(solved ? GOOD : color, 0.22)}
                      stroke={solved ? GOOD : color}
                      strokeWidth={1}
                    />
                    <text
                      x={NODE_W - 23.5}
                      y={37}
                      fill={solved ? GOOD : color}
                      fontSize={10}
                      fontFamily={MONO}
                      textAnchor="middle"
                    >
                      {num(state.reward)}
                    </text>
                  </>
                )}

                <text
                  x={NODE_W - 8}
                  y={17}
                  fill={INK_FAINT}
                  fontSize={9.5}
                  fontFamily={MONO}
                  textAnchor="end"
                >
                  {`#${node.id}`}
                </text>

                {state.reflected && (
                  <circle cx={7} cy={7} r={3.5} fill={VIOLET}>
                    <title>A reflection was written from this node</title>
                  </circle>
                )}
              </g>
            )
          })}
        </g>
      </svg>

      <Stack
        direction="row"
        spacing={0.5}
        sx={{
          position: 'absolute',
          right: 10,
          bottom: 10,
          bgcolor: alpha(SURFACE, 0.9),
          border: `1px solid ${STROKE}`,
          borderRadius: 1,
          p: 0.25,
        }}
      >
        <Tooltip title="Zoom out">
          <IconButton size="small" onClick={() => zoomBy(1 / 1.25)}>
            <RemoveIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Fit the whole tree">
          <IconButton size="small" onClick={() => setCamera(fit())}>
            <CenterFocusStrongIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Zoom in">
          <IconButton size="small" onClick={() => zoomBy(1.25)}>
            <AddIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>

      <Box sx={{ position: 'absolute', left: 12, top: 10, pointerEvents: 'none' }}>
        <Typography variant="caption" sx={{ color: INK_FAINT }}>
          {view.visible.length} of {trace.nodes.length} nodes · drag to pan, scroll to
          zoom, click a node for detail
        </Typography>
      </Box>

      <Legend />
    </Paper>
  )
}

function Legend() {
  const stops = [0, 0.25, 0.5, 0.75, 1]
  return (
    <Stack
      spacing={0.75}
      sx={{
        position: 'absolute',
        left: 12,
        bottom: 10,
        pointerEvents: 'none',
        bgcolor: alpha(SURFACE, 0.82),
        border: `1px solid ${STROKE}`,
        borderRadius: 1,
        px: 1,
        py: 0.75,
      }}
    >
      <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
        <Typography variant="caption" sx={{ color: INK_FAINT }}>
          V(s)
        </Typography>
        <Box sx={{ display: 'flex' }}>
          {stops.map((s) => (
            <Box key={s} sx={{ width: 16, height: 8, bgcolor: valueColor(s) }} />
          ))}
        </Box>
        <Typography variant="caption" sx={{ color: INK_FAINT }}>
          0 → 1
        </Typography>
      </Stack>
      <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center' }}>
        <Swatch color={ACCENT} label="this step" />
        <Swatch color={VIOLET} label="reflected" />
        <Swatch color={PRIMARY} label="path" outline />
      </Stack>
    </Stack>
  )
}

function Swatch({
  color,
  label,
  outline,
}: {
  color: string
  label: string
  outline?: boolean
}) {
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: 'center' }}>
      <Box
        sx={{
          width: 9,
          height: 9,
          borderRadius: '50%',
          bgcolor: outline ? 'transparent' : color,
          border: `2px solid ${color}`,
        }}
      />
      <Typography variant="caption" sx={{ color: INK_FAINT }}>
        {label}
      </Typography>
    </Stack>
  )
}
