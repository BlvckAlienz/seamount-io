// File: frontend/src/components/wallet/ReceiveModal.tsx
import React, { useState, useEffect } from 'react';
import QRCode from 'qrcode.react'; // Install: npm install qrcode.react

interface ReceiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  chain: string;
  address: string;
  chainName: string;
}

const ReceiveModal: React.FC<ReceiveModalProps> = ({ 
  isOpen, 
  onClose, 
  chain, 
  address, 
  chainName 
}) => {
  const [copied, setCopied] = useState(false);
  
  const handleCopyAddress = async () => {
    try {
      await navigator.clipboard.writeText(address);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy address:', err);
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = address;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };
  
  const getExplorerUrl = () => {
    const explorers: { [key: string]: string } = {
      bitcoin: `https://blockstream.info/address/${address}`,
      ethereum: `https://etherscan.io/address/${address}`,
      polygon: `https://polygonscan.com/address/${address}`,
      algorand: `https://algoexplorer.io/address/${address}`,
      arbitrum: `https://arbiscan.io/address/${address}`,
      ton: `https://tonscan.org/address/${address}`,
      tron: `https://tronscan.org/#/address/${address}`,
      solana: `https://explorer.solana.com/address/${address}`
    };
    return explorers[chain] || '#';
  };

  const getChainIcon = () => {
    const icons: { [key: string]: string } = {
      bitcoin: '/icons/bitcoin.png',
      ethereum: '/icons/ethereum.png', 
      polygon: '/icons/polygon.png',
      algorand: '/icons/algorand.png',
      arbitrum: '/icons/ethereum.png', // Use ETH icon for Arbitrum
      ton: '/icons/ton.png',
      tron: '/icons/tron.png',
      solana: '/icons/solana.png'
    };
    return icons[chain] || '/icons/crypto.png';
  };

  // Close modal on Escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div 
        className="bg-white dark:bg-gray-800 rounded-xl p-6 w-full max-w-md relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center">
            <img 
              src={getChainIcon()} 
              alt={chainName}
              className="w-8 h-8 mr-3"
            />
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
              Receive {chainName}
            </h3>
          </div>
          <button 
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 text-2xl font-light p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
          >
            ×
          </button>
        </div>
        
        {/* QR Code */}
        <div className="bg-white p-4 rounded-lg border-2 border-gray-200 dark:border-gray-600 mb-4 flex justify-center">
          {address ? (
            <QRCode 
              value={address} 
              size={200}
              level="M"
              includeMargin={false}
              fgColor="#1f2937"
              bgColor="#ffffff"
            />
          ) : (
            <div className="w-50 h-50 flex items-center justify-center text-gray-500">
              Generating QR code...
            </div>
          )}
        </div>
        
        {/* Address */}
        <div className="mb-6">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2 text-center">
            Your {chainName} Address
          </p>
          <div className="flex items-center justify-between bg-gray-50 dark:bg-gray-700 p-3 rounded-lg border border-gray-200 dark:border-gray-600">
            <code className="text-xs font-mono truncate flex-1 text-gray-800 dark:text-gray-200 mr-3">
              {address}
            </code>
            <button 
              onClick={handleCopyAddress}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                copied 
                  ? 'bg-green-500 text-white' 
                  : 'bg-blue-500 text-white hover:bg-blue-600'
              }`}
            >
              {copied ? '✓ Copied' : 'Copy'}
            </button>
          </div>
        </div>
        
        {/* Explorer Link */}
        <div className="text-center">
          <a 
            href={getExplorerUrl()} 
            target="_blank" 
            rel="noopener noreferrer"
            className="inline-flex items-center text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 text-sm font-medium transition-colors"
          >
            View on Explorer
            <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
          </a>
        </div>
        
        {/* Warning Message */}
        <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <p className="text-xs text-yellow-800 dark:text-yellow-200 text-center">
            ⚠️ Only send {chainName} ({chain.toUpperCase()}) to this address
          </p>
        </div>
      </div>
    </div>
  );
};

export default ReceiveModal;