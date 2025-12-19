// File: frontend/src/pages/OnboardingPage.tsx
// ✅ PRODUCTION READY: Fixed Individual Flow + Enhanced Design

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../config/api';
import toast from 'react-hot-toast';
import { 
  Eye, EyeOff, Copy, Shield, Wallet, CheckCircle, 
  Globe, Lock, Download, Check, AlertCircle,
  Bitcoin, Ethereum, Database, Zap, Sparkles, Coins, Layers
} from 'lucide-react';
import BVNCollectionModal from '../components/onboarding/BVNCollectionModal';
import BusinessQuestionnaireStep from '../components/onboarding/BusinessQuestionnaireStep';

// ============================================================================
// STEP COMPONENTS - ENHANCED DESIGN
// ============================================================================

const WelcomeStep = ({ onNext }: { onNext: () => void }) => (
  <div className="text-center animate-fade-in">
    <div className="mb-8">
      <div className="w-20 h-20 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg animate-pulse">
        <Globe className="h-10 w-10 text-white" />
      </div>
      <h3 className="text-2xl font-bold mb-2 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
        Welcome to Seamount
      </h3>
      <p className="text-gray-400 text-lg">
        Your Gateway to Private Asset Ownership
      </p>
    </div>
    
    <div className="bg-gradient-to-br from-blue-900/20 via-purple-900/20 to-pink-900/20 rounded-xl p-6 mb-8 text-left border border-blue-500/20 backdrop-blur-sm animate-slide-up">
      <h4 className="font-semibold text-white mb-4 flex items-center">
        <CheckCircle className="h-5 w-5 text-blue-400 mr-2" />
        What You'll Get
      </h4>
      <div className="space-y-3 text-gray-300">
        {[
          "Access to Liquidity and Capital from Private Markets",
          "Multi-Chain Smart Wallets (Algorand, Bitcoin, Ethereum, Polygon, Tron)",
          "On-chain 24/7 payments with sub-5 second settlement",
          "Audited Accounts for Tokenized Asset Distribution",
          "Bank-Grade Security with Web3 Freedom"
        ].map((item, idx) => (
          <div key={idx} className="flex items-start transform transition-transform hover:translate-x-1 duration-200">
            <CheckCircle className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
            <span className="text-sm">{item}</span>
          </div>
        ))}
      </div>
    </div>
    
    <button
      onClick={onNext}
      className="w-full bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 text-white font-semibold py-4 px-6 rounded-xl transition-all transform hover:scale-[1.02] shadow-lg hover:shadow-blue-500/50 animate-pulse-button"
    >
      Get Started
    </button>
  </div>
);

const IdentityStep = ({ onVerify, onSkip }: { onVerify: () => void; onSkip: () => void }) => (
  <div className="text-center animate-fade-in">
    <div className="mb-6">
      <div className="w-16 h-16 bg-gradient-to-br from-yellow-500 via-orange-500 to-red-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
        <Shield className="h-8 w-8 text-white" />
      </div>
      <h3 className="text-2xl font-semibold text-white mb-2">Verify Your Identity</h3>
      <p className="text-gray-400">Unlock full platform features and higher limits</p>
    </div>
    
    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 rounded-xl p-6 mb-6 border border-blue-500/30 text-left backdrop-blur-sm">
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="text-center p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-blue-500/50 transition-colors">
          <div className="text-2xl font-bold text-blue-400 mb-1">$10,000</div>
          <div className="text-xs text-gray-400">Without KYC</div>
        </div>
        <div className="text-center p-4 bg-gray-800/50 rounded-lg border border-gray-700 hover:border-green-500/50 transition-colors">
          <div className="text-2xl font-bold text-green-400 mb-1">Unlimited</div>
          <div className="text-xs text-gray-400">With KYC</div>
        </div>
      </div>
      <div className="flex items-center text-sm text-gray-400 space-x-3">
        <span className="flex items-center"><Zap className="h-3 w-3 mr-1" /> Instant</span>
        <span className="flex items-center"><Shield className="h-3 w-3 mr-1" /> Secure</span>
        <span className="flex items-center"><Globe className="h-3 w-3 mr-1" /> Global</span>
      </div>
    </div>
    
    <div className="space-y-3">
      <button
        onClick={onVerify}
        className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all shadow-lg hover:shadow-blue-500/50"
      >
        Verify Now (1 minute)
      </button>
      
      <button
        onClick={onSkip}
        className="w-full text-gray-400 hover:text-gray-300 py-3 rounded-xl hover:bg-gray-800/50 transition-colors border border-gray-700 hover:border-gray-600"
      >
        I'll Do This Later
      </button>
    </div>
  </div>
);

// ============================================================================
// ENHANCED MULTI-CHAIN WALLET STEP WITH BETTER DESIGN
// ============================================================================

const MultiChainWalletStep = ({ onComplete }: { onComplete: (wallets: any) => void }) => {
  const [creating, setCreating] = useState(false);
  const [wallets, setWallets] = useState<any>({});
  
  const chains = [
    { 
      id: 'algorand', 
      name: 'Algorand', 
      icon: Database, 
      color: 'from-blue-500 to-cyan-600',
      description: 'Enterprise blockchain',
      index: 1
    },
    { 
      id: 'bitcoin', 
      name: 'Bitcoin', 
      icon: Bitcoin, 
      color: 'from-orange-500 to-yellow-600',
      description: 'Digital gold',
      index: 2
    },
    { 
      id: 'ethereum', 
      name: 'Ethereum', 
      icon: Coins, 
      color: 'from-gray-400 to-slate-600',
      description: 'Smart contracts',
      index: 3
    },
    { 
      id: 'polygon', 
      name: 'Polygon', 
      icon: Layers, 
      color: 'from-purple-500 to-indigo-600',
      description: 'Layer 2 scaling',
      index: 4
    },
    { 
      id: 'tron', 
      name: 'Tron', 
      icon: Zap, 
      color: 'from-red-500 to-pink-600',
      description: 'High throughput',
      index: 5
    }
  ];

  const createMultiChainWallets = async () => {
    setCreating(true);
    try {
      const response = await apiClient.post('/api/v1/wallet/create-multi-chain', {
        chains: ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron']
      });

      if (response.data.success) {
        setWallets(response.data.wallets);
        toast.success('Multi-chain wallets created successfully!', {
          icon: '🚀',
          duration: 3000
        });
        
        // Auto-complete after successful creation
        setTimeout(() => {
          onComplete(response.data.wallets);
        }, 2000);
      }
    } catch (error: any) {
      console.error('Multi-chain wallet creation failed:', error);
      toast.error(error.response?.data?.error || 'Failed to create wallets. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="text-center animate-fade-in">
      <div className="mb-6">
        <div className="w-16 h-16 bg-gradient-to-br from-purple-500 via-pink-500 to-red-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Sparkles className="h-8 w-8 text-white" />
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Multi-Chain Wallets</h3>
        <p className="text-gray-400">Create unified wallets across multiple blockchains</p>
      </div>

      {/* ENHANCED CHAIN CARDS - UNIFORM DESIGN */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {chains.map((chain) => {
          const Icon = chain.icon;
          const isCreated = wallets[chain.id];
          
          return (
            <div
              key={chain.id}
              className={`relative bg-gradient-to-br ${chain.color} rounded-xl p-5 text-white overflow-hidden group transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl ${
                isCreated ? 'ring-2 ring-green-500/50' : 'ring-1 ring-white/10'
              }`}
            >
              {/* Chain Index Badge */}
              <div className="absolute top-3 right-3 w-8 h-8 bg-black/30 rounded-full flex items-center justify-center text-xs font-bold">
                {chain.index}
              </div>
              
              <div className="flex flex-col items-center">
                <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center mb-4 group-hover:bg-white/30 transition-colors">
                  <Icon className="h-7 w-7" />
                </div>
                
                <h4 className="font-bold text-lg mb-1">{chain.name}</h4>
                <p className="text-xs opacity-80 mb-3">{chain.description}</p>
                
                <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                  isCreated 
                    ? 'bg-green-500/20 text-green-300 border border-green-500/30' 
                    : 'bg-white/10 text-white/80'
                }`}>
                  {isCreated ? (
                    <span className="flex items-center">
                      <Check className="h-3 w-3 mr-1" /> Created
                    </span>
                  ) : (
                    'Ready to create'
                  )}
                </div>
              </div>
              
              {/* Progress Bar Effect */}
              {creating && !isCreated && (
                <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer"></div>
              )}
            </div>
          );
        })}
      </div>

      {/* Unified Block with 5 columns for status */}
      <div className="bg-gradient-to-r from-gray-900/50 to-gray-800/50 rounded-xl p-4 mb-6 border border-gray-700/50">
        <h4 className="font-semibold text-white mb-3 flex items-center">
          <CheckCircle className="h-4 w-4 text-blue-400 mr-2" />
          Multi-Chain Status
        </h4>
        <div className="grid grid-cols-5 gap-2">
          {chains.map(chain => (
            <div key={chain.id} className="text-center">
              <div className={`w-8 h-8 mx-auto rounded-full flex items-center justify-center mb-2 ${
                wallets[chain.id] 
                  ? 'bg-green-500/20 border border-green-500/50' 
                  : 'bg-gray-700/50 border border-gray-600'
              }`}>
                {wallets[chain.id] ? (
                  <Check className="h-4 w-4 text-green-400" />
                ) : (
                  <span className="text-xs text-gray-400">{chain.index}</span>
                )}
              </div>
              <div className="text-xs text-gray-400">{chain.name}</div>
            </div>
          ))}
        </div>
      </div>

      <button
        onClick={createMultiChainWallets}
        disabled={creating || Object.keys(wallets).length === chains.length}
        className="w-full bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 hover:from-purple-700 hover:via-pink-700 hover:to-red-700 text-white font-semibold py-4 px-6 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed shadow-lg hover:shadow-purple-500/50 transition-all duration-300 group"
      >
        {creating ? (
          <div className="flex items-center justify-center gap-3">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
            <span>Creating {Object.keys(wallets).length + 1} of {chains.length} Wallets...</span>
          </div>
        ) : Object.keys(wallets).length === chains.length ? (
          <div className="flex items-center justify-center gap-2">
            <Check className="h-5 w-5" />
            All Wallets Created!
          </div>
        ) : (
          <div className="flex items-center justify-center gap-2">
            <Wallet className="h-5 w-5" />
            Create Multi-Chain Wallets
          </div>
        )}
      </button>

      {Object.keys(wallets).length === chains.length && (
        <div className="mt-4 p-4 bg-gradient-to-r from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl animate-pulse">
          <div className="flex items-center justify-center gap-2 text-green-400">
            <Check className="h-5 w-5" />
            <span className="font-medium">All wallets created! Redirecting to dashboard...</span>
          </div>
          <p className="text-sm text-green-300/70 mt-2">
            Your multi-chain wallets are ready for cross-border payments and tokenization.
          </p>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT - FIXED INDIVIDUAL FLOW
// ============================================================================

const OnboardingPage = () => {
  const [step, setStep] = useState('welcome');
  const [questionnaireData, setQuestionnaireData] = useState<any>(null);
  const [showBVNModal, setShowBVNModal] = useState(false);
  const [userAccountType, setUserAccountType] = useState<string>('');
  const { userProfile, refreshProfile } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (userProfile?.kyc_status === 'verified') {
      navigate('/dashboard');
    }
  }, [userProfile, navigate]);

  const handleWelcomeComplete = () => setStep('questionnaire');

  // FIXED: Handle questionnaire completion - properly routes based on account type
  const handleQuestionnaireComplete = async (data: any) => {
    const toastId = toast.loading('Saving your profile...');
    
    try {
      setUserAccountType(data.accountType);
      
      // Save questionnaire data to backend
      const profileData: any = {
        account_type: data.accountType,
        questionnaire_completed: true,
        questionnaire_completed_at: new Date().toISOString()
      };

      // Only add business fields if account type is business
      if (data.accountType === 'business') {
        profileData.business_type = data.businessType;
        profileData.legal_business_name = data.legalBusinessName;
        profileData.registered_company_number = data.registeredCompanyNumber;
        profileData.company_size = data.companySize;
        profileData.business_sector = data.sector;
        profileData.intent = data.intent;
        profileData.tokenization_details = data.tokenizationDetails;
        profileData.capital_raising_details = data.capitalRaisingDetails;
        profileData.has_corporate_docs = data.hasCorporateDocs;
      }

      await apiClient.put('/api/v1/user/profile', profileData);

      setQuestionnaireData(data);
      toast.success('Profile saved!', { id: toastId });
      
      // FIXED: ALL users proceed to KYC (identity verification)
      setStep('identity');
      
    } catch (error: any) {
      console.error('Questionnaire save error:', error);
      toast.error('Failed to save profile', { id: toastId });
    }
  };

  // FIXED: Handle skipping questionnaire (for individuals)
  const handleQuestionnaireSkip = async () => {
    const toastId = toast.loading('Setting up individual account...');
    
    try {
      // CRITICAL: Save the individual account type to backend
      await apiClient.put('/api/v1/user/profile', {
        account_type: 'individual',
        questionnaire_completed: true,
        questionnaire_completed_at: new Date().toISOString()
      });
      
      toast.success('Individual account configured!', { id: toastId });
      setStep('identity');
    } catch (error: any) {
      console.error('Questionnaire skip error:', error);
      toast.error('Failed to configure individual account', { id: toastId });
      // Still proceed to KYC even if save fails
      setStep('identity');
    }
  };

  const handleStartVerification = () => {
    setShowBVNModal(true);
  };

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

  const handleWalletCreationComplete = async (wallets: any) => {
    const toastId = toast.loading('Completing setup...');
    
    try {
      await apiClient.put('/api/v1/user/profile', {
        kyc_level: userAccountType === 'business' ? 2 : 1,
        onboarding_complete: true,
        onboarding_completed_at: new Date().toISOString(),
        wallets_created: true
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
    step === 'welcome' ? '20%' : 
    step === 'questionnaire' ? '40%' :
    step === 'identity' ? '60%' : 
    step === 'walletCreation' ? '100%' : '100%';

  const stepTitles: { [key: string]: string } = {
    welcome: 'Welcome to Seamount',
    questionnaire: userAccountType === 'business' ? 'Business Profile' : 'Account Setup',
    identity: 'Identity Verification',
    walletCreation: 'Multi-Chain Wallet Setup'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="max-w-4xl w-full bg-gray-800/50 backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden border border-gray-700">
        <div className="bg-gradient-to-r from-gray-900/80 to-gray-800/80 border-b border-gray-700 p-6">
          <div className="flex justify-between items-center text-sm text-gray-400 mb-3">
            <h2 className="font-semibold text-lg text-white">{stepTitles[step]}</h2>
            <span className="flex items-center">
              <span className="mr-2">
                {step === 'welcome' ? '1 of 4' : 
                 step === 'questionnaire' ? '2 of 4' : 
                 step === 'identity' ? '3 of 4' : '4 of 4'}
              </span>
              <span className="text-xs bg-gray-700 px-2 py-1 rounded-full">
                {userAccountType ? userAccountType.toUpperCase() : 'SETUP'}
              </span>
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
            <div 
              className="bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 h-2 rounded-full transition-all duration-700 ease-out"
              style={{ width: progressPercentage }}
            />
          </div>
        </div>
        
        <div className="p-8">
          {step === 'welcome' ? (
            <WelcomeStep onNext={handleWelcomeComplete} />
          ) : step === 'questionnaire' ? (
            <BusinessQuestionnaireStep 
              onComplete={handleQuestionnaireComplete}
              onSkip={handleQuestionnaireSkip}
            />
          ) : step === 'identity' ? (
            <IdentityStep 
              onVerify={handleStartVerification}
              onSkip={handleSkipVerification}
            />
          ) : step === 'walletCreation' ? (
            <MultiChainWalletStep onComplete={handleWalletCreationComplete} />
          ) : null}
        </div>

        {/* Bottom Navigation */}
        {step !== 'welcome' && step !== 'walletCreation' && (
          <div className="p-4 border-t border-gray-700/50 bg-gray-900/30">
            <div className="flex justify-between items-center">
              <button
                onClick={() => {
                  if (step === 'identity') setStep('questionnaire');
                  else if (step === 'questionnaire') setStep('welcome');
                }}
                className="text-gray-400 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800/50 transition-colors"
              >
                ← Back
              </button>
              <div className="text-xs text-gray-500">
                {userAccountType === 'business' ? 'Business Account' : 'Individual Account'}
              </div>
            </div>
          </div>
        )}
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