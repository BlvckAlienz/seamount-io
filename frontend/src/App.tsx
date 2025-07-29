// File Location: /frontend/src/App.tsx
// Description: The definitive main application shell, corrected to match the final project structure.

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';

// --- Core Components & Pages (Verified against your final `tree` structure) ---
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthModal from './components/auth/AuthModal';
import EnvSetup from './components/layout/EnvSetup';

// --- Page Imports ---
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import DashboardPage from './pages/DashboardPage';
import PortfolioPage from './pages/PortfolioPage';
import TradingPage from './pages/TradingPage';
import PaymentsPage from './pages/PaymentsPage';
import SettingsPage from './pages/SettingsPage';
import UserProfilePage from './pages/UserProfilePage';
import ComplianceDashboard from './pages/admin/ComplianceDashboard';

// --- Context & Config ---
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { validateEnvironment, type EnvironmentStatus } from './config/env';

const AppContent: React.FC = () => {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authView, setAuthView] = useState<'login' | 'register'>('register');

  const handleOpenAuth = (view: 'login' | 'register') => {
    setAuthView(view);
    setShowAuthModal(true);
  };
  
  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage onOpenAuth={handleOpenAuth} />} />
        
        {/* Protected Routes */}
        <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute minKycLevel={1}><DashboardPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute minKycLevel={1}><UserProfilePage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute minKycLevel={1}><SettingsPage /></ProtectedRoute>} />
        <Route path="/trading" element={<ProtectedRoute minKycLevel={2}><TradingPage /></ProtectedRoute>} />
        <Route path="/payments" element={<ProtectedRoute minKycLevel={2}><PaymentsPage /></ProtectedRoute>} />
        <Route path="/portfolio" element={<ProtectedRoute minKycLevel={3}><PortfolioPage /></ProtectedRoute>} />
        
        {/* Admin Route */}
        <Route path="/admin/compliance" element={<ProtectedRoute adminRequired={true}><ComplianceDashboard /></ProtectedRoute>} />

        {/* Fallback Route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} initialView={authView} />
    </>
  );
}

function App() {
  const [envStatus, setEnvStatus] = useState<EnvironmentStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const validate = async () => {
      try {
        const status = await validateEnvironment();
        setEnvStatus(status);
      } catch (err) {
        setEnvStatus({ isValid: false, errors: [err instanceof Error ? err.message : 'Unknown error'], warnings: [], criticalServices: [], optionalServices: [] });
      } finally {
        setIsLoading(false);
      }
    };
    validate();
  }, []);

  if (isLoading) {
    return <div className="flex items-center justify-center h-screen bg-gray-950"></div>; // Or your loading skeleton
  }

  if (envStatus && !envStatus.isValid) {
    return <ErrorBoundary><EnvSetup envStatus={envStatus} /></ErrorBoundary>;
  }

  return (
    <ErrorBoundary>
      <AuthProvider>
        <Toaster position="top-right" />
        <Router>
          <AppContent />
        </Router>
        <Analytics />
        <SpeedInsights /> 
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;