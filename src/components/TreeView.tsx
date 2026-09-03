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
 *
 * Zooming out past the point where a whole card is worth drawing, a node keeps
 * its name at a fixed size on screen, truncated to fit, and only becomes a bare
 * value-coloured tile once even that will not fit. Detail is given up one piece
 * at a time; nothing about the tree ever blanks all at once.
 *
 * Every colour reaches the SVG through `style` rather than through `fill` and
 * `stroke` attributes: the palette is a set of CSS variables, and a
 * presentation attribute is not somewhere every browser resolves `var()`.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import IconButton from '@mui/material/IconButton'
import Paper from '@mui/material/Paper'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import useMediaQuery from '@mui/material/useMediaQuery'
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

/** Breathing room around the framed nodes, in screen pixels. On a canvas as
    narrow as a phone's this is most of the width, so it is a share of the
    canvas there and this figure only on anything bigger. */
const PAD = 40
const PAD_SHARE = 0.06
const PAD_MIN = 12
/** Never magnify past this: three nodes should read as a small tree, not as
    three billboards. */
const MAX_SCALE = 1.2
/** The smallest area the camera will frame, in layout units. Without a floor,
    a step whose focus is a single node would fill the pane with it. */
const MIN_FRAME_W = NODE_W * 4.5
const MIN_FRAME_H = NODE_H * 5
/** Above this scale a node carries its whole card: name, V, N, id, reward. */
const DETAIL_SCALE = 0.72
/** What the framing floor relaxes to when the canvas cannot afford it: enough
    over the threshold above that no rounding decides whether a card is drawn. */
const DETAIL_TARGET = DETAIL_SCALE * 1.05
/** Between the two, a node keeps only its name, held at a fixed size on screen
    and truncated to whatever the card can still hold. Below the lower bound
    even three characters will not fit, so the node becomes a value-coloured
    tile and the tree reads as a shape instead. */
const LABEL_SCALE = 0.26
/** The on-screen size of that name, in pixels, whatever the zoom. */
const LABEL_PX = 10
/** Rough advance width of the sans face, as a fraction of its size. Used only
    to decide how much of a name fits; being a little conservative is fine. */
const CHAR_W = 0.56
/** Narrower than this and the overlays start standing on each other, so the
    legend keeps its ramp and drops its swatches. Shorter than the second and
    it stands on the tree itself, so it goes entirely: a handset on its side
    has room for the nodes or for the key, and the nodes are the subject. */
const TIGHT_W = 520
const TIGHT_H = 200
/** How far a pointer may travel and still count as a click on a node. */
const SLOP = 3

interface Props {
  trace: Trace
  view: View
  selected: number | null
  onSelect: (id: number | null) => void
  /** How little vertical room the pane may be given before it insists. */
  minHeight?: number
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

interface Point {
  x: number
  y: number
}

export default function TreeView({
  trace,
  view,
  selected,
  onSelect,
  minHeight = 280,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 900, h: 520 })
  const [camera, setCamera] = useState<Camera | null>(null)
  /** True once the user has taken the camera: it stops following the search. */
  const [free, setFree] = useState(false)
  const drag = useRef<{ x: number; y: number; cam: Camera } | null>(null)
  /** Every finger currently down, so two of them can be read as a pinch. */
  const pointers = useRef(new Map<number, Point>())
  const pinch = useRef<{ dist: number; mid: Point; cam: Camera } | null>(null)
  /** Set once a gesture has travelled far enough to be a pan, not a tap. */
  const panned = useRef(false)

  const coarse = useMediaQuery('(pointer: coarse)')

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
      const pad = Math.min(PAD, Math.max(PAD_MIN, size.w * PAD_SHARE))
      const room = (px: number) => Math.max(1, px - pad * 2)
      // The floor stops a step about one node from filling the pane with it.
      // On a phone-wide canvas, though, four and a half cards of framing is
      // exactly what would push every node below the size at which it carries
      // its own numbers, so the floor never asks for more than the canvas can
      // show at full detail. A frame is still never smaller than its contents.
      const floor = (want: number, px: number) =>
        Math.min(want, room(px) / DETAIL_TARGET)
      const scale = Math.min(
        room(size.w) / Math.max(b.w, floor(MIN_FRAME_W, size.w)),
        room(size.h) / Math.max(b.h, floor(MIN_FRAME_H, size.h)),
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
  const labelled = cam.scale >= LABEL_SCALE
  // In user units, so the drawn size stays constant as the canvas scales.
  const labelFont = LABEL_PX / cam.scale
  const labelRoom = Math.floor((NODE_W - 14) / (labelFont * CHAR_W))
  const tight = size.w < TIGHT_W

  const take = (next: Camera) => {
    setCamera(next)
    setFree(true)
  }

  /** Where a client point falls inside the canvas. */
  const local = (x: number, y: number): Point => {
    const rect = wrapRef.current?.getBoundingClientRect()
    return { x: x - (rect?.left ?? 0), y: y - (rect?.top ?? 0) }
  }

  const zoomTo = (scale: number, at: Point, from: Camera, anchor: Point) => {
    const k = Math.min(Math.max(scale, 0.05), 3) / from.scale
    take({
      scale: from.scale * k,
      x: at.x - (anchor.x - from.x) * k,
      y: at.y - (anchor.y - from.y) * k,
    })
  }

  const zoomBy = (factor: number, cx = size.w / 2, cy = size.h / 2) => {
    zoomTo(cam.scale * factor, { x: cx, y: cy }, cam, { x: cx, y: cy })
  }

  const two = (): [Point, Point] => {
    const [a, b] = [...pointers.current.values()]
    return [a, b]
  }

  const startPinch = () => {
    const [a, b] = two()
    const mid = local((a.x + b.x) / 2, (a.y + b.y) / 2)
    pinch.current = { dist: Math.hypot(a.x - b.x, a.y - b.y) || 1, mid, cam }
    drag.current = null
  }

  const onPointerDown = (e: React.PointerEvent) => {
    pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
    panned.current = false
    if (pointers.current.size === 2) {
      startPinch()
      return
    }
    if (pointers.current.size > 2) return
    drag.current = { x: e.clientX, y: e.clientY, cam }
    ;(e.target as Element).setPointerCapture?.(e.pointerId)
  }

  const onPointerMove = (e: React.PointerEvent) => {
    if (pointers.current.has(e.pointerId)) {
      pointers.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
    }

    // Two fingers: the point the canvas was pinched at stays under them, so
    // the same gesture zooms and pans.
    const p = pinch.current
    if (p && pointers.current.size >= 2) {
      panned.current = true
      const [a, b] = two()
      const dist = Math.hypot(a.x - b.x, a.y - b.y) || 1
      zoomTo(p.cam.scale * (dist / p.dist), local((a.x + b.x) / 2, (a.y + b.y) / 2), p.cam, p.mid)
      return
    }

    const d = drag.current
    if (!d) return
    // A press that never moved is a click, not a pan: the camera keeps
    // following until the pointer has actually travelled.
    if (Math.abs(e.clientX - d.x) + Math.abs(e.clientY - d.y) < SLOP) return
    panned.current = true
    take({
      scale: d.cam.scale,
      x: d.cam.x + (e.clientX - d.x),
      y: d.cam.y + (e.clientY - d.y),
    })
  }

  const onPointerEnd = (e: React.PointerEvent) => {
    pointers.current.delete(e.pointerId)
    if (pointers.current.size < 2) pinch.current = null
    if (pointers.current.size === 0) drag.current = null
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
        minHeight,
        overflow: 'hidden',
        bgcolor: SURFACE,
        backgroundImage: `radial-gradient(${alpha(EDGE, 0.42)} 1px, transparent 1px)`,
        backgroundSize: '22px 22px',
        cursor: 'grab',
        // The canvas takes every touch itself: without this a drag scrolls the
        // page instead of panning, and a pinch zooms the whole document.
        touchAction: 'none',
        userSelect: 'none',
        '&:active': { cursor: 'grabbing' },
      }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerEnd}
      onPointerCancel={onPointerEnd}
      onPointerLeave={onPointerEnd}
      onWheel={(e) => {
        const at = local(e.clientX, e.clientY)
        zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12, at.x, at.y)
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
              strokeWidth={edge.onPath ? 2.4 : 1.4}
              vectorEffect="non-scaling-stroke"
              opacity={edge.onPath ? 1 : dimmed ? 0.45 : 0.8}
              style={{ fill: 'none', stroke: edge.onPath ? ACCENT : EDGE }}
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
                  // A pan that happened to start on a node is not a choice of
                  // that node - which on a touchscreen is most of them.
                  if (panned.current) return
                  onSelect(isSelected ? null : node.id)
                }}
              >
                <title>
                  {`#${node.id} ${node.label}\nV ${num(state.value)}  N ${state.visits}` +
                    (state.reward !== null ? `  reward ${num(state.reward)}` : '') +
                    (node.observation ? `\n${node.observation}` : '')}
                </title>

                <rect width={NODE_W} height={NODE_H} rx={7} style={{ fill: SURFACE }} />
                <rect
                  width={NODE_W}
                  height={NODE_H}
                  rx={7}
                  strokeWidth={isSelected ? 2.4 : focused ? 2.2 : 1.2}
                  vectorEffect="non-scaling-stroke"
                  style={{
                    fill: alpha(color, labelled ? 0.13 : 0.82),
                    stroke: isSelected ? INK : focused ? ACCENT : solved ? GOOD : color,
                  }}
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
                      style={{ fill: color }}
                    />
                    <text x={8} y={16} fontSize={11} fontWeight={600} style={{ fill: INK }}>
                      {truncate(node.label, 14)}
                    </text>
                    <text
                      x={8}
                      y={31}
                      fontSize={9.5}
                      fontFamily={MONO}
                      style={{ fill: INK_DIM }}
                    >
                      {`V ${num(state.value)}  N ${state.visits}`}
                    </text>
                    <text
                      x={NODE_W - 7}
                      y={15}
                      fontSize={9}
                      fontFamily={MONO}
                      textAnchor="end"
                      style={{ fill: INK_FAINT }}
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
                          strokeWidth={1}
                          vectorEffect="non-scaling-stroke"
                          style={{
                            fill: alpha(solved ? GOOD : color, 0.22),
                            stroke: solved ? GOOD : color,
                          }}
                        />
                        <text
                          x={NODE_W - 20.5}
                          y={31.5}
                          fontSize={9}
                          fontFamily={MONO}
                          textAnchor="middle"
                          style={{ fill: solved ? GOOD : color }}
                        >
                          {num(state.reward)}
                        </text>
                      </>
                    )}
                  </>
                ) : labelled ? (
                  <>
                    <rect
                      x={1}
                      y={NODE_H - 4}
                      width={Math.max(0, (NODE_W - 2) * Math.min(state.value, 1))}
                      height={3}
                      rx={1.5}
                      style={{ fill: color }}
                    />
                    <text
                      x={NODE_W / 2}
                      y={NODE_H / 2 + labelFont * 0.34}
                      fontSize={labelFont}
                      fontWeight={600}
                      textAnchor="middle"
                      style={{ fill: INK }}
                    >
                      {truncate(node.label, Math.max(3, labelRoom))}
                    </text>
                  </>
                ) : (
                  // Smaller than a name will fit: a node is one value-coloured
                  // tile. A trajectory that solved the task keeps a mark of its
                  // own, because that is the thing worth finding in an overview.
                  solved && (
                    <circle
                      cx={NODE_W / 2}
                      cy={NODE_H / 2}
                      r={NODE_H / 3}
                      strokeWidth={2.5}
                      vectorEffect="non-scaling-stroke"
                      style={{ fill: SURFACE, stroke: GOOD }}
                    />
                  )
                )}

                {state.reflected && (
                  <circle
                    cx={6}
                    cy={6}
                    r={detailed ? 3.2 : 3.2 / cam.scale}
                    style={{ fill: VIOLET }}
                  >
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
          <IconButton size={coarse ? 'medium' : 'small'} onClick={() => zoomBy(1 / 1.25)}>
            <RemoveIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Fit the whole tree">
          <IconButton size={coarse ? 'medium' : 'small'} onClick={() => take(frame(whole))}>
            <ZoomOutMapIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title={free ? 'Follow the search again' : 'Following the search'}>
          <IconButton
            size={coarse ? 'medium' : 'small'}
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
          <IconButton size={coarse ? 'medium' : 'small'} onClick={() => zoomBy(1.25)}>
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
          // Only where it could outgrow the canvas: an unconditional cap
          // rounds the box differently on a pane that never needed one.
          ...(tight && { maxWidth: 'calc(100% - 24px)' }),
        }}
      >
        <Typography
          variant="caption"
          noWrap={tight}
          sx={{ color: INK_FAINT, ...(tight && { display: 'block' }) }}
        >
          <Box component="span" sx={{ color: INK_DIM, fontFamily: MONO }}>
            {view.visible.length}/{trace.nodes.length}
          </Box>{' '}
          nodes
          {/* On a narrow canvas the hint is what gives way: the gestures are
              the ones a touchscreen already teaches. */}
          {!tight && (
            <>
              {' · '}
              {free ? 'drag to pan, scroll to zoom' : 'the view follows the search'}
              {!detailed && ' · click a node for its detail'}
            </>
          )}
        </Typography>
      </Box>

      {size.h >= TIGHT_H && <Legend tight={tight} />}
    </Paper>
  )
}

function Legend({ tight }: { tight: boolean }) {
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
            <Box key={s} sx={{ width: tight ? 12 : 16, height: 8, bgcolor: valueColor(s) }} />
          ))}
        </Box>
        <Typography variant="caption" sx={{ color: INK_FAINT }}>
          0 → 1
        </Typography>
      </Stack>
      {/* The ramp explains the colour every node carries, so it stays; the
          three conventions below it share a row with the zoom controls and
          are the ones that have to go when the canvas is a phone's wide. */}
      {!tight && (
        <Stack direction="row" spacing={1.25} sx={{ alignItems: 'center' }}>
          <Swatch color={ACCENT} label="this step" />
          <Swatch color={VIOLET} label="reflected" />
          <Swatch color={GOOD} label="solved" outline />
        </Stack>
      )}
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
