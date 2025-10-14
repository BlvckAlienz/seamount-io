import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  minKycLevel?: number;
  requiredRole?: 'tribe' | 'alien';
  allowRestricted?: boolean; // New prop to allow restricted access
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  minKycLevel = 0,
  requiredRole,
  allowRestricted = false // Default to false for security
}) => {
  const { user, role, loading } = useAuth();

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (!user) {
  return <Navigate to="/" replace />;
}

  // Check if user meets KYC requirements
  const meetsKycRequirement = user.kyc_level >= minKycLevel;
  
  // If KYC level is insufficient but restricted access is allowed
  if (!meetsKycRequirement && allowRestricted) {
    // Render children with restricted access
    return <>{children}</>;
  }
  
  // If KYC level is insufficient and restricted access is not allowed
  if (!meetsKycRequirement) {
    return <Navigate to="/onboarding" replace />;
  }

  // Check role
  if (requiredRole && role !== requiredRole) {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;