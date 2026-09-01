import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // Relative asset URLs, so `dist/` works when it is served from a
  // subdirectory or opened through any static file server.
  base: './',

  // `public/` is Vite's default static directory, so the traces committed in
  // `public/traces/` are served at /traces/ in dev and copied into
  // `dist/traces/` by a build. `python scripts/run_lats.py --publish` writes
  // there; anything else it writes goes to the gitignored `results/` folder
  // and reaches the viewer by drag-and-drop instead.
})
