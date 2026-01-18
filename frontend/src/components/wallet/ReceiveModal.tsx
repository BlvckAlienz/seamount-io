// File: frontend/src/components/wallet/ReceiveModal.tsx
/**
 * ✅ UNIFIED RECEIVE MODAL - Multi-Chain Support
 * Features:
 * - Multi-chain selection (Algorand, Bitcoin, Ethereum, Polygon, Tron, Solana)
 * - QR code generation with download
 * - Copy, download, and share functionality
 * - Chain-specific explorer links
 * - Seamount wallet integration
 */

import React, { useState, useEffect } from 'react';
import QRCode from 'qrcode.react';
import { Copy, ExternalLink, Check, X, Download, Share2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '@/contexts/AuthContext';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';

interface ReceiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  preselectedChain?: string; // Optional: auto-select chain
}

// ============================================================================
// CHAIN CONFIGURATION
// ============================================================================
const SUPPORTED_CHAINS = {
  algorand: {
    name: 'Algorand',
    icon: '◉',
    color: 'bg-gray-800',
    explorer: (addr: string) => `https://explorer.perawallet.app/address/${addr}`,
    assets: ['ALGO', 'USDT', 'USDCa', 'goBTC', 'goETH']
  },
  bitcoin: {
    name: 'Bitcoin',
    icon: '₿',
    color: 'bg-orange-600',
    explorer: (addr: string) => `https://blockstream.info/address/${addr}`,
    assets: ['BTC']
  },
  ethereum: {
    name: 'Ethereum',
    icon: 'Ξ',
    color: 'bg-indigo-600',
    explorer: (addr: string) => `https://etherscan.io/address/${addr}`,
    assets: ['ETH', 'USDT', 'USDC']
  },
  polygon: {
    name: 'Polygon',
    icon: '⬣',
    color: 'bg-purple-600',
    explorer: (addr: string) => `https://polygonscan.com/address/${addr}`,
    assets: ['MATIC', 'USDT', 'USDC']
  },
  tron: {
    name: 'TRON',
    icon: '⚡',
    color: 'bg-red-600',
    explorer: (addr: string) => `https://tronscan.org/#/address/${addr}`,
    assets: ['TRX', 'USDT']
  },
  solana: {
    name: 'Solana',
    icon: '◎',
    color: 'bg-green-600',
    explorer: (addr: string) => `https://explorer.solana.com/address/${addr}`,
    assets: ['SOL', 'USDT', 'USDC']
  }
};

const ReceiveModal: React.FC<ReceiveModalProps> = ({ 
  isOpen, 
  onClose,
  preselectedChain
}) => {
  const { userProfile } = useAuth();
  const [selectedChain, setSelectedChain] = useState<string>(preselectedChain || 'algorand');
  const [walletAddress, setWalletAddress] = useState<string>('');
  const [copied, setCopied] = useState(false);

  // ============================================================================
  // GET WALLET ADDRESS FOR SELECTED CHAIN
  // ============================================================================
  useEffect(() => {
    if (!userProfile) return;

    // Map chain to userProfile field
    const addressMap: { [key: string]: string | undefined } = {
      algorand: userProfile.algorand_address,
      bitcoin: userProfile.bitcoin_address,
      ethereum: userProfile.ethereum_address,
      polygon: userProfile.polygon_address,
      tron: userProfile.tron_address,
      solana: userProfile.solana_address
    };

    const address = addressMap[selectedChain];
    
    if (address) {
      setWalletAddress(address);
    } else {
      setWalletAddress('');
      toast.error(`No ${SUPPORTED_CHAINS[selectedChain as keyof typeof SUPPORTED_CHAINS]?.name} wallet found`);
    }
  }, [selectedChain, userProfile]);

  // ============================================================================
  // COPY ADDRESS
  // ============================================================================
  const handleCopy = async () => {
    if (!walletAddress) return;
    
    try {
      await navigator.clipboard.writeText(walletAddress);
      setCopied(true);
      toast.success('Address copied!', { icon: '📋' });
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('Failed to copy');
    }
  };

  // ============================================================================
  // DOWNLOAD QR CODE
  // ============================================================================
  const handleDownloadQR = () => {
    if (!walletAddress) return;
    
    const canvas = document.querySelector('canvas');
    if (canvas) {
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `seamount-${selectedChain}-${walletAddress.slice(0, 8)}.png`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast.success('QR code downloaded!', { icon: '💾' });
        }
      });
    } else {
      toast.error('QR code not available');
    }
  };

  // ============================================================================
  // SHARE ADDRESS
  // ============================================================================
  const handleShare = async () => {
    if (!walletAddress) return;
    
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Seamount ${SUPPORTED_CHAINS[selectedChain as keyof typeof SUPPORTED_CHAINS]?.name} Address`,
          text: `Send crypto to my Seamount wallet: ${walletAddress}`,
        });
        toast.success('Shared successfully!', { icon: '✅' });
      } catch (error: any) {
        if (error.name !== 'AbortError') {
          toast.error('Failed to share');
        }
      }
    } else {
      // Fallback to copy
      handleCopy();
    }
  };

  // ============================================================================
  // BACKDROP CLICK
  // ============================================================================
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  // ============================================================================
  // CLOSE ON ESCAPE
  // ============================================================================
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

  const chainConfig = SUPPORTED_CHAINS[selectedChain as keyof typeof SUPPORTED_CHAINS];

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200"
      onClick={handleBackdropClick}
    >
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-md w-full p-6 md:p-8 border border-gray-700 shadow-2xl animate-in zoom-in-95 duration-200">
        {/* ========== HEADER ========== */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 ${chainConfig?.color} rounded-full flex items-center justify-center text-2xl`}>
              {chainConfig?.icon}
            </div>
            <div>
              <h2 className="text-xl md:text-2xl font-bold text-white">Receive Assets</h2>
              <p className="text-sm text-gray-400">On {chainConfig?.name}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ========== CHAIN SELECTOR ========== */}
        <div className="mb-6">
          <Label className="text-sm font-semibold text-gray-300 mb-2 block">Select Blockchain</Label>
          <Select value={selectedChain} onValueChange={setSelectedChain}>
            <SelectTrigger className="bg-gray-800 border-gray-600 text-white h-12">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-gray-800 border-gray-600">
              {Object.entries(SUPPORTED_CHAINS).map(([key, chain]) => (
                <SelectItem key={key} value={key} className="text-white hover:bg-gray-700">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{chain.icon}</span>
                    <span>{chain.name}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* ========== QR CODE ========== */}
        {walletAddress ? (
          <>
            <div className="bg-white p-4 md:p-6 rounded-xl mb-6 shadow-lg flex items-center justify-center">
              <QRCode 
                value={walletAddress} 
                size={240}
                level="M"
                includeMargin={false}
                fgColor="#1f2937"
                bgColor="#ffffff"
              />
            </div>

            {/* ========== ADDRESS DISPLAY ========== */}
            <div className="bg-gray-800/50 rounded-xl p-4 mb-4 border border-gray-700">
              <p className="text-xs text-gray-400 mb-2">Your {chainConfig?.name} Address</p>
              <p className="text-white font-mono text-xs md:text-sm break-all leading-relaxed">
                {walletAddress}
              </p>
            </div>

            {/* ========== ACTION BUTTONS ========== */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <button
                onClick={handleCopy}
                className={`flex flex-col items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all ${
                  copied
                    ? 'bg-green-600 text-white'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {copied ? <Check className="h-5 w-5" /> : <Copy className="h-5 w-5" />}
                <span className="text-xs">{copied ? 'Copied!' : 'Copy'}</span>
              </button>

              <button
                onClick={handleDownloadQR}
                className="flex flex-col items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-xl font-medium transition-colors"
              >
                <Download className="h-5 w-5" />
                <span className="text-xs">Save QR</span>
              </button>

              <button
                onClick={handleShare}
                className="flex flex-col items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-xl font-medium transition-colors"
              >
                <Share2 className="h-5 w-5" />
                <span className="text-xs">Share</span>
              </button>
            </div>

            {/* ========== EXPLORER LINK ========== */}
            
              href={chainConfig?.explorer(walletAddress)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 text-blue-400 hover:text-blue-300 text-sm transition-colors py-2"
            <a>
              <ExternalLink className="h-4 w-4" />
              View on {chainConfig?.name} Explorer
            </a>

            {/* ========== SUPPORTED ASSETS INFO ========== */}
            <div className="mt-4 bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
              <p className="text-blue-300 text-xs text-center">
                <strong>Supported assets:</strong> {chainConfig?.assets.join(', ')}
              </p>
            </div>
          </>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-400">No wallet address available for {chainConfig?.name}</p>
            <p className="text-sm text-gray-500 mt-2">Create a wallet first in Settings</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReceiveModal;