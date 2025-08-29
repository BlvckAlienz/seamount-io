import React, { useEffect, useState } from 'react';
import { apiClient } from '../../config/api';
import { COMPLYCUBE_CONFIG } from '../../config/env';
import Button from '../ui/Button';

declare global {
  interface Window {
    ComplyCube?: any;
  }
}

const ComplyCubeVerification: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [verificationStarted, setVerificationStarted] = useState(false);

  useEffect(() => {
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
      script.onerror = () => console.error('Failed to load ComplyCube SDK');
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
    try {
      // Get verification token from backend
      const response = await apiClient.post('/api/kyc/start-verification');
      const { token, applicantId } = response.data;

      // Initialize ComplyCube
      if (window.ComplyCube) {
        window.ComplyCube.mount({
          token: token,
          onComplete: (data: any) => {
            console.log('Verification complete', data);
            setVerificationStarted(false);
            // You might want to refresh the user's KYC status here
          },
          onError: (error: any) => {
            console.error('Verification error', error);
            setVerificationStarted(false);
          }
        });
        setVerificationStarted(true);
      } else {
        console.error('ComplyCube SDK not loaded');
      }
    } catch (error) {
      console.error('Failed to start verification', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Identity Verification</h2>
      <p>Complete verification to unlock all features including sending and receiving USDS.</p>
      
      {!verificationStarted ? (
        <Button 
          onClick={startVerification} 
          loading={loading}
          disabled={!COMPLYCUBE_CONFIG.API_KEY}
        >
          {COMPLYCUBE_CONFIG.API_KEY ? 'Start Verification' : 'KYC Not Configured'}
        </Button>
      ) : (
        <div id="complycube-mount"></div>
      )}
    </div>
  );
};

export default ComplyCubeVerification;