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
    minify: 'esbuild', 
    
    // Use default tree shaking which is safe and efficient
    esbuild: {
      treeShaking: true,
    },
    
    // Ensure react/jsx-runtime is not externalized
    rollupOptions: {
      external: [],
    },
  },

  // =============================================================================
  // DEFINITIVE LOCAL DEVELOPMENT SERVER CONFIGURATION
  // =============================================================================
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  
  // Ensure React JSX runtime is properly handled
  optimizeDeps: {
    include: ['react', 'react-dom', 'react/jsx-runtime'],
  },
});