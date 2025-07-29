// File Location: frontend/src/components/auth/ProtectedRoute.tsx
// Description: The definitive, multi-layered security gatekeeper for all frontend routes.

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';

// --- CORRECTED IMPORT PATH ---
// We now use the '@' alias for a robust, absolute path from the '/src' directory.
import { useAuth } from '@/contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactElement;
  minKycLevel?: number;
  adminRequired?: boolean;
}

const LoadingScreen: React.FC = () => (
  <div className="flex items-center justify-center min-h-screen bg-gray-950">
    <div className="relative w-16 h-16">
      <div className="absolute inset-0 rounded-full border-4 border-gray-800"></div>
      <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 animate-spin"></div>
    </div>
  </div>
);

const AccessDeniedCard: React.FC<{ title: string; message: string; actionText: string; actionUrl: string }> = ({ title, message, actionText, actionUrl }) => (
  <div className="flex items-center justify-center min-h-screen bg-gray-950 p-4 text-white">
    <div className="max-w-md w-full bg-gray-900/80 backdrop-blur-lg rounded-xl p-8 text-center shadow-2xl border border-red-800/80">
      <AlertTriangle className="mx-auto h-12 w-12 text-red-500 mb-4" />
      <h2 className="text-2xl font-bold text-white mb-2">{title}</h2>
      <p className="text-gray-400 mb-6">{message}</p>
      <a href={actionUrl} className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors font-semibold">
        {actionText}
      </a>
    </div>
  </div>
);

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, minKycLevel = 0, adminRequired = false }) => {
  const { user, loading, isDemoMode } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingScreen />;
  }

  // --- Check 1: Authentication ---
  if (!user && !isDemoMode) {
    // User is not logged in. Redirect them to the landing page to use the AuthModal.
    // We pass the intended destination in the state so they can be redirected after login.
    return <Navigate to="/" state={{ from: location, openAuth: true }} replace />;
  }
  
  // --- Handle Demo Mode ---
  if (isDemoMode) {
    if (adminRequired) {
      return <AccessDeniedCard 
        title="Admin Access Required"
        message="This feature is not available in demo mode and requires administrator privileges."
        actionText="Exit Demo & Login"
        actionUrl="/"
      />;
    }
    return children; // Allow access for demo users on non-admin routes
  }

  // --- Handle Real User ---
  if (!user) {
    // This is a safety net. If the user object is somehow null after the loading state,
    // send them back to the landing page.
    return <Navigate to="/" replace />;
  }

  // --- Check 2: Admin Role ---
  if (adminRequired && !user.is_admin) {
    return <AccessDeniedCard 
      title="Access Denied"
      message="You do not have the required permissions to access this page."
      actionText="Go to Dashboard"
      actionUrl="/dashboard"
    />;
  }

  // --- Check 3: KYC Trust Level ---
  if (user.kyc_level < minKycLevel) {
    return <AccessDeniedCard 
      title="Verification Required"
      message={`Your current verification level (${user.kyc_level}) is not sufficient. Please complete the next step of your identity verification to access this feature.`}
      actionText="Complete Verification"
      actionUrl="/onboarding"
    />;
  }

  // --- All checks passed ---
  return children;
};

export default ProtectedRoute;