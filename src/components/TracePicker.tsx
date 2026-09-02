/**
 * Choosing a trace: the bundled ones, plus anything the user drops in.
 *
 * The bundled set is grouped by environment and, inside an environment, put in
 * reading order - the offline policy before a real model, a run that solved its
 * task before one that did not. `scripts/run_lats.py` writes the manifest in
 * that order already; sorting again here means a hand-promoted trace lands in
 * the right group too, and that the picker never depends on the file being
 * tidy.
 *
 * Uploaded traces are held in memory for the session only. Nothing is written
 * anywhere, and the file never leaves the browser.
 */

import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import ListSubheader from '@mui/material/ListSubheader'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import Typography from '@mui/material/Typography'
import UploadFileIcon from '@mui/icons-material/UploadFile'

import { ACCENT, GOOD, INK, INK_DIM, INK_FAINT, MONO, STROKE, SURFACE_2, alpha } from '../theme'

export interface Source {
  key: string
  label: string
  kind: 'bundled' | 'uploaded'
  /** Filename inside `public/traces/`, for bundled entries. */
  file?: string
  /** Task id and title, for grouping bundled entries by environment. */
  task?: string
  taskTitle?: string
  note?: string
  solved?: boolean
}

interface Props {
  sources: Source[]
  current: string | null
  disabled?: boolean
  onSelect: (key: string) => void
  onUpload: (files: FileList | null) => void
}

/** One environment's worth of traces, in the order they should be read. */
interface Group {
  key: string
  title: string
  items: Source[]
}

/**
 * Group by environment, keeping the manifest's own order for the groups and
 * for anything it already sorted; a stable sort means the extra keys only move
 * entries the manifest did not place.
 */
function groupByTask(sources: Source[]): Group[] {
  const groups = new Map<string, Group>()
  sources.forEach((source) => {
    const key = source.task ?? source.label
    let group = groups.get(key)
    if (!group) {
      group = { key, title: source.taskTitle ?? source.label, items: [] }
      groups.set(key, group)
    }
    group.items.push(source)
  })
  for (const group of groups.values()) {
    const rank = (s: Source) => [
      s.label.startsWith('mock_') ? 0 : 1,
      s.solved === false ? 1 : 0,
    ]
    group.items = group.items
      .map((s, i) => ({ s, i }))
      .sort((a, b) => {
        const [pa, sa] = rank(a.s)
        const [pb, sb] = rank(b.s)
        return pa - pb || sa - sb || a.i - b.i
      })
      .map(({ s }) => s)
  }
  return [...groups.values()]
}

export default function TracePicker({
  sources,
  current,
  disabled,
  onSelect,
  onUpload,
}: Props) {
  const bundled = sources.filter((s) => s.kind === 'bundled')
  const uploaded = sources.filter((s) => s.kind === 'uploaded')
  const selected = sources.find((s) => s.key === current)

  const items: React.ReactNode[] = []
  for (const group of groupByTask(bundled)) {
    items.push(<Subheader key={`h-${group.key}`}>{group.title}</Subheader>)
    items.push(...group.items.map(renderItem))
  }
  if (uploaded.length) {
    items.push(<Subheader key="h-uploaded">Uploaded this session</Subheader>)
    items.push(...uploaded.map(renderItem))
  }

  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
      <Typography
        variant="subtitle2"
        sx={{ color: INK_FAINT, textTransform: 'uppercase', display: { xs: 'none', sm: 'block' } }}
      >
        Trace
      </Typography>

      <Select
        size="small"
        value={sources.some((s) => s.key === current) ? current : ''}
        displayEmpty
        disabled={disabled || sources.length === 0}
        onChange={(e) => onSelect(String(e.target.value))}
        MenuProps={{ slotProps: { paper: { sx: { maxHeight: 520, mt: 0.5 } } } }}
        renderValue={() => (
          <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
            {selected && (
              <Box
                sx={{
                  width: 7,
                  height: 7,
                  borderRadius: '50%',
                  flexShrink: 0,
                  bgcolor: selected.solved === false ? ACCENT : GOOD,
                }}
              />
            )}
            <Typography sx={{ fontFamily: MONO, fontSize: '0.78rem', color: INK }}>
              {selected ? selected.label : 'no trace loaded'}
            </Typography>
          </Stack>
        )}
        sx={{ minWidth: 268, '& .MuiSelect-select': { py: 0.7 } }}
      >
        {items.length ? (
          items
        ) : (
          <MenuItem value="" disabled>
            nothing in public/traces/
          </MenuItem>
        )}
      </Select>

      <Button
        component="label"
        size="small"
        variant="outlined"
        startIcon={<UploadFileIcon />}
        sx={{ whiteSpace: 'nowrap', color: INK_DIM, borderColor: STROKE }}
      >
        Upload
        <input
          hidden
          type="file"
          accept="application/json,.json"
          multiple
          onChange={(e) => {
            onUpload(e.target.files)
            // Allow re-selecting the same file after fixing it on disk.
            e.target.value = ''
          }}
        />
      </Button>
    </Stack>
  )
}

function Subheader({ children }: { children: React.ReactNode }) {
  return (
    <ListSubheader
      sx={{
        bgcolor: SURFACE_2,
        color: INK_DIM,
        fontSize: '0.7rem',
        fontWeight: 700,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
        lineHeight: 2.4,
        borderTop: `1px solid ${STROKE}`,
        borderBottom: `1px solid ${STROKE}`,
      }}
    >
      {children}
    </ListSubheader>
  )
}

function renderItem(source: Source) {
  return (
    <MenuItem
      key={source.key}
      value={source.key}
      sx={{ display: 'block', py: 0.9, borderBottom: `1px solid ${alpha(STROKE, 0.7)}` }}
    >
      <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
        <Typography sx={{ fontFamily: MONO, fontSize: '0.8rem', color: INK }}>
          {source.label}
        </Typography>
        {source.solved !== undefined && (
          <Chip
            size="small"
            label={source.solved ? 'solved' : 'unsolved'}
            sx={{
              height: 18,
              fontSize: '0.63rem',
              fontWeight: 700,
              bgcolor: alpha(source.solved ? GOOD : ACCENT, 0.12),
              color: source.solved ? GOOD : ACCENT,
            }}
          />
        )}
      </Stack>
      {source.note && (
        <Box sx={{ maxWidth: 470, whiteSpace: 'normal' }}>
          <Typography variant="caption" sx={{ color: INK_DIM, lineHeight: 1.45 }}>
            {source.note}
          </Typography>
        </Box>
      )}
      {!source.note && source.kind === 'uploaded' && (
        <Typography variant="caption" sx={{ color: INK_FAINT }}>
          uploaded
        </Typography>
      )}
    </MenuItem>
  )
}
