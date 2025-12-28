import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      // Ensure shared package dependencies are resolved from the main app
      external: [],
    }
  },
  optimizeDeps: {
    // Include shared package dependencies for pre-bundling
    include: ['axios', 'lucide-react', 'clsx']
  }
})