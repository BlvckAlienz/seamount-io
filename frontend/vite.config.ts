import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  // --- Core Plugins ---
  plugins: [react()],

  // --- Path Aliases for Clean Imports ---
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },

  // --- Production Build Configuration ---
  build: {
    outDir: 'dist',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // Removes console.log from production builds
      },
    },
  },

  // =============================================================================
  // DEFINITIVE LOCAL DEVELOPMENT SERVER CONFIGURATION
  // =============================================================================
  server: {
    proxy: {
      // This rule intercepts all requests made from the frontend to a path starting with '/api'
      '/api': {
        // It forwards them to your local Python backend server
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,

        // --- THE CRITICAL FIX IS HERE ---
        // This 'rewrite' function is a powerful rule that intercepts the path before forwarding.
        // It uses a regular expression (`/^\/api\/api/`) to find any path that accidentally
        // starts with `/api/api` and intelligently corrects it to a single `/api`.
        // This permanently solves the "double api" bug for your local development.
        rewrite: (path) => path.replace(/^\/api\/api/, '/api'),
      },
    },
  },
});