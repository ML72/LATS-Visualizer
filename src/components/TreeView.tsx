/**
 * The search tree.
 *
 * An SVG the user can pan and zoom, drawing only the nodes that exist as of the
 * current step so the tree grows as the timeline advances. Node fill is the
 * value ramp, the ring is the objective reward when there is one, and the
 * current step's path is drawn in amber over the top.
 *
 * Two decisions keep a forty-five node trace readable in a pane that holds
 * about ten cards.
 *
 * **The layout is of the visible nodes, not of the finished tree.** Placing
 * every node the search will *eventually* build spreads six visible nodes
 * across six thousand pixels, so every early step was drawn at the zoom the
 * last step needs - legible cards rendered as specks. Laying out what is on
 * screen costs the property that a node never moves, and buys a tree that is
 * readable from the first step; the transform transition turns the cost into
 * the tree visibly making room for a new sibling.
 *
 * **The camera frames the step, not the tree.** A replay is read one operation
 * at a time and the panel beside it is talking about particular nodes, so those
 * are the ones worth having on screen at a size you can read. The whole tree is
 * one button away, and the moment the user pans or zooms the camera stops
 * following until they ask it to resume.
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
import ZoomOutMapIcon from '@mui/icons-material/ZoomOutMap'

import type { Trace } from '../types'
import type { View } from '../lib/layout'
import { NODE_H, NODE_W, layoutTree } from '../lib/layout'
import { num, truncate } from '../lib/format'
import {
  ACCENT,
  CARD_SHADOW,
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

/** Breathing room around the framed nodes, in screen pixels. */
const PAD = 40
/** Never magnify past this: three nodes should read as a small tree, not as
    three billboards. */
const MAX_SCALE = 1.2
/** The smallest area the camera will frame, in layout units. Without a floor,
    a step whose focus is a single node would fill the pane with it. */
const MIN_FRAME_W = NODE_W * 4.5
const MIN_FRAME_H = NODE_H * 5
/** Below this scale a card's text is smaller than it is worth drawing, so a
    node becomes a value-coloured tile and the tree reads as a shape. */
const DETAIL_SCALE = 0.72

interface Props {
  trace: Trace
  view: View
  selected: number | null
  onSelect: (id: number | null) => void
}

interface Camera {
  x: number
  y: number
  scale: number
}

/** A rectangle in layout coordinates. */
interface Frame {
  x: number
  y: number
  w: number
  h: number
}

export default function TreeView({ trace, view, selected, onSelect }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 900, h: 520 })
  const [camera, setCamera] = useState<Camera | null>(null)
  /** True once the user has taken the camera: it stops following the search. */
  const [free, setFree] = useState(false)
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

  // The layout of what exists now, not of what the search will end up with.
  const layout = useMemo(() => layoutTree(view.visible), [view.visible])

  const boxOf = useCallback(
    (ids: Iterable<number>): Frame | null => {
      let x0 = Infinity
      let y0 = Infinity
      let x1 = -Infinity
      let y1 = -Infinity
      for (const id of ids) {
        const p = layout.placed.get(id)
        if (!p) continue
        x0 = Math.min(x0, p.x)
        y0 = Math.min(y0, p.y)
        x1 = Math.max(x1, p.x + NODE_W)
        y1 = Math.max(y1, p.y + NODE_H)
      }
      if (!Number.isFinite(x0)) return null
      return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }
    },
    [layout],
  )

  const whole = useMemo<Frame>(
    () =>
      boxOf(layout.placed.keys()) ?? { x: 0, y: 0, w: layout.width, h: layout.height },
    [boxOf, layout],
  )

  /**
   * What this step is about: the nodes it names, plus each one's parent. The
   * parent costs no width - it sits over its own children - and it answers
   * "where in the tree is this" for free.
   */
  const subject = useMemo<Frame>(() => {
    // The last step is the summary: show everything the search built, with the
    // winning trajectory drawn through it.
    if (view.step.op === 'result') return whole
    const ids = new Set(view.step.focus ?? [])
    if (ids.size === 0) return whole
    const byId = new Map(view.visible.map((n) => [n.id, n]))
    for (const id of [...ids]) {
      const parent = byId.get(id)?.parent
      if (parent !== null && parent !== undefined) ids.add(parent)
    }
    return boxOf(ids) ?? whole
  }, [view.step, view.visible, boxOf, whole])

  const frame = useCallback(
    (b: Frame): Camera => {
      const scale = Math.min(
        Math.max(1, size.w - PAD * 2) / Math.max(b.w, MIN_FRAME_W),
        Math.max(1, size.h - PAD * 2) / Math.max(b.h, MIN_FRAME_H),
        MAX_SCALE,
      )
      return {
        scale,
        x: size.w / 2 - (b.x + b.w / 2) * scale,
        y: size.h / 2 - (b.y + b.h / 2) * scale,
      }
    },
    [size.w, size.h],
  )

  // Following by default; the user's own camera wins the moment there is one.
  const cam = free && camera ? camera : frame(subject)
  const detailed = cam.scale >= DETAIL_SCALE

  const take = (next: Camera) => {
    setCamera(next)
    setFree(true)
  }

  const zoomBy = (factor: number, cx = size.w / 2, cy = size.h / 2) => {
    const scale = Math.min(Math.max(cam.scale * factor, 0.05), 3)
    const k = scale / cam.scale
    take({ scale, x: cx - (cx - cam.x) * k, y: cy - (cy - cam.y) * k })
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
  // Following is animated so a step reads as the camera moving to it; dragging
  // is not, because a lagging canvas feels broken. A browser that will not
  // transition the transform attribute simply cuts, which is what it did before.
  const glide = free ? 'none' : 'transform 380ms cubic-bezier(0.4, 0, 0.2, 1)'

  return (
    <Paper
      ref={wrapRef}
      elevation={0}
      sx={{
        position: 'relative',
        flex: 1,
        minHeight: 280,
        overflow: 'hidden',
        bgcolor: SURFACE,
        backgroundImage: `radial-gradient(${alpha(EDGE, 0.42)} 1px, transparent 1px)`,
        backgroundSize: '22px 22px',
        cursor: 'grab',
        '&:active': { cursor: 'grabbing' },
      }}
      onPointerDown={(e) => {
        drag.current = { x: e.clientX, y: e.clientY, cam }
        ;(e.target as Element).setPointerCapture?.(e.pointerId)
      }}
      onPointerMove={(e) => {
        const d = drag.current
        if (!d) return
        // A press that never moved is a click, not a pan: the camera keeps
        // following until the pointer has actually travelled.
        if (Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) < 3) return
        take({
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
        <g
          transform={`translate(${cam.x} ${cam.y}) scale(${cam.scale})`}
          style={{ transition: glide }}
        >
          {edges.map((edge) => (
            <path
              key={edge.key}
              d={edge.d}
              fill="none"
              stroke={edge.onPath ? ACCENT : EDGE}
              strokeWidth={edge.onPath ? 2.4 : 1.4}
              vectorEffect="non-scaling-stroke"
              opacity={edge.onPath ? 1 : dimmed ? 0.45 : 0.8}
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
                style={{ cursor: 'pointer', transition: glide }}
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

                <rect width={NODE_W} height={NODE_H} rx={7} fill={SURFACE} />
                <rect
                  width={NODE_W}
                  height={NODE_H}
                  rx={7}
                  fill={alpha(color, detailed ? 0.13 : 0.82)}
                  stroke={
                    isSelected ? INK : focused ? ACCENT : detailed ? color : alpha(color, 0.9)
                  }
                  strokeWidth={isSelected ? 2.4 : focused ? 2.2 : 1.2}
                  vectorEffect="non-scaling-stroke"
                />

                {detailed ? (
                  <>
                    {/* A value bar along the bottom edge: the same number as
                        the fill, but readable at a glance across the tree. */}
                    <rect
                      x={1}
                      y={NODE_H - 4}
                      width={Math.max(0, (NODE_W - 2) * Math.min(state.value, 1))}
                      height={3}
                      rx={1.5}
                      fill={color}
                    />
                    <text x={8} y={16} fill={INK} fontSize={11} fontWeight={600}>
                      {truncate(node.label, 14)}
                    </text>
                    <text x={8} y={31} fill={INK_DIM} fontSize={9.5} fontFamily={MONO}>
                      {`V ${num(state.value)}  N ${state.visits}`}
                    </text>
                    <text
                      x={NODE_W - 7}
                      y={15}
                      fill={INK_FAINT}
                      fontSize={9}
                      fontFamily={MONO}
                      textAnchor="end"
                    >
                      {`#${node.id}`}
                    </text>
                    {state.reward !== null && (
                      <>
                        <rect
                          x={NODE_W - 34}
                          y={22}
                          width={27}
                          height={13}
                          rx={6.5}
                          fill={alpha(solved ? GOOD : color, 0.22)}
                          stroke={solved ? GOOD : color}
                          strokeWidth={1}
                          vectorEffect="non-scaling-stroke"
                        />
                        <text
                          x={NODE_W - 20.5}
                          y={31.5}
                          fill={solved ? GOOD : color}
                          fontSize={9}
                          fontFamily={MONO}
                          textAnchor="middle"
                        >
                          {num(state.reward)}
                        </text>
                      </>
                    )}
                  </>
                ) : (
                  // Zoomed out, a node is one value-coloured tile. A trajectory
                  // that solved the task keeps a mark of its own, because that
                  // is the thing worth finding in an overview.
                  solved && (
                    <circle
                      cx={NODE_W / 2}
                      cy={NODE_H / 2}
                      r={NODE_H / 3}
                      fill={SURFACE}
                      stroke={GOOD}
                      strokeWidth={2.5}
                      vectorEffect="non-scaling-stroke"
                    />
                  )
                )}

                {state.reflected && (
                  <circle cx={6} cy={6} r={detailed ? 3.2 : 6} fill={VIOLET}>
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
        spacing={0.25}
        sx={{
          position: 'absolute',
          right: 10,
          bottom: 10,
          bgcolor: SURFACE,
          border: `1px solid ${STROKE}`,
          borderRadius: 1,
          boxShadow: CARD_SHADOW,
          p: 0.25,
        }}
      >
        <Tooltip title="Zoom out">
          <IconButton size="small" onClick={() => zoomBy(1 / 1.25)}>
            <RemoveIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Fit the whole tree">
          <IconButton size="small" onClick={() => take(frame(whole))}>
            <ZoomOutMapIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title={free ? 'Follow the search again' : 'Following the search'}>
          <IconButton
            size="small"
            onClick={() => {
              setFree(false)
              setCamera(null)
            }}
            sx={{ color: free ? PRIMARY : INK_FAINT }}
          >
            <CenterFocusStrongIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Zoom in">
          <IconButton size="small" onClick={() => zoomBy(1.25)}>
            <AddIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>

      <Box
        sx={{
          position: 'absolute',
          left: 12,
          top: 10,
          pointerEvents: 'none',
          bgcolor: SURFACE,
          border: `1px solid ${STROKE}`,
          borderRadius: 1,
          boxShadow: CARD_SHADOW,
          px: 1,
          py: 0.4,
        }}
      >
        <Typography variant="caption" sx={{ color: INK_FAINT }}>
          <Box component="span" sx={{ color: INK_DIM, fontFamily: MONO }}>
            {view.visible.length}/{trace.nodes.length}
          </Box>{' '}
          nodes ·{' '}
          {free
            ? 'drag to pan, scroll to zoom'
            : detailed
              ? 'the view follows the search'
              : 'too many at this zoom to label — click one for detail'}
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
        bgcolor: SURFACE,
        border: `1px solid ${STROKE}`,
        borderRadius: 1,
        boxShadow: CARD_SHADOW,
        px: 1,
        py: 0.75,
      }}
    >
      <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
        <Typography variant="caption" sx={{ color: INK_FAINT }}>
          V(s)
        </Typography>
        <Box sx={{ display: 'flex', borderRadius: 0.5, overflow: 'hidden' }}>
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
        <Swatch color={GOOD} label="solved" outline />
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
