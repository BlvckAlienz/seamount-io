// File Location: frontend/src/components/onboarding/ComplyCubeVerification.tsx
import React, { useEffect, useState, useRef } from 'react';
import { apiClient } from '../../config/api';
import { COMPLYCUBE_CONFIG } from '../../config/env';
import Button from '../ui/Button';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';

declare global {
  interface Window {
    ComplyCube?: any;
  }
}

const ComplyCubeVerification: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [verificationStarted, setVerificationStarted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { refreshKycStatus } = useAuth();
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
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

  const startVerification = async () => {
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
            }
          });
          
          // Mount to the specific element
          session.mount('#complycube-mount');
          setVerificationStarted(true);
        } else {
          console.error('ComplyCube SDK not loaded');
          setError('Verification service not available. Please refresh and try again.');
        }
      }, 100);
    } catch (error: any) {
      console.error('Failed to start verification', error);
      setError(error.response?.data?.detail || 'Failed to start verification');
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

  return (
    <div>
      <h2>Identity Verification</h2>
      <p>Complete verification to unlock all features including sending and receiving USDS.</p>
      
      {error && (
        <div style={{ color: 'red', marginBottom: '1rem' }}>
          {error}
          <button onClick={() => setError(null)} style={{ marginLeft: '1rem' }}>
            Dismiss
          </button>
        </div>
      )}
      
      {!verificationStarted ? (
        <div>
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
            style={{ marginLeft: '1rem' }}
          >
            I'll do this later
          </Button>
        </div>
      ) : (
        <div id="complycube-mount" ref={mountRef}></div>
      )}
    </div>
  );
};

export default ComplyCubeVerification;