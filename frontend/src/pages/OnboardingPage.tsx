import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../config/api';
import toast from 'react-hot-toast';

interface StepProps {
  onNext: (data?: any) => void;
  onPrev: () => void;
  stepData: any;
}

interface OnboardingStepConfig {
  id: number;
  title: string;
  description: string;
  component: React.FC<StepProps>;
}

// Step 1: Welcome
const WelcomeStep: React.FC<StepProps> = ({ onNext }) => {
  return (
    <div className="text-center">
      <div className="mb-8">
        <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v.01" />
          </svg>
        </div>
        <h3 className="text-xl font-semibold mb-2">
          Welcome to the Future of Cross-Border Payments
        </h3>
        <p className="text-gray-600">
          Send USDS stablecoins globally with minimal fees and instant settlement.
        </p>
      </div>
      <div className="bg-blue-50 rounded-lg p-6 mb-8 text-left">
        <h4 className="font-semibold text-blue-900 mb-3">What you'll get:</h4>
        <ul className="text-blue-800 text-sm space-y-2">
          {["Instant global transfers with USDS stablecoin", "Low remittance fees (2.6% per transaction)", "24/7/365 decentralized settlement", "Auto-conversion to preferred currencies"].map(item => (
            <li key={item} className="flex items-center">
              <svg className="w-4 h-4 text-blue-600 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"></path></svg>
              {item}
            </li>
          ))}
        </ul>
      </div>
      <button
        onClick={() => onNext()}
        className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
      >
        Let's Get Started
      </button>
    </div>
  );
};

// Step 2: Identity Verification
const IdentityStep: React.FC<StepProps> = ({ onNext, onPrev }) => {
  const [loading, setLoading] = useState(false);

  const startVerification = async () => {
    setLoading(true);
    try {
      // Get verification token from backend
      const response = await apiClient.post('/api/kyc/start-verification');
      const { token } = response.data;
      
      // Initialize ComplyCube
      if (window.ComplyCube) {
        window.ComplyCube.mount({
          token: token,
          onComplete: (data: any) => {
            console.log('Verification complete', data);
            toast.success('Identity verification completed successfully!');
            onNext();
          },
          onError: (error: any) => {
            console.error('Verification error', error);
            toast.error('Verification failed. Please try again.');
            setLoading(false);
          }
        });
      } else {
        toast.error('Verification service not available');
        setLoading(false);
      }
    } catch (error) {
      console.error('Failed to start verification', error);
      toast.error('Failed to start verification process.');
      setLoading(false);
    }
  };

  return (
    <div className="text-center">
      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-2">Identity Verification</h3>
        <p className="text-gray-600">
          Verify your identity to unlock full access to Seamount's features.
        </p>
      </div>
      
      <div className="bg-blue-50 rounded-lg p-6 mb-8 text-left">
        <h4 className="font-semibold text-blue-900 mb-3">Why verify?</h4>
        <ul className="text-blue-800 text-sm space-y-2">
          <li>• Send and receive USDS stablecoins</li>
          <li>• Access cross-border payment features</li>
          <li>• Higher transaction limits</li>
          <li>• Enhanced security features</li>
        </ul>
      </div>
      
      <div className="space-y-4">
        <button
          onClick={startVerification}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Starting Verification...' : 'Verify Now'}
        </button>
        
        <button
          onClick={onNext}
          className="w-full border border-gray-300 text-gray-600 py-3 px-6 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
        >
          Skip for Now
        </button>
      </div>
    </div>
  );
};

// Step 3: Wallet Setup
const WalletStep: React.FC<StepProps> = ({ onNext, onPrev }) => {
  const [loading, setLoading] = useState(false);

  const setupWallet = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post('/api/wallet/create');
      toast.success('Wallet created successfully!');
      onNext();
    } catch (error) {
      console.error('Failed to create wallet', error);
      toast.error('Failed to create wallet. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-center">
      <div className="mb-8">
        <h3 className="text-xl font-semibold mb-2">Wallet Setup</h3>
        <p className="text-gray-600">
          Create your secure wallet to send, receive, and trade USDS.
        </p>
      </div>
      
      <div className="space-y-4">
        <button
          onClick={setupWallet}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Creating Wallet...' : 'Create Secure Wallet'}
        </button>
        
        <button
          onClick={onPrev}
          className="w-full border border-gray-300 text-gray-600 py-3 px-6 rounded-lg font-semibold hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
      </div>
    </div>
  );
};

// Main Onboarding Component
const onboardingSteps: OnboardingStepConfig[] = [
  { id: 1, title: "Welcome to Seamount", description: "Let's get you set up for cross-border payments", component: WelcomeStep },
  { id: 2, title: "Identity Verification", description: "Verify your identity for secure transactions", component: IdentityStep },
  { id: 3, title: "Wallet Setup", description: "Create your digital wallet", component: WalletStep },
];

const OnboardingPage: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(1);
  const [stepData, setStepData] = useState({});

  const handleNext = (data?: any) => {
    if (data) {
      setStepData(prev => ({ ...prev, [currentStep]: data }));
    }
    
    if (currentStep < onboardingSteps.length) {
      setCurrentStep(currentStep + 1);
    } else {
      // Onboarding complete
      toast.success('Onboarding completed successfully!');
      navigate('/dashboard');
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const CurrentStepComponent = onboardingSteps[currentStep - 1].component;
  const progress = (currentStep / onboardingSteps.length) * 100;

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">Get Started with Seamount</h1>
          <p className="mt-2 text-gray-600">
            Complete these steps to unlock global payments.
          </p>
        </div>
        
        <div className="bg-white rounded-2xl shadow-xl p-8 space-y-8">
          <div>
            <div className="flex justify-between text-sm text-gray-500 mb-2">
              <span>Step {currentStep} of {onboardingSteps.length}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2.5">
              <div 
                className="bg-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
          
          <div>
            <CurrentStepComponent
              onNext={handleNext}
              onPrev={handlePrev}
              stepData={stepData}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default OnboardingPage;