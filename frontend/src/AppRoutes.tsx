import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';

// --- Components & Pages ---
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthModal from './components/auth/AuthModal';
import LandingPage from './pages/LandingPage';
import DashboardPage from './pages/DashboardPage';
import OnboardingPage from './pages/OnboardingPage';
import PortfolioPage from './pages/PortfolioPage';
import TradingPage from './pages/TradingPage';
import PaymentsPage from './pages/PaymentsPage';
import SettingsPage from './pages/SettingsPage';
import Help from './pages/Help';
import AuthDebugPage from './pages/AuthDebugPage';
import WalletSetupPage from './pages/WalletSetupPage';
import UserProfilePage from './pages/UserProfilePage';

const AppRoutes: React.FC = () => {
  const { loading } = useAuth();
  const [showAuthModal, setShowAuthModal] = React.useState(false);
  const [authView, setAuthView] = React.useState<'login' | 'register'>('register');

  const handleOpenAuth = (view: 'login' | 'register') => {
    setAuthView(view);
    setShowAuthModal(true);
  };
  
  if (loading) {
    return <div className="flex items-center justify-center h-screen bg-gray-950"></div>;
  }

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage onOpenAuth={handleOpenAuth} />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/dashboard" element={<ProtectedRoute minKycLevel={1}><DashboardPage /></ProtectedRoute>} />
        <Route path="/portfolio" element={<ProtectedRoute minKycLevel={1}><PortfolioPage /></ProtectedRoute>} />
        <Route path="/trading" element={<ProtectedRoute minKycLevel={2}><TradingPage /></ProtectedRoute>} />
        <Route path="/payments" element={<ProtectedRoute minKycLevel={2}><PaymentsPage /></ProtectedRoute>} />
        <Route path="/settings" element={<ProtectedRoute minKycLevel={0}><SettingsPage /></ProtectedRoute>} />
        <Route path="/help" element={<Help />} />
        <Route path="/debug" element={<AuthDebugPage />} />
        <Route path="/wallet-setup" element={<ProtectedRoute minKycLevel={1}><WalletSetupPage /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute minKycLevel={1}><UserProfilePage /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <AuthModal 
        isOpen={showAuthModal} 
        onClose={() => setShowAuthModal(false)} 
        initialView={authView}
      />
    </>
  );
};

export default AppRoutes;