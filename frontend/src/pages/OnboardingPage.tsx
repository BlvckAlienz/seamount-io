// frontend/src/components/Onboarding.tsx

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

interface OnboardingStep {
  id: number;
  title: string;
  description: string;
  component: React.ComponentType<StepProps>;
}

interface StepProps {
  onNext: (data?: any) => void;
  onPrev: () => void;
  stepData: any;
}

interface Achievement {
  name: string;
  condition: (step: number) => boolean;
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: 1,
    title: "Welcome to Seamount",
    description: "Let's get you set up for cross-border payments",
    component: WelcomeStep
  },
  {
    id: 2,
    title: "Identity Verification",
    description: "Verify your identity for secure transactions",
    component: IdentityStep
  },
  {
    id: 3,
    title: "Wallet Setup",
    description: "Connect or create your digital wallet",
    component: WalletStep
  },
  {
    id: 4,
    title: "Payment Preferences",
    description: "Set up your payment methods and preferences",
    component: PaymentStep
  },
  {
    id: 5,
    title: "Security Setup",
    description: "Enable security features for your account",
    component: SecurityStep
  }
];

const Onboarding: React.FC = () => {
  const { user, onboardingStep, updateOnboardingStep, completeOnboarding, isDemoMode } = useAuth();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(onboardingStep || 1);
  const [stepData, setStepData] = useState<Record<number, any>>({});
  const [isLoading, setIsLoading] = useState(false);
  const [unlockedAchievements, setUnlockedAchievements] = useState<string[]>([]);

  const achievements: Achievement[] = [
    { name: "Welcome Aboard", condition: (step: number) => step >= 1 },
    { name: "Profile Pro", condition: (step: number) => step >= 2 },
    { name: "Document Detective", condition: (step: number) => step >= 3 },
    { name: "Verification Virtuoso", condition: (step: number) => step >= 4 },
    { name: "Onboarding Overlord", condition: (step: number) => step >= 5 },
  ];

  const stepMessages = [
    "Welcome to Seamount.io! Ready to navigate the trading seas?",
    "Tell us about yourself—no treasure map required!",
    "Upload your documents. Lost on the trading route? Our 404 page won’t help here!",
    "Verifying you now. Almost ready to sail the blockchain waves!",
    "Congrats! You’ve docked at Seamount.io—time to profit!",
  ];

  useEffect(() => {
    const newAchievements = achievements.filter(
      a => a.condition(currentStep) && !unlockedAchievements.includes(a.name)
    );
    if (newAchievements.length > 0) {
      setUnlockedAchievements(prev => [...prev, ...newAchievements.map(a => a.name)]);
    }
  }, [currentStep]);

  useEffect(() => {
    if (onboardingStep !== currentStep) {
      setCurrentStep(onboardingStep || 1);
    }
  }, [onboardingStep]);

  const handleNext = async (data?: any) => {
    try {
      setIsLoading(true);
      if (data) {
        setStepData(prev => ({ ...prev, [currentStep]: data }));
      }
      const nextStep = currentStep + 1;
      if (nextStep > onboardingSteps.length) {
        await completeOnboarding();
        toast.success('Onboarding completed! Welcome to Seamount.io');
        navigate('/dashboard');
      } else {
        setCurrentStep(nextStep);
        await updateOnboardingStep(nextStep, { ...stepData, [currentStep]: data });
        toast.success('Progress saved');
      }
    } catch (error) {
      console.error('Onboarding step error:', error);
      toast.error('Failed to save progress. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePrev = async () => {
    if (currentStep > 1) {
      const prevStep = currentStep - 1;
      setCurrentStep(prevStep);
      try {
        await updateOnboardingStep(prevStep, stepData);
      } catch (error) {
        console.warn('Failed to update step on back:', error);
      }
    }
  };

  const handleSkipOnboarding = async () => {
    if (isDemoMode || confirm('Skip onboarding? You can complete it later from settings.')) {
      try {
        await completeOnboarding();
        navigate('/dashboard');
      } catch (error) {
        console.error('Skip onboarding error:', error);
      }
    }
  };

  const currentStepConfig = onboardingSteps[currentStep - 1];
  const CurrentStepComponent = currentStepConfig.component;
  const progress = (currentStep / onboardingSteps.length) * 100;

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-2xl mx-auto px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Get Started with Seamount
          </h1>
          <p className="text-gray-600">
            {isDemoMode && <span className="text-blue-600 font-medium">[Demo Mode] </span>}
            Complete setup to start sending payments globally
          </p>
        </div>
        <div className="mb-8">
          <div className="flex justify-between text-sm text-gray-500 mb-2">
            <span>Step {currentStep} of {onboardingSteps.length}</span>
            <span>{Math.round(progress)}% complete</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        <div className="bg-white rounded-lg shadow-md p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-2">
              {currentStepConfig.title}
            </h2>
            <p className="text-gray-600">
              {currentStepConfig.description}
            </p>
            <p className="text-gray-600 italic">
              {stepMessages[currentStep - 1]}
            </p>
          </div>
          <CurrentStepComponent
            onNext={handleNext}
            onPrev={handlePrev}
            stepData={stepData[currentStep] || {}}
          />
        </div>
        <div className="text-center mt-6">
          <button
            onClick={handleSkipOnboarding}
            className="text-gray-500 hover:text-gray-700 disabled:opacity-50"
            disabled={isLoading}
          >
            Skip for now
          </button>
        </div>
        {unlockedAchievements.length > 0 && (
          <div className="text-center mt-6">
            <h3 className="text-lg font-semibold mb-2">Achievements Unlocked</h3>
            <ul className="list-disc list-inside text-gray-700">
              {unlockedAchievements.map((achievement, index) => (
                <li key={index}>{achievement}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

const WelcomeStep: React.FC<StepProps> = ({ onNext, stepData }) => {
  const { isDemoMode } = useAuth();
  
  return (
    <div className="text-center">
      <div className="mb-8">
        <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s}
        </div>
        <h3 className="text-xl font-semibold mb-2">
          Welcome to the Future of Cross-Border Payments
        </h3>
        <p className="text-gray-600">
          {isDemoMode ? 
            "Experience Seamount.io in demo mode with simulated features." :
            "Send USDS stablecoins globally with minimal fees and instant settlement."
          }
        </p>
      </div>
      <div className="bg-blue-50 rounded-lg p-6 mb-8">
        <h4 className="font-semibold text-blue-900 mb-3">What you'll get:</h4>
        <ul className="text-blue-800 text-sm space-y-2">
          <li>✓ Instant global transfers with USDS stablecoin</li>
          <li>✓ Minimal network fees (~$0.01 per transaction)</li>
          <li>✓ 24/7/365 decentralized settlement</li>
          <li>✓ Multi-blockchain support (Solana, Ethereum)</li>
          <li>✓ Auto-conversion to preferred currencies</li>
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

const IdentityStep: React.FC<StepProps> = ({ onNext, onPrev, stepData }) => {
  const [formData, setFormData] = useState({
    fullName: stepData.fullName || '',
    dateOfBirth: stepData.dateOfBirth || '',
    country: stepData.country || '',
    idType: stepData.idType || 'passport',
    idNumber: stepData.idNumber || '',
    ...stepData
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { isDemoMode } = useAuth();

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    if (!formData.fullName.trim()) newErrors.fullName = 'Full name is required';
    if (!formData.dateOfBirth) newErrors.dateOfBirth = 'Date of birth is required';
    if (!formData.country) newErrors.country = 'Country is required';
    if (!formData.idNumber.trim()) newErrors.idNumber = 'ID number is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm()) {
      onNext(formData);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {isDemoMode && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-800">
            <strong>Demo Mode:</strong> Use any values - no real verification required.
          </p>
        </div>
      )}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Full Name
        </label>
        <input
          type="text"
          value={formData.fullName}
          onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
          className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            errors.fullName ? 'border-red-500' : 'border-gray-300'
          }`}
          placeholder="Enter your full legal name"
        />
        {errors.fullName && <p className="text-red-500 text-sm mt-1">{errors.fullName}</p>}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Date of Birth
          </label>
          <input
            type="date"
            value={formData.dateOfBirth}
            onChange={(e) => setFormData({ ...formData, dateOfBirth: e.target.value })}
            className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              errors.dateOfBirth ? 'border-red-500' : 'border-gray-300'
            }`}
          />
          {errors.dateOfBirth && <p className="text-red-500 text-sm mt-1">{errors.dateOfBirth}</p>}
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Country
          </label>
          <select
            value={formData.country}
            onChange={(e) => setFormData({ ...formData, country: e.target.value })}
            className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              errors.country ? 'border-red-500' : 'border-gray-300'
            }`}
          >
            <option value="">Select Country</option>
            <option value="US">United States</option>
            <option value="KE">Kenya</option>
            <option value="NG">Nigeria</option>
            <option value="GB">United Kingdom</option>
            <option value="CA">Canada</option>
            <option value="AU">Australia</option>
            <option value="DE">Germany</option>
            <option value="FR">France</option>
          </select>
          {errors.country && <p className="text-red-500 text-sm mt-1">{errors.country}</p>}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            ID Type
          </label>
          <select
            value={formData.idType}
            onChange={(e) => setFormData({ ...formData, idType: e.target.value })}
            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="passport">Passport</option>
            <option value="national_id">National ID</option>
            <option value="drivers_license">Driver's License</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            ID Number
          </label>
          <input
            type="text"
            value={formData.idNumber}
            onChange={(e) => setFormData({ ...formData, idNumber: e.target.value })}
            className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              errors.idNumber ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="Enter ID number"
          />
          {errors.idNumber && <p className="text-red-500 text-sm mt-1">{errors.idNumber}</p>}
        </div>
      </div>
      <div className="flex justify-between">
        <button
          type="button"
          onClick={onPrev}
          className="px-6 py-2 text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50"
        >
          Back
        </button>
        <button
          type="submit"
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Continue
        </button>
      </div>
    </form>
  );
};

const WalletStep: React.FC<StepProps> = ({ onNext, onPrev, stepData }) => {
  const [walletOption, setWalletOption] = useState(stepData.walletOption || '');
  const [walletAddress, setWalletAddress] = useState(stepData.walletAddress || '');
  const [isConnecting, setIsConnecting] = useState(false);
  const { isDemoMode } = useAuth();

  const connectWallet = async (type: string) => {
    setIsConnecting(true);
    try {
      if (isDemoMode) {
        await new Promise(resolve => setTimeout(resolve, 1500));
        const mockAddress = `demo_${type}_${Date.now().toString().slice(-6)}`;
        setWalletAddress(mockAddress);
        setWalletOption(type);
        toast.success(`Demo ${type} wallet connected!`);
      } else {
        switch (type) {
          case 'phantom':
            break;
          case 'metamask':
            break;
          case 'create':
            break;
        }
      }
    } catch (error) {
      toast.error('Failed to connect wallet');
      console.error('Wallet connection error:', error);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleContinue = () => {
    if (walletOption && walletAddress) {
      onNext({ walletOption, walletAddress });
    }
  };

  return (
    <div className="space-y-6">
      {isDemoMode && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>Demo Mode:</strong> Wallet connections are simulated.
          </p>
        </div>
      )}
      <div className="text-center mb-8">
        <h3 className="text-lg font-semibold mb-2">Connect Your Wallet</h3>
        <p className="text-gray-600">
          Choose how you'd like to manage your USDS and other crypto assets
        </p>
      </div>
      <div className="space-y-4">
        <div className={`border-2 rounded-lg p-6 cursor-pointer transition-colors ${
          walletOption === 'phantom' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
        }`} onClick={() => connectWallet('phantom')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-purple-600 font-bold">P</span>
              </div>
              <div>
                <h4 className="font-semibold">Phantom Wallet</h4>
                <p className="text-sm text-gray-600">Solana-native wallet (Recommended)</p>
              </div>
            </div>
            {walletOption === 'phantom' && (
              <div className="text-green-500">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>
        </div>
        <div className={`border-2 rounded-lg p-6 cursor-pointer transition-colors ${
          walletOption === 'metamask' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
        }`} onClick={() => connectWallet('metamask')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center mr-4">
                <span className="text-orange-600 font-bold">M</span>
              </div>
              <div>
                <h4 className="font-semibold">MetaMask</h4>
                <p className="text-sm text-gray-600">Ethereum-compatible wallet</p>
              </div>
            </div>
            {walletOption === 'metamask' && (
              <div className="text-green-500">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>
        </div>
        <div className={`border-2 rounded-lg p-6 cursor-pointer transition-colors ${
          walletOption === 'create' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
        }`} onClick={() => connectWallet('create')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center mr-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
              <div>
                <h4 className="font-semibold">Create New Wallet</h4>
                <p className="text-sm text-gray-600">Generate a secure wallet managed by Seamount</p>
              </div>
            </div>
            {walletOption === 'create' && (
              <div className="text-green-500">
                <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>
        </div>
      </div>
      {walletAddress && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-green-500 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <div>
              <p className="text-sm font-medium text-green-800">Wallet Connected</p>
              <p className="text-sm text-green-600 font-mono">{walletAddress}</p