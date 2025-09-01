import React, { useState, useEffect, useRef } from 'react';
import { Shield, CheckCircle, AlertCircle, X } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import Button from '../ui/Button';
import Card from '../Card';
import { apiClient } from '../../config/api';
import { supabase } from '../../lib/supabase';
import './KycVerification.css';

interface KycVerificationProps {
  onComplete?: () => void;
  onCancel?: () => void;
}

const KycVerification: React.FC<KycVerificationProps> = ({ onComplete, onCancel }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verificationStatus, setVerificationStatus] = useState<'pending' | 'processing' | 'completed' | 'failed'>('pending');
  const [sdkToken, setSdkToken] = useState<string | null>(null);
  const [sdkLoaded, setSdkLoaded] = useState(false);
  const mountRef = useRef<HTMLDivElement>(null);
  const { user, refreshKycStatus } = useAuth();

  // Ensure mount point exists
  useEffect(() => {
    if (!document.getElementById('complycube-mount')) {
      const mountPoint = document.createElement('div');
      mountPoint.id = 'complycube-mount';
      mountPoint.style.width = '100%';
      mountPoint.style.minHeight = '500px';
      document.body.appendChild(mountPoint);
    }
  }, []);

  // Load ComplyCube script
  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://assets.complycube.com/web-sdk/v1/complycube.min.js';
    script.async = true;
    script.onload = () => {
      // Now load the CSS
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://assets.complycube.com/web-sdk/v1/style.css';
      document.head.appendChild(link);
      setSdkLoaded(true);
      setLoading(false);
    };
    script.onerror = () => {
      setError('Failed to load verification service');
      setLoading(false);
    };
    document.head.appendChild(script);

    return () => {
      // Clean up
      document.head.removeChild(script);
    };
  }, []);

  // Get verification token
  useEffect(() => {
    const fetchToken = async () => {
      try {
        const response = await apiClient.post('/api/kyc/start-verification');
        setSdkToken(response.data.token);
      } catch (error: any) {
        console.error('Failed to get verification token:', error);
        setError(error.response?.data?.detail || 'Failed to start verification');
        setLoading(false);
      }
    };

    if (sdkLoaded && !sdkToken) {
      fetchToken();
    }
  }, [sdkLoaded, sdkToken]);

  // Initialize SDK when token is available
  useEffect(() => {
    if (sdkToken && mountRef.current) {
      const mountElement = document.getElementById('complycube-mount');
      
      if (!mountElement) {
        console.error('Mount element not found');
        setError('Verification UI failed to load. Please try again.');
        return;
      }

      // Initialize ComplyCube with a slight delay to ensure mount point is ready
      setTimeout(() => {
        try {
          const session = (window as any).ComplyCube.mount({
            token: sdkToken,
            onComplete: (data: any) => {
              console.log('Verification completed:', data);
              setVerificationStatus('completed');
              refreshKycStatus();
              if (onComplete) {
                setTimeout(() => {
                  onComplete();
                }, 3000);
              }
            },
            onError: (error: any) => {
              console.error('Verification error:', error);
              setError('Verification failed. Please try again.');
              setVerificationStatus('failed');
            },
            onCancel: () => {
              console.log('Verification cancelled by user');
              if (onCancel) onCancel();
            }
          });
          
          // Mount to the specific element
          session.mount('#complycube-mount');
        } catch (sdkError) {
          console.error('SDK initialization error:', sdkError);
          setError('Failed to initialize verification. Please refresh and try again.');
        }
      }, 100);
    }
  }, [sdkToken, onComplete, onCancel, refreshKycStatus]);

  // Add skip verification function
  const skipVerification = async () => {
    try {
      setLoading(true);
      // Call backend API to mark KYC as skipped
      await apiClient.post('/api/kyc/skip');
      // Refresh user status
      await refreshKycStatus();
      if (onCancel) onCancel();
    } catch (error: any) {
      console.error('Failed to skip verification:', error);
      setError('Failed to skip verification. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <div className="text-center py-8">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full border-4 border-gray-700"></div>
            <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 animate-spin"></div>
          </div>
          <h3 className="text-xl font-bold text-white mb-2">Loading Verification</h3>
          <p className="text-gray-300">Please wait...</p>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <div className="text-center py-8">
          <AlertCircle className="h-16 w-16 text-red-500 mx-auto mb-6" />
          <h3 className="text-xl font-bold text-white mb-2">Verification Failed</h3>
          <p className="text-red-400 mb-4">{error}</p>
          <div className="flex space-x-4 justify-center">
            <Button onClick={() => window.location.reload()}>Try Again</Button>
            <Button onClick={skipVerification} variant="outline">
              Skip Verification
            </Button>
          </div>
        </div>
      </Card>
    );
  }

  if (verificationStatus === 'completed') {
    return (
      <Card>
        <div className="text-center py-8">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-6" />
          <h3 className="text-xl font-bold text-white mb-2">Verification Successful</h3>
          <p className="text-gray-300 mb-6">
            Your identity has been verified successfully. You now have full access to all features.
          </p>
          <Button
            onClick={onComplete}
            className="bg-gradient-to-r from-green-600 to-teal-600"
          >
            Continue to Platform
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <div className="flex items-center space-x-3 mb-6">
        <Shield className="h-6 w-6 text-blue-500" />
        <h2 className="text-xl font-bold text-white">Identity Verification</h2>
      </div>
      <div className="mb-4">
        <p className="text-gray-300">
          Complete identity verification to access all platform features. This process usually takes 2-3 minutes.
        </p>
      </div>
      
      {/* Mount point for ComplyCube SDK - Always rendered but hidden until token is available */}
      <div ref={mountRef} className="complycube-container">
        <div 
          id="complycube-mount" 
          style={{ 
            minHeight: '500px', 
            width: '100%',
            display: sdkToken ? 'block' : 'none'
          }}
        ></div>
        
        {!sdkToken && (
          <div className="text-center py-8">
            <div className="relative w-16 h-16 mx-auto mb-6">
              <div className="absolute inset-0 rounded-full border-4 border-gray-700"></div>
              <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 animate-spin"></div>
            </div>
            <p className="text-gray-300">Preparing verification...</p>
          </div>
        )}
      </div>
      
      <div className="mt-4 text-center">
        <Button onClick={skipVerification} variant="outline" size="sm">
          Skip for Now
        </Button>
        <p className="text-xs text-gray-400 mt-2">
          You can complete verification later from your settings
        </p>
      </div>
    </Card>
  );
};

export default KycVerification;