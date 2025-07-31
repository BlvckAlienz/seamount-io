import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';

// --- Components & Pages ---
import ProtectedRoute from './components/auth/ProtectedRoute';
import AuthModal from './components/auth/AuthModal';
import LandingPage from './pages/LandingPage';
import DashboardPage from './pages/DashboardPage';
// ... import all other pages

const AppRoutes: React.FC = () => {
  const { loading } = useAuth();
  const [showAuthModal, setShowAuthModal] = React.useState(false);
  const [authView, setAuthView] = React.useState<'login' | 'register'>('register');

  const handleOpenAuth = (view: 'login' | 'register') => {
    setAuthView(view);
    setShowAuthModal(true);
  };
  
  if (loading) {
    // Show a global loading spinner while the app determines the auth state
    return <div className="flex items-center justify-center h-screen bg-gray-950"></div>;
  }

  return (
    <>
      <Routes>
        <Route path="/" element={<LandingPage onOpenAuth={handleOpenAuth} />} />
        <Route path="/dashboard" element={<ProtectedRoute minKycLevel={1}><DashboardPage /></ProtectedRoute>} />
        {/* ... all your other routes */}
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