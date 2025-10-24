// File: frontend/src/components/payments/ReceiveModal.tsx
// Replace the entire file with this:

import React, { useState, useEffect } from 'react';
import { Copy, ExternalLink, Check, X, Download, Share2 } from 'lucide-react';
import toast from 'react-hot-toast';
import QRCodeGenerator from '../QRCodeGenerator';
import { useAuth } from '../../contexts/AuthContext';

interface ReceiveModalProps {
  onClose: () => void;
}

const ReceiveModal: React.FC<ReceiveModalProps> = ({ onClose }) => {
  const [copied, setCopied] = useState(false);
  const [walletAddress, setWalletAddress] = useState<string>('');
  const { userProfile } = useAuth();

  useEffect(() => {
    // ✅ Use Seamount's Algorand wallet address, not external wallets
    if (userProfile?.algorand_address) {
      setWalletAddress(userProfile.algorand_address);
    } else {
      toast.error('No Seamount wallet found');
      onClose();
    }
  }, [userProfile, onClose]);

  const handleCopy = async () => {
    if (!walletAddress) return;
    
    try {
      await navigator.clipboard.writeText(walletAddress);
      setCopied(true);
      toast.success('Address copied!');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('Failed to copy');
    }
  };

  const handleDownloadQR = () => {
    if (!walletAddress) return;
    
    const canvas = document.querySelector('canvas');
    if (canvas) {
      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `seamount-wallet-${walletAddress.slice(0, 8)}.png`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          toast.success('QR code downloaded!');
        }
      });
    } else {
      toast.error('QR code not available');
    }
  };

  const handleShare = async () => {
    if (!walletAddress) return;
    
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Seamount Wallet Address',
          text: `Send crypto to my Seamount Algorand wallet: ${walletAddress}`,
        });
        toast.success('Shared successfully!');
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

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  if (!walletAddress) {
    return (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div className="bg-gray-800 rounded-2xl p-6">
          <p className="text-white">Loading wallet address...</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200"
      onClick={handleBackdropClick}
    >
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-md w-full p-6 md:p-8 border border-gray-700 shadow-2xl animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl md:text-2xl font-bold text-white">Receive Assets</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="text-gray-400 text-sm mb-6">
          Share your Seamount wallet address to receive payments
        </p>

        {/* QR Code */}
        <div className="bg-white p-4 md:p-6 rounded-xl mb-6 shadow-lg flex items-center justify-center">
          <QRCodeGenerator data={walletAddress} size={240} />
        </div>

        {/* Address Display */}
        <div className="bg-gray-800/50 rounded-xl p-4 mb-4 border border-gray-700">
          <p className="text-xs text-gray-400 mb-2">Your Seamount Wallet Address</p>
          <p className="text-white font-mono text-xs md:text-sm break-all leading-relaxed">
            {walletAddress}
          </p>
        </div>

        {/* Action Buttons */}
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

        {/* Explorer Link */}
        <a
          href={`https://explorer.perawallet.app/address/${walletAddress}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 text-blue-400 hover:text-blue-300 text-sm transition-colors py-2"
        >
          <ExternalLink className="h-4 w-4" />
          View on Algorand Explorer
        </a>

        {/* Info Banner */}
        <div className="mt-4 bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
          <p className="text-blue-300 text-xs text-center">
            <strong>Multi-asset wallet:</strong> Accepts ALGO, USDT, USDCa, goBTC, and goETH
          </p>
        </div>
      </div>
    </div>
  );
};

export default ReceiveModal;