// File Location: frontend/src/components/ProtectedRoute.tsx
// Description: The definitive, multi-layered security gatekeeper for all frontend routes.

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Shield, AlertTriangle, Info } from 'lucide-react';

interface ProtectedRouteProps {
  children: React.ReactElement;
  minKycLevel?: number; // e.g., 1 for basic access, 2 for trading, etc.
  adminRequired?: boolean; // Set to true for admin-only routes
}

const LoadingScreen = () => (
  <div className="flex items-center justify-center min-h-screen bg-gray-50">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
  </div>
);

const AccessDeniedCard = ({ title, message, actionText, actionUrl }: { title: string, message: string, actionText: string, actionUrl: string }) => (
  <div className="flex items-center justify-center min-h-screen bg-gray-50 p-4">
    <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
      <AlertTriangle className="mx-auto h-12 w-12 text-red-500 mb-4" />
      <h2 className="text-2xl font-bold text-gray-800 mb-2">{title}</h2>
      <p className="text-gray-600 mb-6">{message}</p>
      <a href={actionUrl} className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors">
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
  // If the user is not authenticated and not in demo mode, redirect to login.
  if (!user && !isDemoMode) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
  // If in demo mode, allow access to non-admin routes, otherwise show a message.
  if (isDemoMode) {
    if (adminRequired) {
      return <AccessDeniedCard 
        title="Admin Access Required"
        message="This feature is not available in demo mode and requires administrator privileges."
        actionText="Exit Demo & Login"
        actionUrl="/login"
      />;
    }
    return children; // Allow access for demo users on non-admin routes
  }

  // At this point, we know we have a real, authenticated user.
  if (!user) {
    // This case should theoretically not be hit, but it's a safety net.
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // --- Check 2: Admin Role ---
  // If the route requires an admin and the user is not one, deny access.
  if (adminRequired && !user.is_admin) {
    return <AccessDeniedCard 
      title="Access Denied"
      message="You do not have the required permissions to access this page."
      actionText="Go to Dashboard"
      actionUrl="/dashboard"
    />;
  }

  // --- Check 3: KYC Trust Level ---
  // If the route requires a minimum KYC level and the user doesn't meet it, deny access.
  if (user.kyc_level < minKycLevel) {
    return <AccessDeniedCard 
      title="Verification Required"
      message={`Your current verification level (${user.kyc_level}) is not sufficient. Please complete the next step of your identity verification to access this feature.`}
      actionText="Complete Verification"
      actionUrl="/onboarding"
    />;
  }

  // --- All checks passed ---
  // The user is authenticated and has the required permissions. Render the component.
  return children;
};

export default ProtectedRoute;