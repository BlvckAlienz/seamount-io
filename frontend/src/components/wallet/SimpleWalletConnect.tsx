// File: frontend/src/components/wallet/SimpleWalletConnect.tsx
import React, { useState, useEffect } from 'react';
import { Wallet, X, CheckCircle, ExternalLink, Smartphone, Monitor } from 'lucide-react';
import toast from 'react-hot-toast';

interface SimpleWalletConnectProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletConnected: (address: string, provider: string) => void;
}

const SimpleWalletConnect: React.FC<SimpleWalletConnectProps> = ({
  isOpen,
  onClose,
  onWalletConnected
}) => {
  const [connectionStep, setConnectionStep] = useState<'select' | 'connecting' | 'success'>('select');
  const [selectedProvider, setSelectedProvider] = useState<string>('');

  const walletProviders = [
    {
      id: 'pera',
      name: 'Pera Wallet',
      icon: '🟢',
      description: 'Algorand Mobile Wallet',
      mobile: true,
      desktop: false,
      deeplink: 'algorand://wc?',
      webUrl: 'https://web.perawallet.app',
      installUrl: 'https://perawallet.app/download/'
    },
    {
      id: 'defly',
      name: 'Defly Wallet',
      icon: '🔷',
      description: 'Algorand Trading Wallet',
      mobile: true,
      desktop: false,
      deeplink: 'defly://wc?',
      webUrl: 'https://app.defly.app',
      installUrl: 'https://defly.app/download/'
    },
    {
      id: 'metamask',
      name: 'MetaMask',
      icon: '🦊',
      description: 'EVM & Multi-Chain',
      mobile: true,
      desktop: true,
      deeplink: 'metamask://wc?',
      webUrl: 'https://metamask.io',
      installUrl: 'https://metamask.io/download/'
    },
    {
      id: 'walletconnect',
      name: 'WalletConnect',
      icon: '🔗',
      description: 'Multi-Wallet Standard',
      mobile: true,
      desktop: true,
      deeplink: '',
      webUrl: 'https://walletconnect.com',
      installUrl: ''
    }
  ];

  useEffect(() => {
    if (!isOpen) {
      setConnectionStep('select');
      setSelectedProvider('');
    }
  }, [isOpen]);

  const isMobile = () => {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  };

  const connectToWallet = async (providerId: string) => {
    setSelectedProvider(providerId);
    setConnectionStep('connecting');

    const provider = walletProviders.find(p => p.id === providerId);
    if (!provider) return;

    try {
      // Check if we're on mobile and try deeplink
      if (isMobile() && provider.deeplink) {
        // Try to open the wallet app
        window.location.href = provider.deeplink;
        
        // Fallback: if wallet not installed, redirect to install page after delay
        setTimeout(() => {
          if (provider.installUrl) {
            window.open(provider.installUrl, '_blank');
          }
        }, 1000);
      } else {
        // Desktop: redirect to web wallet or install page
        if (provider.webUrl) {
          window.open(provider.webUrl, '_blank');
        } else if (provider.installUrl) {
          window.open(provider.installUrl, '_blank');
        }
      }

      // Simulate successful connection for demo
      // In production, you'd wait for actual wallet connection callback
      setTimeout(() => {
        const demoAddress = `0x${Math.random().toString(16).substr(2, 40)}`;
        setConnectionStep('success');
        toast.success(`${provider.name} connected!`);
        
        setTimeout(() => {
          onWalletConnected(demoAddress, providerId);
          onClose();
        }, 1500);
      }, 2000);

    } catch (error) {
      console.error('Connection failed:', error);
      toast.error(`Failed to connect to ${provider.name}`);
      setConnectionStep('select');
    }
  };

  const openExternalLink = (url: string) => {
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
            <h3 className="text-xl font-bold text-white flex items-center gap-2">
              <Wallet className="text-cyan-400 h-5 w-5" />
              {connectionStep === 'select' && 'Connect Wallet'}
              {connectionStep === 'connecting' && 'Connecting...'}
              {connectionStep === 'success' && 'Connected!'}
            </h3>
            <p className="text-gray-400 text-sm">
              {connectionStep === 'select' && 'Choose your wallet provider'}
              {connectionStep === 'connecting' && `Connecting to ${selectedProvider}...`}
              {connectionStep === 'success' && 'Wallet connected successfully'}
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
                  className="w-full flex items-center gap-4 p-4 border border-gray-600 rounded-xl hover:border-cyan-500 hover:bg-gray-700/50 transition-all group"
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

                  <div className="text-gray-400 group-hover:text-cyan-400 transition-colors">
                    →
                  </div>
                </button>
              ))}

              <div className="pt-4 border-t border-gray-700">
                <p className="text-center text-gray-400 text-sm">
                  Your wallet connection is secure and encrypted
                </p>
              </div>
            </>
          )}

          {connectionStep === 'connecting' && (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-cyan-600 mx-auto mb-4"></div>
              <p className="text-white font-medium mb-2">
                Connecting to {walletProviders.find(p => p.id === selectedProvider)?.name}
              </p>
              <p className="text-gray-400 text-sm">
                {isMobile() ? 'Opening wallet app...' : 'Redirecting to wallet...'}
              </p>
            </div>
          )}

          {connectionStep === 'success' && (
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="h-8 w-8 text-green-400" />
              </div>
              <p className="text-white font-medium mb-2">Wallet Connected!</p>
              <p className="text-gray-400 text-sm">
                Your {walletProviders.find(p => p.id === selectedProvider)?.name} wallet is now connected.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SimpleWalletConnect;