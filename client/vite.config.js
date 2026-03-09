// Vite config for frontend
import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 5174,
    host: '0.0.0.0',
    strictPort: false,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'esbuild',
  },
  define: {
    'import.meta.env.VITE_API_URL': JSON.stringify(
      process.env.VITE_API_URL || 'http://localhost:8000'
    ),
  },
  envPrefix: 'VITE_',
})
