import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { Analytics } from '@vercel/analytics/react';
import { SpeedInsights } from '@vercel/speed-insights/react';
import { apiClient } from './config/api';

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
import AuthDebugPage from './pages/AuthDebugPage'; // ADD THIS IMPORT

// --- Context ---
import { AuthProvider } from './contexts/AuthContext';

// Custom Hook for Session Management
const useSession = () => {
  const [session, setSession] = useState<{ id: string | null; consentGiven: boolean }>({
    id: null,
    consentGiven: localStorage.getItem('seamount_consent_given') === 'true',
  });
  const { session: authSession } = useAuth(); // Get auth state from context

  useEffect(() => {
    // If consent is already given, no need to initialize a new session fingerprint
    if (session.consentGiven) {
      return;
    }

    const initializeSession = async () => {
      try {
        const { data } = await apiClient.post('/api/v1/session/initialize');
        setSession({ id: data.session_id, consentGiven: false });
      } catch (error) {
        console.error("Failed to initialize session:", error);
        // If this fails, we treat it as if consent was given to not block the UI
        setSession({ id: null, consentGiven: true }); 
      }
    };
    
    // Only initialize session if user is not authenticated
    // or if we don't have a session ID yet
    if (!authSession && !session.id) {
      initializeSession();
    }
  }, [session.consentGiven, authSession, session.id]);

  const handleConsentGiven = () => {
    localStorage.setItem('seamount_consent_given', 'true');
    setSession(prev => ({ ...prev, consentGiven: true }));
  };
  
  return {
    sessionId: session.id,
    consentGiven: session.consentGiven,
    handleConsentGiven,
  };
};

const AppContent: React.FC = () => {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authView, setAuthView] = useState<'login' | 'register'>('register');
  const { sessionId, consentGiven, handleConsentGiven } = useSession();

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
        <Route path="/debug-auth" element={<AuthDebugPage />} /> {/* ADD THIS ROUTE */}
        
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

        {/* Fallback Route */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)} 
        initialView={authView}
      />

      {!consentGiven && sessionId && (
        <CookieConsentBanner sessionId={sessionId} onConsentGiven={handleConsentGiven} />
      )}
    </>
  );
}

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