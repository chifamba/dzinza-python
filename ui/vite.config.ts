/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts', // Path to your setup file
    css: true, // If you want to process CSS during tests (e.g. for CSS modules)
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000', // Default backend port
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      }
    }
  }
})
