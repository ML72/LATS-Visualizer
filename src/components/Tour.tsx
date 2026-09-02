/**
 * The first-run tour: four coach marks over the four things you need.
 *
 * The viewer has one genuine discoverability problem - the trace picker sits in
 * the corner of the app bar and looks like chrome, so a first-time visitor
 * never learns that there are eleven other runs to look at. Rather than shout
 * in the layout, the tour says it once, on the first visit, and then gets out
 * of the way. It is replayable from the app bar afterwards.
 *
 * The spotlight is one absolutely positioned box with a very large box-shadow:
 * the shadow paints the dim over the whole viewport and the box itself stays
 * clear, so the cutout follows the target's real geometry with no SVG mask and
 * no second layer to keep in sync.
 */

import { useEffect, useLayoutEffect, useState } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Portal from '@mui/material/Portal'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'

import { ACCENT, CARD_SHADOW, INK, INK_DIM, INK_FAINT, PRIMARY, STROKE, SURFACE } from '../theme'

export interface TourStop {
  /** Stable key, and the ref that finds the thing being pointed at. */
  id: string
  title: string
  body: string
  target: React.RefObject<HTMLElement | null>
  /** Where to put the card. 'auto' picks the side with the most room. */
  place?: Side | 'auto'
}

type Side = 'top' | 'bottom' | 'left' | 'right'

interface Rect {
  top: number
  left: number
  width: number
  height: number
}

/** Breathing room between the highlight and the thing it highlights. */
const HALO = 8
/** The scrim, and the ring on it. Amber, but keyed to a dark ground. */
const SCRIM = 'rgba(15, 23, 42, 0.55)'
const RING = '#F59E0B'
const CARD_W = 330
const GAP = 14
const MARGIN = 12

export default function Tour({
  stops,
  open,
  onClose,
}: {
  stops: TourStop[]
  open: boolean
  onClose: () => void
}) {
  const [i, setI] = useState(0)
  const [rect, setRect] = useState<Rect | null>(null)

  // Only stops whose target is actually on screen: the narrow layout drops
  // panels, and pointing at something that is not there is worse than silence.
  const live = stops.filter((s) => s.target.current)
  const stop = live[Math.min(i, live.length - 1)]
  const target = stop?.target

  // The spotlight tracks the real element, so it stays right when the window
  // resizes, the layout reflows, or a panel scrolls under it.
  useLayoutEffect(() => {
    if (!open) return
    const measure = () => {
      const el = target?.current
      if (!el) return setRect(null)
      const r = el.getBoundingClientRect()
      setRect({ top: r.top, left: r.left, width: r.width, height: r.height })
    }
    measure()
    window.addEventListener('resize', measure)
    window.addEventListener('scroll', measure, true)
    return () => {
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', measure, true)
    }
  }, [open, target])

  const count = live.length
  const back = () => setI(Math.max(0, i - 1))
  const next = () => (i + 1 >= count ? onClose() : setI(i + 1))

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      } else if (e.key === 'ArrowRight' || e.key === 'Enter') {
        e.preventDefault()
        if (i + 1 >= count) onClose()
        else setI(i + 1)
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        setI(Math.max(0, i - 1))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, i, count, onClose])

  if (!open || !stop || !rect) return null

  const hole = {
    top: rect.top - HALO,
    left: rect.left - HALO,
    width: rect.width + HALO * 2,
    height: rect.height + HALO * 2,
  }
  const { side, card, anchor } = place(hole, stop.place ?? 'auto')
  const last = i >= count - 1

  return (
    <Portal>
      {/* This layer takes every click, so nothing reaches the app behind it. */}
      <Box onClick={next} sx={{ position: 'fixed', inset: 0, zIndex: 1500 }}>
        {/* The dim and the cutout in one element: the shadow paints the scrim
            over the whole viewport and the box itself stays clear. It is not a
            hit target - the shadow is painted, not hit-tested - so the click
            handler lives on the layer above. */}
        <Box
          sx={{
            position: 'absolute',
            ...hole,
            pointerEvents: 'none',
            borderRadius: '10px',
            boxShadow: `0 0 0 9999px ${SCRIM}`,
            outline: `2px solid ${RING}`,
            outlineOffset: 0,
            transition: 'top 220ms ease, left 220ms ease, width 220ms ease, height 220ms ease',
          }}
        />

        <Box
          onClick={(e) => e.stopPropagation()}
          sx={{
            position: 'absolute',
            ...card,
            width: CARD_W,
            maxWidth: `calc(100vw - ${MARGIN * 2}px)`,
            bgcolor: SURFACE,
            border: `1px solid ${STROKE}`,
            borderRadius: 1.5,
            boxShadow: `${CARD_SHADOW}, 0 12px 32px rgba(15, 23, 42, 0.18)`,
            p: 2,
          }}
        >
          <Arrow side={side} hole={hole} left={anchor} />

          <Typography
            variant="subtitle2"
            sx={{ color: ACCENT, textTransform: 'uppercase', mb: 0.75 }}
          >
            {i + 1} of {count}
          </Typography>
          <Typography variant="h6" sx={{ color: INK, mb: 0.5 }}>
            {stop.title}
          </Typography>
          <Typography variant="body2" sx={{ color: INK_DIM }}>
            {stop.body}
          </Typography>

          <Stack direction="row" spacing={1} sx={{ alignItems: 'center', mt: 2 }}>
            <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
              {live.map((s, n) => (
                <Box
                  key={s.id}
                  sx={{
                    width: n === i ? 16 : 6,
                    height: 6,
                    borderRadius: 3,
                    bgcolor: n === i ? ACCENT : STROKE,
                    transition: 'width 180ms ease, background-color 180ms ease',
                  }}
                />
              ))}
            </Stack>
            <Box sx={{ flex: 1 }} />
            <Button size="small" onClick={onClose} sx={{ color: INK_FAINT }}>
              Skip
            </Button>
            {i > 0 && (
              <Button size="small" onClick={back} sx={{ color: INK_DIM }}>
                Back
              </Button>
            )}
            <Button
              size="small"
              variant="contained"
              disableElevation
              onClick={next}
              sx={{ bgcolor: PRIMARY, minWidth: 72 }}
            >
              {last ? 'Got it' : 'Next'}
            </Button>
          </Stack>
        </Box>
      </Box>
    </Portal>
  )
}

/** What to hand straight to `position: absolute`. */
type Placement = { top?: number; left?: number; right?: number; bottom?: number }

/**
 * Choose a side, then pin the card by the edge facing away from the target.
 *
 * A card below the target is placed by its top, a card above it by its bottom,
 * and likewise left and right - so the gap between card and target is exact
 * whatever the card ends up measuring. ``ROOM`` is only ever used to pick a
 * side; being wrong there is a worse position, never a collision.
 */
function place(
  hole: Rect,
  want: Side | 'auto',
): { side: Side; card: Placement; anchor: number } {
  const vw = window.innerWidth
  const vh = window.innerHeight
  /** Enough vertical room to be worth trying. Not a measurement. */
  const ROOM = 210

  const room: Record<Side, number> = {
    bottom: vh - (hole.top + hole.height),
    top: hole.top,
    right: vw - (hole.left + hole.width),
    left: hole.left,
  }
  const needs = (s: Side) => (s === 'left' || s === 'right' ? CARD_W : ROOM) + GAP + MARGIN

  let side: Side
  if (want !== 'auto' && room[want] >= needs(want)) {
    side = want
  } else {
    side =
      (['bottom', 'top', 'right', 'left'] as Side[]).find((s) => room[s] >= needs(s)) ??
      (room.bottom >= room.top ? 'bottom' : 'top')
  }

  const clamp = (v: number, max: number) => Math.max(MARGIN, Math.min(v, max - MARGIN))
  if (side === 'bottom' || side === 'top') {
    const left = clamp(hole.left + hole.width / 2 - CARD_W / 2, vw - CARD_W)
    const card =
      side === 'bottom'
        ? { top: hole.top + hole.height + GAP, left }
        : { bottom: vh - hole.top + GAP, left }
    return { side, card, anchor: left }
  }
  // Beside the target: line the card up with the top of the hole rather than
  // its middle, which for a full-height panel is the only sane reading order.
  const top = clamp(hole.top, vh - ROOM)
  const card =
    side === 'right'
      ? { top, left: hole.left + hole.width + GAP }
      : { top, right: vw - hole.left + GAP }
  return { side, card, anchor: 0 }
}

/** A small rotated square on the card edge, aimed at the middle of the hole. */
function Arrow({
  side,
  hole,
  left: cardLeft,
}: {
  side: Side
  hole: Rect
  /** Viewport x of the card's left edge, for the vertical placements. */
  left: number
}) {
  const size = 11
  const half = size / 2
  const base: Record<string, unknown> = {
    position: 'absolute',
    width: size,
    height: size,
    bgcolor: SURFACE,
    transform: 'rotate(45deg)',
  }
  const along = (centre: number, start: number, extent: number) =>
    Math.max(16, Math.min(centre - start - half, extent - 16 - size))

  if (side === 'bottom' || side === 'top') {
    const left = along(hole.left + hole.width / 2, cardLeft, CARD_W)
    return (
      <Box
        sx={{
          ...base,
          left,
          ...(side === 'bottom'
            ? { top: -half, borderLeft: `1px solid ${STROKE}`, borderTop: `1px solid ${STROKE}` }
            : { bottom: -half, borderRight: `1px solid ${STROKE}`, borderBottom: `1px solid ${STROKE}` }),
        }}
      />
    )
  }
  return (
    <Box
      sx={{
        ...base,
        top: 22,
        ...(side === 'right'
          ? { left: -half, borderLeft: `1px solid ${STROKE}`, borderBottom: `1px solid ${STROKE}` }
          : { right: -half, borderRight: `1px solid ${STROKE}`, borderTop: `1px solid ${STROKE}` }),
      }}
    />
  )
}

