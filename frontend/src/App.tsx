// File: frontend/src/App.tsx
// ✅ UNIFIED WALLET ARCHITECTURE - SINGLE PROVIDER SYSTEM

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';
import { api } from '@/lib/api';
import ResetPasswordPage from '@/pages/ResetPasswordPage';

// --- Core Components & Pages ---
import EnhancedErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthModal from './components/auth/AuthModal';
import InvestorContact from './components/InvestorContact';
import { CookieConsentBanner } from './components/CookieConsentBanner';

// --- Page Imports ---
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import DashboardPage from './pages/DashboardPage';
import AdminDashboard from './pages/AdminDashboard';
import PortfolioPage from './pages/PortfolioPage';
import TradingPage from './pages/TradingPage';
import PaymentsPage from './pages/PaymentsPage';
import SettingsPage from './pages/SettingsPage';
import UserProfilePage from './pages/UserProfilePage';
import ComplianceDashboard from './pages/admin/ComplianceDashboard';
import AuthDebugPage from './pages/AuthDebugPage';
import WalletRecovery from './pages/wallet-recovery';

// --- Context & Hooks ---
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { WalletOrchestratorProvider } from './contexts/WalletOrchestratorContext'; // ✅ UNIFIED PROVIDER
import { useAutoLogout } from './hooks/useAutoLogout';
import { DebugEnv } from './components/DebugEnv';

// 🚨 REMOVE THESE IMPORTS (causing conflicts):
// import { WalletConnectProvider } from './contexts/WalletConnectContext'; ❌
// import { WalletProvider } from './contexts/WalletContext'; ❌

const AppContent: React.FC = () => {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authView, setAuthView] = useState<'login' | 'register'>('register');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [consentGiven, setConsentGiven] = useState<boolean>(false);

  useAutoLogout();
  const auth = useAuth();
  const authSession = auth?.session || null;

  useEffect(() => {
    try {
      const stored = localStorage.getItem('seamount_consent_given');
      if (stored === 'true') {
        setConsentGiven(true);
      }
    } catch (error) {
      console.error('Failed to read consent:', error);
    }
  }, []);

  useEffect(() => {
    const initializeAnonymousSession = async () => {
      try {
        const response = await api.post('/api/v1/session/initialize');
        console.log('🔄 Session initialize response:', response);
        
        if (response && response.data) {
          setSessionId(response.data.session_id || response.data.id);
        } else if (response && response.session_id) {
          setSessionId(response.session_id);
        } else {
          console.warn('⚠️ Unexpected session response structure:', response);
          setSessionId(`anon_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
        }
      } catch (error) {
        console.error("Failed to initialize anonymous session:", error);
        setSessionId(`anon_error_${Date.now()}`);
      }
    };
    
    if (!authSession && !consentGiven) {
      initializeAnonymousSession();
    }
  }, [authSession, consentGiven]);

  const handleConsentGiven = () => {
    try {
      localStorage.setItem('seamount_consent_given', 'true');
      setConsentGiven(true);
    } catch (error) {
      console.error('Failed to save consent:', error);
    }
  };

  const handleOpenAuth = (view: 'login' | 'register') => {
    setAuthView(view);
    setShowAuthModal(true);
  };

  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage onOpenAuth={handleOpenAuth} />} />
        <Route path="/contact" element={<InvestorContact />} />
        <Route path="/debug-auth" element={<AuthDebugPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        
        {/* Protected Routes */}
        <Route 
          path="/onboarding" 
          element={
            <ProtectedRoute>
              <OnboardingPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/admin" 
          element={
            <ProtectedRoute adminRequired={true}>
              <AdminDashboard />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/profile" 
          element={
            <ProtectedRoute>
              <UserProfilePage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/settings" 
          element={
            <ProtectedRoute>
              <SettingsPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/trading" 
          element={
            <ProtectedRoute>
              <TradingPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/payments" 
          element={
            <ProtectedRoute>
              <PaymentsPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/portfolio" 
          element={
            <ProtectedRoute>
              <PortfolioPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/wallet-recovery" 
          element={
            <ProtectedRoute>
              <WalletRecovery />
            </ProtectedRoute>
          } 
        />
        
        {/* Admin Compliance Route */}
        <Route 
          path="/admin/compliance" 
          element={
            <ProtectedRoute adminRequired={true}>
              <ComplianceDashboard />
            </ProtectedRoute>
          } 
        />

        {/* Fallback Route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)} 
        initialView={authView}
      />

      {!authSession && !consentGiven && sessionId && (
        <CookieConsentBanner 
          sessionId={sessionId} 
          onConsentGiven={handleConsentGiven} 
        />
      )}
    </>
  );
};

function App() {
  return (
    <EnhancedErrorBoundary>
      <Router>
        <AuthProvider>
          {/* ✅ SINGLE UNIFIED WALLET PROVIDER */}
          <WalletOrchestratorProvider>
            <DebugEnv />
            <Toaster position="top-right" />
            <AppContent />
            <Analytics />
            <SpeedInsights />
          </WalletOrchestratorProvider>
        </AuthProvider>
      </Router>
    </EnhancedErrorBoundary>
  );
}

export default App;