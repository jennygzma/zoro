import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return undefined
          }

          if (id.includes('reactflow')) {
            return 'vendor-reactflow'
          }

          if (id.includes('/refractor/lang/')) {
            const langPath = id.split('/refractor/lang/')[1] || ''
            const firstChar = (langPath[0] || 'm').toLowerCase()
            const bucket = firstChar < 'n' ? 'am' : 'nz'
            return `vendor-refractor-${bucket}`
          }

          if (id.includes('/refractor/')) {
            return 'vendor-refractor-core'
          }

          if (id.includes('/highlight.js/')) {
            return 'vendor-highlight'
          }

          if (id.includes('react-markdown') || id.includes('react-syntax-highlighter')) {
            return 'vendor-markdown'
          }

          if (id.includes('/@emotion/')) {
            return 'vendor-emotion'
          }

          if (id.includes('/axios/')) {
            return 'vendor-axios'
          }

          if (id.includes('@mui/')) {
            return 'vendor-mui'
          }

          if (id.includes('/react/') || id.includes('/react-dom/')) {
            return 'vendor-react'
          }

          return 'vendor-misc'
        },
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5274,
    strictPort: true,
  },
  preview: {
    host: '0.0.0.0',
    port: 5274,
    strictPort: true,
  },
})
