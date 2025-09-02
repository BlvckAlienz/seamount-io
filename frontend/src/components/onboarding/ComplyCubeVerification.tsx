// File Location: frontend/src/components/onboarding/ComplyCubeVerification.tsx
// CRITICAL FIX: Proper exit handling and error recovery

import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../config/api';
import { COMPLYCUBE_CONFIG } from '../../config/env';
import Button from '../ui/Button';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';
import './ComplyCubeVerification.css';

declare global {
  interface Window {
    ComplyCube?: any;
  }
}

interface ProfileCheckResponse {
  profile_complete: boolean;
  missing_fields: string[];
  errors: string[];
  can_start_kyc: boolean;
  kyc_status: string;
}

const ComplyCubeVerification: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [verificationStarted, setVerificationStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profileComplete, setProfileComplete] = useState(false);
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [profileData, setProfileData] = useState({
    first_name: '',
    last_name: '',
    email: ''
  });
  const { refreshKycStatus, user, skipVerification } = useAuth();
  const [complyCubeSession, setComplyCubeSession] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Check profile completeness on component mount
    checkProfileCompleteness();
    
    // Ensure mount point exists
    if (!document.getElementById('complycube-mount')) {
      const mountPoint = document.createElement('div');
      mountPoint.id = 'complycube-mount';
      mountPoint.style.width = '100%';
      mountPoint.style.minHeight = '400px';
      document.body.appendChild(mountPoint);
    }

    // Load ComplyCube SDK dynamically
    const loadComplyCubeSDK = async () => {
      if (!COMPLYCUBE_CONFIG.API_KEY) {
        console.error('ComplyCube API key not configured');
        return;
      }

      // Load CSS
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = COMPLYCUBE_CONFIG.SDK_STYLES;
      document.head.appendChild(link);

      // Load JS
      const script = document.createElement('script');
      script.src = COMPLYCUBE_CONFIG.SDK_SCRIPT;
      script.async = true;
      script.onload = () => console.log('ComplyCube SDK loaded');
      script.onerror = () => {
        console.error('Failed to load ComplyCube SDK');
        setError('Failed to load verification service');
      };
      document.head.appendChild(script);

      return () => {
        document.head.removeChild(link);
        document.head.removeChild(script);
      };
    };

    loadComplyCubeSDK();
  }, []);

  const checkProfileCompleteness = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/kyc/profile-check');
      const data: ProfileCheckResponse = response.data;
      
      setProfileComplete(data.profile_complete);
      setMissingFields(data.missing_fields);
      
      // Pre-fill email if available from auth context
      if (user?.email && !profileData.email) {
        setProfileData(prev => ({ ...prev, email: user.email }));
      }
      
      if (!data.profile_complete) {
        setError(`Please complete your profile first. Missing: ${data.missing_fields.join(', ')}`);
      }
    } catch (error: any) {
      console.error('Failed to check profile completeness:', error);
      setError('Failed to check profile status. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const updateProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      
      await apiClient.post('/api/kyc/update-profile', profileData);
      await checkProfileCompleteness();
      
      toast.success('Profile updated successfully!');
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Failed to update profile. Please try again.';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const startVerification = async () => {
    // Double-check profile completeness before starting
    try {
      setError(null);
      const profileCheck = await apiClient.get('/api/kyc/profile-check');
      if (!profileCheck.data.profile_complete) {
        setError('Please complete your profile first');
        setProfileComplete(false);
        setMissingFields(profileCheck.data.missing_fields);
        return;
      }
    } catch (error) {
      setError('Unable to verify profile status. Please try again.');
      return;
    }

    setLoading(true);
    try {
      // Get verification token from backend
      const response = await apiClient.post('/api/kyc/start-verification');
      const { token, applicantId } = response.data;

      // Initialize ComplyCube with enhanced error handling
      setTimeout(() => {
        if (window.ComplyCube) {
          const session = window.ComplyCube.mount({
            token: token,
            onComplete: (data: any) => {
              console.log('Verification complete', data);
              setVerificationStarted(false);
              toast.success('Verification completed successfully!');
              refreshKycStatus();
              // Navigate to dashboard after successful verification
              setTimeout(() => navigate('/dashboard'), 1000);
            },
            onError: (error: any) => {
              console.error('Verification error', error);
              setVerificationStarted(false);
              setError('Verification failed. You can skip for now and try again later.');
              toast.error('Verification failed. Please try again or skip for now.');
            },
            onCancel: () => {
              console.log('Verification cancelled by user');
              handleVerificationExit('User cancelled verification');
            },
            onModalClose: () => {
              console.log('Modal closed by user');
              handleVerificationExit('Verification modal closed');
            },
            onExit: (reason: any) => {
              console.log('User exited verification:', reason);
              handleVerificationExit(`Verification exited: ${reason}`);
            }
          });
          
          // Mount to the specific element
          session.mount('#complycube-mount');
          setVerificationStarted(true);
          setComplyCubeSession(session);
        } else {
          console.error('ComplyCube SDK not loaded');
          setError('Verification service not available. Please refresh and try again.');
        }
      }, 100);
    } catch (error: any) {
      console.error('Failed to start verification', error);
      const errorMsg = error.response?.data?.detail || 'Failed to start verification';
      setError(errorMsg);
      toast.error(errorMsg);
      
      // Check if it's a profile completeness error
      if (errorMsg.includes('first_name') || errorMsg.includes('last_name') || errorMsg.includes('Missing fields')) {
        // Re-check profile completeness
        await checkProfileCompleteness();
      }
    } finally {
      setLoading(false);
    }
  };

  // ENHANCED: Proper exit handling with user feedback
  const handleVerificationExit = (reason: string) => {
    console.log('Handling verification exit:', reason);
    setVerificationStarted(false);
    
    if (complyCubeSession) {
      try {
        complyCubeSession.unmount();
      } catch (error) {
        console.error('Error unmounting ComplyCube session:', error);
      }
      setComplyCubeSession(null);
    }
    
    // Show user-friendly message and options
    toast.info('Verification paused. You can continue anytime or skip for now.');
    setError(null); // Clear any existing errors
  };

  const handleSkipVerification = async () => {
    try {
      if (skipVerification) {
        await skipVerification();
        toast.success('Verification skipped. You can complete it later in settings.');
        navigate('/dashboard');
      }
    } catch (error: any) {
      console.error('Failed to skip verification:', error);
      toast.error('Failed to skip verification. Please try again.');
    }
  };

  const handleGoToDashboard = () => {
    navigate('/dashboard');
  };

  // Profile completion form
  if (!profileComplete && missingFields.length > 0) {
    return (
      <div className="complycube-verification-container">
        <div className="verification-header">
          <h2>Complete Your Profile</h2>
          <p>Please provide the missing information to start verification:</p>
        </div>

        <div className="profile-form">
          {missingFields.includes('first_name') && (
            <div className="form-group">
              <label htmlFor="first_name">First Name *</label>
              <input
                id="first_name"
                type="text"
                value={profileData.first_name}
                onChange={(e) => setProfileData(prev => ({ ...prev, first_name: e.target.value }))}
                placeholder="Enter your first name"
                required
              />
            </div>
          )}

          {missingFields.includes('last_name') && (
            <div className="form-group">
              <label htmlFor="last_name">Last Name *</label>
              <input
                id="last_name"
                type="text"
                value={profileData.last_name}
                onChange={(e) => setProfileData(prev => ({ ...prev, last_name: e.target.value }))}
                placeholder="Enter your last name"
                required
              />
            </div>
          )}

          {missingFields.includes('email') && (
            <div className="form-group">
              <label htmlFor="email">Email *</label>
              <input
                id="email"
                type="email"
                value={profileData.email}
                onChange={(e) => setProfileData(prev => ({ ...prev, email: e.target.value }))}
                placeholder="Enter your email"
                required
              />
            </div>
          )}

          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <div className="form-actions">
            <Button 
              onClick={updateProfile}
              disabled={loading}
              className="primary"
            >
              {loading ? 'Updating...' : 'Update Profile'}
            </Button>
            
            <Button 
              onClick={handleGoToDashboard}
              variant="outline"
              className="secondary"
            >
              Go to Dashboard
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="complycube-verification-container">
      <div className="verification-header">
        <h2>Identity Verification</h2>
        <p>Complete your identity verification to unlock all platform features.</p>
      </div>

      {error && (
        <div className="error-message">
          {error}
          {error.includes('skip') && (
            <div className="error-actions">
              <Button 
                onClick={handleSkipVerification}
                variant="outline"
                className="skip-button"
              >
                Skip for Now
              </Button>
            </div>
          )}
        </div>
      )}

      {!verificationStarted ? (
        <div className="verification-actions">
          <Button 
            onClick={startVerification}
            disabled={loading || !profileComplete}
            className="start-verification-btn"
          >
            {loading ? 'Starting...' : 'Start Verification'}
          </Button>

          <div className="skip-options">
            <p>You can also:</p>
            <Button 
              onClick={handleSkipVerification}
              variant="outline"
              className="skip-button"
            >
              Skip for Now
            </Button>
            <Button 
              onClick={handleGoToDashboard}
              variant="text"
              className="dashboard-button"
            >
              Go to Dashboard
            </Button>
          </div>
        </div>
      ) : (
        <div className="verification-in-progress">
          <p>Verification in progress...</p>
          <div id="complycube-mount"></div>
          
          <div className="progress-actions">
            <Button 
              onClick={() => handleVerificationExit('User manually exited')}
              variant="outline"
              className="exit-button"
            >
              Exit Verification
            </Button>
          </div>
        </div>
      )}

      <div className="verification-info">
        <p>✅ Secure and compliant identity verification</p>
        <p>🚀 Get access to advanced trading features</p>
        <p>💰 Increase your transaction limits</p>
      </div>
    </div>
  );
};

export default ComplyCubeVerification;