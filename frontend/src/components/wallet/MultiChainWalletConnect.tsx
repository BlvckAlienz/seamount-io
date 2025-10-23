// File: frontend/src/components/wallet/MultiChainWalletConnect.tsx

import React, { useState } from 'react';
import { Wallet, Check, Loader } from 'lucide-react';
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
    const toastId = toast.loading('Creating your multi-chain wallet...');
    
    try {
      const response = await apiClient.post('/api/v1/user/provision-wallets');
      
      if (response.data.success && response.data.mnemonic) {
        toast.success('Wallet created on 4 chains!', { id: toastId });
        onWalletCreated(response.data.mnemonic);
        onClose();
      } else {
        throw new Error('Wallet creation failed');
      }
    } catch (error: any) {
      console.error('Wallet creation error:', error);
      toast.error(error.response?.data?.detail || 'Wallet creation failed', { id: toastId });
    } finally {
      setLoading(null);
    }
  };

  const handleConnectExternal = async (walletId: string) => {
    setLoading(walletId);
    toast('External wallet integration coming soon! 🚀', { icon: '⏳' });
    setLoading(null);
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