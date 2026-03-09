import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  minKycLevel?: number;
  requiredRole?: 'tribe' | 'alien';
  allowRestricted?: boolean;
  adminRequired?: boolean; // ADD THIS PROP
  businessRequired?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  minKycLevel = 0,
  requiredRole,
  allowRestricted = false,
  adminRequired = false,
  businessRequired = false // 🆕 ADD THIS
}) => {
  const { user, role, loading, userProfile } = useAuth(); // 🆕 ADD userProfile

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  console.log('🔍 ProtectedRoute Debug:', {
    user,
    userProfile,
    isAdmin: userProfile?.is_admin,
    kycLevel: user?.kyc_level,
    accountType: userProfile?.account_type,
    loading
  });

  if (!user) {
    return <Navigate to="/" replace />;
  }

  // ADD ADMIN CHECK
  if (adminRequired && !userProfile?.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  // 🚨 Admin bypass — skip ALL other guards (KYC, role, business checks)
  if (userProfile?.is_admin) {
    return <>{children}</>;
  }

  // 🆕 ADD BUSINESS CHECK
  if (businessRequired && userProfile?.account_type !== 'business') {
    return <Navigate to="/dashboard" replace />;
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