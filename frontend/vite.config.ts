import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { nodePolyfills } from 'vite-plugin-node-polyfills';

export default defineConfig({
  plugins: [
    react(),
    nodePolyfills({
      include: ['buffer', 'process', 'crypto', 'stream', 'util'],
      globals: {
        Buffer: true,
        global: true,
        process: true,
      },
    }),
  ],
  base: '/',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      'viem/chains': path.resolve(__dirname, 'node_modules/viem/chains'),
      'wagmi/chains': path.resolve(__dirname, 'node_modules/wagmi/chains'),
    },
  },
  define: {
    global: 'globalThis',
    'process.env': {},
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: 'terser',
    terserOptions: {
      compress: {
        // 🚨 Prevent terser from optimizing away BigInt checks
        pure_getters: false,
        keep_fargs: true,
        keep_fnames: true,
      },
      mangle: {
        // 🚨 Don't mangle Math.pow - keep our override
        reserved: ['Math', 'pow', 'BigInt']
      }
    },
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'web3-vendor': ['wagmi', 'viem', '@reown/appkit', '@reown/appkit-adapter-wagmi'],  // ✅ NEW
        },
      },
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'buffer',
      'wagmi',
      'viem',
      '@reown/appkit',               // ✅ NEW
      '@reown/appkit-adapter-wagmi', // ✅ NEW
      'process',
    ],
    esbuildOptions: {
      define: {
        global: 'globalThis',
      },
      target: 'es2020',
      supported: {
        'bigint': true,
      },
    },
  },
});