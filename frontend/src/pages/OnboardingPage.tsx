// File: frontend/src/pages/OnboardingPage.tsx
// ✅ PRODUCTION READY: Multi-chain wallet creation integrated

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../config/api';
import toast from 'react-hot-toast';
import { 
  Eye, EyeOff, Copy, Shield, Wallet, CheckCircle, 
  Globe, Lock, Download, Check, AlertCircle,
  Bitcoin, Coins, Sparkles
} from 'lucide-react';
import BVNCollectionModal from '../components/onboarding/BVNCollectionModal';

// ============================================================================
// STEP COMPONENTS - UPDATED FOR MULTI-CHAIN
// ============================================================================

const WelcomeStep = ({ onNext }: { onNext: () => void }) => (
  <div className="text-center">
    <div className="mb-8">
      <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg animate-pulse">
        <Globe className="h-10 w-10 text-white" />
      </div>
      <h3 className="text-2xl font-bold mb-3 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
        Welcome to Seamount
      </h3>
      <p className="text-gray-400 text-lg">
        The future of cross-border payments is here
      </p>
    </div>
    
    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 rounded-xl p-6 mb-8 text-left border border-blue-500/30 backdrop-blur-sm">
      <h4 className="font-semibold text-white mb-4 flex items-center">
        <CheckCircle className="h-5 w-5 text-blue-400 mr-2" />
        What You'll Get
      </h4>
      <div className="space-y-3 text-gray-300">
        {[
          "Multi-chain wallet (Bitcoin, Ethereum, Polygon, Algorand)",
          "Lightning-fast settlement (sub-5 seconds)",
          "Cross-border transfers at 1.2% (vs 6-8% traditional)",
          "Bank-grade security with Web3 freedom"
        ].map((item, idx) => (
          <div key={idx} className="flex items-start transform transition-transform hover:translate-x-2">
            <CheckCircle className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
    
    <button
      onClick={onNext}
      className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all transform hover:scale-105 shadow-lg hover:shadow-blue-500/50"
    >
      Get Started
    </button>
  </div>
);

const IdentityStep = ({ onVerify, onSkip }: { onVerify: () => void; onSkip: () => void }) => (
  <div className="text-center">
    <div className="mb-6">
      <div className="w-16 h-16 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
        <Shield className="h-8 w-8 text-white" />
      </div>
      <h3 className="text-2xl font-semibold text-white mb-2">Verify Your Identity</h3>
      <p className="text-gray-400">Unlock full platform features and higher limits</p>
    </div>
    
    <div className="bg-blue-900/20 rounded-xl p-6 mb-6 border border-blue-500/30 text-left">
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center p-4 bg-gray-800/50 rounded-lg">
          <div className="text-2xl font-bold text-blue-400 mb-1">$5,000</div>
          <div className="text-xs text-gray-400">Without KYC</div>
        </div>
        <div className="text-center p-4 bg-gray-800/50 rounded-lg">
          <div className="text-2xl font-bold text-green-400 mb-1">Unlimited</div>
          <div className="text-xs text-gray-400">With KYC</div>
        </div>
      </div>
      <p className="text-sm text-gray-400">
        ⚡ Instant verification • 🔒 Bank-grade security • 🌍 Global access
      </p>
    </div>
    
    <div className="space-y-3">
      <button
        onClick={onVerify}
        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all shadow-lg hover:shadow-blue-500/50"
      >
        Verify Now (2 minutes)
      </button>
      
      <button
        onClick={onSkip}
        className="w-full text-gray-400 hover:text-gray-300 py-3 rounded-xl hover:bg-gray-800/50 transition-colors"
      >
        I'll Do This Later
      </button>
    </div>
  </div>
);

const MultiChainWalletStep = ({ onComplete }: { onComplete: (wallets: any) => void }) => {
  const [creating, setCreating] = useState(false);
  const [wallets, setWallets] = useState<any>({});
  
  const chains = [
    { id: 'bitcoin', name: 'Bitcoin', icon: Bitcoin, color: 'from-orange-500 to-yellow-600' },
    { id: 'ethereum', name: 'Ethereum', icon: Coins, color: 'from-gray-400 to-slate-600' },
    { id: 'polygon', name: 'Polygon', icon: Coins, color: 'from-purple-500 to-indigo-600' },
    { id: 'algorand', name: 'Algorand', icon: Shield, color: 'from-blue-500 to-cyan-600' }
  ];

  const createMultiChainWallets = async () => {
    setCreating(true);
    try {
      const response = await apiClient.post('/api/v1/wallet/create-multi-chain', {
        chains: ['bitcoin', 'ethereum', 'polygon', 'algorand']
      });

      if (response.data.success) {
        setWallets(response.data.wallets);
        toast.success(`Wallets created on ${response.data.total_chains} chains!`);
        
        // Auto-complete after successful creation
        setTimeout(() => {
          onComplete(response.data.wallets);
        }, 2000);
      }
    } catch (error: any) {
      console.error('Multi-chain wallet creation failed:', error);
      toast.error(error.response?.data?.error || 'Failed to create wallets');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="text-center">
      <div className="mb-6">
        <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Sparkles className="h-8 w-8 text-white" />
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Multi-Chain Wallets</h3>
        <p className="text-gray-400">Create your unified wallets across multiple blockchains</p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        {chains.map(chain => (
          <div key={chain.id} className={`bg-gradient-to-br ${chain.color} rounded-xl p-4 text-white`}>
            <chain.icon className="h-8 w-8 mx-auto mb-2" />
            <div className="text-sm font-semibold">{chain.name}</div>
            <div className="text-xs opacity-80">
              {wallets[chain.id] ? '✓ Created' : 'Ready to create'}
            </div>
          </div>
        ))}
      </div>

      <div className="bg-blue-900/20 rounded-xl p-4 mb-6 border border-blue-500/30 text-left">
        <h4 className="font-semibold text-white mb-2 flex items-center">
          <CheckCircle className="h-4 w-4 text-blue-400 mr-2" />
          One Account, Multi-Chain Wallets
        </h4>
        <ul className="text-sm text-gray-300 space-y-1">
          <li>• Two recovery phrases for five chains</li>
          <li>• Auto-routing to fastest/cheapest network</li>
          <li>• Unified balance across Algorand, Bitcoin, Ethereum, Polygon, and Tron</li>
          <li>• No blockchain complexity - we handle everything</li>
        </ul>
      </div>

      <button
        onClick={createMultiChainWallets}
        disabled={creating || Object.keys(wallets).length > 0}
        className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold py-4 px-6 rounded-xl disabled:opacity-50 shadow-lg transition-all"
      >
        {creating ? (
          <div className="flex items-center justify-center gap-2">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            Creating Multi-Chain Wallets...
          </div>
        ) : Object.keys(wallets).length > 0 ? (
          <div className="flex items-center justify-center gap-2">
            <Check className="h-5 w-5" />
            Wallets Created Successfully!
          </div>
        ) : (
          'Create Multi-Chain Wallet'
        )}
      </button>

      {Object.keys(wallets).length > 0 && (
        <div className="mt-4 p-3 bg-green-900/20 border border-green-500/30 rounded-lg">
          <p className="text-green-400 text-sm">
            ✓ Your multi-chain wallets are ready! Redirecting to dashboard...
          </p>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT - UPDATED FOR MULTI-CHAIN
// ============================================================================

const OnboardingPage = () => {
  const [step, setStep] = useState('welcome');
  const [mnemonic, setMnemonic] = useState<string | null>(null);
  const [showBVNModal, setShowBVNModal] = useState(false);
  const { completeOnboarding, userProfile, refreshProfile } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (userProfile?.kyc_status === 'verified') {
      navigate('/dashboard');
    }
  }, [userProfile, navigate]);

  const handleWelcomeComplete = () => setStep('identity');

  const handleStartVerification = () => {
    setShowBVNModal(true);
  };

  // ✅ UPDATED: Handle BVN submit with multi-chain wallet creation
  const handleBVNSubmit = async (formData: any) => {
    const toastId = toast.loading('Starting verification...');
    
    try {
      // 1. Store KYC data
      await apiClient.post('/api/v1/kyc/submit-kyc-data', {
        bvn: formData.idNumber,
        id_type: formData.idType,
        date_of_birth: formData.dateOfBirth,
        gender: formData.gender,
        phone: formData.phoneNumber,
        country_code: formData.country
      });

      // 2. Start verification
      const verifyResponse = await apiClient.post('/api/v1/kyc/start-verification');
      
      toast.success('Verification submitted!', { id: toastId });

      // 3. Proceed to wallet creation step
      setShowBVNModal(false);
      setStep('walletCreation');
      
    } catch (error: any) {
      console.error('KYC submission error:', error);
      toast.error(error.response?.data?.detail || 'Verification failed', { id: toastId });
      setShowBVNModal(false);
    }
  };

  // ✅ UPDATED: Skip verification with multi-chain wallet creation
  const handleSkipVerification = async () => {
    try {
      const toastId = toast.loading('Skipping verification...');
      const response = await apiClient.post('/api/v1/kyc/skip-verification');
      
      if (response.data.success) {
        toast.success('Verification skipped!', { id: toastId });
        setStep('walletCreation');
      }
    } catch (error: any) {
      console.error('Skip verification error:', error);
      toast.error(error.response?.data?.detail || 'Failed to skip verification');
    }
  };

  // ✅ NEW: Handle multi-chain wallet creation completion
  const handleWalletCreationComplete = async (wallets: any) => {
    const toastId = toast.loading('Completing setup...');
    
    try {
      await apiClient.put('/api/v1/user/profile', {
        kyc_level: 1,
        onboarding_complete: true
      });
      
      await refreshProfile();
      toast.success('Welcome to Seamount!', { id: toastId });
      navigate('/dashboard');
    } catch (error) {
      console.error('Setup completion error:', error);
      toast.error('Setup failed', { id: toastId });
    }
  };

  const progressPercentage = 
    step === 'welcome' ? '25%' : 
    step === 'identity' ? '50%' : 
    step === 'walletCreation' ? '100%' : '100%';

  const stepTitles: { [key: string]: string } = {
    welcome: 'Welcome to Seamount',
    identity: 'Identity Verification',
    walletCreation: 'Multi-Chain Wallet Setup'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-gray-800/50 backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden border border-gray-700">
        <div className="bg-gray-900/50 border-b border-gray-700 p-6">
          <div className="flex justify-between items-center text-sm text-gray-400 mb-3">
            <h2 className="font-semibold text-lg text-white">{stepTitles[step]}</h2>
            <span>
              {step === 'welcome' ? '1 of 3' : step === 'identity' ? '2 of 3' : '3 of 3'}
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2">
            <div 
              className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-500"
              style={{ width: progressPercentage }}
            />
          </div>
        </div>
        
        <div className="p-8">
          {step === 'welcome' ? (
            <WelcomeStep onNext={handleWelcomeComplete} />
          ) : step === 'identity' ? (
            <IdentityStep 
              onVerify={handleStartVerification}
              onSkip={handleSkipVerification}
            />
          ) : step === 'walletCreation' ? (
            <MultiChainWalletStep onComplete={handleWalletCreationComplete} />
          ) : null}
        </div>
      </div>

      {/* BVN Collection Modal */}
      {showBVNModal && (
        <BVNCollectionModal
          onComplete={handleBVNSubmit}
          onCancel={() => setShowBVNModal(false)}
          userEmail={userProfile?.email || ''}
          countryCode={userProfile?.country_code || 'NG'}
        />
      )}
    </div>
  );
};

export default OnboardingPage;