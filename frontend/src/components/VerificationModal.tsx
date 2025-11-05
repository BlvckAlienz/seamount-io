import React from 'react';
import { X, Shield, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button.tsx';
import { useAuth } from '../contexts/AuthContext';

interface VerificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  actionDescription?: string;
}

const VerificationModal: React.FC<VerificationModalProps> = ({ 
  isOpen, 
  onClose, 
  actionDescription = "perform this action" 
}) => {
  const { user, skipVerification } = useAuth();

  if (!isOpen) return null;

  const handleVerifyNow = () => {
    window.location.href = '/onboarding';
  };

  const handleSkip = async () => {
    try {
      await skipVerification();
      onClose();
    } catch (error) {
      console.error('Failed to skip verification:', error);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl max-w-md w-full p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
        >
          <X className="h-5 w-5" />
        </button>
        
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="h-8 w-8 text-blue-600" />
          </div>
          <h3 className="text-xl font-bold text-gray-900 mb-2">Verification Required</h3>
          <p className="text-gray-600">
            To {actionDescription}, you need to complete identity verification.
          </p>
        </div>
        
        <div className="bg-blue-50 rounded-lg p-4 mb-6">
          <h4 className="font-semibold text-blue-900 mb-2">Benefits of verification:</h4>
          <ul className="text-blue-800 text-sm space-y-1">
            <li>• Send and receive USDS stablecoins</li>
            <li>• Access to cross-border payments</li>
            <li>• Higher transaction limits</li>
            <li>• Enhanced security features</li>
          </ul>
        </div>
        
        <div className="flex flex-col space-y-3">
          <Button
            onClick={handleVerifyNow}
            className="bg-blue-600 hover:bg-blue-700 text-white"
           
          >
            Verify Now
          </Button>
          <Button
            onClick={handleSkip}
            variant="outline"
          >
            Maybe Later
          </Button>
        </div>
        
        {user?.kyc_status === 'pending' && (
          <p className="text-sm text-gray-500 mt-4 text-center">
            Your verification is already in progress. Check your email for updates.
          </p>
        )}
      </div>
    </div>
  );
};

export default VerificationModal;