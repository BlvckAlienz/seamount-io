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
  const [copied, setCopied] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const [currentIconIndex, setCurrentIconIndex] = useState(0);

  // Create single wallet
  const createSingleWallet = async (chain: string) => {
    try {
      toast.loading(`Creating ${chain} wallet...`);
      const response = await apiClient.post(`/api/v1/wallet/${chain}/create`);
      
      if (response.data.success) {
        toast.success(`${chain} wallet created successfully!`);
        onCardClick(); // refresh
      } else {
        toast.error(`Failed to create ${chain} wallet`);
      }
    } catch (error: any) {
      console.error(`Failed to create ${chain} wallet:`, error);
      const errorMessage = error.response?.data?.detail || error.message || `Failed to create ${chain} wallet`;
      toast.error(errorMessage);
    }
  };

  // Chain configuration
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
    return configs[chain as keyof typeof configs] || {
      name: chain.toUpperCase(),
      icon: '',
      color: 'from-gray-500 to-gray-700',
      symbol: chain.toUpperCase()
    };
  };

  // Reliable icon fallbacks
  const getReliableIcons = (chain: string): string[] => {
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
    if (status === 'not_created') {
      if (chain === 'xrp') {
        window.location.href = '/xrp';
        return;
      }
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
      className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-xl hover:shadow-blue-500/10 transform hover:-translate-y-1 cursor-pointer group relative"
    >
      {/* Tron Activation Tooltip & Preferred Badge */}
      {chain === 'tron' && status === 'created' && (
        <>
          {/* Preferred Badge */}
          <div className="absolute top-2 right-2 z-10 flex items-center gap-1 px-2 py-1 bg-gradient-to-r from-purple-600/90 to-cyan-600/90 rounded-full text-[10px] font-bold text-white border border-cyan-400/50 shadow-lg">
            <span className="text-cyan-300">⚡</span>
            <span>PREFERRED</span>
          </div>

          {/* Activation Tooltip Trigger */}
          <div 
            className="absolute bottom-2 left-2 z-10 flex items-center gap-1 text-xs text-cyan-400/70 cursor-help border border-cyan-500/30 rounded-full px-2 py-1 bg-gradient-to-r from-cyan-900/20 to-purple-900/20 backdrop-blur-sm hover:border-cyan-400/50 transition-all"
            onMouseEnter={() => setShowTooltip(true)}
            onMouseLeave={() => setShowTooltip(false)}
            onClick={(e) => e.stopPropagation()}
          >
            <span className="text-cyan-400">⚡</span>
            <span>Activation Required</span>
          </div>

          {/* Tooltip */}
          {showTooltip && (
            <>
              <div 
                className="fixed inset-0 z-40" 
                onClick={() => setShowTooltip(false)}
              />
              <div className="absolute z-50 bottom-full left-0 mb-2 w-64 p-3 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 border border-cyan-500/30 rounded-lg shadow-2xl backdrop-blur-md">
                <div className="absolute bottom-[-6px] left-4 w-3 h-3 bg-gray-900 border-r border-b border-cyan-500/30 transform rotate-45"></div>
                
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-1 h-8 bg-gradient-to-b from-cyan-400 to-purple-500 rounded-full"></div>
                  <h4 className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
                    TRON Activation
                  </h4>
                </div>
                
                <p className="text-xs text-gray-300 mb-2">
                  Your Tron wallet needs a minimum of <span className="text-cyan-400 font-bold">1 TRX</span> to be activated on the network.
                </p>
                
                <div className="space-y-1 text-xs">
                  <div className="flex items-start gap-2">
                    <span className="text-cyan-400 mt-0.5">•</span>
                    <span className="text-gray-400">Send at least 1 TRX to activate</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-cyan-400 mt-0.5">•</span>
                    <span className="text-gray-400">Keep ≥0.1 TRX to stay active</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-cyan-400 mt-0.5">•</span>
                    <span className="text-gray-400">Without activation, tokens won't arrive</span>
                  </div>
                </div>
                
                <div className="mt-3 pt-2 border-t border-cyan-500/30">
                  <a 
                    href="https://tronscan.org/#/address/TR9vTo1mvpf93LzDPfo7tY7CRXxB1fKijb"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <ExternalLink className="h-3 w-3" />
                    View on Tronscan
                  </a>
                </div>
              </div>
            </>
          )}
        </>
      )}

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