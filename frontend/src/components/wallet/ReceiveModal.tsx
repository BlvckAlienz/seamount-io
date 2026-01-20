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
import QRCode from "react-qr-code";
import { Copy, ExternalLink, Check, X, Download, Share2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '@/contexts/AuthContext';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';

interface ReceiveModalProps {
  isOpen: boolean;
  onClose: () => void;
  preselectedChain?: string; // Optional: auto-select chain
  walletAddresses?: { [chain: string]: string }; // ✅ ADD THIS
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
  preselectedChain,
  walletAddresses // ✅ ADD THIS
}) => {
  const { userProfile } = useAuth();
  const [selectedChain, setSelectedChain] = useState<string>(preselectedChain || 'algorand');
  const [walletAddress, setWalletAddress] = useState<string>('');
  const [copied, setCopied] = useState(false);

  // ============================================================================
  // GET WALLET ADDRESS FOR SELECTED CHAIN
  // ============================================================================
  useEffect(() => {
    console.log('🔍 ReceiveModal Debug:', {
      selectedChain,
      walletAddresses,
      specificAddress: walletAddresses?.[selectedChain],
      allChains: Object.keys(walletAddresses || {})
    });

    // ✅ PRIORITY 1: Use passed wallet addresses (from parent component)
    if (walletAddresses && walletAddresses[selectedChain]) {
      console.log('✅ Found wallet address:', walletAddresses[selectedChain]);
      setWalletAddress(walletAddresses[selectedChain]);
      return;
    }

    // ✅ PRIORITY 2: Fallback to userProfile (for Algorand legacy support)
    if (!userProfile) {
      console.log('⚠️ No userProfile available');
      setWalletAddress('');
      return;
    }

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
      console.log('✅ Found address in userProfile:', address);
      setWalletAddress(address);
    } else {
      console.warn(`❌ No ${selectedChain} wallet found in either source`);
      setWalletAddress('');
    }
  }, [selectedChain, userProfile, walletAddresses]);

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
    
    try {
      // Find the SVG element (react-qr-code renders SVG)
      const svgElement = document.querySelector('#qr-code-svg') as SVGElement;
      
      if (!svgElement) {
        toast.error('QR code not ready yet');
        return;
      }

      // Get SVG data
      const svgData = new XMLSerializer().serializeToString(svgElement);
      const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
      const svgUrl = URL.createObjectURL(svgBlob);

      // Create canvas to convert SVG to PNG
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      img.onload = () => {
        // Set canvas size to match QR code
        canvas.width = img.width;
        canvas.height = img.height;

        // Draw white background
        ctx!.fillStyle = '#ffffff';
        ctx!.fillRect(0, 0, canvas.width, canvas.height);

        // Draw QR code
        ctx!.drawImage(img, 0, 0);

        // Convert to blob and download
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
            URL.revokeObjectURL(svgUrl);
            toast.success('QR code downloaded!', { icon: '💾' });
          }
        }, 'image/png');
      };

      img.onerror = () => {
        URL.revokeObjectURL(svgUrl);
        toast.error('Failed to generate QR image');
      };

      img.src = svgUrl;

    } catch (error) {
      console.error('QR download error:', error);
      toast.error('Download failed');
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
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-2 sm:p-4 animate-in fade-in duration-200"
      onClick={handleBackdropClick}
    >
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-xl sm:rounded-2xl max-w-md w-full max-h-[95vh] sm:max-h-[90vh] overflow-y-auto p-4 sm:p-6 md:p-8 border border-gray-700 shadow-2xl animate-in zoom-in-95 duration-200">
        {/* ========== HEADER ========== */}
        <div className="flex items-center justify-between mb-4 sm:mb-6">
          <div className="flex items-center gap-2 sm:gap-3">
            <div className={`w-8 h-8 sm:w-10 sm:h-10 ${chainConfig?.color} rounded-full flex items-center justify-center text-xl sm:text-2xl flex-shrink-0`}>
              {chainConfig?.icon}
            </div>
            <div className="min-w-0">
              <h2 className="text-lg sm:text-xl md:text-2xl font-bold text-white truncate">Receive Assets</h2>
              <p className="text-xs sm:text-sm text-gray-400 truncate">On {chainConfig?.name}</p>
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
        <div className="mb-4 sm:mb-6">
          <Label className="text-xs sm:text-sm font-semibold text-gray-300 mb-2 block">Select Blockchain</Label>
          <Select value={selectedChain} onValueChange={setSelectedChain}>
            <SelectTrigger className="bg-gray-800 border-gray-600 text-white h-10 sm:h-12 text-sm sm:text-base">
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

        {/* ========== CONDITIONAL CONTENT ========== */}
        {walletAddress ? (
          <>
            {/* ========== QR CODE ========== */}
            <div className="bg-white p-3 sm:p-4 md:p-6 rounded-lg sm:rounded-xl mb-4 sm:mb-6 shadow-lg flex items-center justify-center">
              <div className="w-full max-w-[240px] aspect-square">
                <QRCode 
                  id="qr-code-svg"
                  value={walletAddress} 
                  size={240}
                  style={{ height: "100%", maxWidth: "100%", width: "100%" }}
                  fgColor="#1f2937"
                  bgColor="#ffffff"
                />
              </div>
            </div>

            {/* ========== ADDRESS DISPLAY ========== */}
            <div className="bg-gray-800/50 rounded-lg sm:rounded-xl p-3 sm:p-4 mb-3 sm:mb-4 border border-gray-700">
              <p className="text-[10px] sm:text-xs text-gray-400 mb-1 sm:mb-2">
                Your {chainConfig?.name} Address
              </p>
              <p className="text-white font-mono text-[10px] sm:text-xs md:text-sm break-all leading-relaxed">
                {walletAddress}
              </p>
            </div>

            {/* ========== ACTION BUTTONS ========== */}
            <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-3 sm:mb-4">
              <button
                onClick={handleCopy}
                className={`flex flex-col items-center justify-center gap-1 sm:gap-2 py-2 sm:py-3 rounded-lg sm:rounded-xl font-medium transition-all ${
                  copied
                    ? "bg-green-600 text-white"
                    : "bg-blue-600 hover:bg-blue-700 text-white"
                }`}
              >
                {copied ? (
                  <Check className="h-4 w-4 sm:h-5 sm:w-5" />
                ) : (
                  <Copy className="h-4 w-4 sm:h-5 sm:w-5" />
                )}
                <span className="text-[10px] sm:text-xs">
                  {copied ? "Copied!" : "Copy"}
                </span>
              </button>

              <button
                onClick={handleDownloadQR}
                className="flex flex-col items-center justify-center gap-1 sm:gap-2 bg-gray-700 hover:bg-gray-600 text-white py-2 sm:py-3 rounded-lg sm:rounded-xl font-medium transition-colors"
              >
                <Download className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="text-[10px] sm:text-xs">Save QR</span>
              </button>

              <button
                onClick={handleShare}
                className="flex flex-col items-center justify-center gap-1 sm:gap-2 bg-gray-700 hover:bg-gray-600 text-white py-2 sm:py-3 rounded-lg sm:rounded-xl font-medium transition-colors"
              >
                <Share2 className="h-4 w-4 sm:h-5 sm:w-5" />
                <span className="text-[10px] sm:text-xs">Share</span>
              </button>
            </div>

            {/* ========== EXPLORER LINK ========== */}
            {chainConfig?.explorer && walletAddress && (
              <a
                href={chainConfig.explorer(walletAddress)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-1 sm:gap-2 text-blue-400 hover:text-blue-300 text-xs sm:text-sm transition-colors py-2 mb-3"
              >
                <ExternalLink className="h-3 w-3 sm:h-4 sm:w-4" />
                <span className="truncate">View on {chainConfig?.name} Explorer</span>
              </a>
            )}

            {/* ========== SUPPORTED ASSETS INFO ========== */}
            <div className="mt-3 sm:mt-4 bg-blue-900/20 border border-blue-500/30 rounded-lg p-2 sm:p-3">
              <p className="text-blue-300 text-[10px] sm:text-xs text-center leading-relaxed">
                <strong>Supported assets:</strong> {chainConfig?.assets.join(', ')}
              </p>
            </div>
          </>
        ) : (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">{chainConfig?.icon}</span>
            </div>
            <p className="text-gray-400 font-semibold mb-2">No {chainConfig?.name} Wallet Found</p>
            <p className="text-sm text-gray-500 mb-4">Create a {chainConfig?.name} wallet to receive funds</p>
            <button
              onClick={() => {
                onClose();
                window.location.href = '/dashboard';
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
            >
              Create {chainConfig?.name} Wallet
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReceiveModal;