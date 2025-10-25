// File: frontend/src/components/wallet/CreateWalletModal.tsx
// ✅ PRODUCTION READY: Multi-chain wallet creation modal

import React, { useState } from 'react';
import { 
  X, Bitcoin, Coins, Shield, Sparkles, Check, 
  AlertCircle, Key, Wallet, Copy, ExternalLink
} from 'lucide-react';
import { apiClient } from '../../config/api';
import toast from 'react-hot-toast';

interface CreateWalletModalProps {
  isOpen: boolean;
  onClose: () => void;
  onWalletCreated: (wallets: any) => void;
  existingWallets: any;
}

interface ChainConfig {
  id: string;
  name: string;
  icon: any;
  color: string;
  symbol: string;
  explorer: string;
  description: string;
}

const CreateWalletModal: React.FC<CreateWalletModalProps> = ({
  isOpen,
  onClose,
  onWalletCreated,
  existingWallets
}) => {
  const [creating, setCreating] = useState(false);
  const [creationProgress, setCreationProgress] = useState<{ [key: string]: 'idle' | 'creating' | 'success' | 'error' }>({});
  const [createdWallets, setCreatedWallets] = useState<any>({});

  const chains: ChainConfig[] = [
    {
      id: 'bitcoin',
      name: 'Bitcoin',
      icon: Bitcoin,
      color: 'from-orange-500 to-yellow-600',
      symbol: 'BTC',
      explorer: 'https://blockstream.info',
      description: 'World\'s first cryptocurrency'
    },
    {
      id: 'ethereum',
      name: 'Ethereum', 
      icon: Coins,
      color: 'from-gray-400 to-slate-600',
      symbol: 'ETH',
      explorer: 'https://etherscan.io',
      description: 'Smart contract platform'
    },
    {
      id: 'polygon',
      name: 'Polygon',
      icon: Coins,
      color: 'from-purple-500 to-indigo-600',
      symbol: 'MATIC',
      explorer: 'https://polygonscan.com',
      description: 'Ethereum scaling solution'
    },
    {
      id: 'algorand',
      name: 'Algorand',
      icon: Shield,
      color: 'from-blue-500 to-cyan-600',
      symbol: 'ALGO',
      explorer: 'https://algoexplorer.io',
      description: 'High-speed blockchain'
    }
  ];

  if (!isOpen) return null;

  const resetState = () => {
    setCreating(false);
    setCreationProgress({});
    setCreatedWallets({});
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  const createSingleChainWallet = async (chain: string) => {
    setCreationProgress(prev => ({ ...prev, [chain]: 'creating' }));
    
    try {
      const response = await apiClient.post(`/api/v1/wallet/${chain}/create`);
      
      if (response.data.success) {
        setCreationProgress(prev => ({ ...prev, [chain]: 'success' }));
        setCreatedWallets(prev => ({
          ...prev,
          [chain]: response.data.wallet
        }));
        
        toast.success(`${chain.toUpperCase()} wallet created!`);
        return response.data.wallet;
      }
    } catch (error: any) {
      console.error(`${chain} wallet creation failed:`, error);
      setCreationProgress(prev => ({ ...prev, [chain]: 'error' }));
      toast.error(error.response?.data?.error || `Failed to create ${chain} wallet`);
    }
  };

  const createAllChains = async () => {
    setCreating(true);
    setCreationProgress(
      chains.reduce((acc, chain) => {
        acc[chain.id] = 'creating';
        return acc;
      }, {} as any)
    );

    try {
      const response = await apiClient.post('/api/v1/wallet/create-multi-chain', {
        chains: chains.map(chain => chain.id)
      });

      if (response.data.success) {
        // Update progress to success for all created chains
        const newProgress = { ...creationProgress };
        Object.keys(response.data.wallets).forEach(chain => {
          newProgress[chain] = 'success';
        });
        setCreationProgress(newProgress);
        
        setCreatedWallets(response.data.wallets);
        onWalletCreated(response.data.wallets);
        
        toast.success(`Wallets created on ${response.data.total_chains} chains!`);
      }
    } catch (error: any) {
      console.error('Multi-chain wallet creation failed:', error);
      toast.error(error.response?.data?.error || 'Failed to create wallets');
    } finally {
      setCreating(false);
    }
  };

  const getChainStatus = (chainId: string) => {
    if (existingWallets[chainId]?.address) {
      return 'existing';
    }
    return creationProgress[chainId] || 'idle';
  };

  const getStatusIcon = (chainId: string) => {
    const status = getChainStatus(chainId);
    
    switch (status) {
      case 'existing':
        return <Check className="h-5 w-5 text-green-400" />;
      case 'success':
        return <Check className="h-5 w-5 text-green-400" />;
      case 'creating':
        return <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-400" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-400" />;
      default:
        return <Key className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusText = (chainId: string) => {
    const status = getChainStatus(chainId);
    
    switch (status) {
      case 'existing':
        return 'Created';
      case 'success':
        return 'Created';
      case 'creating':
        return 'Creating...';
      case 'error':
        return 'Failed';
      default:
        return 'Create';
    }
  };

  const copyAddress = (address: string, chainName: string) => {
    navigator.clipboard.writeText(address);
    toast.success(`${chainName} address copied!`);
  };

  const viewOnExplorer = (chainId: string, address: string) => {
    const chain = chains.find(c => c.id === chainId);
    if (chain) {
      window.open(`${chain.explorer}/address/${address}`, '_blank');
    }
  };

  const createdCount = chains.filter(chain => 
    getChainStatus(chain.id) === 'existing' || getChainStatus(chain.id) === 'success'
  ).length;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden border border-blue-500/30 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Create Multi-Chain Wallet</h2>
              <p className="text-gray-400 text-sm">One wallet, multiple blockchains</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {/* Progress Summary */}
          <div className="bg-blue-900/20 rounded-xl p-4 mb-6 border border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-blue-300 text-sm">Creation Progress</span>
              <span className="text-white font-semibold">
                {createdCount} of {chains.length} chains
              </span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-blue-600 to-purple-600 h-2 rounded-full transition-all duration-500"
                style={{ width: `${(createdCount / chains.length) * 100}%` }}
              />
            </div>
          </div>

          {/* Chain Cards */}
          <div className="space-y-4">
            {chains.map(chain => {
              const status = getChainStatus(chain.id);
              const wallet = createdWallets[chain.id] || existingWallets[chain.id];
              const address = wallet?.address;
              
              return (
                <div 
                  key={chain.id}
                  className={`bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-xl p-4 border transition-all ${
                    status === 'existing' || status === 'success' 
                      ? 'border-green-500/30' 
                      : status === 'error'
                      ? 'border-red-500/30'
                      : 'border-gray-700/50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`p-3 rounded-xl bg-gradient-to-br ${chain.color} text-white shadow-lg`}>
                        <chain.icon className="h-6 w-6" />
                      </div>
                      <div>
                        <div className="text-white font-semibold">{chain.name}</div>
                        <div className="text-gray-400 text-sm">{chain.description}</div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-3">
                      {address && (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => copyAddress(address, chain.name)}
                            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
                            title="Copy address"
                          >
                            <Copy className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => viewOnExplorer(chain.id, address)}
                            className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
                            title="View on explorer"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </button>
                        </div>
                      )}
                      
                      <div className="flex items-center gap-2">
                        {getStatusIcon(chain.id)}
                        <span className={`text-sm font-medium ${
                          status === 'existing' || status === 'success' ? 'text-green-400' :
                          status === 'creating' ? 'text-blue-400' :
                          status === 'error' ? 'text-red-400' :
                          'text-gray-400'
                        }`}>
                          {getStatusText(chain.id)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Address Display */}
                  {address && (
                    <div className="mt-3 p-3 bg-gray-800/50 rounded-lg border border-gray-700/50">
                      <div className="text-xs text-gray-400 mb-1">Address</div>
                      <div className="text-sm text-white font-mono truncate">
                        {address}
                      </div>
                    </div>
                  )}

                  {/* Create Button for individual chains */}
                  {!address && status === 'idle' && (
                    <div className="mt-3">
                      <button
                        onClick={() => createSingleChainWallet(chain.id)}
                        disabled={creating}
                        className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
                      >
                        <Key className="h-4 w-4" />
                        Create {chain.name} Wallet
                      </button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Benefits Section */}
          <div className="mt-6 bg-green-900/20 rounded-xl p-4 border border-green-500/30">
            <h4 className="font-semibold text-green-400 mb-2 flex items-center">
              <Sparkles className="h-4 w-4 mr-2" />
              Multi-Chain Benefits
            </h4>
            <ul className="text-sm text-green-300 space-y-1">
              <li>• Auto-routing to fastest/cheapest network</li>
              <li>• Unified balance across all chains</li>
              <li>• Single recovery phrase for all wallets</li>
              <li>• No blockchain complexity - we handle everything</li>
            </ul>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-6 border-t border-gray-700">
          <button
            onClick={handleClose}
            className="flex-1 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors"
          >
            {createdCount > 0 ? 'Close' : 'Cancel'}
          </button>
          
          <button
            onClick={createAllChains}
            disabled={creating || createdCount === chains.length}
            className="flex-1 flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-3 px-4 rounded-lg font-semibold transition-all disabled:opacity-50 shadow-lg"
          >
            {creating ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Creating All Wallets...
              </>
            ) : createdCount === chains.length ? (
              <>
                <Check className="h-5 w-5" />
                All Wallets Created!
              </>
            ) : (
              <>
                <Wallet className="h-5 w-5" />
                Create All Wallets ({chains.length - createdCount} remaining)
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default CreateWalletModal;