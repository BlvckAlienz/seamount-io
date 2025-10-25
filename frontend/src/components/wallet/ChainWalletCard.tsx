// File: frontend/src/components/wallet/ChainWalletCard.tsx
import React, { useState } from 'react';

interface ChainWalletCardProps {
  chain: string;
  balance: string;
  address: string;
  chainName: string;
  onViewClick: () => void;
  onBuyClick: (chain: string, address: string, chainName: string) => void;
}

const ChainWalletCard: React.FC<ChainWalletCardProps> = ({ 
  chain, 
  balance, 
  address, 
  chainName,
  onViewClick,
  onBuyClick
}) => {
  const getChainIcon = () => {
    const icons: { [key: string]: string } = {
      bitcoin: '/icons/bitcoin.png',
      ethereum: '/icons/ethereum.png',
      polygon: '/icons/polygon.png',
      algorand: '/icons/algorand.png',
    };
    return icons[chain] || '/icons/crypto.png';
  };

  const getChainColor = () => {
    const colors: { [key: string]: string } = {
      bitcoin: 'bg-orange-500',
      ethereum: 'bg-purple-500',
      polygon: 'bg-indigo-500',
      algorand: 'bg-black',
    };
    return colors[chain] || 'bg-gray-500';
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow">
      {/* Chain Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <div className={`relative ${getChainColor()} rounded-lg p-2 mr-3`}>
            <img 
              src={getChainIcon()} 
              alt={chainName}
              className="w-6 h-6"
            />
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-white">
              {chainName}
            </h4>
            <span className="text-xs text-green-500 font-medium flex items-center">
              <span className="w-2 h-2 bg-green-500 rounded-full mr-1"></span>
              Live
            </span>
          </div>
        </div>
        <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full">
          {chain.toUpperCase()}
        </span>
      </div>
      
      {/* Balance Display */}
      <div className="mb-5">
        <p className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
          {balance || '0.00'}
        </p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Balance
        </p>
      </div>
      
      {/* Action Buttons - UPDATED: View & Buy */}
      <div className="flex space-x-3">
        <button 
          onClick={onViewClick}
          className="flex-1 bg-blue-500 hover:bg-blue-600 text-white py-2.5 px-4 rounded-lg font-medium transition-colors text-sm"
        >
          View
        </button>
        <button 
          onClick={() => onBuyClick(chain, address, chainName)}
          className="flex-1 bg-green-500 hover:bg-green-600 text-white py-2.5 px-4 rounded-lg font-medium transition-colors text-sm"
        >
          Buy
        </button>
      </div>
      
      {/* Address (Truncated) */}
      {address && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Your Address</p>
          <code className="text-xs font-mono text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 px-2 py-1 rounded break-all">
            {address}
          </code>
        </div>
      )}
    </div>
  );
};

export default ChainWalletCard;