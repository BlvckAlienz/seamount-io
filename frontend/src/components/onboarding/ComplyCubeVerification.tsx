// File Location: frontend/src/components/onboarding/ComplyCubeVerification.tsx
import React, { useEffect, useState, useRef } from 'react';
import { apiClient } from '../../config/api';
import { COMPLYCUBE_CONFIG } from '../../config/env';
import Button from '../ui/Button';
import { useAuth } from '../../contexts/AuthContext';
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
  const { refreshKycStatus, user } = useAuth();
  const [complyCubeSession, setComplyCubeSession] = useState<any>(null);

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
      const response = await apiClient.get('/api/kyc/profile-check');
      const data: ProfileCheckResponse = response.data;
      
      setProfileComplete(data.profile_complete);
      setMissingFields(data.missing_fields);
      
      // Pre-fill email if available from auth context
      if (user?.email && !profileData.email) {
        setProfileData(prev => ({ ...prev, email: user.email }));
      }
      
      if (!data.profile_complete) {
        setError('Please complete your profile before starting verification');
      }
    } catch (error: any) {
      console.error('Failed to check profile completeness:', error);
      setError('Failed to check profile status');
    }
  };

  const updateProfile = async () => {
    try {
      setLoading(true);
      await apiClient.post('/api/kyc/update-profile', profileData);
      await checkProfileCompleteness();
      setError(null);
    } catch (error: any) {
      setError('Failed to update profile: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const startVerification = async () => {
    // Double-check profile completeness before starting
    try {
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
    setError(null);
    try {
      // Get verification token from backend
      const response = await apiClient.post('/api/kyc/start-verification');
      const { token, applicantId } = response.data;

      // Initialize ComplyCube with a slight delay to ensure mount point is ready
      setTimeout(() => {
        if (window.ComplyCube) {
          const session = window.ComplyCube.mount({
            token: token,
            onComplete: (data: any) => {
              console.log('Verification complete', data);
              setVerificationStarted(false);
              refreshKycStatus();
            },
            onError: (error: any) => {
              console.error('Verification error', error);
              setVerificationStarted(false);
              setError('Verification failed. Please try again.');
            },
            onCancel: () => {
              console.log('Verification cancelled by user');
              setVerificationStarted(false);
            },
            onModalClose: () => {
              console.log('Modal closed by user');
              setVerificationStarted(false);
            },
            onExit: (reason: any) => {
              console.log('User exited verification:', reason);
              setVerificationStarted(false);
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
      
      // Check if it's a profile completeness error
      if (errorMsg.includes('first name') || errorMsg.includes('last name')) {
        // Re-check profile completeness
        await checkProfileCompleteness();
      }
    } finally {
      setLoading(false);
    }
  };

  const skipVerification = async () => {
    try {
      setLoading(true);
      // Call backend API to mark KYC as skipped
      await apiClient.post('/api/kyc/skip');
      // Refresh user status
      await refreshKycStatus();
    } catch (error: any) {
      console.error('Failed to skip verification:', error);
      setError('Failed to skip verification. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const exitVerification = () => {
    setVerificationStarted(false);
    if (complyCubeSession) {
      complyCubeSession.unmount();
    }
  };

  // Show profile completion form if profile is incomplete
  if (!profileComplete) {
    return (
      <div className="profile-completion-overlay">
        <div className="profile-completion-modal">
          <h2>Complete Your Profile</h2>
          <p>Please complete your profile information before starting verification:</p>
          
          <div className="profile-form">
            {missingFields.includes('first_name') && (
              <div className="form-group">
                <label>First Name</label>
                <input
                  type="text"
                  value={profileData.first_name}
                  onChange={(e) => setProfileData({...profileData, first_name: e.target.value})}
                  placeholder="Enter your first name"
                  required
                />
              </div>
            )}
            
            {missingFields.includes('last_name') && (
              <div className="form-group">
                <label>Last Name</label>
                <input
                  type="text"
                  value={profileData.last_name}
                  onChange={(e) => setProfileData({...profileData, last_name: e.target.value})}
                  placeholder="Enter your last name"
                  required
                />
              </div>
            )}
            
            {missingFields.includes('email') && (
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={profileData.email}
                  onChange={(e) => setProfileData({...profileData, email: e.target.value})}
                  placeholder="Enter your email"
                  required
                />
              </div>
            )}
          </div>
          
          {error && (
            <div className="error-message">
              {error}
              <button onClick={() => setError(null)} className="dismiss-btn">
                Dismiss
              </button>
            </div>
          )}
          
          <div className="button-group">
            <Button onClick={updateProfile} loading={loading}>
              Update Profile
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="verification-container">
      <h2>Identity Verification</h2>
      <p>Complete verification to unlock all features including sending and receiving USDS.</p>
      
      {error && (
        <div className="error-message">
          {error}
          <button onClick={() => setError(null)} className="dismiss-btn">
            Dismiss
          </button>
        </div>
      )}
      
      {!verificationStarted ? (
        <div className="button-group">
          <Button 
            onClick={startVerification} 
            loading={loading}
            disabled={!COMPLYCUBE_CONFIG.API_KEY}
          >
            {COMPLYCUBE_CONFIG.API_KEY ? 'Start Verification' : 'KYC Not Configured'}
          </Button>
          <Button 
            onClick={skipVerification} 
            variant="outline"
            className="skip-btn"
          >
            I'll do this later
          </Button>
        </div>
      ) : (
        <>
          <div id="complycube-mount"></div>
          <div className="exit-verification">
            <button onClick={exitVerification} className="exit-btn">
              Exit Verification
            </button>
          </div>
        </>
      )}
    </div>
  );
};

export default ComplyCubeVerification;