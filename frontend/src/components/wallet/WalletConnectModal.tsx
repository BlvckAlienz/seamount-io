// File: frontend/src/components/wallet/WalletConnectModal.tsx
import React, { useState } from 'react';
import { Wallet, X, CheckCircle, ExternalLink, AlertCircle, Copy, Check } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../../config/api';

interface WalletConnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletConnected: (address: string, provider: string) => void;
}

const WalletConnectModal: React.FC<WalletConnectModalProps> = ({
  isOpen,
  onClose,
  onWalletConnected
}) => {
  const [connectionStep, setConnectionStep] = useState<'select' | 'connecting' | 'connected'>('select');
  const [selectedProvider, setSelectedProvider] = useState<string>('');
  const [walletAddress, setWalletAddress] = useState<string>('');
  const [copied, setCopied] = useState(false);

  const walletProviders = [
    {
      id: 'pera',
      name: 'Pera Wallet',
      icon: '🟢',
      description: 'Connect your Algorand wallet',
      supportedChains: ['Algorand']
    },
    {
      id: 'metamask',
      name: 'MetaMask',
      icon: '🦊',
      description: 'Connect your Ethereum wallet',
      supportedChains: ['Ethereum', 'Polygon']
    }
  ];

  const connectToWallet = async (providerId: string) => {
    setSelectedProvider(providerId);
    setConnectionStep('connecting');

    try {
      let address = '';
      
      if (providerId === 'pera') {
        address = await connectPeraWallet();
      } else if (providerId === 'metamask') {
        address = await connectMetaMask();
      }

      if (address) {
        // ✅ Store the connected wallet in our backend
        await apiClient.post('/api/v1/user/connected-wallets', {
          wallet_address: address,
          provider: providerId,
          chain: providerId === 'pera' ? 'algorand' : 'ethereum'
        });

        setWalletAddress(address);
        setConnectionStep('connected');
        toast.success(`${walletProviders.find(p => p.id === providerId)?.name} connected!`);
        
        // Notify parent after delay
        setTimeout(() => {
          onWalletConnected(address, providerId);
          onClose();
        }, 2000);
      }
    } catch (error: any) {
      console.error(`Connection failed:`, error);
      toast.error(error.message || 'Connection failed');
      setConnectionStep('select');
    }
  };

  const connectPeraWallet = async (): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (typeof window === 'undefined') {
        reject(new Error('Window not available'));
        return;
      }

      // Check if Pera Wallet is installed
      if (!(window as any).PeraWallet) {
        // Open Pera install in new tab, but keep user on Seamount
        window.open('https://perawallet.app/download/', '_blank');
        reject(new Error('Pera Wallet not detected. Please install it and try again.'));
        return;
      }

      try {
        const peraWallet = new (window as any).PeraWallet();
        
        peraWallet.connect()
          .then((accounts: string[]) => {
            if (accounts && accounts.length > 0) {
              resolve(accounts[0]);
            } else {
              reject(new Error('No accounts found'));
            }
          })
          .catch((error: any) => {
            if (error?.data?.type === 'CONNECT_MODAL_CLOSED') {
              reject(new Error('Connection cancelled by user'));
            } else {
              reject(error);
            }
          });
      } catch (error) {
        reject(error);
      }
    });
  };

  const connectMetaMask = async (): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (typeof window === 'undefined' || !(window as any).ethereum) {
        // Open MetaMask install in new tab, but keep user on Seamount
        window.open('https://metamask.io/download/', '_blank');
        reject(new Error('MetaMask not detected. Please install it and try again.'));
        return;
      }

      const ethereum = (window as any).ethereum;
      
      ethereum.request({ 
        method: 'eth_requestAccounts' 
      })
      .then((accounts: string[]) => {
        if (accounts && accounts.length > 0) {
          resolve(accounts[0]);
        } else {
          reject(new Error('No accounts found'));
        }
      })
      .catch((error: any) => {
        if (error.code === 4001) {
          reject(new Error('Connection rejected by user'));
        } else {
          reject(error);
        }
      });
    });
  };

  const copyAddress = () => {
    navigator.clipboard.writeText(walletAddress);
    setCopied(true);
    toast.success('Wallet address copied!');
    setTimeout(() => setCopied(false), 2000);
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
              {connectionStep === 'connected' && 'Connected!'}
            </h3>
            <p className="text-gray-400 text-sm">
              {connectionStep === 'select' && 'Choose your wallet provider'}
              {connectionStep === 'connecting' && `Connecting to ${selectedProvider}...`}
              {connectionStep === 'connected' && 'Your wallet is now connected'}
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
                    <div className="text-xs text-gray-500 mt-1">
                      {provider.supportedChains.join(', ')}
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

          {connectionStep === 'connected' && (
            <div className="text-center py-4">
              <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="h-8 w-8 text-green-400" />
              </div>
              <p className="text-white font-medium mb-2">Wallet Connected!</p>
              <p className="text-gray-400 text-sm mb-4">
                Your {walletProviders.find(p => p.id === selectedProvider)?.name} wallet is now connected to Seamount.
              </p>
              
              {/* Show connected address */}
              <div className="bg-gray-900/50 rounded-lg p-3 mb-4">
                <p className="text-xs text-gray-400 mb-1">Connected Address</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 font-mono text-sm text-white break-all">
                    {walletAddress}
                  </code>
                  <button
                    onClick={copyAddress}
                    className="p-1 hover:bg-gray-700 rounded transition-colors"
                  >
                    {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4 text-gray-400" />}
                  </button>
                </div>
              </div>

              <button
                onClick={onClose}
                className="w-full bg-cyan-600 hover:bg-cyan-700 text-white py-3 rounded-lg transition-colors"
              >
                Start Using Seamount
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WalletConnectModal;