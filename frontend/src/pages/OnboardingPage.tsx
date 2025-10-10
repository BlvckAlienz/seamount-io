import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '../config/api';
import toast from 'react-hot-toast';
import { Eye, EyeOff, Copy, Shield, Wallet, CheckCircle, Globe, Lock, Download, Check, AlertCircle } from 'lucide-react';
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
const IdentityStep = ({ onNext, onPrev, userProfile }) => {
  const [loading, setLoading] = useState(false);
  const [showBVNModal, setShowBVNModal] = useState(false);
  
  const isNigerianUser = userProfile?.country_code === 'NG' || userProfile?.country === 'NG';
  const hasBVN = userProfile?.bvn && userProfile?.date_of_birth && userProfile?.gender;

const startVerification = async () => {
  setLoading(true);
  
  try {
    const { data } = await apiClient.post('/api/v1/kyc/start-verification');
    
    if (data.success) {
      toast.success('Verification started!');
      onNext();
    } else {
      throw new Error(data.message || 'Verification failed');
    }
  } catch (error: any) {
    if (error.response?.status === 400) {
      const errorDetail = error.response?.data?.detail;
      const errorType = typeof errorDetail === 'object' ? errorDetail.type : null;
      const errorMessage = typeof errorDetail === 'object' ? errorDetail.message : errorDetail;
      
      if (errorType === 'missing_bvn') {
        // Nigerian user missing BVN data
        toast.error('BVN verification required for Nigerian users');
        setShowBVNModal(true);
      } else if (errorType === 'profile_incomplete') {
        // Generic profile incomplete
        const missingFields = errorDetail.missing_fields || [];
        toast.error(`Please complete: ${missingFields.join(', ')}`);
        // TODO: Show inline profile editor or redirect to profile page
      } else {
        // Generic 400 error
        toast.error(errorMessage || 'Please complete your profile before verification');
      }
    } else if (error.response?.status === 500) {
      const errorDetail = error.response?.data?.detail;
      const errorMessage = typeof errorDetail === 'object' ? errorDetail.message : errorDetail;
      toast.error(errorMessage || 'Verification service temporarily unavailable');
    } else {
      toast.error('Verification failed: ' + (error.response?.data?.detail?.message || error.message));
    }
  } finally {
    setLoading(false);
  }
};

  const handleBVNComplete = async (bvnData) => {
    setShowBVNModal(false);
    toast.success('Information saved! Starting verification...');
    setTimeout(() => startVerification(), 1000);
  };

  const handleSkip = () => {
    toast('You can verify later from Settings');
    onNext();
  };

  if (showBVNModal && isNigerianUser) {
    return (
      <BVNCollectionModal
        onComplete={handleBVNComplete}
        onCancel={() => setShowBVNModal(false)}
        userEmail={userProfile?.email || ''}
      />
    );
  }

  return (
    <div className="text-center">
      <div className="mb-6">
        <div className="w-16 h-16 bg-gradient-to-br from-yellow-500 to-orange-600 rounded-full flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Shield className="h-8 w-8 text-white" />
        </div>
        <h3 className="text-2xl font-semibold text-white mb-2">Verify Your Identity</h3>
        <p className="text-gray-400">Unlock full platform features with quick verification</p>
      </div>
      
      {isNigerianUser && !hasBVN && (
        <div className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-4 mb-6 text-left">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-blue-300 text-sm font-medium mb-1">Nigerian User - Fast Track</p>
              <p className="text-gray-300 text-xs">
                You'll be prompted for your BVN, date of birth, and gender for instant verification via Regfyl.
              </p>
            </div>
          </div>
        </div>
      )}
      
      <div className="bg-blue-900/20 p-5 rounded-xl text-left border border-blue-500/30 mb-6">
        <h4 className="font-medium text-blue-300 mb-3">Why We Verify</h4>
        <ul className="text-sm text-gray-300 space-y-2">
          {[
            "Comply with global financial regulations",
            "Protect your account from fraud",
            "Enable higher transaction limits",
            "Access institutional features"
          ].map(item => (
            <li key={item} className="flex items-start">
              <CheckCircle className="h-4 w-4 text-blue-400 mr-2 mt-0.5 flex-shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
      
      <div className="space-y-3">
        <button
          onClick={startVerification}
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold py-4 px-6 rounded-xl transition-all disabled:opacity-50 shadow-lg"
        >
          {loading ? 'Checking profile...' : 'Start Verification'}
        </button>
        
        <button
          onClick={handleSkip}
          className="w-full text-gray-400 hover:text-gray-300 py-3 rounded-xl hover:bg-gray-800/50 transition-colors"
        >
          I'll Do This Later
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

// Wallet Backup Step
const WalletBackupStep = ({ onNext, onPrev, mnemonic }) => {
  const [showMnemonic, setShowMnemonic] = useState(false);
  const [copied, setCopied] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verificationWords, setVerificationWords] = useState([]);
  const [userInputs, setUserInputs] = useState({});
  
  const words = mnemonic.split(' ');

  useEffect(() => {
    const positions = [];
    while (positions.length < 3) {
      const pos = Math.floor(Math.random() * 25);
      if (!positions.includes(pos)) positions.push(pos);
    }
    setVerificationWords(positions.sort((a, b) => a - b));
  }, []);

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

  const verifyWords = () => {
    const allCorrect = verificationWords.every(pos => 
      userInputs[pos]?.toLowerCase().trim() === words[pos].toLowerCase()
    );
    
    if (allCorrect) {
      toast.success('Verification successful!');
      onNext();
    } else {
      toast.error('Incorrect words. Please check and try again.');
    }
  };

  if (verifying) {
    return (
      <div className="text-left">
        <div className="text-center mb-6">
          <Check className="h-12 w-12 text-green-400 mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-white mb-2">Verify Your Phrase</h3>
          <p className="text-gray-400">Enter these words to confirm you saved it</p>
        </div>

        <div className="space-y-4 mb-6">
          {verificationWords.map(pos => (
            <div key={pos}>
              <label className="block text-sm text-gray-400 mb-2">
                Word #{pos + 1}
              </label>
              <input
                type="text"
                value={userInputs[pos] || ''}
                onChange={(e) => setUserInputs({ ...userInputs, [pos]: e.target.value })}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none"
                placeholder="Enter word"
              />
            </div>
          ))}
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => setVerifying(false)}
            className="flex-1 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors"
          >
            â† Back
          </button>
          <button
            onClick={verifyWords}
            className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white py-3 px-4 rounded-lg transition-all shadow-lg"
          >
            Verify & Complete
          </button>
        </div>
      </div>
    );
  }

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
          {words.map((word, index) => (
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
          onClick={() => setVerifying(true)}
          disabled={!showMnemonic}
          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white font-semibold py-4 px-6 rounded-xl transition-all disabled:opacity-50 shadow-lg"
        >
          I've Backed It Up â†’
        </button>
        
        {onPrev && (
          <button 
            onClick={onPrev}
            className="w-full text-gray-500 py-2 text-sm hover:text-gray-400"
          >
            â† Back
          </button>
        )}
      </div>
    </div>
  );
};

// Main Component
const OnboardingPage = () => {
  const [step, setStep] = useState('welcome');
  const [mnemonic, setMnemonic] = useState(null);
  const [detectedCountry, setDetectedCountry] = useState(null);
  const { completeOnboarding, userProfile } = useAuth();
  const navigate = useNavigate();

  // Redirect if already verified
  useEffect(() => {
    if (userProfile?.kyc_status === 'verified') {
      navigate('/dashboard');
    }
  }, [userProfile, navigate]);

  const handleWelcomeComplete = () => setStep('identity');

  const handleIdentityComplete = async () => {
    const toastId = toast.loading('Creating your wallet...');
    
    try {
      // Save detected country
      if (detectedCountry) {
        localStorage.setItem('user_country', detectedCountry.code);
      }
      
      const response = await apiClient.post('/api/v1/user/provision-wallets');
      
      if (response.data.success && response.data.mnemonic) {
        toast.success('Wallet created!', { id: toastId });
        setMnemonic(response.data.mnemonic);
        setStep('walletBackup');
      } else {
        throw new Error('No mnemonic returned');
      }
    } catch (error) {
      console.error('Wallet creation error:', error);
      toast.error('Could not create wallet. Proceeding to dashboard.', { id: toastId });
      await completeOnboarding();
    }
  };

  const handleBackupComplete = async () => {
    await completeOnboarding();
  };

  const handleStepBack = () => {
    if (step === 'walletBackup') setStep('identity');
    else if (step === 'identity') setStep('welcome');
  };

  const progressPercentage = 
    step === 'welcome' ? '33%' : 
    step === 'identity' ? '66%' : '100%';

  const stepTitles = {
    welcome: 'Welcome to Seamount',
    identity: 'Identity Verification', 
    walletBackup: 'Wallet Backup'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-gray-800/50 backdrop-blur-xl rounded-2xl shadow-2xl overflow-hidden border border-gray-700">
        <div className="bg-gray-900/50 border-b border-gray-700 p-6">
          <div className="flex justify-between items-center text-sm text-gray-400 mb-3">
            <h2 className="font-semibold text-lg text-white">{stepTitles[step]}</h2>
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
              onNext={handleIdentityComplete} 
              onPrev={handleStepBack} 
              userProfile={userProfile}
            />
          ) : mnemonic ? (
            <WalletBackupStep onNext={handleBackupComplete} onPrev={handleStepBack} mnemonic={mnemonic} />
          ) : (
            <div className="text-center p-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-400">Creating your wallet...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OnboardingPage;