// File: frontend/src/main.tsx
// ✅ FIXED: Removed duplicate BrowserRouter

import './polyfills';
import { warmUpServer } from './config/api';

// Fire warm-up immediately — don't await, don't block render
warmUpServer();

// ============================================================================
// 🔇 SUPPRESS HARMLESS CONSOLE ERRORS
// ============================================================================
if (typeof window !== 'undefined') {
  const originalError = console.error;
  const originalWarn = console.warn;
  
  console.error = (...args: any[]) => {
    const msg = args[0]?.toString() || '';
    
    // Suppress harmless errors
    if (
      msg.includes('MetaMask extension not found') ||
      msg.includes('Failed to connect to MetaMask') ||
      msg.includes('Uncaught (in promise)') ||
      msg.includes('pulse.walletconnect.org') ||
      args[0]?.message?.includes('MetaMask')
    ) {
      return; // Silently ignore
    }
    
    originalError(...args);
  };
  
  console.warn = (...args: any[]) => {
    const msg = args[0]?.toString() || '';
    
    if (msg.includes('pulse.walletconnect.org')) {
      return; // Silently ignore
    }
    
    originalWarn(...args);
  };
}
// ============================================================================

// Now safe to import React and other libraries
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Toaster } from 'react-hot-toast';
import App from './App.tsx';
import './index.css';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { appkit } from './config/walletConnect'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* 🔄 REMOVED: <BrowserRouter> - Already in App.tsx */}
    <App />
    
    {/* ✅ TOAST CONFIGURATION: Z-INDEX ABOVE ALL MODALS */}
    <Toaster
      position="top-right"
      containerStyle={{
        zIndex: 99999, // ✅ CRITICAL: Higher than modal z-index (50)
      }}
      toastOptions={{
        duration: 5000,
        style: {
          background: '#1f2937',
          color: '#ffffff',
          fontSize: '14px',
          fontWeight: '500',
          padding: '16px',
          borderRadius: '12px',
          boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3)',
          zIndex: 99999,
        },
        success: {
          duration: 5000,
          style: {
            background: '#10b981',
            color: '#ffffff',
          },
          iconTheme: {
            primary: '#ffffff',
            secondary: '#10b981',
          },
        },
        error: {
          duration: 6000,
          style: {
            background: '#ef4444',
            color: '#ffffff',
          },
          iconTheme: {
            primary: '#ffffff',
            secondary: '#ef4444',
          },
        },
      }}
    />
  </StrictMode>
);