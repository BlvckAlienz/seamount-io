// File: frontend/src/components/wallet/ChainWalletCard.tsx
import React, { useState } from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../../config/api';

interface ChainWalletCardProps {
  chain: string;
  address: string;
  balance: number;
  status: 'created' | 'pending' | 'not_created';
  onCardClick: () => void;
}

const ChainWalletCard: React.FC<ChainWalletCardProps> = ({ 
  chain, 
  address, 
  balance, 
  status, 
  onCardClick 
}) => {
  // Add this function to create single wallet
  const createSingleWallet = async (chain: string) => {
    try {
      toast.loading(`Creating ${chain} wallet...`);
      const response = await apiClient.post(`/api/v1/wallet/${chain}/create`);
      
      if (response.data.success) {
        toast.success(`${chain} wallet created successfully!`);
        // Refresh the wallet status
        onCardClick(); // This will trigger parent to refresh
      } else {
        toast.error(`Failed to create ${chain} wallet`);
      }
    } catch (error: any) {
      console.error(`Failed to create ${chain} wallet:`, error);
      const errorMessage = error.response?.data?.detail || error.message || `Failed to create ${chain} wallet`;
      toast.error(errorMessage);
    }
  };

  // Primary icon configuration
  const getChainConfig = (chain: string) => {
    const configs = {
      algorand: {
        name: 'Algorand',
        icon: 'https://cryptologos.cc/logos/algorand-algo-logo.svg',
        color: 'from-blue-500 to-cyan-600',
        symbol: 'ALGO'
      },
      bitcoin: {
        name: 'Bitcoin',
        icon: 'https://cryptologos.cc/logos/bitcoin-btc-logo.svg',
        color: 'from-orange-500 to-yellow-600',
        symbol: 'BTC'
      },
      ethereum: {
        name: 'Ethereum', 
        icon: 'https://cryptologos.cc/logos/ethereum-eth-logo.svg',
        color: 'from-gray-400 to-slate-600',
        symbol: 'ETH'
      },
      polygon: {
        name: 'Polygon',
        icon: 'https://cryptologos.cc/logos/polygon-matic-logo.svg',
        color: 'from-purple-500 to-indigo-600',
        symbol: 'MATIC'
      },
      tron: {
        name: 'TRON',
        icon: 'https://cryptologos.cc/logos/tron-trx-logo.svg',
        color: 'from-red-500 to-red-700',
        symbol: 'TRX'
      },
      solana: {
        name: 'Solana',
        icon: 'https://cryptologos.cc/logos/solana-sol-logo.svg',
        color: 'from-purple-400 to-pink-600',
        symbol: 'SOL'
      },
      xrp: {
        name: 'XRP Ledger',
        icon: 'https://cryptologos.cc/logos/xrp-xrp-logo.svg',
        color: 'from-blue-400 to-cyan-500',
        symbol: 'RLUSD'
      }
    };
    // ✅ Default to a generic config, NOT algorand
    return configs[chain as keyof typeof configs] || {
      name: chain.toUpperCase(),
      icon: '',
      color: 'from-gray-500 to-gray-700',
      symbol: chain.toUpperCase()
    };
  };

  // 🔥 ABSOLUTE RELIABILITY: Multiple fallback icons
  const getReliableIcons = (chain: string) => {
    const iconFallbacks: { [key: string]: string[] } = {
      bitcoin: [
        'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/btc.png',
        'https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@bea1a9722a8c63169dcc06e86182bf2c55a76bbc/128/color/btc.png',
        'https://cryptoicon-api.vercel.app/api/icon/btc'
      ],
      ethereum: [
        'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/eth.png',
        'https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@bea1a9722a8c63169dcc06e86182bf2c55a76bbc/128/color/eth.png',
        'https://cryptoicon-api.vercel.app/api/icon/eth'
      ],
      polygon: [
        'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/matic.png',
        'https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@bea1a9722a8c63169dcc06e86182bf2c55a76bbc/128/color/matic.png',
        'https://cryptoicon-api.vercel.app/api/icon/matic'
      ],
      algorand: [
        'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/algo.png',
        'https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@bea1a9722a8c63169dcc06e86182bf2c55a76bbc/128/color/algo.png',
        'https://cryptoicon-api.vercel.app/api/icon/algo'
      ],
      tron: [
        'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/trx.png',
        'https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@bea1a9722a8c63169dcc06e86182bf2c55a76bbc/128/color/trx.png',
        'https://cryptoicon-api.vercel.app/api/icon/trx'
      ],
      solana: [
        'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/sol.png',
        'https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@bea1a9722a8c63169dcc06e86182bf2c55a76bbc/128/color/sol.png',
        'https://cryptoicon-api.vercel.app/api/icon/sol'
      ],
      xrp: [
        'https://raw.githubusercontent.com/spothq/cryptocurrency-icons/master/128/color/xrp.png',
        'https://cdn.jsdelivr.net/gh/atomiclabs/cryptocurrency-icons@bea1a9722a8c63169dcc06e86182bf2c55a76bbc/128/color/xrp.png',
        'https://cryptoicon-api.vercel.app/api/icon/xrp'
      ]
    };

    return iconFallbacks[chain] || iconFallbacks.xrp || [];
  };

  const config = getChainConfig(chain);
  const iconFallbacks = getReliableIcons(chain);
  const [currentIconIndex, setCurrentIconIndex] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleIconError = () => {
    if (currentIconIndex < iconFallbacks.length - 1) {
      setCurrentIconIndex(currentIconIndex + 1);
    }
  };

  const copyAddress = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!address) {
      toast.error('No address available');
      return;
    }
    navigator.clipboard.writeText(address);
    setCopied(true);
    toast.success(`${config.name} address copied!`);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCardClick = () => {
    // XRP is custodial — no blockchain wallet to create.
    // Navigate to XRP hub which auto-assigns destination tag on load.
    if (chain === 'xrp') {
      window.location.href = '/xrp';
      return;
    }
    if (status === 'not_created') {
      createSingleWallet(chain);
      return;
    }
    onCardClick();
  };

  if (status === 'not_created') {
    return (
      <div 
        onClick={handleCardClick}
        className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-lg cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} text-white shadow-lg`}>
            <img 
              src={iconFallbacks[currentIconIndex]} 
              alt={config.name} 
              className="w-6 h-6"
              onError={handleIconError}
            />
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-400">Ready to Create</div>
          </div>
        </div>

        <div className="mb-4">
          <div className="text-white font-semibold">{config.name}</div>
          <div className="text-gray-400 text-sm">Click to create wallet</div>
        </div>

        <div className="w-full bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium text-center transition-colors group-hover:scale-105">
          {chain === 'xrp' ? 'Set Up Account' : 'Create Wallet'}
        </div>
      </div>
    );
  }

  return (
    <div 
      onClick={handleCardClick}
      className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-xl hover:shadow-blue-500/10 transform hover:-translate-y-1 cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} text-white shadow-lg`}>
          <img 
            src={iconFallbacks[currentIconIndex]} 
            alt={config.name} 
            className="w-6 h-6"
            onError={handleIconError}
          />
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">
            {balance > 0 ? `$${balance.toFixed(2)}` : '$0.00'}
          </div>
          <div className="text-sm text-gray-400 flex items-center gap-1">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            Live
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="text-white font-semibold">{config.name}</div>
        <div className="text-gray-400 text-sm flex items-center gap-2 mt-1">
          {address ? (
            <>
              <span className="truncate">{address.slice(0, 8)}...{address.slice(-6)}</span>
              <button 
                onClick={copyAddress}
                className="hover:text-blue-400 transition-colors"
              >
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              </button>
            </>
          ) : (
            <span className="text-gray-500">Creating...</span>
          )}
        </div>
      </div>

      {/* Click Hint */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{status === 'created' ? 'Click to view assets' : 'Wallet created'}</span>
        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  );
};

export default ChainWalletCard;