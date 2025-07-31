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
    // This proxy is ESSENTIAL for your "Two Terminals" local development workflow.
    // It tells your Vite server (running on port 5173) to forward any request
    // it sees for '/api' over to your Python backend server (running on port 8000).
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // The rewrite is removed as it's no longer necessary with the corrected apiClient
      },
    },
  },
});