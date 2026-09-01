/**
 * Choosing a trace: the bundled ones, plus anything the user drops in.
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

import { ACCENT, GOOD, INK_DIM, INK_FAINT, alpha } from '../theme'

export interface Source {
  key: string
  label: string
  kind: 'bundled' | 'uploaded'
  /** Filename inside `public/traces/`, for bundled entries. */
  file?: string
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

export default function TracePicker({
  sources,
  current,
  disabled,
  onSelect,
  onUpload,
}: Props) {
  const bundled = sources.filter((s) => s.kind === 'bundled')
  const uploaded = sources.filter((s) => s.kind === 'uploaded')

  const items: React.ReactNode[] = []
  if (bundled.length) {
    items.push(
      <ListSubheader key="h-bundled" sx={{ bgcolor: 'transparent', lineHeight: 2.2 }}>
        from public/traces/
      </ListSubheader>,
    )
    items.push(...bundled.map(renderItem))
  }
  if (uploaded.length) {
    items.push(
      <ListSubheader key="h-uploaded" sx={{ bgcolor: 'transparent', lineHeight: 2.2 }}>
        uploaded this session
      </ListSubheader>,
    )
    items.push(...uploaded.map(renderItem))
  }

  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
      <Select
        size="small"
        value={sources.some((s) => s.key === current) ? current : ''}
        displayEmpty
        disabled={disabled || sources.length === 0}
        onChange={(e) => onSelect(String(e.target.value))}
        renderValue={(value) => {
          const source = sources.find((s) => s.key === value)
          return (
            <Typography sx={{ fontSize: '0.82rem' }}>
              {source ? source.label : 'no trace loaded'}
            </Typography>
          )
        }}
        sx={{ minWidth: 260, '& .MuiSelect-select': { py: 0.65 } }}
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
        sx={{ whiteSpace: 'nowrap' }}
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

function renderItem(source: Source) {
  return (
    <MenuItem key={source.key} value={source.key} sx={{ display: 'block', py: 0.75 }}>
      <Stack direction="row" spacing={0.75} sx={{ alignItems: 'center' }}>
        <Typography sx={{ fontSize: '0.84rem' }}>{source.label}</Typography>
        {source.solved !== undefined && (
          <Chip
            size="small"
            label={source.solved ? 'solved' : 'unsolved'}
            sx={{
              height: 17,
              fontSize: '0.62rem',
              bgcolor: alpha(source.solved ? GOOD : ACCENT, 0.14),
              color: source.solved ? GOOD : ACCENT,
            }}
          />
        )}
      </Stack>
      {source.note && (
        <Box sx={{ maxWidth: 460, whiteSpace: 'normal' }}>
          <Typography variant="caption" sx={{ color: INK_FAINT, lineHeight: 1.4 }}>
            {source.note}
          </Typography>
        </Box>
      )}
      {!source.note && source.kind === 'uploaded' && (
        <Typography variant="caption" sx={{ color: INK_DIM }}>
          uploaded
        </Typography>
      )}
    </MenuItem>
  )
}
