import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiClient, API_ENDPOINTS } from '../config/api';
import toast from 'react-hot-toast';
import { Eye, EyeOff, Copy, ArrowLeft } from 'lucide-react';
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
    const toastId = toast.loading('Initializing secure verification...');

    if (!window.ComplyCube) {
      toast.error('Verification service failed to load. Please refresh and try again.', { id: toastId });
      setLoading(false);
      return;
    }

    try {
      const { data } = await apiClient.post<{ token: string }>(API_ENDPOINTS.KYC.START_VERIFICATION);
      if (!data.token) throw new Error("Verification token was not provided by the server.");

      toast.success('Starting verification...', { id: toastId });
      setSdkInitialized(true);
      
      // ComplyCube's mount returns an object with another mount method
      const session = window.ComplyCube.mount({
        token: data.token,
        onComplete: (data: any) => {
          console.log('KYC Verification complete:', data);
          toast.success('Identity verification submitted successfully!');
          onNext();
        },
        onError: (error: any) => {
          console.error('ComplyCube SDK error:', error);
          toast.error('Verification failed. You can skip and try again later.');
          setSdkInitialized(false);
          setLoading(false);
        }
      });
      session.mount('#complycube-mount');

    } catch (error: any) {
      console.error('Failed to start verification flow:', error);
      const errorMsg = error.response?.data?.detail || 'Could not start verification.';
      toast.error(`Error: ${errorMsg}`, { id: toastId });
      setSdkInitialized(false);
      setLoading(false);
    }
  };
  
  const handleSkip = async () => {
    toast('You can complete verification later from your settings.');
    await completeOnboarding();
  };

  return (
    <div className="text-center">
      <h3 className="text-xl font-semibold mb-2">Verify Your Identity</h3>
      <p className="text-gray-600 mb-6">For your security, we need to confirm you're you. This unlocks all platform features.</p>
      
      {sdkInitialized ? (
        <div id="complycube-mount" style={{ minHeight: '450px' }} className="w-full"></div>
      ) : (
        <div className="space-y-4">
          <Button
            onClick={startVerification}
            loading={loading}
            className="w-full"
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
    const words = mnemonic.split(' ');

    const handleCopy = () => {
        navigator.clipboard.writeText(mnemonic);
        toast.success('Mnemonic phrase copied to clipboard!');
    };

    return (
        <div className="text-left">
            <h3 className="text-xl font-semibold mb-2 text-center">Back Up Your Wallet</h3>
            <p className="text-gray-600 mb-6 text-center">This is your master key. Write it down and store it somewhere safe.</p>
            
            <div className="relative border border-gray-200 rounded-lg p-4 mb-4">
                <div className={`grid grid-cols-3 gap-2 text-gray-800 ${!showMnemonic ? 'blur-sm' : ''}`}>
                    {words.map((word, index) => (
                        <div key={index} className="flex items-center">
                            <span className="text-gray-400 w-6 text-sm">{index + 1}.</span>
                            <span>{word}</span>
                        </div>
                    ))}
                </div>
                {!showMnemonic && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/80">
                         <Button onClick={() => setShowMnemonic(true)} icon={Eye}>Reveal Phrase</Button>
                    </div>
                )}
            </div>

            <div className="flex justify-center gap-4 mb-6">
                 <Button onClick={handleCopy} variant="secondary" icon={Copy} disabled={!showMnemonic}>Copy</Button>
                 <Button onClick={() => setShowMnemonic(!showMnemonic)} variant="secondary" icon={showMnemonic ? EyeOff : Eye}>
                     {showMnemonic ? 'Hide' : 'Reveal'}
                 </Button>
            </div>

            <div className="bg-red-50 border-l-4 border-red-400 text-red-800 p-4 rounded-r-lg">
                <p className="font-bold">Do NOT lose this phrase.</p>
                <p className="text-sm">Seamount cannot recover your wallet if you lose your mnemonic. You are in control.</p>
            </div>

            <Button onClick={() => onNext()} disabled={!showMnemonic} className="w-full mt-8">I've Backed It Up, Finish</Button>
        </div>
    );
};

// --- Main Onboarding Component ---
const OnboardingPage: React.FC = () => {
  const [step, setStep] = useState<'identity' | 'walletBackup'>('identity');
  const [mnemonic, setMnemonic] = useState<string | null>(null);
  const { completeOnboarding, triggerWalletCreation } = useAuth();
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
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-6 md:p-8">
          <div className="mb-6">
            <div className="flex justify-between items-center text-sm text-gray-500 mb-2">
              <h2 className="font-semibold text-lg text-gray-800">
                {step === 'identity' ? 'Step 1: Identity' : 'Step 2: Wallet Backup'}
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
          
          {step === 'identity' ? (
            <IdentityStep onNext={handleIdentityComplete} stepData={{}} />
          ) : mnemonic ? (
            <WalletBackupStep onNext={handleBackupComplete} stepData={{}} mnemonic={mnemonic} />
          ) : (
            <div className="text-center p-8">
              <p className="text-gray-600">Loading wallet...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OnboardingPage;