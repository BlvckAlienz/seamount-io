// File: frontend/src/pages/OnboardingPage.tsx
// 🚀 WEB3 REDESIGN: Mobile-friendly + Iconic Web3 Aesthetic

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../config/api';
import toast from 'react-hot-toast';
import { 
  Shield, Wallet, CheckCircle, Globe, Download, Check,
  Bitcoin, Ethereum, Database, Zap, Sparkles, Layers, 
  Lock, Users, Building, User, Rocket, Coins,
  ArrowRight, ArrowLeft, Loader2
} from 'lucide-react';
import BVNCollectionModal from '../components/onboarding/BVNCollectionModal';
import BusinessQuestionnaireStep from '../components/onboarding/BusinessQuestionnaireStep';

// ============================================================================
// CUSTOM ANIMATIONS & STYLES
// ============================================================================

const shimmerEffect = `
  @keyframes shimmer {
    0% { background-position: -200% center; }
    100% { background-position: 200% center; }
  }
  
  .animate-shimmer {
    background: linear-gradient(90deg, 
      transparent 0%, 
      rgba(255,255,255,0.1) 50%, 
      transparent 100%);
    background-size: 200% 100%;
    animation: shimmer 2s infinite;
  }
  
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
  }
  
  .animate-float {
    animation: float 3s ease-in-out infinite;
  }
  
  @keyframes glow {
    0%, 100% { box-shadow: 0 0 20px rgba(59, 130, 246, 0.3); }
    50% { box-shadow: 0 0 40px rgba(59, 130, 246, 0.6); }
  }
  
  .animate-glow {
    animation: glow 2s ease-in-out infinite;
  }
  
  @keyframes pulse-soft {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
  }
  
  .animate-pulse-soft {
    animation: pulse-soft 2s ease-in-out infinite;
  }
`;

// ============================================================================
// STEP COMPONENTS - WEB3 REDESIGN
// ============================================================================

const WelcomeStep = ({ onNext }: { onNext: () => void }) => (
  <div className="text-center space-y-6">
    {/* Animated Header */}
    <div className="relative mb-8">
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-pink-500/20 blur-2xl rounded-full" />
      <div className="relative w-24 h-24 mx-auto mb-4">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-600 rounded-full animate-pulse-soft" />
        <div className="absolute inset-2 bg-gradient-to-br from-gray-900 to-gray-800 rounded-full flex items-center justify-center">
          <Globe className="h-12 w-12 text-white" />
        </div>
        <div className="absolute -top-2 -right-2 w-8 h-8 bg-green-500 rounded-full flex items-center justify-center animate-float">
          <span className="text-lg">🌊</span>
        </div>
      </div>
      
      <h1 className="text-3xl md:text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
        Welcome to Seamount
      </h1>
      <p className="text-gray-300 text-lg">🌐 Your Gateway to Web3 & Private Markets</p>
    </div>
    
    {/* Benefits Card */}
    <div className="relative">
      <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10 rounded-2xl blur-xl" />
      <div className="relative bg-gray-900/80 backdrop-blur-xl rounded-2xl p-6 border border-gray-700/50 space-y-4">
        <h3 className="text-xl font-semibold text-white flex items-center gap-2">
          <span className="text-2xl">🎯</span>
          What You'll Get
        </h3>
        
        <div className="space-y-3">
          {[
            { emoji: "💎", text: "Access to Private Market Liquidity & Capital" },
            { emoji: "🔗", text: "Multi-Chain Smart Wallets (5+ Chains)" },
            { emoji: "⚡", text: "Sub-5s Settlement with 24/7 On-chain Payments" },
            { emoji: "📊", text: "Audited Accounts for Tokenized Assets" },
            { emoji: "🛡️", text: "Bank-Grade Security with Web3 Freedom" }
          ].map((item, idx) => (
            <div key={idx} className="flex items-center gap-3 p-3 bg-gray-800/30 rounded-xl hover:bg-gray-800/50 transition-all duration-300 hover:scale-[1.02]">
              <span className="text-2xl">{item.emoji}</span>
              <span className="text-gray-200 text-sm">{item.text}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
    
    {/* Action Button */}
    <button
      onClick={onNext}
      className="group relative w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 hover:from-blue-700 hover:via-purple-700 hover:to-pink-700 text-white font-semibold text-lg transition-all duration-300 transform hover:scale-[1.02] shadow-2xl shadow-blue-500/30 hover:shadow-blue-500/50 overflow-hidden"
    >
      <div className="absolute inset-0 animate-shimmer" />
      <span className="relative flex items-center justify-center gap-3">
        <span>Get Started</span>
        <ArrowRight className="h-5 w-5 group-hover:translate-x-2 transition-transform" />
      </span>
    </button>
  </div>
);

const IdentityStep = ({ onVerify, onSkip }: { onVerify: () => void; onSkip: () => void }) => (
  <div className="text-center space-y-6">
    {/* Animated Header */}
    <div className="relative mb-8">
      <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-yellow-500 via-orange-500 to-red-500 rounded-2xl flex items-center justify-center shadow-2xl shadow-orange-500/30 animate-glow">
        <Shield className="h-10 w-10 text-white" />
      </div>
      
      <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 flex items-center justify-center gap-2">
        <span className="text-3xl">🔐</span>
        Identity Verification
      </h2>
      <p className="text-gray-400">Unlock full Web3 platform access</p>
    </div>
    
    {/* Limits Comparison */}
    <div className="grid grid-cols-2 gap-4 mb-6">
      <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-xl p-4 border border-gray-700 relative overflow-hidden">
        <div className="absolute top-2 right-2 px-2 py-1 bg-gray-700 rounded-full text-xs">Basic</div>
        <div className="text-3xl font-bold text-blue-400 mb-2">$10K</div>
        <div className="text-xs text-gray-400 mb-3">Daily Limit</div>
        <div className="space-y-1 text-left">
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <span className="text-lg">👤</span>
            <span>Personal Use</span>
          </div>
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <span className="text-lg">🔄</span>
            <span>Basic Trading</span>
          </div>
        </div>
      </div>
      
      <div className="bg-gradient-to-br from-green-900/30 to-emerald-900/30 rounded-xl p-4 border border-green-500/50 relative overflow-hidden group hover:border-green-400/70 transition-colors">
        <div className="absolute top-2 right-2 px-2 py-1 bg-green-500/20 text-green-300 rounded-full text-xs">Pro</div>
        <div className="text-3xl font-bold text-green-400 mb-2">∞</div>
        <div className="text-xs text-gray-300 mb-3">Unlimited Access</div>
        <div className="space-y-1 text-left">
          <div className="flex items-center gap-2 text-green-300 text-sm">
            <span className="text-lg">🚀</span>
            <span>Full Platform</span>
          </div>
          <div className="flex items-center gap-2 text-green-300 text-sm">
            <span className="text-lg">💎</span>
            <span>All Features</span>
          </div>
        </div>
        <div className="absolute -bottom-4 -right-4 text-4xl opacity-10">⭐</div>
      </div>
    </div>
    
    {/* Benefits */}
    <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 rounded-xl p-4 border border-blue-500/20 backdrop-blur-sm">
      <div className="flex items-center justify-center gap-3 mb-3">
        <span className="text-2xl">⚡</span>
        <span className="text-sm text-gray-300">Instant Verification • 256-bit Encryption • Global Access</span>
        <span className="text-2xl">🌍</span>
      </div>
    </div>
    
    {/* Buttons */}
    <div className="space-y-3">
      <button
        onClick={onVerify}
        className="group w-full py-4 px-6 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold rounded-2xl transition-all duration-300 transform hover:scale-[1.02] shadow-2xl shadow-green-500/30"
      >
        <span className="flex items-center justify-center gap-3">
          <span className="text-xl">✅</span>
          <span>Verify Now (1 minute)</span>
        </span>
      </button>
      
      <button
        onClick={onSkip}
        className="w-full py-3 text-gray-400 hover:text-gray-300 rounded-2xl hover:bg-gray-800/50 transition-colors border border-gray-700 hover:border-gray-600"
      >
        <span className="flex items-center justify-center gap-2">
          <span>⏭️</span>
          <span>I'll Do This Later</span>
        </span>
      </button>
    </div>
  </div>
);

// ============================================================================
// ENHANCED MULTI-CHAIN WALLET STEP - WEB3 STYLE
// ============================================================================

const MultiChainWalletStep = ({ onComplete }: { onComplete: (wallets: any) => void }) => {
  const [creating, setCreating] = useState(false);
  const [wallets, setWallets] = useState<any>({});
  const [progress, setProgress] = useState(0);
  
  const chains = [
    { 
      id: 'algorand', 
      name: 'Algorand', 
      icon: Database, 
      color: 'from-blue-500 to-cyan-500',
      gradient: 'bg-gradient-to-br from-blue-600 to-cyan-600',
      emoji: '🔷',
      description: 'Enterprise Blockchain',
      index: 1
    },
    { 
      id: 'bitcoin', 
      name: 'Bitcoin', 
      icon: Bitcoin, 
      color: 'from-orange-500 to-yellow-500',
      gradient: 'bg-gradient-to-br from-orange-600 to-yellow-600',
      emoji: '🟠',
      description: 'Digital Gold',
      index: 2
    },
    { 
      id: 'ethereum', 
      name: 'Ethereum', 
      icon: Coins, 
      color: 'from-gray-400 to-slate-500',
      gradient: 'bg-gradient-to-br from-gray-600 to-slate-600',
      emoji: '⚫',
      description: 'Smart Contracts',
      index: 3
    },
    { 
      id: 'polygon', 
      name: 'Polygon', 
      icon: Layers, 
      color: 'from-purple-500 to-indigo-500',
      gradient: 'bg-gradient-to-br from-purple-600 to-indigo-600',
      emoji: '🟣',
      description: 'Layer 2 Scaling',
      index: 4
    },
    { 
      id: 'tron', 
      name: 'Tron', 
      icon: Zap, 
      color: 'from-red-500 to-pink-500',
      gradient: 'bg-gradient-to-br from-red-600 to-pink-600',
      emoji: '🔴',
      description: 'High Throughput',
      index: 5
    },
    { 
    id: 'solana', 
    name: 'Solana', 
    icon: Zap, 
    color: 'from-purple-400 to-pink-600',
    gradient: 'bg-gradient-to-br from-purple-500 to-pink-700',
    emoji: '🟣',
    description: 'Ultra-Fast Blockchain',
    index: 6
    }
  ];

  const createMultiChainWallets = async () => {
    setCreating(true);
    setProgress(0);
    
    // Simulate progressive creation
    const interval = setInterval(() => {
      setProgress(prev => Math.min(prev + 20, 100));
    }, 300);
    
    try {
      const response = await apiClient.post('/api/v1/wallet/create-multi-chain', {
        chains: ['algorand', 'bitcoin', 'ethereum', 'polygon', 'tron', 'solana']
      });

      if (response.data.success) {
        setWallets(response.data.wallets);
        setProgress(100);
        clearInterval(interval);
        
        toast.success('🚀 Multi-chain wallets created!', {
          duration: 3000,
          icon: '🎉'
        });
        
        // Auto-complete after successful creation
        setTimeout(() => {
          onComplete(response.data.wallets);
        }, 2000);
      }
    } catch (error: any) {
      console.error('Multi-chain wallet creation failed:', error);
      toast.error(error.response?.data?.error || 'Failed to create wallets', {
        icon: '❌'
      });
      clearInterval(interval);
    } finally {
      if (!wallets.algorand) {
        setCreating(false);
      }
    }
  };

  return (
    <div className="text-center space-y-6">
      {/* Header */}
      <div className="relative mb-6">
        <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-purple-600 via-pink-600 to-red-600 rounded-2xl flex items-center justify-center shadow-2xl shadow-purple-500/30">
          <Sparkles className="h-10 w-10 text-white" />
        </div>
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-2 flex items-center justify-center gap-2">
          <span className="text-3xl">🔗</span>
          Multi-Chain Wallets
        </h2>
        <p className="text-gray-400">Your unified access to Web3 ecosystems</p>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <div className="flex items-center justify-between text-sm text-gray-400 mb-2">
          <span>Setup Progress</span>
          <span>{progress}%</span>
        </div>
        <div className="w-full h-3 bg-gray-800 rounded-full overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Chain Cards Grid - RESPONSIVE & PROPERLY SIZED */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        {chains.map((chain) => {
          const Icon = chain.icon;
          const isCreated = wallets[chain.id];
          const isCreatingThis = creating && !isCreated;
          
          return (
            <div
              key={chain.id}
              className={`relative group ${chain.gradient} rounded-xl p-3 text-white transition-all duration-300 transform hover:scale-105 ${
                isCreated ? 'ring-2 ring-green-500/50 shadow-lg' : 'shadow-md'
              } hover:shadow-xl hover:shadow-purple-500/20`}
            >
              {/* Chain Index */}
              <div className="absolute -top-2 -left-2 w-6 h-6 bg-black/50 rounded-full flex items-center justify-center text-xs font-bold border border-white/20">
                {chain.index}
              </div>
              
              {/* Chain Icon */}
              <div className="flex flex-col items-center space-y-2">
                <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center group-hover:bg-white/30 transition-colors">
                  {isCreatingThis ? (
                    <Loader2 className="h-6 w-6 animate-spin" />
                  ) : isCreated ? (
                    <div className="text-2xl">{chain.emoji}</div>
                  ) : (
                    <Icon className="h-6 w-6" />
                  )}
                </div>
                
                <div className="text-center">
                  <div className="font-bold text-sm mb-0.5">{chain.name}</div>
                  <div className="text-xs opacity-80">{chain.description}</div>
                </div>
                
                {/* Status Badge */}
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                  isCreated 
                    ? 'bg-green-500/20 text-green-300 border border-green-500/30' 
                    : 'bg-white/10 text-white/80'
                }`}>
                  {isCreatingThis ? (
                    <span className="flex items-center">
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                      Creating
                    </span>
                  ) : isCreated ? (
                    <span className="flex items-center">
                      <Check className="h-3 w-3 mr-1" />
                      Ready
                    </span>
                  ) : (
                    'Waiting'
                  )}
                </div>
              </div>
              
              {/* Shimmer Effect for Creating */}
              {isCreatingThis && (
                <div className="absolute inset-0 animate-shimmer rounded-xl" />
              )}
            </div>
          );
        })}
      </div>

      {/* Status Overview */}
      <div className="bg-gradient-to-r from-gray-900/80 to-gray-800/80 rounded-xl p-4 mb-4 border border-gray-700/50 backdrop-blur-sm">
        <h4 className="font-semibold text-white mb-3 flex items-center gap-2">
          <span className="text-xl">📊</span>
          Chain Status Overview
        </h4>
        <div className="grid grid-cols-6 gap-2">
          {chains.map(chain => {
            const isCreated = wallets[chain.id];
            return (
              <div key={chain.id} className="text-center">
                <div className={`w-10 h-10 mx-auto rounded-xl flex items-center justify-center mb-2 text-lg ${
                  isCreated 
                    ? 'bg-green-500/20 border border-green-500/30' 
                    : 'bg-gray-700/50 border border-gray-600'
                }`}>
                  {isCreated ? '✅' : chain.emoji}
                </div>
                <div className="text-xs text-gray-400 font-medium">{chain.name.substring(0, 4)}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={createMultiChainWallets}
        disabled={creating || Object.keys(wallets).length === chains.length}
        className="group relative w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-purple-600 via-pink-600 to-red-600 hover:from-purple-700 hover:via-pink-700 hover:to-red-700 text-white font-semibold text-lg transition-all duration-300 transform disabled:opacity-50 disabled:cursor-not-allowed shadow-2xl shadow-purple-500/30 hover:shadow-purple-500/50 overflow-hidden"
      >
        <div className="absolute inset-0 animate-shimmer" />
        <span className="relative flex items-center justify-center gap-3">
          {creating ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>Creating Wallets ({Object.keys(wallets).length + 1}/{chains.length})...</span>
            </>
          ) : Object.keys(wallets).length === chains.length ? (
            <>
              <span className="text-xl">🎉</span>
              <span>All Wallets Created!</span>
            </>
          ) : (
            <>
              <Wallet className="h-5 w-5" />
              <span>Create Multi-Chain Wallets</span>
              <span className="text-xl opacity-80">🔗</span>
            </>
          )}
        </span>
      </button>

      {/* Success Message */}
      {Object.keys(wallets).length === chains.length && (
        <div className="animate-pulse-soft p-4 bg-gradient-to-r from-green-900/30 to-emerald-900/30 border border-green-500/30 rounded-xl">
          <div className="flex items-center justify-center gap-3 text-green-400">
            <span className="text-2xl">✨</span>
            <div>
              <div className="font-bold">All Systems Go!</div>
              <div className="text-sm text-green-300/70">Redirecting to your Web3 dashboard...</div>
            </div>
            <span className="text-2xl">✨</span>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// MAIN COMPONENT - MOBILE-FRIENDLY REDESIGN
// ============================================================================

const OnboardingPage = () => {
  const [step, setStep] = useState('welcome');
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

  const handleQuestionnaireComplete = async (data: any) => {
    const toastId = toast.loading('Saving your profile...');
    
    try {
      setUserAccountType(data.accountType);
      
      const profileData: any = {
        account_type: data.accountType,
        questionnaire_completed: true,
        questionnaire_completed_at: new Date().toISOString()
      };

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

      // ✅ REFRESH PROFILE to get latest data
      await refreshProfile();

      toast.success('🎯 Profile saved!', { id: toastId });
      setStep('identity');
      
    } catch (error: any) {
      console.error('Questionnaire save error:', error);
      toast.error('❌ Failed to save profile', { id: toastId });
    }
  };

  const handleQuestionnaireSkip = async () => {
    const toastId = toast.loading('Setting up individual account...');
    
    try {
      await apiClient.put('/api/v1/user/profile', {
        account_type: 'individual',
        questionnaire_completed: true,
        questionnaire_completed_at: new Date().toISOString()
      });
      
      setUserAccountType('individual');
      toast.success('👤 Individual account configured!', { id: toastId });
      setStep('identity');
    } catch (error: any) {
      console.error('Questionnaire skip error:', error);
      toast.error('❌ Failed to configure account', { id: toastId });
      setStep('identity');
    }
  };

  const handleStartVerification = () => {
    setShowBVNModal(true);
  };

  const handleBVNSubmit = async (formData: any) => {
    const toastId = toast.loading('Starting verification...');
    
    try {
      await apiClient.post('/api/v1/kyc/submit-kyc-data', {
        bvn: formData.idNumber,
        id_type: formData.idType,
        date_of_birth: formData.dateOfBirth,
        gender: formData.gender,
        phone: formData.phoneNumber,
        country_code: formData.country
      });

      const verifyResponse = await apiClient.post('/api/v1/kyc/start-verification');

      // Save compliance profile silently (powers WapiPay payment rails)
      try {
        await apiClient.post('/api/v1/user/compliance-profile', {
          id_type:        formData.idType,
          id_number:      formData.idNumber,
          date_of_birth:  formData.dateOfBirth,
          phone_number:   formData.phoneNumber,
          country_code:   formData.country,
          source_of_funds: 'Employment',
        });
      } catch (profileErr) {
        console.warn('Compliance profile save failed (non-fatal):', profileErr);
      }
      
      toast.success('✅ Verification submitted!', { id: toastId });
      setShowBVNModal(false);
      setStep('walletCreation');
      
    } catch (error: any) {
      console.error('KYC submission error:', error);
      toast.error('❌ Verification failed', { id: toastId });
      setShowBVNModal(false);
    }
  };

  const handleSkipVerification = async () => {
    try {
      const toastId = toast.loading('Skipping verification...');
      const response = await apiClient.post('/api/v1/kyc/skip-verification');
      
      if (response.data.success) {
        toast.success('⏭️ Verification skipped!', { id: toastId });
        setStep('walletCreation');
      }
    } catch (error: any) {
      console.error('Skip verification error:', error);
      toast.error('❌ Failed to skip verification');
    }
  };

  const handleWalletCreationComplete = async (wallets: any) => {
    const toastId = toast.loading('Finalizing setup...');
    
    try {
      await apiClient.put('/api/v1/user/profile', {
        kyc_level: userAccountType === 'business' ? 2 : 1,
        onboarding_complete: true,
        onboarding_completed_at: new Date().toISOString(),
        wallets_created: true
      });
      
      await refreshProfile();
      toast.success('🚀 Welcome to Seamount!', { id: toastId });
      setTimeout(() => navigate('/dashboard'), 1000);
    } catch (error) {
      console.error('Setup completion error:', error);
      toast.error('❌ Setup failed', { id: toastId });
    }
  };

  const progressPercentage = 
    step === 'welcome' ? '25%' : 
    step === 'questionnaire' ? '50%' :
    step === 'identity' ? '75%' : 
    step === 'walletCreation' ? '100%' : '100%';

  const stepTitles: { [key: string]: string } = {
    welcome: 'Welcome to Seamount',
    questionnaire: userAccountType === 'business' ? 'Business Profile' : 'Account Setup',
    identity: 'Identity Verification',
    walletCreation: 'Multi-Chain Setup'
  };

  const stepEmojis: { [key: string]: string } = {
    welcome: '🌊',
    questionnaire: userAccountType === 'business' ? '🏢' : '👤',
    identity: '🔐',
    walletCreation: '🔗'
  };

  return (
    <>
      <style>{shimmerEffect}</style>
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md md:max-w-lg lg:max-w-xl bg-gray-900/80 backdrop-blur-xl rounded-3xl shadow-2xl overflow-hidden border border-gray-700/50">
          {/* Progress Header */}
          <div className="relative p-6 border-b border-gray-700/50 bg-gradient-to-r from-gray-900/90 to-black/90">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                  <span className="text-xl">{stepEmojis[step]}</span>
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">{stepTitles[step]}</h2>
                  <div className="text-xs text-gray-400">
                    Step {['welcome', 'questionnaire', 'identity', 'walletCreation'].indexOf(step) + 1} of 4
                  </div>
                </div>
              </div>
              <div className="px-3 py-1 bg-gray-800/50 rounded-full text-xs font-medium border border-gray-700">
                {userAccountType ? userAccountType.toUpperCase() : 'SETUP'}
              </div>
            </div>
            
            {/* Animated Progress Bar */}
            <div className="relative">
              <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full transition-all duration-700 ease-out"
                  style={{ width: progressPercentage }}
                />
              </div>
              <div className="absolute -bottom-1 left-0 w-2 h-2 bg-white rounded-full animate-glow" 
                style={{ left: `calc(${progressPercentage} - 4px)` }} />
            </div>
          </div>
          
          {/* Main Content */}
          <div className="p-6 md:p-8">
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
          
          {/* Navigation Footer */}
          {step !== 'welcome' && step !== 'walletCreation' && (
            <div className="p-4 border-t border-gray-700/30 bg-black/30">
              <button
                onClick={() => {
                  if (step === 'identity') setStep('questionnaire');
                  else if (step === 'questionnaire') setStep('welcome');
                }}
                className="flex items-center gap-2 text-gray-400 hover:text-white px-4 py-2 rounded-lg hover:bg-gray-800/50 transition-colors group"
              >
                <ArrowLeft className="h-4 w-4 group-hover:-translate-x-1 transition-transform" />
                <span>Back</span>
              </button>
            </div>
          )}
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
    </>
  );
};

export default OnboardingPage;