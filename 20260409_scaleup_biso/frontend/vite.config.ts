import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'https://beau-immusical-rina.ngrok-free.dev',
        changeOrigin: true,
        headers: { 'ngrok-skip-browser-warning': 'true' },
      },
    },
  },
})
