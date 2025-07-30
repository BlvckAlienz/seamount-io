// File Location: /frontend/src/App.tsx
// Description: The definitive, production-ready application shell and router for Seamount.io.

import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';

// --- Core Components & Pages (Verified against your final `tree` structure) ---
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthModal from './components/auth/AuthModal';

// --- Page Imports (Verified against your final `tree` structure) ---
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import DashboardPage from './pages/DashboardPage';
import PortfolioPage from './pages/PortfolioPage';
import TradingPage from './pages/TradingPage';
import PaymentsPage from './pages/PaymentsPage';
import SettingsPage from './pages/SettingsPage';
import UserProfilePage from './pages/UserProfilePage';
import ComplianceDashboard from './pages/admin/ComplianceDashboard';

// --- Context ---
import { AuthProvider } from './contexts/AuthContext';

// AppContent handles the routing and modal state, keeping the main App component clean.
// This is a best practice for performance and separation of concerns.
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
        
        {/* Protected Routes with Progressive KYC Levels */}
        <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute minKycLevel={1}><DashboardPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute minKycLevel={1}><UserProfilePage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute minKycLevel={1}><SettingsPage /></ProtectedRoute>} />
        <Route path="/trading" element={<ProtectedRoute minKycLevel={2}><TradingPage /></ProtectedRoute>} />
        <Route path="/payments" element={<ProtectedRoute minKycLevel={2}><PaymentsPage /></ProtectedRoute>} />
        <Route path="/portfolio" element={<ProtectedRoute minKycLevel={3}><PortfolioPage /></ProtectedRoute>} />
        
        {/* Admin Route */}
        <Route path="/admin/compliance" element={<ProtectedRoute adminRequired={true}><ComplianceDashboard /></ProtectedRoute>} />

        {/* Fallback Route - redirect unknown paths to the landing page */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)} 
        initialView={authView}
      />
    </>
  );
}

function App() {
  // A production app trusts its environment has been set correctly by Vercel.
  // The complex and fragile client-side validation logic has been completely removed.
  // This is the standard, robust pattern for production applications.

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