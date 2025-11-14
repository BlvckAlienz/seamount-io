// File: src/main.tsx
import './polyfills'; // ✅ ADD THIS LINE - MUST BE FIRST
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.tsx';
import './index.css';
import { Toaster } from 'react-hot-toast';

<Toaster
  position="top-right"
  containerStyle={{
    zIndex: 99999, // ✅ VERY HIGH - above everything
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
    },
    success: {
      duration: 5000,
      iconTheme: {
        primary: '#10b981',
        secondary: '#ffffff',
      },
    },
    error: {
      duration: 6000,
      iconTheme: {
        primary: '#ef4444',
        secondary: '#ffffff',
      },
    },
  }}
/>

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);