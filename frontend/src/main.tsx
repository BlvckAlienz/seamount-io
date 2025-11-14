// File: frontend/src/main.tsx
// ✅ FIXED: Removed duplicate BrowserRouter

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { Toaster } from 'react-hot-toast';
import App from './App.tsx';
import './index.css';

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