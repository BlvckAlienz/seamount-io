// File: frontend/src/pages/OnboardingPage.tsx
// FINAL PRODUCTION VERSION - Fixed onboarding recognition

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../config/api';
import toast from 'react-hot-toast';
import { Shield, Wallet, CheckCircle, Globe, Lock, Download, Check, Copy, Eye, EyeOff } from 'lucide-react';
import BVNCollectionModal from '../components/onboarding/BVNCollectionModal';

// Welcome Step
const WelcomeStep = ({ onNext }) => (
  <div className="text-center">
    <div className="mb-8">
      <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
        <Globe className="h-10 w-10 text-white" />
      </div>
      <h3 className="text-2xl font-bold mb-3 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
        Welcome to Seamount
      </h3>
      <p className="text-gray-400 text-lg">
        The future of cross-border payments is here
      </p>
    </div>
    
    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 rounded-xl p-6 mb-8 text-left border border-blue-500/30">
      <h4 className="font-semibold text-white mb-4 flex items-center">
        <CheckCircle className="h-5 w-5 text-blue-400 mr-2" />
        What You'll Get
      </h4>
      <div className="space-y-3 text-gray-300">
        {[
          "Multi-asset wallet (ALGO, USDT, USDCa, goBTC, goETH)",
          "Sub-5-second settlement on Algorand",
          "Cross-border transfers at 2.9% (vs 7% traditional)",
          "Bank-grade security with Web3 benefits"
        ].map(item => (
          <div key={item} className="flex items-start">
            <CheckCircle className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5" />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
    
    <button
      onClick={onNext}
      className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all transform hover:scale-105 shadow-lg"
    >
      Get Started
    </button>
  </div>
);

// Identity Verification Step
const IdentityStep = ({ onVerify, onSkip, onPrev }) => {
  return (
    <div className="text-center">
      <div className="mb-6">
        <div className="w-16 h-16 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Shield className="h-8 w-8 text-white" />
        </div>
        <h3 className="text-2xl font-semibold text-white mb-2">Verify Your Identity</h3>
        <p className="text-gray-400">Unlock full platform features</p>
      </div>
      
      <div className="space-y-3">
        <button
          onClick={onVerify}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all shadow-lg"
        >
          Start Verification
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
};

// Wallet Backup Step
const WalletBackupStep = ({ onNext, onPrev, mnemonic }) => {
  const [showMnemonic, setShowMnemonic] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(mnemonic);
    setCopied(true);
    toast.success('Recovery phrase copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadBackup = () => {
    const blob = new Blob([
      `Seamount Wallet Recovery Phrase\n\n`,
      `KEEP THIS SAFE! Never share with anyone.\n\n`,
      `Recovery Phrase:\n${mnemonic}\n\n`,
      `Created: ${new Date().toISOString()}`
    ], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'seamount-recovery-phrase.txt';
    a.click();
    toast.success('Recovery phrase downloaded!');
  };

  return (
    <div className="text-left">
      <div className="text-center mb-6">
        <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Wallet className="h-8 w-8 text-white" />
        </div>
        <h3 className="text-2xl font-bold text-white mb-2">Back Up Your Wallet</h3>
        <p className="text-gray-400">This is your master key. Store it safely offline.</p>
      </div>
      
      <div className="relative border border-gray-700 rounded-xl p-5 mb-4 bg-gray-900/50">
        <div className={`grid grid-cols-3 gap-2 text-gray-300 ${!showMnemonic ? 'blur-sm' : ''}`}>
          {mnemonic.split(' ').map((word, index) => (
            <div key={index} className="flex items-center bg-gray-800/50 rounded px-3 py-2 text-sm">
              <span className="text-gray-500 w-6">{index + 1}.</span>
              <span className="font-mono">{word}</span>
            </div>
          ))}
        </div>
        {!showMnemonic && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/90 rounded-xl">
            <button
              onClick={() => setShowMnemonic(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg transition-colors"
            >
              <Eye className="h-5 w-5" />
              Reveal Phrase
            </button>
          </div>
        )}
      </div>

      <div className="flex gap-3 mb-6">
        <button 
          onClick={handleCopy} 
          disabled={!showMnemonic}
          className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-lg border transition-colors ${
            copied 
              ? "bg-green-900/20 border-green-500 text-green-400" 
              : "border-gray-700 text-gray-300 hover:bg-gray-800"
          }`}
        >
          {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          {copied ? "Copied!" : "Copy"}
        </button>
        <button 
          onClick={downloadBackup}
          disabled={!showMnemonic}
          className="flex-1 flex items-center justify-center gap-2 border border-gray-700 text-gray-300 py-3 rounded-lg hover:bg-gray-800 transition-colors"
        >
          <Download className="h-4 w-4" />
          Download
        </button>
      </div>

      <div className="bg-red-900/20 border-l-4 border-red-500 text-red-300 p-4 rounded-r-lg mb-6">
        <div className="flex items-start gap-3">
          <Lock className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-bold mb-1">Never Lose This Phrase</p>
            <p className="text-sm">Seamount cannot recover your wallet. You are in full control.</p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        <button 
          onClick={onNext}
          disabled={!showMnemonic}
          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold py-4 px-6 rounded-xl transition-all disabled:opacity-50 shadow-lg"
        >
          I've Backed It Up - Complete Setup
        </button>
        
        {onPrev && (
          <button 
            onClick={onPrev}
            className="w-full text-gray-500 py-2 text-sm hover:text-gray-400"
          >
            Back
          </button>
        )}
      </div>
    </div>
  );
};

// Main Onboarding Component - PRODUCTION READY
const OnboardingPage = () => {
  const [step, setStep] = useState('welcome');
  const [mnemonic, setMnemonic] = useState(null);
  const [showBVNModal, setShowBVNModal] = useState(false);
  const { userProfile, refreshProfile } = useAuth();
  const navigate = useNavigate();

  // ✅ FIXED: Check if user should even be in onboarding
  useEffect(() => {
    const checkOnboardingStatus = async () => {
      if (!userProfile?.id) return;

      try {
        // Check if user already completed onboarding
        if (userProfile.onboarding_complete) {
          console.log('✅ User already completed onboarding - redirecting to dashboard');
          navigate('/dashboard');
          return;
        }

        // Check for existing wallet
        try {
          const walletResponse = await apiClient.get('/api/v1/user/wallet-info');
          if (walletResponse.data.wallet_exists) {
            console.log('✅ Wallet exists but onboarding not complete - marking complete');
            // User has wallet but onboarding not marked complete
            await apiClient.put('/api/v1/user/profile', {
              onboarding_complete: true
            });
            await refreshProfile();
            navigate('/dashboard');
            return;
          }
        } catch (walletError) {
          console.log('Wallet check failed, continuing with onboarding');
        }

      } catch (error) {
        console.error('Onboarding status check failed:', error);
        // Continue with normal onboarding flow
      }
    };

    checkOnboardingStatus();
  }, [userProfile, navigate, refreshProfile]);

  const handleWelcomeComplete = () => setStep('identity');

  const handleStartVerification = () => {
    setShowBVNModal(true);
  };

  // ✅ FIXED KYC Submission - Using YOUR working logic
  const handleBVNSubmit = async (formData) => {
    const toastId = toast.loading('Starting verification...');
    const isNigerian = formData.country === 'NG';
    
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

      // 2. YOUR WORKING APPROACH: Handle different verification pathways
      try {
        const verifyResponse = await apiClient.post('/api/v1/kyc/start-verification');
        
        if (verifyResponse.data.alien_pathway || verifyResponse.data.status === 'pending_support') {
          // Handle non-Nigerian users gracefully
          toast.dismiss(toastId);
          toast('🔄 ID verification for your country is coming soon', { 
            duration: 6000,
            icon: '🧩'
          });
          
          // STILL CREATE WALLET even if KYC is limited
          const walletResponse = await apiClient.post('/api/v1/user/provision-wallets');
          if (walletResponse.data.success && walletResponse.data.mnemonic) {
            toast.success('Wallet created!');
            setMnemonic(walletResponse.data.mnemonic);
            setShowBVNModal(false);
            setStep('walletBackup');
            return;
          }
        }
        
        // Nigerian user flow
        toast.success('Verification submitted!', { id: toastId });
        toast('🎉 Our team will review within 24 hours', { duration: 5000, icon: '⏰' });

        const walletResponse = await apiClient.post('/api/v1/user/provision-wallets');
        if (walletResponse.data.success && walletResponse.data.mnemonic) {
          setMnemonic(walletResponse.data.mnemonic);
          setShowBVNModal(false);
          setStep('walletBackup');
        }
        
      } catch (verifyError) {
        console.error('Verification error:', verifyError);
        
        const is500Error = verifyError.response?.status === 500;
        const errorDetail = verifyError.response?.data?.detail || '';
        const isRegfylError = errorDetail.includes('Regfyl') || errorDetail.includes('service unavailable');
        
        if (!isNigerian && is500Error && isRegfylError) {
          // Graceful fallback for international users
          toast.dismiss(toastId);
          toast('🔄 ID verification for your country is coming soon', { 
            duration: 6000,
            icon: '🧩'
          });
          
          try {
            const walletResponse = await apiClient.post('/api/v1/user/provision-wallets');
            if (walletResponse.data.success && walletResponse.data.mnemonic) {
              toast.success('Wallet created!');
              setMnemonic(walletResponse.data.mnemonic);
              setShowBVNModal(false);
              setStep('walletBackup');
              return;
            }
          } catch (walletError) {
            console.error('Wallet creation failed:', walletError);
            toast.error('Wallet creation failed. Please contact support.');
            setShowBVNModal(false);
            return;
          }
        }
        
        toast.error(errorDetail || 'Verification failed', { id: toastId });
        setShowBVNModal(false);
      }
      
    } catch (error) {
      console.error('KYC submission error:', error);
      toast.error(error.response?.data?.detail || 'Failed to submit KYC data', { id: toastId });
      setShowBVNModal(false);
    }
  };

  // ✅ FIXED Skip Flow - NO Regfyl call
  const handleSkipVerification = async () => {
    const toastId = toast.loading('Setting up your wallet...');
    
    try {
      await apiClient.post('/api/v1/kyc/skip-verification');
      const walletResponse = await apiClient.post('/api/v1/user/provision-wallets');
      
      if (walletResponse.data.success && walletResponse.data.mnemonic) {
        toast.success('Wallet created!', { id: toastId });
        setMnemonic(walletResponse.data.mnemonic);
        setStep('walletBackup');
      } else {
        throw new Error('Wallet creation failed');
      }
    } catch (error) {
      console.error('Skip error:', error);
      toast.error('Failed to create wallet', { id: toastId });
    }
  };

  // ✅ FIXED Backup Complete
  const handleBackupComplete = async () => {
    const toastId = toast.loading('Completing setup...');
    
    try {
      await apiClient.put('/api/v1/user/profile', {
        onboarding_complete: true
      });
      
      await refreshProfile();
      toast.success('Welcome to Seamount!', { id: toastId });
      navigate('/dashboard');
      
    } catch (error) {
      console.error('Backup error:', error);
      toast.error('Setup failed', { id: toastId });
    }
  };

  const handleStepBack = () => {
    if (step === 'walletBackup') setStep('identity');
    else if (step === 'identity') setStep('welcome');
  };

  const progressPercentage = 
    step === 'welcome' ? '33%' : 
    step === 'identity' ? '66%' : '100%';

  if (!userProfile) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-gray-800/50 backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden border border-gray-700">
        <div className="bg-gray-900/50 border-b border-gray-700 p-6">
          <div className="flex justify-between items-center text-sm text-gray-400 mb-3">
            <h2 className="font-semibold text-lg text-white">
              {step === 'welcome' ? 'Welcome to Seamount' : 
               step === 'identity' ? 'Identity Verification' : 
               'Wallet Backup'}
            </h2>
            <span>
              {step === 'welcome' ? '1 of 3' : 
               step === 'identity' ? '2 of 3' : '3 of 3'}
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
              onPrev={handleStepBack}
            />
          ) : mnemonic ? (
            <WalletBackupStep onNext={handleBackupComplete} onPrev={handleStepBack} mnemonic={mnemonic} />
          ) : (
            <div className="text-center p-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-400">Processing...</p>
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
    </div>
  );
};

export default OnboardingPage;