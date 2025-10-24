// File: frontend/src/components/wallet/MultiChainWalletConnect.tsx
// FIXED VERSION - All async/await properly handled

import React, { useState } from 'react';
import { Wallet, Check, Loader, Shield, X, AlertCircle, ExternalLink } from 'lucide-react';
import { apiClient } from '../../config/api';
import toast from 'react-hot-toast';

interface WalletOption {
  id: string;
  name: string;
  icon: string;
  chains: string[];
  description: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onWalletCreated: (mnemonic: string) => void;
}

export const MultiChainWalletConnect: React.FC<Props> = ({ isOpen, onClose, onWalletCreated }) => {
  const [loading, setLoading] = useState<string | null>(null);
  const [selectedWallet, setSelectedWallet] = useState<string | null>(null);
  const [showAddressModal, setShowAddressModal] = useState(false);
  const [selectedExternalWallet, setSelectedExternalWallet] = useState<WalletOption | null>(null);

  const WALLET_OPTIONS: WalletOption[] = [
    {
      id: 'seamount-native',
      name: 'Create Seamount Wallet',
      icon: '🌊',
      chains: ['Algorand', 'Bitcoin', 'Ethereum', 'Polygon'],
      description: 'New multi-chain wallet (Recommended)'
    },
    {
      id: 'coinbase',
      name: 'Coinbase Wallet', 
      icon: '🟡',
      chains: ['Ethereum', 'Polygon', 'Arbitrum'],
      description: 'Connect your Coinbase wallet'
    },
    {
      id: 'binance',
      name: 'Binance Chain Wallet',
      icon: '🟠', 
      chains: ['Binance Smart Chain'],
      description: 'Connect your Binance wallet'
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
    }
  ];

  const AddressInputModal: React.FC<{
    isOpen: boolean;
    onClose: () => void;
    wallet: WalletOption;
    onAddressSubmit: (address: string, walletId: string) => void;
  }> = ({ isOpen, onClose, wallet, onAddressSubmit }) => {
    const [address, setAddress] = useState('');
    const [validating, setValidating] = useState(false);
    const [isValid, setIsValid] = useState<boolean | null>(null);

    const validateAddress = async (addr: string): Promise<boolean> => {
      const validations: { [key: string]: RegExp } = {
        'pera': /^[A-Z2-7]{58}$/, // Algorand
        'metamask': /^0x[a-fA-F0-9]{40}$/, // Ethereum
        'coinbase': /^0x[a-fA-F0-9]{40}$/, // Ethereum
        'binance': /^0x[a-fA-F0-9]{40}$/, // BSC uses same format
      };

      const regex = validations[wallet.id] || /^[a-zA-Z0-9]{20,60}$/;
      return regex.test(addr);
    };

    const handleAddressChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
      const addr = e.target.value;
      setAddress(addr);
      
      if (addr.length > 10) {
        setValidating(true);
        const valid = await validateAddress(addr);
        setIsValid(valid);
        setValidating(false);
      } else {
        setIsValid(null);
      }
    };

    const handleSubmit = () => {
      if (isValid) {
        onAddressSubmit(address, wallet.id);
        setAddress('');
        setIsValid(null);
      }
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
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold text-white">Connect {wallet.name}</h3>
              <p className="text-gray-400 text-sm">Enter your wallet address</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X className="h-5 w-5 text-gray-400" />
            </button>
          </div>

          {/* Address Input */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">
                Wallet Address
              </label>
              <div className="relative">
                <input
                  type="text"
                  value={address}
                  onChange={handleAddressChange}
                  placeholder={`Enter your ${wallet.name} address...`}
                  className={`w-full bg-gray-900 border rounded-lg px-4 py-3 text-white focus:outline-none focus:ring-2 ${
                    isValid === true 
                      ? 'border-green-500 focus:ring-green-500/20' 
                      : isValid === false 
                      ? 'border-red-500 focus:ring-red-500/20'
                      : 'border-gray-600 focus:ring-blue-500/20'
                  }`}
                />
                {validating && (
                  <div className="absolute right-3 top-3">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                  </div>
                )}
                {isValid === true && !validating && (
                  <Check className="absolute right-3 top-3 h-5 w-5 text-green-500" />
                )}
                {isValid === false && !validating && (
                  <AlertCircle className="absolute right-3 top-3 h-5 w-5 text-red-500" />
                )}
              </div>
              
              {/* Validation Messages */}
              {isValid === false && (
                <p className="text-red-400 text-sm mt-2 flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  Invalid {wallet.name} address format
                </p>
              )}
              {isValid === true && (
                <p className="text-green-400 text-sm mt-2 flex items-center gap-2">
                  <Check className="h-4 w-4" />
                  Valid address format
                </p>
              )}
            </div>

            {/* Chain Info */}
            <div className="bg-gray-900/50 rounded-lg p-4">
              <p className="text-sm text-gray-400 mb-2">Supported Chains:</p>
              <div className="flex flex-wrap gap-2">
                {wallet.chains.map(chain => (
                  <span 
                    key={chain}
                    className="text-xs bg-blue-900/30 text-blue-300 px-2 py-1 rounded"
                  >
                    {chain}
                  </span>
                ))}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-2">
              <button
                onClick={onClose}
                className="flex-1 border border-gray-600 text-gray-300 py-3 rounded-lg hover:bg-gray-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!isValid || validating}
                className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white py-3 rounded-lg transition-colors"
              >
                Connect Wallet
              </button>
            </div>

            {/* Help Link */}
            <div className="text-center pt-2">
              <a
                href={`https://support.seamount.io/wallets/${wallet.id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
                How to find my {wallet.name} address
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const handleCreateWallet = async () => {
    setLoading('seamount-native');
    const toastId = toast.loading('Creating your multi-chain wallet...');
    
    try {
      console.log('🔄 Calling /api/v1/user/provision-wallets...');
      
      const response = await apiClient.post('/api/v1/user/provision-wallets');
      console.log('📦 API Response:', response.data);
      
      // ✅ IMPROVED: Handle different response structures
      if (response.data && response.data.success) {
        if (response.data.mnemonic) {
          // ✅ SUCCESS: New wallet created with mnemonic
          toast.success('Multi-chain wallet created!', { id: toastId });
          onWalletCreated(response.data.mnemonic);
          onClose();
        } else if (response.data.wallet_address) {
          // ✅ SUCCESS: Wallet exists but no mnemonic returned
          toast.success('Wallet already exists!', { id: toastId });
          // For existing wallets, we need to handle this differently
          // Since we can't get the mnemonic again, we'll create a new one
          // or skip to dashboard. For now, show error.
          throw new Error('Wallet already exists. Please contact support to reset.');
        } else {
          throw new Error('Wallet creation succeeded but no mnemonic returned');
        }
      } else {
        // Handle API success: false or unexpected response
        const errorMessage = response.data?.detail || response.data?.error || response.data?.message || 'Wallet creation failed';
        throw new Error(errorMessage);
      }
    } catch (error: any) {
      console.error('❌ Wallet creation error details:', error);
      
      // ✅ IMPROVED: Better error logging
      if (error.response) {
        console.error('📡 Server response error:', error.response.data);
        console.error('🔢 HTTP Status:', error.response.status);
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

  // ✅ FIXED: Proper async function for external wallet connection
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

  // ✅ FIXED: Add missing helper functions
  const handleExternalWalletSuccess = async (address: string, walletId: string) => {
    const toastId = toast.loading(`Connecting ${walletId}...`);
    
    try {
      // Save the external wallet to user profile
      const response = await apiClient.post('/api/v1/user/link-external-wallet', {
        wallet_type: walletId,
        address: address,
        chain: getPrimaryChain(walletId)
      });

      if (response.data.success) {
        toast.success(`${walletId.charAt(0).toUpperCase() + walletId.slice(1)} connected!`, { 
          id: toastId,
          duration: 3000 
        });
        
        // Close modal and proceed
        onClose();
        
        // Notify parent component about successful external wallet connection
        onWalletCreated(`EXTERNAL_WALLET_${walletId}_CONNECTED`);
      } else {
        throw new Error(response.data.error || 'Failed to link wallet');
      }
    } catch (error: any) {
      console.error('Wallet linking error:', error);
      toast.error(
        error.response?.data?.detail || error.message || 'Failed to connect wallet', 
        { id: toastId }
      );
    }
  };

  const getPrimaryChain = (walletId: string): string => {
    const chainMap: { [key: string]: string } = {
      'pera': 'algorand',
      'metamask': 'ethereum', 
      'coinbase': 'ethereum',
      'binance': 'bsc'
    };
    return chainMap[walletId] || 'multichain';
  };

  // ✅ FIXED: Add missing manual address submission handler
  const handleManualAddressSubmit = async (address: string, walletId: string) => {
    const toastId = toast.loading(`Verifying ${walletId} address...`);
    
    try {
      // Validate address format first
      const validationResponse = await apiClient.post('/api/v1/wallet/validate-address', {
        address: address,
        chain: getPrimaryChain(walletId)
      });

      if (!validationResponse.data.valid) {
        throw new Error('Invalid address format for this wallet type');
      }

      // Save the external wallet
      const saveResponse = await apiClient.post('/api/v1/user/link-external-wallet', {
        wallet_type: walletId,
        address: address,
        chain: getPrimaryChain(walletId),
        is_manual: true
      });

      if (saveResponse.data.success) {
        toast.success(`${walletId} address saved!`, { id: toastId });
        
        setShowAddressModal(false);
        setSelectedExternalWallet(null);
        onClose();
        
        // Notify parent
        onWalletCreated(`EXTERNAL_WALLET_${walletId}_CONNECTED`);
      } else {
        throw new Error(saveResponse.data.error || 'Failed to save wallet');
      }
    } catch (error: any) {
      console.error('Manual wallet connection error:', error);
      toast.error(
        error.response?.data?.detail || error.message || 'Failed to connect wallet', 
        { id: toastId }
      );
    }
  };

  // ✅ FIXED: Add automated connection handler
  const handleAutomatedConnection = (address: string, provider: string) => {
    console.log(`✅ Automated connection: ${provider} - ${address}`);
    
    // Save the connected wallet
    handleExternalWalletSuccess(address, provider);
    
    // Close the automated modal
    setShowAutomatedConnect(false);
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

      {/* Existing Address Input Modal */}
      {selectedExternalWallet && (
        <AddressInputModal
          isOpen={showAddressModal}
          onClose={() => {
            setShowAddressModal(false);
            setSelectedExternalWallet(null);
          }}
          wallet={selectedExternalWallet}
          onAddressSubmit={handleManualAddressSubmit}
        />
      )}

      {/* Automated Wallet Connect Modal */}
      {showAutomatedConnect && (
        <AutomatedWalletConnect
          isOpen={showAutomatedConnect}
          onClose={() => setShowAutomatedConnect(false)}
          onWalletConnected={handleAutomatedConnection}
        />
      )}
    </div>
  );
};