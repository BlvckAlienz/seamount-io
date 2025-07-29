// File Location: /frontend/src/App.tsx
// Description: The definitive main application shell with Vercel Analytics and Speed Insights integrated.

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';

// --- Core Components & Pages ---
import ErrorBoundary from './components/ErrorBoundary';
import Dashboard from './components/Dashboard';
import Portfolio from './components/Portfolio';
import Trading from './components/Trading';
import Payments from './components/Payments';
import Settings from './components/Settings';
import EnvSetup from './components/EnvSetup';
import Login from './components/Login';
import Signup from './components/Signup';
import Onboarding from './components/Onboarding';
import ProtectedRoute from './components/ProtectedRoute';
import ComplianceDashboard from './pages/admin/ComplianceDashboard';
import LoginModal from './components/LoginModal';

// --- Context & Config ---
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { validateEnvironment, type EnvironmentStatus } from './config/env';

// --- Landing Page Component ---
const LandingPage = ({ onShowLogin }: { onShowLogin: () => void }) => {
  const { enterDemoMode } = useAuth();
  // ... [Your full LandingPage JSX code goes here. It is unchanged.] ...
  return ( <div>Landing Page Placeholder</div> ); // Placeholder for brevity
};

const validateWithRetry = async (maxRetries = 3): Promise<EnvironmentStatus> => {
  // ... [Your full validateWithRetry function code goes here. It is unchanged.] ...
};

function App() {
  const [envStatus, setEnvStatus] = useState<EnvironmentStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [showLoginModal, setShowLoginModal] = useState(false);

  useEffect(() => {
    const initializeApp = async () => {
      try {
        setIsLoading(true);
        const status = await validateWithRetry(3);
        setEnvStatus(status);
      } catch (err) {
        console.error('💥 App initialization failed:', err);
        setEnvStatus({ isValid: false, errors: [err instanceof Error ? err.message : 'Unknown error'], warnings: [], criticalServices: [], optionalServices: [] });
      } finally {
        setIsLoading(false);
      }
    };
    initializeApp();
  }, []);

  if (isLoading) {
    // ... [Your full loading UI JSX code goes here. It is unchanged.] ...
    return <div>Loading...</div>; // Placeholder for brevity
  }

  if (envStatus && !envStatus.isValid) {
    return <ErrorBoundary><EnvSetup envStatus={envStatus} /></ErrorBoundary>;
  }

  return (
    <ErrorBoundary>
      <AuthProvider>
        <Toaster position="top-right" />
        <Router>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/" element={<LandingPage onShowLogin={() => setShowLoginModal(true)} />} />
            
            {/* Onboarding Route */}
            <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />

            {/* Core User Routes */}
            <Route path="/dashboard" element={<ProtectedRoute minKycLevel={1}><Dashboard /></ProtectedRoute>} />
            <Route path="/settings" element={<ProtectedRoute minKycLevel={1}><Settings /></ProtectedRoute>} />
            <Route path="/trading" element={<ProtectedRoute minKycLevel={2}><Trading /></ProtectedRoute>} />
            <Route path="/payments" element={<ProtectedRoute minKycLevel={2}><Payments /></ProtectedRoute>} />
            <Route path="/portfolio" element={<ProtectedRoute minKycLevel={3}><Portfolio /></ProtectedRoute>} />

            {/* Admin-Only Routes */}
            <Route path="/admin/compliance" element={<ProtectedRoute adminRequired={true}><ComplianceDashboard /></ProtectedRoute>} />

            {/* Fallback Route */}
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          {showLoginModal && <LoginModal onClose={() => setShowLoginModal(false)} />}
        </Router>
        
        {/* VERCEL OBSERVAILITY SUITE */}
        {/* These components are placed here to ensure they are loaded once */}
        {/* and can monitor the entire application lifecycle globally. */}
        <Analytics />
        <SpeedInsights /> 
        {/* <<<====== 2. ADD THE COMPONENT HERE */}

      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;