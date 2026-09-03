import { StrictMode, useLayoutEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import CssBaseline from '@mui/material/CssBaseline'
import { ThemeProvider } from '@mui/material/styles'

import App from './App'
import { ColorModeContext, type Mode, applyMode, makeTheme, storedMode } from './theme'

/**
 * The colour mode lives here, above everything that could care about it.
 *
 * The tokens themselves are CSS variables keyed off `data-theme` on <html>, so
 * this state exists only to rebuild MUI's palette - which has to be given
 * literal colours - and to let the app bar's toggle reach the setter. The
 * document is written in a layout effect rather than an effect so the attribute
 * and the MUI theme land in the same paint; otherwise a toggle shows one frame
 * of dark controls on a light page.
 */
export function Root() {
  const [mode, setMode] = useState<Mode>(storedMode)
  const theme = useMemo(() => makeTheme(mode), [mode])
  const colorMode = useMemo(
    () => ({
      mode,
      toggle: () => setMode((m) => (m === 'light' ? 'dark' : 'light')),
    }),
    [mode],
  )

  useLayoutEffect(() => applyMode(mode), [mode])

  return (
    <ThemeProvider theme={theme}>
      <ColorModeContext.Provider value={colorMode}>
        <CssBaseline />
        <App />
      </ColorModeContext.Provider>
    </ThemeProvider>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
)
