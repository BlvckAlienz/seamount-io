import React, { useState } from 'react';
import { X, Wallet, ChevronRight, Check, ExternalLink, AlertCircle } from 'lucide-react';
import { useWalletOrchestrator, NETWORK_CONFIGS } from '@/contexts/WalletOrchestratorContext';

interface UnifiedWalletModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultAction?: 'send' | 'bet' | 'earn' | 'swap';
}

// Define NETWORK_CONFIGS locally if not exported from context
const NETWORK_CONFIGS = {
  basecamp: {
    name: 'Basecamp',
    description: 'CAMP Testnet',
    type: 'testnet' as const,
    nativeCurrency: 'CAMP',
    chainId: '0x1cbc67c35a',
    icon: '/networks/basecamp.svg'
  },
  // Add other networks as needed
  ethereum: {
    name: 'Ethereum',
    description: 'Ethereum Mainnet',
    type: 'mainnet' as const,
    nativeCurrency: 'ETH',
    chainId: '0x1',
    icon: '/networks/ethereum.svg'
  },
  polygon: {
    name: 'Polygon',
    description: 'Polygon Mainnet',
    type: 'mainnet' as const,
    nativeCurrency: 'MATIC',
    chainId: '0x89',
    icon: '/networks/polygon.svg'
  }
};

export function UnifiedWalletModal({ isOpen, onClose, defaultAction }: UnifiedWalletModalProps) {
  const [selectedNetwork, setSelectedNetwork] = useState<string | null>(null);
  const [showNetworkDetails, setShowNetworkDetails] = useState(false);
  
  const {
    wallets,
    connectWallet,
    disconnectWallet,
    isConnecting,
    getBestNetworkForAction,
    isWalletConnected
  } = useWalletOrchestrator();

  if (!isOpen) return null;

  // Determine which networks to show based on default action
  const getRecommendedNetworks = () => {
    if (defaultAction) {
      const bestNetwork = getBestNetworkForAction(defaultAction);
      return [bestNetwork];
    }
    return Object.keys(NETWORK_CONFIGS) as Array<keyof typeof NETWORK_CONFIGS>;
  };

  const handleConnect = async (network: keyof typeof NETWORK_CONFIGS) => {
    await connectWallet(network);
    if (!isConnecting) {
      onClose();
    }
  };

  const renderNetworkCard = (networkId: keyof typeof NETWORK_CONFIGS) => {
    const config = NETWORK_CONFIGS[networkId];
    const wallet = wallets[networkId];
    const isConnected = isWalletConnected(networkId);
    
    return (
      <div
        key={networkId}
        className={`p-4 rounded-xl border transition-all cursor-pointer hover:scale-[1.02] ${
          isConnected
            ? 'bg-green-500/10 border-green-500/30'
            : 'bg-gray-800/50 border-gray-700/50 hover:border-blue-500/30'
        }`}
        onClick={() => setSelectedNetwork(networkId)}
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
              isConnected ? 'bg-green-500/20' : 'bg-gray-700'
            }`}>
              <div className="w-8 h-8 flex items-center justify-center">
                {networkId === 'basecamp' && (
                  <div className="w-6 h-6 rounded-full bg-gradient-to-r from-green-500 to-emerald-600"></div>
                )}
                {networkId === 'ethereum' && (
                  <div className="w-6 h-6 rounded-full bg-gradient-to-r from-purple-500 to-blue-500"></div>
                )}
                {networkId === 'polygon' && (
                  <div className="w-6 h-6 rounded-full bg-gradient-to-r from-indigo-500 to-purple-600"></div>
                )}
              </div>
            </div>
            <div>
              <div className="font-semibold text-white">{config.name}</div>
              <div className="text-sm text-gray-400">{config.description}</div>
            </div>
          </div>
          
          {isConnected ? (
            <div className="flex items-center gap-2 text-green-400">
              <Check className="w-5 h-5" />
              <span className="text-sm font-medium">Connected</span>
            </div>
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>
        
        <div className="flex items-center justify-between text-sm">
          <div className="text-gray-400">
            {config.type === 'testnet' && '🟡 Testnet'}
            {config.type === 'mainnet' && '🟢 Mainnet'}
            {config.type === 'camp_mainnet_future' && '🔵 Future'}
          </div>
          <div className="text-gray-400">{config.nativeCurrency}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gray-900 rounded-2xl border border-gray-800 max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-800">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Wallet className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Connect Wallet</h2>
                <p className="text-gray-400 text-sm">
                  {defaultAction 
                    ? `Choose network for ${defaultAction}`
                    : 'Select network to connect'}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>
          
          {defaultAction === 'bet' && (
            <div className="mt-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
              <div className="flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-yellow-400 mt-0.5" />
                <div className="text-sm text-yellow-300">
                  Prediction markets currently use <strong>testnet tokens</strong>.
                  Get free CAMP at{' '}
                  <a
                    href="https://faucet.campnetwork.xyz"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-yellow-200"
                  >
                    faucet.campnetwork.xyz
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>
        
        {/* Network Selection */}
        <div className="p-6">
          <div className="space-y-3">
            {getRecommendedNetworks().map(renderNetworkCard)}
          </div>
          
          {/* Network Details */}
          {selectedNetwork && (
            <div className="mt-6 p-4 bg-gray-800/50 rounded-xl border border-gray-700">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-white">
                  {NETWORK_CONFIGS[selectedNetwork as keyof typeof NETWORK_CONFIGS].name}
                </h3>
                {isWalletConnected(selectedNetwork as keyof typeof NETWORK_CONFIGS) ? (
                  <button
                    onClick={() => disconnectWallet(selectedNetwork as keyof typeof NETWORK_CONFIGS)}
                    className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg text-sm transition-colors"
                  >
                    Disconnect
                  </button>
                ) : (
                  <button
                    onClick={() => handleConnect(selectedNetwork as keyof typeof NETWORK_CONFIGS)}
                    disabled={isConnecting}
                    className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm transition-colors disabled:opacity-50"
                  >
                    {isConnecting ? 'Connecting...' : 'Connect'}
                  </button>
                )}
              </div>
              
              <div className="text-sm text-gray-400 space-y-1">
                <div>Type: {NETWORK_CONFIGS[selectedNetwork as keyof typeof NETWORK_CONFIGS].type}</div>
                <div>Chain ID: {NETWORK_CONFIGS[selectedNetwork as keyof typeof NETWORK_CONFIGS].chainId}</div>
                <div>Currency: {NETWORK_CONFIGS[selectedNetwork as keyof typeof NETWORK_CONFIGS].nativeCurrency}</div>
              </div>
            </div>
          )}
          
          {/* Helper Text */}
          <div className="mt-6 text-center text-sm text-gray-500">
            <p>Can't see your wallet? Make sure it supports the selected network.</p>
          </div>
        </div>
      </div>
    </div>
  );
}