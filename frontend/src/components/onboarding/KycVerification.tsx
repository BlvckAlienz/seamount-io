// File Location: frontend/src/components/onboarding/KycVerification.tsx
// HYBRID APPROACH INTEGRATION: Smart BVN collection before verification

import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';
import ComplyCubeVerification from './ComplyCubeVerification';
import BVNCollectionModal from './BVNCollectionModal';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';
import UniversalIDModal from './UniversalIDModal';
import { AlertCircle } from 'lucide-react';

interface ProfileCheck {
  profile_complete: boolean;
  missing_fields: string[];
  errors: string[];
  can_start_kyc: boolean;
  kyc_status: string;
}

interface KycVerificationProps {
  onComplete?: () => void;
  onError?: (error: string) => void;
}

export const KycVerification: React.FC<KycVerificationProps> = ({ onComplete, onError }) => {
  const { user, userProfile } = useAuth();
  const [loading, setLoading] = useState(false);
  const [profileCheck, setProfileCheck] = useState<ProfileCheck | null>(null);
  const [showComplyCube, setShowComplyCube] = useState(false);
  const [showBVNModal, setShowBVNModal] = useState(false);
  const [error, setError] = useState<string>('');
  const [profileData, setProfileData] = useState({
    first_name: '',
    last_name: '',
    email: ''
  });

  const isNigerianUser = userProfile?.country_code === 'NG' || userProfile?.country === 'NG';

  useEffect(() => {
    checkProfileCompleteness();
  }, [user]);

  const checkProfileCompleteness = async () => {
    if (!user) return;
    
    setLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/kyc/profile-check', {
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Profile check failed: ${response.status}`);
      }

      const data: ProfileCheck = await response.json();
      setProfileCheck(data);

      if (user.user_metadata) {
        setProfileData({
          first_name: user.user_metadata.first_name || '',
          last_name: user.user_metadata.last_name || '',
          email: user.email || ''
        });
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Profile check failed';
      console.error('Profile check error:', err);
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async () => {
    if (!user) return;
    
    setLoading(true);
    setError('');

    try {
      const requiredFields = ['first_name', 'last_name', 'email'];
      const missingFields = requiredFields.filter(field => 
        !profileData[field as keyof typeof profileData]?.trim()
      );

      if (missingFields.length > 0) {
        throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(profileData.email)) {
        throw new Error('Invalid email format');
      }

      const response = await fetch('/api/kyc/update-profile', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(profileData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Profile update failed: ${response.status}`);
      }

      await checkProfileCompleteness();

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Profile update failed';
      console.error('Profile update error:', err);
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // HYBRID APPROACH: Check if BVN is needed before starting verification
const handleStartKyc = async () => {
  if (!user || !profileCheck?.can_start_kyc) return;

  // Detect country if not set
  let country = userProfile?.country_code;
  
  if (!country) {
    try {
      const response = await fetch('/api/kyc/detect-country');
      const data = await response.json();
      if (data.success) {
        country = data.country_code;
      }
    } catch (error) {
      console.error('Country detection failed:', error);
      country = 'US'; // Fallback
    }
  }

  // Check if country-specific data needed
  const needsIDData = ['NG', 'KE', 'GH'].includes(country);
  
  if (needsIDData) {
    // Check if data already collected
    const hasRequiredData = country === 'NG' 
      ? userProfile?.bvn && userProfile?.date_of_birth && userProfile?.gender
      : userProfile?.id_number && userProfile?.date_of_birth;
    
    if (!hasRequiredData) {
      setShowBVNModal(true); // Will now show UniversalIDModal
      return;
    }
  }

  // Proceed to verification
  await initiateVerification();
};

  const handleBVNComplete = async (bvnData: any) => {
    setShowBVNModal(false);
    
    // BVN saved successfully, now start verification
    await initiateVerification();
  };

  const initiateVerification = async () => {
    if (!user) return;

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/kyc/start-verification', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.error || errorData.detail || `KYC start failed: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        // Check which provider was used
        if (result.provider === 'regfyl') {
          // Regfyl doesn't have interactive flow - redirect to pending page
          window.location.href = `/kyc-regfyl-pending?user_id=${userProfile?.id}`;
        } else {
          // ComplyCube has interactive flow
          setShowComplyCube(true);
          setProfileCheck(prev => prev ? { ...prev, kyc_status: 'in_progress' } : null);
        }
      } else {
        throw new Error(result.message || 'Failed to start KYC verification');
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'KYC initialization failed';
      console.error('KYC start error:', err);
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleComplyCubeComplete = (status: string) => {
    setShowComplyCube(false);
    setProfileCheck(prev => prev ? { ...prev, kyc_status: status } : null);
    
    if (status === 'completed') {
      onComplete?.();
    }
  };

  const handleComplyCubeError = (errorMessage: string) => {
    console.error('ComplyCube verification error:', errorMessage);
    setError(errorMessage);
    setShowComplyCube(false);
    onError?.(errorMessage);
  };

  if (loading && !profileCheck) {
    return (
      <Card className="p-6">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p>Checking profile status...</p>
        </div>
      </Card>
    );
  }

  if (error && !profileCheck) {
    return (
      <Card className="p-6 border-red-200 bg-red-50">
        <h3 className="text-lg font-semibold text-red-800 mb-2">Profile Check Failed</h3>
        <p className="text-red-600 mb-4">{error}</p>
        <Button onClick={checkProfileCompleteness} disabled={loading}>
          {loading ? 'Retrying...' : 'Retry Profile Check'}
        </Button>
      </Card>
    );
  }

  // Show BVN Collection Modal
 {showBVNModal && user && (
  <UniversalIDModal
    countryCode={userProfile?.country_code || 'US'}
    countryName={userProfile?.country || 'United States'}
    onComplete={handleBVNComplete}
    onCancel={() => setShowBVNModal(false)}
    userEmail={user.email || ''}
  />
)}

  // Show ComplyCube verification
  if (showComplyCube && profileCheck?.can_start_kyc) {
    return (
      <ComplyCubeVerification
        onComplete={handleComplyCubeComplete}
        onError={handleComplyCubeError}
      />
    );
  }

  // Show KYC status if already in progress or completed
  if (profileCheck?.kyc_status === 'in_progress' || profileCheck?.kyc_status === 'pending') {
    return (
      <Card className="p-6 border-yellow-200 bg-yellow-50">
        <h3 className="text-lg font-semibold text-yellow-800 mb-2">Verification In Progress</h3>
        <p className="text-yellow-700 mb-4">
          Your identity verification is currently being processed. This may take up to 24 hours.
        </p>
        <Button 
          onClick={() => setShowComplyCube(true)} 
          variant="outline"
          className="border-yellow-300 text-yellow-800 hover:bg-yellow-100"
        >
          Continue Verification
        </Button>
      </Card>
    );
  }

  if (profileCheck?.kyc_status === 'completed' || profileCheck?.kyc_status === 'verified') {
    return (
      <Card className="p-6 border-green-200 bg-green-50">
        <h3 className="text-lg font-semibold text-green-800 mb-2">✅ Verification Complete</h3>
        <p className="text-green-700">
          Your identity has been successfully verified. You can now access all platform features.
        </p>
      </Card>
    );
  }

  if (profileCheck?.kyc_status === 'rejected') {
    return (
      <Card className="p-6 border-red-200 bg-red-50">
        <h3 className="text-lg font-semibold text-red-800 mb-2">Verification Rejected</h3>
        <p className="text-red-600 mb-4">
          Your identity verification was not successful. Please contact support for assistance.
        </p>
        <Button 
          onClick={handleStartKyc} 
          disabled={loading}
          className="bg-red-600 hover:bg-red-700"
        >
          {loading ? 'Processing...' : 'Retry Verification'}
        </Button>
      </Card>
    );
  }

  // Show profile completion form if profile is incomplete
  if (!profileCheck?.profile_complete) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Complete Your Profile</h3>
        <p className="text-gray-600 mb-6">
          Please complete your profile information before starting identity verification.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              First Name *
            </label>
            <input
              type="text"
              value={profileData.first_name}
              onChange={(e) => setProfileData(prev => ({ ...prev, first_name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your first name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Last Name *
            </label>
            <input
              type="text"
              value={profileData.last_name}
              onChange={(e) => setProfileData(prev => ({ ...prev, last_name: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your last name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email *
            </label>
            <input
              type="email"
              value={profileData.email}
              onChange={(e) => setProfileData(prev => ({ ...prev, email: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your email"
            />
          </div>
        </div>

        <Button 
          onClick={handleUpdateProfile} 
          disabled={loading}
          className="w-full mt-6"
        >
          {loading ? 'Updating...' : 'Save Profile & Continue'}
        </Button>
      </Card>
    );
  }

  // Show ready to start KYC
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Start Identity Verification</h3>
      <p className="text-gray-600 mb-6">
        Your profile is complete. Click below to start the identity verification process.
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      {isNigerianUser && !userProfile?.bvn && (
        <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-md flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <p className="text-blue-700 text-sm">
            Nigerian users: You'll need to provide your BVN, date of birth, and gender for verification.
          </p>
        </div>
      )}

      <Button 
        onClick={handleStartKyc} 
        disabled={loading}
        className="w-full"
      >
        {loading ? 'Starting Verification...' : 'Start Verification'}
      </Button>
    </Card>
  );
};

export default KycVerification;