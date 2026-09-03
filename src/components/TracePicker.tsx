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
import IconButton from '@mui/material/IconButton'
import ListSubheader from '@mui/material/ListSubheader'
import MenuItem from '@mui/material/MenuItem'
import Select from '@mui/material/Select'
import Stack from '@mui/material/Stack'
import Tooltip from '@mui/material/Tooltip'
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
  /** Phone: a row of its own under the app bar, so the select takes the width
      and the upload button gives up its label rather than its target. */
  compact?: boolean
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
  compact,
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

  const upload = (
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
  )

  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
      {!compact && (
        <Typography
          variant="subtitle2"
          sx={{ color: INK_FAINT, textTransform: 'uppercase', display: { xs: 'none', sm: 'block' } }}
        >
          Trace
        </Typography>
      )}

      <Select
        size="small"
        value={sources.some((s) => s.key === current) ? current : ''}
        displayEmpty
        disabled={disabled || sources.length === 0}
        onChange={(e) => onSelect(String(e.target.value))}
        MenuProps={{
          slotProps: {
            paper: { sx: { maxHeight: 520, mt: 0.5, maxWidth: 'calc(100vw - 24px)' } },
          },
        }}
        renderValue={() => (
          <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center', minWidth: 0 }}>
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
            <Typography
              noWrap
              sx={{ fontFamily: MONO, fontSize: '0.78rem', color: INK, minWidth: 0 }}
            >
              {selected ? selected.label : 'no trace loaded'}
            </Typography>
          </Stack>
        )}
        sx={
          compact
            ? { flex: 1, minWidth: 0, '& .MuiSelect-select': { py: 0.7 } }
            : { minWidth: 268, '& .MuiSelect-select': { py: 0.7 } }
        }
      >
        {items.length ? (
          items
        ) : (
          <MenuItem value="" disabled>
            nothing in public/traces/
          </MenuItem>
        )}
      </Select>

      {compact ? (
        <Tooltip title="Upload a trace" arrow>
          <IconButton
            component="label"
            size="small"
            aria-label="upload a trace"
            sx={{
              flexShrink: 0,
              color: INK_DIM,
              border: `1px solid ${STROKE}`,
              borderRadius: 1,
            }}
          >
            <UploadFileIcon fontSize="small" />
            {upload}
          </IconButton>
        </Tooltip>
      ) : (
        <Button
          component="label"
          size="small"
          variant="outlined"
          startIcon={<UploadFileIcon />}
          sx={{ whiteSpace: 'nowrap', color: INK_DIM, borderColor: STROKE }}
        >
          Upload
          {upload}
        </Button>
      )}
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
        <Box sx={{ maxWidth: 'min(470px, calc(100vw - 72px))', whiteSpace: 'normal' }}>
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
