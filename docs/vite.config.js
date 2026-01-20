import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './', // Important for GitHub Pages relative paths
  build: {
    outDir: '.', // Output to root of docs/ so it works immediately
    emptyOutDir: false, // Don't delete source files!
  }
})
