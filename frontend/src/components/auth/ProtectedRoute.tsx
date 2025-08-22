import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  minKycLevel?: number;
  requiredRole?: 'tribe' | 'alien';
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  minKycLevel = 0,
  requiredRole 
}) => {
  const { user, role, loading } = useAuth();

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Check KYC level
  if (user.kyc_level < minKycLevel) {
    return <Navigate to="/onboarding" replace />;
  }

  // Check role
  if (requiredRole && role !== requiredRole) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;