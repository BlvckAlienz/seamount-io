import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, API_ENDPOINTS } from '../config/api';
import toast from 'react-hot-toast';
import { Eye, EyeOff, Copy, ArrowLeft, Shield, Wallet, CheckCircle } from 'lucide-react';
import Button from '../components/ui/Button';

// Make sure ComplyCube is declared on the window object
declare global {
  interface Window {
    ComplyCube?: {
      mount: (options: any) => { mount: (selector: string) => void };
    };
  }
}

// --- Step Interfaces ---
interface StepProps {
  onNext: (data?: any) => void;
  stepData: any;
}

// --- STEP 1: Identity Verification ---
const IdentityStep: React.FC<StepProps> = ({ onNext }) => {
  const [loading, setLoading] = useState(false);
  const [sdkInitialized, setSdkInitialized] = useState(false);
  const { completeOnboarding } = useAuth();

 const startVerification = async () => {
  setLoading(true);
  try {
    // FIXED: Use the correct API endpoint that matches backend routing
    const { data } = await apiClient.post<{ token: string }>(
      "/api/v1/kyc/start-verification"  // Matches backend router prefix
    );
    
    if (window.ComplyCube) {
      const session = window.ComplyCube.mount({
        token: data.token,
        onComplete: () => {
          toast.success('Verification completed!');
          onNext();
        },
        onError: (error: any) => {
          toast.error('Verification failed: ' + error.message);
          setLoading(false);
        }
      });
      session.mount('#complycube-mount');
      setSdkInitialized(true);
    }
  } catch (error: any) {
    toast.error('Failed to start verification: ' + error.message);
    setLoading(false);
  }
};
  
  const handleSkip = async () => {
    toast('You can complete verification later from your settings.');
    await completeOnboarding();
  };

  return (
    <div className="text-center">
      <div className="mb-6">
        <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <Shield className="h-8 w-8 text-blue-600" />
        </div>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">Verify Your Identity</h3>
        <p className="text-gray-600">For your security, we need to confirm you're you. This unlocks all platform features.</p>
      </div>
      
      {sdkInitialized ? (
        <div id="complycube-mount" style={{ minHeight: '450px' }} className="w-full"></div>
      ) : (
        <div className="space-y-4">
          <div className="bg-blue-50 p-4 rounded-lg text-left">
            <h4 className="font-medium text-blue-800 mb-2">Why we verify identity:</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li className="flex items-start">
                <CheckCircle className="h-4 w-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" />
                <span>Comply with financial regulations</span>
              </li>
              <li className="flex items-start">
                <CheckCircle className="h-4 w-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" />
                <span>Protect your account from fraud</span>
              </li>
              <li className="flex items-start">
                <CheckCircle className="h-4 w-4 text-blue-500 mr-2 mt-0.5 flex-shrink-0" />
                <span>Enable higher transaction limits</span>
              </li>
            </ul>
          </div>
          
          <Button
            onClick={startVerification}
            loading={loading}
            className="w-full bg-blue-600 hover:bg-blue-700"
          >
            Start Secure Verification
          </Button>
          <button
            onClick={handleSkip}
            className="w-full text-sm text-gray-600 py-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            I'll Do This Later
          </button>
        </div>
      )}
    </div>
  );
};

// --- STEP 2: Wallet Backup (Self-Custody) ---
const WalletBackupStep: React.FC<StepProps & { mnemonic: string }> = ({ onNext, mnemonic }) => {
    const [showMnemonic, setShowMnemonic] = useState(false);
    const [copied, setCopied] = useState(false);
    const words = mnemonic.split(' ');

    const handleCopy = () => {
        navigator.clipboard.writeText(mnemonic);
        setCopied(true);
        toast.success('Mnemonic phrase copied to clipboard!');
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="text-left">
            <div className="mb-6 text-center">
                <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <Wallet className="h-8 w-8 text-purple-600" />
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-2">Back Up Your Wallet</h3>
                <p className="text-gray-600">This is your master key. Write it down and store it somewhere safe.</p>
            </div>
            
            <div className="relative border border-gray-200 rounded-lg p-4 mb-4 bg-gray-50">
                <div className={`grid grid-cols-3 gap-2 text-gray-800 ${!showMnemonic ? 'blur-sm' : ''}`}>
                    {words.map((word, index) => (
                        <div key={index} className="flex items-center">
                            <span className="text-gray-400 w-6 text-sm">{index + 1}.</span>
                            <span>{word}</span>
                        </div>
                    ))}
                </div>
                {!showMnemonic && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/90 rounded-lg">
                         <Button onClick={() => setShowMnemonic(true)} icon={Eye}>Reveal Phrase</Button>
                    </div>
                )}
            </div>

            <div className="flex justify-center gap-4 mb-6">
                 <Button 
                   onClick={handleCopy} 
                   variant="secondary" 
                   icon={Copy} 
                   disabled={!showMnemonic}
                   className={copied ? "bg-green-100 text-green-800 border-green-200" : ""}
                 >
                     {copied ? "Copied!" : "Copy"}
                 </Button>
                 <Button 
                   onClick={() => setShowMnemonic(!showMnemonic)} 
                   variant="secondary" 
                   icon={showMnemonic ? EyeOff : Eye}
                 >
                     {showMnemonic ? 'Hide' : 'Reveal'}
                 </Button>
            </div>

            <div className="bg-red-50 border-l-4 border-red-400 text-red-800 p-4 rounded-r-lg mb-6">
                <p className="font-bold">Do NOT lose this phrase.</p>
                <p className="text-sm">Seamount cannot recover your wallet if you lose your mnemonic. You are in control.</p>
            </div>

            <Button 
              onClick={() => onNext()} 
              disabled={!showMnemonic} 
              className="w-full bg-purple-600 hover:bg-purple-700"
            >
                I've Backed It Up, Continue
            </Button>
        </div>
    );
};

// --- Main Onboarding Component ---
const OnboardingPage: React.FC = () => {
  const [step, setStep] = useState<'identity' | 'walletBackup'>('identity');
  const [mnemonic, setMnemonic] = useState<string | null>(null);
  const { completeOnboarding, triggerWalletCreation, userProfile } = useAuth();
  const navigate = useNavigate();

  // Load ComplyCube SDK when the component mounts
  useEffect(() => {
    const scriptId = 'complycube-sdk';
    if (document.getElementById(scriptId)) return; // Already loaded

    const script = document.createElement('script');
    script.id = scriptId;
    script.src = "https://assets.complycube.com/web-sdk/v1/complycube.min.js";
    script.async = true;
    script.onload = () => console.log('ComplyCube SDK loaded.');
    script.onerror = () => toast.error('Could not load verification service. Please refresh.');
    document.body.appendChild(script);

    return () => {
      const sdkScript = document.getElementById(scriptId);
      if (sdkScript) document.body.removeChild(sdkScript);
    };
  }, []);
  
  // Add this useEffect for smart redirects
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    
    if (message === 'verify_to_access') {
      toast('Please complete verification to access this feature');
    }
    
    // Check if user is already verified
    if (userProfile?.kyc_status === 'verified') {
      navigate('/dashboard');
    }
  }, [userProfile, navigate]);

  const handleIdentityComplete = async () => {
    const toastId = toast.loading('Creating your secure wallet...');
    const { success, mnemonic: receivedMnemonic } = await triggerWalletCreation();

    if (success && receivedMnemonic) {
        toast.success('Wallet created! Please back up your recovery phrase.', { id: toastId });
        setMnemonic(receivedMnemonic);
        setStep('walletBackup');
    } else {
        toast.error('Could not create your wallet. You can try again later from your settings.', { id: toastId });
        await completeOnboarding();
    }
  };

  const handleBackupComplete = async () => {
      await completeOnboarding();
  };

  const progressPercentage = step === 'identity' ? '50%' : '100%';

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Progress Header */}
        <div className="bg-white border-b border-gray-200 p-6">
          <div className="flex justify-between items-center text-sm text-gray-500 mb-2">
            <h2 className="font-semibold text-lg text-gray-900">
              {step === 'identity' ? 'Identity Verification' : 'Wallet Backup'}
            </h2>
            <span>{step === 'identity' ? '1 of 2' : '2 of 2'}</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-in-out"
              style={{ width: progressPercentage }}
            />
          </div>
        </div>
        
        {/* Step Content */}
        <div className="p-6 md:p-8">
          {step === 'identity' ? (
            <IdentityStep onNext={handleIdentityComplete} stepData={{}} />
          ) : mnemonic ? (
            <WalletBackupStep onNext={handleBackupComplete} stepData={{}} mnemonic={mnemonic} />
          ) : (
            <div className="text-center p-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Creating your wallet...</p>
            </div>
          )}
        </div>
        
        {/* Back Button */}
        {step === 'walletBackup' && (
          <div className="px-6 pb-6">
            <button
              onClick={() => setStep('identity')}
              className="flex items-center text-sm text-gray-600 hover:text-gray-900"
            >
              <ArrowLeft className="h-4 w-4 mr-1" />
              Back to verification
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default OnboardingPage;