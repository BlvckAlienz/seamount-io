import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import Button from '../Button';
import Card from '../Card';
import { apiClient } from '../../config/api';

interface KycVerificationProps {
  onComplete?: () => void;
  onCancel?: () => void;
}

const KycVerification: React.FC<KycVerificationProps> = ({ onComplete, onCancel }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verificationStatus, setVerificationStatus] = useState<'pending' | 'processing' | 'completed' | 'failed'>('pending');
  const { user, refreshKycStatus } = useAuth();

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

  const startVerification = async () => {
    try {
      setLoading(true);
      setError(null);

      // Get token from backend
      const response = await apiClient.post('/api/kyc/token');
      const { token } = response.data;

      // Mount ComplyCube
      (window as any).ComplyCube.mount({
        token: token,
        onComplete: (data: any) => {
          console.log('Verification completed:', data);
          setVerificationStatus('completed');
          // Refresh KYC status
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
        }
      });

    } catch (error: any) {
      console.error('Failed to start verification:', error);
      setError(error.response?.data?.detail || 'Failed to start verification');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!loading) {
      startVerification();
    }
  }, [loading]);

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
          <Button onClick={startVerification}>Try Again</Button>
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
      <div id="complycube-mount"></div>
    </Card>
  );
};

export default KycVerification;