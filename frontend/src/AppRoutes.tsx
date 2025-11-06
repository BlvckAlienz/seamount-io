// File: frontend/src/AppRoutes.tsx
import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

// Components
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthModal from './components/auth/AuthModal';

// Pages
import LandingPage from './pages/LandingPage';
import DashboardPage from './pages/DashboardPage';
import OnboardingPage from './pages/OnboardingPage';
import portfolioPage from './pages/portfolioPage';
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
  const navigate = useNavigate();
  const { session } = useAuth();

  const handleOpenAuth = (view: 'login' | 'register') => {
    setAuthView(view);
    setShowAuthModal(true);
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
      </div>
    );
  }

  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<LandingPage onOpenAuth={handleOpenAuth} />} />
        <Route path="/help" element={<Help />} />
        <Route path="/debug" element={<AuthDebugPage />} />
        
        {/* Protected Routes */}
        <Route 
          path="/onboarding" 
          element={
            <ProtectedRoute minKycLevel={0}>
              <OnboardingPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/dashboard" 
          element={
            <ProtectedRoute minKycLevel={0}>
              <DashboardPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/portfolio" 
          element={
            <ProtectedRoute minKycLevel={0}>
              <portfolioPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/settings" 
          element={
            <ProtectedRoute minKycLevel={0}>
              <SettingsPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/wallet-setup" 
          element={
            <ProtectedRoute minKycLevel={0}>
              <WalletSetupPage 
                userId={session?.user?.id || ''} 
                onComplete={(wallet) => {
                  console.log('Wallet created:', wallet);
                  navigate('/dashboard');
                }}
              />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/profile" 
          element={
            <ProtectedRoute minKycLevel={0}>
              <UserProfilePage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/trading" 
          element={
            <ProtectedRoute minKycLevel={1}>
              <TradingPage />
            </ProtectedRoute>
          } 
        />
        <Route 
          path="/payments" 
          element={
            <ProtectedRoute minKycLevel={1}>
              <PaymentsPage />
            </ProtectedRoute>
          } 
        />
        
        {/* Catch-all */}
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