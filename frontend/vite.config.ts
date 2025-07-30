import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    // We add the terser minifier for secure, production-grade builds
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Removes console logs from production code
      },
    },
  },
  server: {
    // Proxy for local development to avoid CORS issues
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000', // Your local FastAPI backend
        changeOrigin: true,
      },
    },
  },
});