import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  define: {
    global: 'globalThis', // ✅ ADD THIS LINE - FIXES "global is not defined"
  },
  build: {
    outDir: 'dist',
    sourcemap: false, // Disable for production
    minify: 'esbuild',
    target: 'es2015',
    rollupOptions: {
      output: {
        // Simpler chunk strategy - let Vite handle it
        manualChunks: undefined, // Remove manual chunking
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom'], // Pre-bundle these
    exclude: [], // Don't exclude anything
  },
});