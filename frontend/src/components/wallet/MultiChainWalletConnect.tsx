// File: frontend/src/components/wallet/MultiChainWalletConnect.tsx

import React, { useState } from 'react';
import { Wallet, Check, Loader, Shield } from 'lucide-react';
import { apiClient } from '../../config/api';
import toast from 'react-hot-toast';

interface WalletOption {
  id: string;
  name: string;
  icon: string;
  chains: string[];
  description: string;
}

const WALLET_OPTIONS: WalletOption[] = [
  {
    id: 'seamount-native',
    name: 'Create Seamount Wallet',
    icon: '🌊',
    chains: ['Algorand', 'Bitcoin', 'Ethereum', 'Polygon'],
    description: 'New multi-chain wallet (Recommended)'
  },
  {
    id: 'pera',
    name: 'Pera Wallet',
    icon: '🟢',
    chains: ['Algorand'],
    description: 'Connect your Algorand wallet'
  },
  {
    id: 'metamask',
    name: 'MetaMask',
    icon: '🦊',
    chains: ['Ethereum', 'Polygon', 'Arbitrum'],
    description: 'Connect your EVM wallet'
  },
  {
    id: 'walletconnect',
    name: 'WalletConnect',
    icon: '🔗',
    chains: ['Multi-chain'],
    description: 'Connect any WalletConnect-compatible wallet'
  }
];

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onWalletCreated: (mnemonic: string) => void;
}

export const MultiChainWalletConnect: React.FC<Props> = ({ isOpen, onClose, onWalletCreated }) => {
  const [loading, setLoading] = useState<string | null>(null);
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);

  const handleCreateWallet = async () => {
  setLoading('seamount-native');
  const toastId = toast.loading('Checking your wallet...');
  
  try {
    console.log('🔄 Calling /api/v1/user/provision-wallets...');
    
    const response = await apiClient.post('/api/v1/user/provision-wallets');
    console.log('📦 API Response:', response.data);
    
    // ✅ COMPREHENSIVE response validation
    if (response.data) {
      if (response.data.success === true) {
        if (response.data.mnemonic) {
          // ✅ SUCCESS: New wallet created with mnemonic
          toast.success('Multi-chain wallet created!', { id: toastId });
          onWalletCreated(response.data.mnemonic);
          onClose();
        } else {
          // ✅ WALLET EXISTS: No mnemonic but wallet exists - complete onboarding
          toast.success('Welcome back! Your wallet is ready.', { id: toastId });
          // Call onWalletCreated with a special value to indicate wallet exists
          onWalletCreated('WALLET_ALREADY_EXISTS');
          onClose();
        }
      } else if (response.data.success === false) {
        // Handle specific error codes
        if (response.data.code === 'WALLET_ALREADY_EXISTS') {
          // ✅ WALLET EXISTS: Complete onboarding without mnemonic
          toast.success('Welcome back! Your wallet is ready.', { id: toastId });
          onWalletCreated('WALLET_ALREADY_EXISTS');
          onClose();
        } else {
          // ❌ Other errors
          const errorMsg = response.data.error || response.data.detail || 'Wallet creation failed';
          throw new Error(errorMsg);
        }
      } else {
        // ❌ UNEXPECTED: No success field
        throw new Error('Invalid response from server');
      }
    } else {
      // ❌ NO RESPONSE DATA
      throw new Error('No response from server');
    }
  } catch (error: any) {
    console.error('❌ Wallet creation error details:', error);
    
    // ✅ COMPREHENSIVE error logging
    if (error.response) {
      console.error('📡 Server response error:', error.response.data);
      console.error('🔢 HTTP Status:', error.response.status);
      
      // ✅ SPECIFIC: Handle wallet exists error from HTTP exception
      if (error.response.data?.code === 'WALLET_ALREADY_EXISTS' || 
          error.response.status === 409) { // 409 Conflict often used for "already exists"
        toast.success('Welcome back! Your wallet is ready.', { id: toastId });
        onWalletCreated('WALLET_ALREADY_EXISTS');
        onClose();
        return;
      }
      
      const serverError = error.response.data?.detail || error.response.data?.error || `Server error: ${error.response.status}`;
      toast.error(serverError, { id: toastId });
    } else if (error.message) {
      console.error('💬 Error message:', error.message);
      toast.error(error.message, { id: toastId });
    } else {
      console.error('🚨 Unknown error:', error);
      toast.error('Wallet creation failed. Please try again.', { id: toastId });
    }
  } finally {
    setLoading(null);
  }
};

  // TEMPORARY: Add this debug function to MultiChainWalletConnect.tsx
  const debugCreateWallet = async () => {
    setLoading('seamount-native');
    const toastId = toast.loading('Creating debug wallet...');
    
    try {
      console.log('🔄 Calling DEBUG endpoint...');
      
      // Temporary: Use debug endpoint
      const response = await apiClient.post('/api/v1/user/debug/provision-wallets');
      console.log('📦 DEBUG API Response:', response.data);
      
      if (response.data && response.data.success && response.data.mnemonic) {
        toast.success('Debug wallet created!', { id: toastId });
        onWalletCreated(response.data.mnemonic);
        onClose();
      } else {
        throw new Error('Debug wallet creation failed: ' + (response.data?.error || 'Unknown error'));
      }
    } catch (error: any) {
      console.error('❌ Debug wallet creation error:', error);
      toast.error(error.message, { id: toastId });
    } finally {
      setLoading(null);
    }
  };

  // TEMPORARY: Replace the handleCreateWallet call with debugCreateWallet in the button click
  // In the wallet options mapping, change:
  // if (wallet.id === 'seamount-native') {
  //   debugCreateWallet(); // TEMPORARY DEBUG
  // }

  const handleConnectExternal = async (walletId: string) => {
    setLoading(walletId);
    
    try {
      switch (walletId) {
        case 'pera':
          // ✅ PERA WALLET INTEGRATION
          if (typeof window !== 'undefined' && (window as any).PeraWallet) {
            const peraWallet = new (window as any).PeraWallet();
            const accounts = await peraWallet.connect();
            toast.success(`Connected: ${accounts[0].slice(0, 10)}...`);
          } else {
            // Redirect to Pera Wallet download
            window.open('https://perawallet.app/', '_blank');
            toast.error('Please install Pera Wallet app');
          }
          break;
          
        case 'metamask':
          // ✅ METAMASK INTEGRATION
          if (typeof window !== 'undefined' && (window as any).ethereum) {
            try {
              const accounts = await (window as any).ethereum.request({
                method: 'eth_requestAccounts'
              });
              toast.success(`Connected: ${accounts[0].slice(0, 10)}...`);
            } catch (metaError) {
              toast.error('User rejected MetaMask connection');
            }
          } else {
            window.open('https://metamask.io/download/', '_blank');
            toast.error('Please install MetaMask extension');
          }
          break;
          
        case 'walletconnect':
          // ✅ WALLETCONNECT INTEGRATION
          toast('WalletConnect integration coming soon!', { icon: '🔗' });
          break;
          
        default:
          toast('External wallet integration coming soon! 🚀', { icon: '⏳' });
      }
    } catch (error) {
      console.error(`External wallet connection failed for ${walletId}:`, error);
      toast.error(`Failed to connect ${walletId}`);
    } finally {
      setLoading(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto border border-gray-700 shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-gray-800 border-b border-gray-700 p-6 z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Wallet className="h-6 w-6 text-blue-400" />
              <h2 className="text-2xl font-bold text-white">Connect Wallet</h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
          <p className="text-gray-400 mt-2">Choose how you want to access Seamount</p>
        </div>

        {/* Wallet Options */}
        <div className="p-6 space-y-3">
          {WALLET_OPTIONS.map(wallet => (
            <button
              key={wallet.id}
              onClick={() => {
                setSelectedWallet(wallet.id);
                if (wallet.id === 'seamount-native') {
                  handleCreateWallet();
                } else {
                  handleConnectExternal(wallet.id);
                }
              }}
              disabled={loading !== null}
              className={`
                w-full flex items-center gap-4 p-5 rounded-xl transition-all
                ${selectedWallet === wallet.id ? 'bg-blue-600/20 border-blue-500' : 'bg-gray-700/30 border-gray-600'}
                border-2 hover:border-blue-500 hover:bg-gray-700/50
                disabled:opacity-50 disabled:cursor-not-allowed
                group
              `}
            >
              {/* Icon */}
              <div className="text-4xl">{wallet.icon}</div>

              {/* Content */}
              <div className="flex-1 text-left">
                <div className="font-semibold text-white mb-1">{wallet.name}</div>
                <div className="text-sm text-gray-400 mb-2">{wallet.description}</div>
                <div className="flex flex-wrap gap-1">
                  {wallet.chains.map(chain => (
                    <span key={chain} className="text-xs bg-gray-800 px-2 py-1 rounded text-gray-300">
                      {chain}
                    </span>
                  ))}
                </div>
              </div>

              {/* Status */}
              {loading === wallet.id ? (
                <Loader className="h-5 w-5 text-blue-400 animate-spin" />
              ) : (
                <div className="text-gray-400 group-hover:text-blue-400 transition-colors">
                  →
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-700 p-6 bg-gray-900/50">
          <div className="flex items-start gap-2 text-sm text-gray-400">
            <Shield className="h-4 w-4 mt-0.5 text-yellow-400" />
            <p>
              <strong className="text-white">Security Tip:</strong> Never share your recovery phrase. 
              Seamount will never ask for it.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};