# File Location: frontend/src/components/onboarding/KycVerification.tsx
# CRITICAL FIX: Enhanced error handling and profile validation

import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/AuthContext';
import ComplyCubeVerification from './ComplyCubeVerification';
import { Button } from '../ui/Button';
import { Card } from '../ui/Card';

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
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [profileCheck, setProfileCheck] = useState<ProfileCheck | null>(null);
  const [showComplyCube, setShowComplyCube] = useState(false);
  const [error, setError] = useState<string>('');
  const [profileData, setProfileData] = useState({
    first_name: '',
    last_name: '',
    email: ''
  });

  // CRITICAL: Check profile completeness on component mount
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

      // Pre-populate form with existing data if available
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
      // Validate required fields
      const requiredFields = ['first_name', 'last_name', 'email'];
      const missingFields = requiredFields.filter(field => 
        !profileData[field as keyof typeof profileData]?.trim()
      );

      if (missingFields.length > 0) {
        throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
      }

      // Validate email format
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

      const result = await response.json();
      console.log('Profile updated:', result);

      // Re-check profile completeness
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

  const handleStartKyc = async () => {
    if (!user || !profileCheck?.can_start_kyc) return;

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
      console.log('KYC started:', result);
      
      if (result.success) {
        setShowComplyCube(true);
        // Update profile check to reflect new status
        setProfileCheck(prev => prev ? { ...prev, kyc_status: 'in_progress' } : null);
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
    console.log('ComplyCube verification completed:', status);
    setShowComplyCube(false);
    
    // Update local status
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

  // Show ComplyCube verification if KYC is ready
  if (showComplyCube && profileCheck?.can_start_kyc) {
    return (
      <ComplyCubeVerification
        onComplete={handleComplyCubeComplete}
        onError={handleComplyCubeError}
      />
    );
  }

  // Show KYC status if already in progress or completed
  if (profileCheck?.kyc_status === 'in_progress') {
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

  if (profileCheck?.kyc_status === 'completed') {
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
              Email Address *
            </label>
            <input
              type="email"
              value={profileData.email}
              onChange={(e) => setProfileData(prev => ({ ...prev, email: e.target.value }))}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter your email address"
            />
          </div>

          <Button
            onClick={handleUpdateProfile}
            disabled={loading}
            className="w-full mt-6"
          >
            {loading ? 'Updating Profile...' : 'Update Profile'}
          </Button>
        </div>

        {profileCheck?.missing_fields.length > 0 && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <p className="text-yellow-800 text-sm">
              <strong>Missing fields:</strong> {profileCheck.missing_fields.join(', ')}
            </p>
          </div>
        )}
      </Card>
    );
  }

  // Show KYC start button if profile is complete
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Identity Verification</h3>
      <p className="text-gray-600 mb-6">
        Complete identity verification to unlock all platform features and increase your transaction limits.
      </p>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}

      <div className="space-y-4">
        <div className="p-4 bg-green-50 border border-green-200 rounded-md">
          <h4 className="font-medium text-green-800 mb-2">✅ Profile Complete</h4>
          <p className="text-green-700 text-sm">
            Your profile information is complete and ready for verification.
          </p>
        </div>

        <Button
          onClick={handleStartKyc}
          disabled={loading || !profileCheck?.can_start_kyc}
          className="w-full"
        >
          {loading ? 'Starting Verification...' : 'Start Identity Verification'}
        </Button>
      </div>
    </Card>
  );
};