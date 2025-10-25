// File: frontend/src/components/wallet/ChainWalletCard.tsx
import React, { useState } from 'react';
import { Copy, Check, ExternalLink } from 'lucide-react';

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
  const getChainConfig = (chain: string) => {
    const configs = {
      bitcoin: {
        name: 'Bitcoin',
        icon: 'https://cdn-icons-png.flaticon.com/512/825/825423.png', // Bitcoin by Freepik
        color: 'from-orange-500 to-yellow-600',
        symbol: 'BTC'
      },
      ethereum: {
        name: 'Ethereum', 
        icon: 'https://cdn-icons-png.flaticon.com/512/825/825426.png', // ETH by bouzix
        color: 'from-gray-400 to-slate-600',
        symbol: 'ETH'
      },
      polygon: {
        name: 'Polygon',
        icon: 'https://cdn-icons-png.flaticon.com/512/8241/8241186.png', // Matic by bouzix
        color: 'from-purple-500 to-indigo-600',
        symbol: 'MATIC'
      },
      algorand: {
        name: 'Algorand',
        icon: 'https://cdn-icons-png.flaticon.com/512/6250/6250945.png', // Algorand by bouzix
        color: 'from-blue-500 to-cyan-600',
        symbol: 'ALGO'
      }
    };
    return configs[chain as keyof typeof configs] || configs.algorand;
  };

  const config = getChainConfig(chain);
  const [copied, setCopied] = useState(false);

  const copyAddress = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering card click
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
      // For not created wallets, we might want to trigger creation
      // or show a different action. For now, just return.
      return;
    }
    onCardClick();
  };

  if (status === 'not_created') {
    return (
      <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all cursor-not-allowed">
        <div className="flex items-center justify-between mb-4">
          <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} text-white shadow-lg`}>
            <img src={config.icon} alt={config.name} className="w-6 h-6" />
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-400">Not Created</div>
          </div>
        </div>

        <div className="mb-4">
          <div className="text-white font-semibold">{config.name}</div>
          <div className="text-gray-400 text-sm">Complete onboarding to create wallet</div>
        </div>

        <div className="w-full bg-gray-700 text-gray-500 py-3 px-4 rounded-lg font-medium text-center">
          Wallet Not Created
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
          <img src={config.icon} alt={config.name} className="w-6 h-6" />
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
            <span className="text-gray-500">No address</span>
          )}
        </div>
      </div>

      {/* Click Hint */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>Click to view assets</span>
        <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
    </div>
  );
};

export default ChainWalletCard;