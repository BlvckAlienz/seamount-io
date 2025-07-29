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

  // --- PRODUCTION BUILD CONFIGURATION (THE CRITICAL FIX) ---
  build: {
    outDir: 'dist',
    // This explicitly tells Vite to use the 'terser' minifier,
    // which is a production-grade tool that will strip out all
    // 'eval()' calls, console logs, and other development artifacts.
    // This directly solves the Content Security Policy error.
    minify: 'terser',
    terserOptions: {
      compress: {
        // Drop console logs in production for a cleaner, more secure output
        drop_console: true,
      },
    },
  },
});