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

  // =============================================================================
  // DEFINITIVE PRODUCTION BUILD CONFIGURATION
  // =============================================================================
  build: {
    outDir: 'dist',
    // We are switching to Vite's default, highly optimized, and safer 'esbuild' minifier.
    // It is significantly faster and less prone to the aggressive tree-shaking errors
    // that can incorrectly remove `onClick` handlers. This is the most critical fix.
    minify: 'esbuild', 
  },

  // =============================================================================
  // DEFINITIVE LOCAL DEVELOPMENT SERVER CONFIGURATION
  // =============================================================================
  server: {
    proxy: {
      // This proxy is ESSENTIAL for your "Two Terminals" local development workflow.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});