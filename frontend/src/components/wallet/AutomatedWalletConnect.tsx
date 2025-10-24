// File: frontend/src/components/wallet/AutomatedWalletConnect.tsx
import React, { useState, useEffect } from 'react';
import { X, Loader, Check, AlertCircle, ExternalLink, Smartphone, Monitor } from 'lucide-react';
import toast from 'react-hot-toast';

interface AutomatedWalletConnectProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletConnected: (address: string, provider: string) => void;
}

const AutomatedWalletConnect: React.FC<AutomatedWalletConnectProps> = ({
  isOpen,
  onClose,
  onWalletConnected
}) => {
  const [connectionStep, setConnectionStep] = useState<'select' | 'connecting' | 'success' | 'error'>('select');
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const walletProviders = [
    {
      id: 'pera',
      name: 'Pera Wallet',
      icon: '🟢',
      description: 'Algorand Mobile Wallet',
      mobile: true,
      desktop: false,
      deeplink: 'algorand://',
      website: 'https://perawallet.app'
    },
    {
      id: 'metamask',
      name: 'MetaMask',
      icon: '🦊',
      description: 'EVM & Multi-Chain',
      mobile: true,
      desktop: true,
      deeplink: 'metamask://',
      website: 'https://metamask.io'
    },
    {
      id: 'trustwallet',
      name: 'Trust Wallet',
      icon: '🔷',
      description: 'Multi-Chain Mobile',
      mobile: true,
      desktop: false,
      deeplink: 'trust://',
      website: 'https://trustwallet.com'
    },
    {
      id: 'coinbase',
      name: 'Coinbase Wallet',
      icon: '🟡',
      description: 'Multi-Chain',
      mobile: true,
      desktop: true,
      deeplink: 'cbwallet://',
      website: 'https://coinbase.com/wallet'
    }
  ];

  useEffect(() => {
    if (!isOpen) {
      // Reset state when modal closes
      setConnectionStep('select');
      setSelectedProvider('');
      setErrorMessage('');
    }
  }, [isOpen]);

  const detectWallet = (providerId: string) => {
    const provider = walletProviders.find(p => p.id === providerId);
    if (!provider) return false;

    // Check if wallet is installed
    switch (providerId) {
      case 'metamask':
        return typeof window !== 'undefined' && !!(window as any).ethereum?.isMetaMask;
      case 'coinbase':
        return typeof window !== 'undefined' && !!(window as any).ethereum?.isCoinbaseWallet;
      case 'trustwallet':
        return typeof window !== 'undefined' && !!(window as any).ethereum?.isTrust;
      case 'pera':
        return typeof window !== 'undefined' && !!(window as any).PeraWallet;
      default:
        return false;
    }
  };

  const connectToWallet = async (providerId: string) => {
    setSelectedProvider(providerId);
    setConnectionStep('connecting');
    setErrorMessage('');

    try {
      let address = '';

      switch (providerId) {
        case 'metamask':
          address = await connectMetaMask();
          break;
        case 'coinbase':
          address = await connectCoinbase();
          break;
        case 'trustwallet':
          address = await connectTrustWallet();
          break;
        case 'pera':
          address = await connectPeraWallet();
          break;
        default:
          throw new Error('Unsupported wallet provider');
      }

      if (address) {
        setConnectionStep('success');
        toast.success(`${providerId} connected successfully!`);
        
        // Notify parent after a brief success display
        setTimeout(() => {
          onWalletConnected(address, providerId);
          onClose();
        }, 1500);
      } else {
        throw new Error('Failed to get wallet address');
      }

    } catch (error: any) {
      console.error(`Connection failed for ${providerId}:`, error);
      setConnectionStep('error');
      setErrorMessage(error.message || 'Connection failed');
      
      // Show fallback options for mobile
      if (isMobile() && !detectWallet(providerId)) {
        setErrorMessage('Wallet app not detected. Please install the app or use manual connection.');
      }
    }
  };

  const connectMetaMask = async (): Promise<string> => {
    if (typeof window === 'undefined') throw new Error('Window not available');
    
    const ethereum = (window as any).ethereum;
    if (!ethereum) throw new Error('MetaMask not installed');

    try {
      const accounts = await ethereum.request({ 
        method: 'eth_requestAccounts' 
      });
      
      if (accounts && accounts.length > 0) {
        return accounts[0];
      }
      throw new Error('No accounts found');
    } catch (error: any) {
      if (error.code === 4001) {
        throw new Error('Connection rejected by user');
      }
      throw error;
    }
  };

  const connectCoinbase = async (): Promise<string> => {
    if (typeof window === 'undefined') throw new Error('Window not available');
    
    const ethereum = (window as any).ethereum;
    if (!ethereum?.isCoinbaseWallet) {
      // Try to use WalletLink as fallback
      if ((window as any).WalletLink) {
        // WalletLink implementation would go here
        throw new Error('Coinbase Wallet connection not implemented');
      }
      throw new Error('Coinbase Wallet not detected');
    }

    return connectMetaMask(); // Coinbase Wallet supports EIP-1193
  };

  const connectTrustWallet = async (): Promise<string> => {
    if (typeof window === 'undefined') throw new Error('Window not available');
    
    const ethereum = (window as any).ethereum;
    if (!ethereum?.isTrust) {
      throw new Error('Trust Wallet not detected');
    }

    return connectMetaMask(); // Trust Wallet supports EIP-1193
  };

  const connectPeraWallet = async (): Promise<string> => {
    if (typeof window === 'undefined') throw new Error('Window not available');
    
    const PeraWallet = (window as any).PeraWallet;
    if (!PeraWallet) {
      // Redirect to Pera Wallet download on mobile
      if (isMobile()) {
        window.location.href = 'https://perawallet.app/download/';
        throw new Error('Redirecting to Pera Wallet download...');
      }
      throw new Error('Pera Wallet not detected');
    }

    try {
      const peraWallet = new PeraWallet();
      const accounts = await peraWallet.connect();
      
      if (accounts && accounts.length > 0) {
        return accounts[0];
      }
      throw new Error('No accounts found');
    } catch (error: any) {
      if (error?.data?.type === 'CONNECT_MODAL_CLOSED') {
        throw new Error('Connection cancelled by user');
      }
      throw error;
    }
  };

  const isMobile = () => {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  };

  const openWalletWebsite = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={handleBackdropClick}
    >
      <div className="bg-gray-800 rounded-2xl max-w-md w-full p-6 border border-gray-700 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-white">
              {connectionStep === 'select' && 'Connect Wallet'}
              {connectionStep === 'connecting' && 'Connecting...'}
              {connectionStep === 'success' && 'Connected!'}
              {connectionStep === 'error' && 'Connection Failed'}
            </h3>
            <p className="text-gray-400 text-sm">
              {connectionStep === 'select' && 'Choose your wallet provider'}
              {connectionStep === 'connecting' && `Connecting to ${selectedProvider}...`}
              {connectionStep === 'success' && 'Wallet connected successfully'}
              {connectionStep === 'error' && 'Failed to connect wallet'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-4">
          {connectionStep === 'select' && (
            <>
              {walletProviders.map(provider => (
                <button
                  key={provider.id}
                  onClick={() => connectToWallet(provider.id)}
                  className="w-full flex items-center gap-4 p-4 border border-gray-600 rounded-xl hover:border-blue-500 hover:bg-gray-700/50 transition-all group"
                >
                  <div className="text-2xl">{provider.icon}</div>
                  
                  <div className="flex-1 text-left">
                    <div className="font-semibold text-white mb-1">{provider.name}</div>
                    <div className="text-sm text-gray-400">{provider.description}</div>
                    <div className="flex items-center gap-2 mt-1">
                      {provider.mobile && <Smartphone className="h-3 w-3 text-green-400" />}
                      {provider.desktop && <Monitor className="h-3 w-3 text-blue-400" />}
                      <span className="text-xs text-gray-500">
                        {provider.mobile && provider.desktop ? 'Mobile & Desktop' : 
                         provider.mobile ? 'Mobile Only' : 'Desktop Only'}
                      </span>
                    </div>
                  </div>

                  <div className="text-gray-400 group-hover:text-blue-400 transition-colors">
                    →
                  </div>
                </button>
              ))}

              <div className="pt-4 border-t border-gray-700">
                <p className="text-center text-gray-400 text-sm">
                  Don't have a wallet?{' '}
                  <button
                    onClick={() => toast.info('Wallet creation guide coming soon')}
                    className="text-blue-400 hover:text-blue-300 underline"
                  >
                    Learn how to get started
                  </button>
                </p>
              </div>
            </>
          )}

          {connectionStep === 'connecting' && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-white font-medium mb-2">Connecting to {selectedProvider}</p>
              <p className="text-gray-400 text-sm">
                Please approve the connection in your wallet...
              </p>
            </div>
          )}

          {connectionStep === 'success' && (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <Check className="h-8 w-8 text-green-400" />
              </div>
              <p className="text-white font-medium mb-2">Wallet Connected!</p>
              <p className="text-gray-400 text-sm">
                Your {selectedProvider} wallet is now connected to Seamount.
              </p>
            </div>
          )}

          {connectionStep === 'error' && (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="h-8 w-8 text-red-400" />
              </div>
              <p className="text-white font-medium mb-2">Connection Failed</p>
              <p className="text-gray-400 text-sm mb-4">{errorMessage}</p>
              
              <div className="space-y-3">
                <button
                  onClick={() => setConnectionStep('select')}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg transition-colors"
                >
                  Try Another Wallet
                </button>
                
                {selectedProvider && (
                  <button
                    onClick={() => openWalletWebsite(
                      walletProviders.find(p => p.id === selectedProvider)?.website || '#'
                    )}
                    className="w-full flex items-center justify-center gap-2 border border-gray-600 text-gray-300 py-3 rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                    Get {walletProviders.find(p => p.id === selectedProvider)?.name}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AutomatedWalletConnect;