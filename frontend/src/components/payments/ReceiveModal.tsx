// File Location: frontend/src/components/payments/ReceiveModal.tsx
import React, { useState } from 'react';
import { Copy, ExternalLink, Check, X, Download } from 'lucide-react';
import toast from 'react-hot-toast';
import QRCodeGenerator from '../QRCodeGenerator';

interface ReceiveModalProps {
  walletAddress: string;
  onClose: () => void;
}

const ReceiveModal: React.FC<ReceiveModalProps> = ({ walletAddress, onClose }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(walletAddress);
    setCopied(true);
    toast.success('Address copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownloadQR = () => {
    const canvas = document.querySelector('canvas');
    if (canvas) {
      const url = canvas.toDataURL('image/png');
      const a = document.createElement('a');
      a.href = url;
      a.download = `seamount-wallet-${walletAddress.slice(0, 8)}.png`;
      a.click();
      toast.success('QR code downloaded!');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-md w-full p-8 border border-gray-700 shadow-2xl animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-white">Receive Assets</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <p className="text-gray-400 text-sm mb-6">
          Share this address or QR code to receive payments
        </p>

        {/* QR Code */}
        <div className="bg-white p-6 rounded-xl mb-6 shadow-lg">
          <QRCodeGenerator data={walletAddress} size={240} />
        </div>

        {/* Address Display */}
        <div className="bg-gray-800/50 rounded-xl p-4 mb-4 border border-gray-700">
          <p className="text-xs text-gray-400 mb-2">Your Algorand Address</p>
          <p className="text-white font-mono text-sm break-all leading-relaxed">
            {walletAddress}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <button
            onClick={handleCopy}
            className={`flex items-center justify-center gap-2 py-3 rounded-xl font-medium transition-all ${
              copied
                ? 'bg-green-600 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied!' : 'Copy'}
          </button>

          <button
            onClick={handleDownloadQR}
            className="flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-xl font-medium transition-colors"
          >
            <Download className="h-4 w-4" />
            Save QR
          </button>
        </div>

        {/* Explorer Link */}
        
          href={`https://explorer.perawallet.app/address/${walletAddress}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 text-blue-400 hover:text-blue-300 text-sm transition-colors"
        <a>
          <ExternalLink className="h-4 w-4" />
          View on Explorer
        </a>

        {/* Info Banner */}
        <div className="mt-6 bg-blue-900/20 border border-blue-500/30 rounded-lg p-3">
          <p className="text-blue-300 text-xs">
            <strong>Multi-asset wallet:</strong> This address accepts ALGO, USDT, USDCa, goBTC, and goETH
          </p>
        </div>
      </div>
    </div>
  );
};

export default ReceiveModal;