import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// In dev, calls to /api are proxied to the FastAPI backend (default :8100), so
// the frontend can use same-origin fetches and avoid CORS entirely. Override the
// target with PROMPTLAB_API_PROXY when the backend runs on another port.
// Port 5174 (not the common 5173) to avoid clashing with another local dev server.
const apiTarget = process.env.PROMPTLAB_API_PROXY || 'http://localhost:8100'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/api': apiTarget,
    },
  },
})
