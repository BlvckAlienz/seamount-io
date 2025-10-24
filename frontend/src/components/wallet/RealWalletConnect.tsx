// File: frontend/src/components/wallet/RealWalletConnect.tsx
import React, { useState, useEffect } from 'react';
import { Wallet, X, CheckCircle, ExternalLink, Smartphone, Monitor, AlertCircle } from 'lucide-react';
import { WalletConnectModal } from '@walletconnect/modal';
import { WalletConnectProvider } from '@walletconnect/web3-provider';
import Web3 from 'web3';
import toast from 'react-hot-toast';

interface RealWalletConnectProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletConnected: (address: string, provider: string, chainId?: number) => void;
}

const RealWalletConnect: React.FC<RealWalletConnectProps> = ({
  isOpen,
  onClose,
  onWalletConnected
}) => {
  const [connectionStep, setConnectionStep] = useState<'select' | 'connecting' | 'success' | 'error'>('select');
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [provider, setProvider] = useState<WalletConnectProvider | null>(null);
  const [web3, setWeb3] = useState<Web3 | null>(null);

  const walletProviders = [
    {
      id: 'walletconnect',
      name: 'WalletConnect',
      icon: '🔗',
      description: 'Connect any WalletConnect-compatible wallet',
      mobile: true,
      desktop: true,
      supportedChains: ['Ethereum', 'Polygon', 'Binance Smart Chain']
    },
    {
      id: 'metamask',
      name: 'MetaMask',
      icon: '🦊',
      description: 'EVM & Multi-Chain Wallet',
      mobile: true,
      desktop: true,
      supportedChains: ['Ethereum', 'Polygon', 'Arbitrum', 'Optimism']
    },
    {
      id: 'pera',
      name: 'Pera Wallet',
      icon: '🟢',
      description: 'Algorand Mobile Wallet',
      mobile: true,
      desktop: false,
      supportedChains: ['Algorand']
    },
    {
      id: 'coinbase',
      name: 'Coinbase Wallet',
      icon: '🟡',
      description: 'Multi-Chain Wallet',
      mobile: true,
      desktop: true,
      supportedChains: ['Ethereum', 'Polygon', 'Arbitrum']
    }
  ];

  // Initialize WalletConnect
  useEffect(() => {
    const initWalletConnect = async () => {
      try {
        const walletConnectProvider = new WalletConnectProvider({
          infuraId: '27e484dcd9e3efcfd25a83a78777cdf1', // Free Infura ID for Ethereum
          qrcodeModalOptions: {
            mobileLinks: [
              'metamask',
              'trust',
              'rainbow',
              'argent',
              'coinbase',
              'imtoken'
            ]
          }
        });

        setProvider(walletConnectProvider);
        setWeb3(new Web3(walletConnectProvider as any));

        // Subscribe to connection events
        walletConnectProvider.on('connect', (error, payload) => {
          if (error) {
            console.error('Connection error:', error);
            return;
          }
          handleConnectionSuccess(walletConnectProvider, 'walletconnect');
        });

        walletConnectProvider.on('disconnect', (error) => {
          console.log('Wallet disconnected');
        });

      } catch (error) {
        console.error('Failed to initialize WalletConnect:', error);
      }
    };

    if (isOpen) {
      initWalletConnect();
    }

    return () => {
      if (provider) {
        provider.disconnect();
      }
    };
  }, [isOpen]);

  const connectToWallet = async (providerId: string) => {
    setSelectedProvider(providerId);
    setConnectionStep('connecting');
    setErrorMessage('');

    try {
      switch (providerId) {
        case 'walletconnect':
          await connectWithWalletConnect();
          break;
        case 'metamask':
          await connectWithMetaMask();
          break;
        case 'pera':
          await connectWithPera();
          break;
        case 'coinbase':
          await connectWithCoinbase();
          break;
        default:
          throw new Error('Unsupported wallet provider');
      }
    } catch (error: any) {
      console.error(`Connection failed for ${providerId}:`, error);
      setConnectionStep('error');
      setErrorMessage(error.message || 'Connection failed');
    }
  };

  const connectWithWalletConnect = async () => {
    if (!provider) throw new Error('WalletConnect not initialized');

    try {
      await provider.enable();
      // The connection will be handled by the event listener
    } catch (error: any) {
      if (error.message?.includes('User rejected')) {
        throw new Error('Connection rejected by user');
      }
      throw error;
    }
  };

  const connectWithMetaMask = async () => {
    if (typeof window === 'undefined' || !(window as any).ethereum) {
      // Redirect to MetaMask install
      window.open('https://metamask.io/download/', '_blank');
      throw new Error('MetaMask not detected. Redirecting to install page.');
    }

    const ethereum = (window as any).ethereum;
    
    try {
      const accounts = await ethereum.request({ 
        method: 'eth_requestAccounts' 
      });
      
      if (accounts && accounts.length > 0) {
        const chainId = await ethereum.request({ method: 'eth_chainId' });
        handleConnectionSuccess(ethereum, 'metamask', parseInt(chainId), accounts[0]);
      } else {
        throw new Error('No accounts found');
      }
    } catch (error: any) {
      if (error.code === 4001) {
        throw new Error('Connection rejected by user');
      }
      throw error;
    }
  };

  const connectWithPera = async () => {
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
        handleConnectionSuccess(peraWallet, 'pera', undefined, accounts[0]);
      } else {
        throw new Error('No accounts found');
      }
    } catch (error: any) {
      if (error?.data?.type === 'CONNECT_MODAL_CLOSED') {
        throw new Error('Connection cancelled by user');
      }
      throw error;
    }
  };

  const connectWithCoinbase = async () => {
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

    // Coinbase Wallet supports EIP-1193, so we can use the same method as MetaMask
    return connectWithMetaMask();
  };

  const handleConnectionSuccess = (
    walletProvider: any, 
    providerId: string, 
    chainId?: number, 
    address?: string
  ) => {
    let finalAddress = address;

    // If no address provided, try to get it from the provider
    if (!finalAddress && providerId === 'walletconnect' && provider) {
      finalAddress = provider.accounts[0];
    }

    if (!finalAddress) {
      throw new Error('Could not retrieve wallet address');
    }

    setConnectionStep('success');
    toast.success(`${providerId} connected successfully!`);

    // Notify parent after a brief success display
    setTimeout(() => {
      onWalletConnected(finalAddress!, providerId, chainId);
      onClose();
    }, 1500);
  };

  const isMobile = () => {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
  };

  const openWalletWebsite = (providerId: string) => {
    const provider = walletProviders.find(p => p.id === providerId);
    if (!provider) return;

    const urls: { [key: string]: string } = {
      'metamask': 'https://metamask.io',
      'pera': 'https://perawallet.app',
      'coinbase': 'https://coinbase.com/wallet',
      'walletconnect': 'https://walletconnect.com'
    };

    window.open(urls[providerId] || '#', '_blank', 'noopener,noreferrer');
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
                        {provider.supportedChains.join(', ')}
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
                Please approve the connection in your wallet...
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
                  className="w-full bg-cyan-600 hover:bg-cyan-700 text-white py-3 rounded-lg transition-colors"
                >
                  Try Another Wallet
                </button>
                
                {selectedProvider && (
                  <button
                    onClick={() => openWalletWebsite(selectedProvider)}
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

export default RealWalletConnect;