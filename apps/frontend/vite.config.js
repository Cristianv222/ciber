import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    dedupe: ['three'],
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      // Necesario para que el hot-reload detecte cambios dentro del contenedor
      usePolling: true,
    },
  },
})
