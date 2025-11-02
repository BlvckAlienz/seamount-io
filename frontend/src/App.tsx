import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';
import { apiClient, API_ENDPOINTS } from './config/api';

// --- Core Components & Pages ---
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthModal from './components/auth/AuthModal';
import InvestorContact from './components/InvestorContact';
import { CookieConsentBanner } from './components/CookieConsentBanner';

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
import AuthDebugPage from './pages/AuthDebugPage';
import WalletRecovery from './pages/wallet-recovery';

// --- Context & Hooks ---
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { useAutoLogout } from './hooks/useAutoLogout';

const AppContent: React.FC = () => {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authView, setAuthView] = useState<'login' | 'register'>('register');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [consentGiven, setConsentGiven] = useState<boolean>(false);

  // ✅ Auto-logout hook (only runs for authenticated users)
  useAutoLogout();

  // ✅ Call hook unconditionally at top level
  const auth = useAuth();
  const authSession = auth?.session || null;

  // ✅ Initialize consent from localStorage after mount
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
    // Initialize anonymous session for unauthenticated users without consent
    const initializeAnonymousSession = async () => {
      try {
        const { data } = await apiClient.post(API_ENDPOINTS.SESSION.INITIALIZE);
        setSessionId(data.session_id);
      } catch (error) {
        console.error("Failed to initialize anonymous session:", error);
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
        
        {/* Protected Routes */}
        <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><UserProfilePage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        <Route path="/trading" element={<ProtectedRoute><TradingPage /></ProtectedRoute>} />
        <Route path="/payments" element={<ProtectedRoute><PaymentsPage /></ProtectedRoute>} />
        <Route path="/portfolio" element={<ProtectedRoute><PortfolioPage /></ProtectedRoute>} />
        <Route path="/wallet-recovery" element={<ProtectedRoute><WalletRecovery /></ProtectedRoute>} />

        {/* Admin Route */}
        <Route path="/admin/compliance" element={<ProtectedRoute adminRequired={true}><ComplianceDashboard /></ProtectedRoute>} />

        {/* Fallback Route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)} 
        initialView={authView}
      />

      {!authSession && !consentGiven && sessionId && (
        <CookieConsentBanner sessionId={sessionId} onConsentGiven={handleConsentGiven} />
      )}
    </>
  );
};

function App() {
  return (
    <ErrorBoundary>
      <Router>
        <AuthProvider>
          <Toaster position="top-right" />
          <AppContent />
          <Analytics />
          <SpeedInsights /> 
        </AuthProvider>
      </Router>
    </ErrorBoundary>
  );
}

export default App;