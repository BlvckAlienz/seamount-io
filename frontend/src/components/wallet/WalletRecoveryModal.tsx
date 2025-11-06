// File: frontend/src/components/wallet/WalletRecoveryModal.tsx
// 🔥 STREAMLINED: No test, no instructions, auto-dismiss after download

import React, { useState, useEffect } from 'react';
import { X, Download, Check, AlertTriangle, Copy, Eye, EyeOff, Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import { seedAPI, apiClient } from '../../config/api';

interface RecoverySeeds {
  algorand_seed?: string;
  wdk_seed?: string;
  wallet_addresses: { [key: string]: string };
  security_warning: string;
}

interface WalletRecoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const WalletRecoveryModal: React.FC<WalletRecoveryModalProps> = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [seeds, setSeeds] = useState<RecoverySeeds | null>(null);
  const [showSeeds, setShowSeeds] = useState(false);
  const [copiedAlgo, setCopiedAlgo] = useState(false);
  const [copiedWdk, setCopiedWdk] = useState(false);
  const [algoDownloaded, setAlgoDownloaded] = useState(false);
  const [wdkDownloaded, setWdkDownloaded] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchSeeds();
    }
  }, [isOpen]);

  const fetchSeeds = async () => {
    try {
      setLoading(true);
      const response = await seedAPI.getRecoverySeeds();
      
      if (response.data.success) {
        setSeeds(response.data);
        toast.success('✅ Seed phrases decrypted successfully');
      } else {
        toast.error(response.data.error || 'Failed to retrieve seeds');
      }
    } catch (error: any) {
      console.error('Seed recovery error:', error);
      
      if (error.response?.status === 429) {
        toast.error('⏰ Rate limit: Max 3 requests/hour');
        return;
      }
      
      const errorMsg = error.response?.data?.detail || 
                      error.response?.data?.error ||
                      'Failed to retrieve seed phrases';
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadAlgorand = async () => {
    if (!seeds?.algorand_seed) return;

    const content = `
SEAMOUNT ALGORAND WALLET RECOVERY
==================================
⚠️ KEEP THIS FILE SECURE - NEVER SHARE IT
Generated: ${new Date().toISOString()}

🌐 ALGORAND SEED PHRASE (25 words)
----------------------------------
${seeds.algorand_seed}

Address: ${seeds.wallet_addresses?.algorand || 'N/A'}

⚠️ SECURITY WARNING
-------------------
${seeds.security_warning}
    `.trim();

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seamount-algorand-recovery-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success('✅ Algorand seed downloaded');
    setAlgoDownloaded(true);
    
    // Mark as backed up
    try {
      await apiClient.post('/api/v1/wallet-backup/mark-backed-up', { chains: ['algorand'] });
    } catch (error) {
      console.error('Failed to mark backup:', error);
    }

    checkAndDismiss();
  };

  const handleDownloadWDK = async () => {
    if (!seeds?.wdk_seed) return;

    const content = `
SEAMOUNT MULTI-CHAIN WALLET RECOVERY (WDK)
===========================================
⚠️ KEEP THIS FILE SECURE - NEVER SHARE IT
Generated: ${new Date().toISOString()}

🔗 MULTI-CHAIN SEED PHRASE (12 words)
-------------------------------------
${seeds.wdk_seed}

Supported Chains:
${Object.entries(seeds.wallet_addresses || {})
  .filter(([chain]) => chain !== 'algorand')
  .map(([chain, address]) => `  ${chain.toUpperCase()}: ${address}`)
  .join('\n')}

⚠️ SECURITY WARNING
-------------------
${seeds.security_warning}
    `.trim();

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seamount-multichain-recovery-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success('✅ Multi-chain seed downloaded');
    setWdkDownloaded(true);
    
    // Mark as backed up
    try {
      await apiClient.post('/api/v1/wallet-backup/mark-backed-up', { 
        chains: ['bitcoin', 'ethereum', 'polygon', 'tron'] 
      });
    } catch (error) {
      console.error('Failed to mark backup:', error);
    }

    checkAndDismiss();
  };

  const checkAndDismiss = () => {
    // Determine which seeds the user actually has
    const hasAlgoSeed = !!seeds?.algorand_seed;
    const hasWdkSeed = !!seeds?.wdk_seed;
    
    // Check if each available seed is backed up
    const algoComplete = hasAlgoSeed ? algoDownloaded : true; // No Algo wallet = auto-complete
    const wdkComplete = hasWdkSeed ? wdkDownloaded : true;    // No WDK wallet = auto-complete
    
    // Only dismiss if ALL AVAILABLE seeds are backed up
    if (algoComplete && wdkComplete) {
      const message = hasAlgoSeed && hasWdkSeed 
        ? '🎉 All seeds backed up! This modal will not appear again.'
        : '🎉 Seed backed up! This modal will not appear again.';
      
      toast.success(message);
      
      setTimeout(() => {
        onClose();
      }, 2000);
    }
  };

  const handleCopy = (text: string, type: 'algo' | 'wdk') => {
    navigator.clipboard.writeText(text);
    if (type === 'algo') {
      setCopiedAlgo(true);
      setTimeout(() => setCopiedAlgo(false), 2000);
    } else {
      setCopiedWdk(true);
      setTimeout(() => setCopiedWdk(false), 2000);
    }
    toast.success(`${type === 'algo' ? 'Algorand' : 'Multi-chain'} seed copied!`);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-2 sm:p-4">
      <div className="bg-white dark:bg-white rounded-2xl max-w-5xl w-full max-h-[92vh] overflow-hidden border-2 border-red-300 shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-red-500 to-orange-500 p-4 sm:p-6 border-b-2 border-red-600">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-2 sm:p-3 rounded-lg">
                <Shield className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
              </div>
              <div>
                <h2 className="text-xl sm:text-2xl font-bold text-white">🔐 Wallet Recovery Seeds</h2>
                <p className="text-red-50 text-sm sm:text-base">CRITICAL: Download both seed files now</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
            >
              <X className="w-5 h-5 sm:w-6 sm:h-6" />
            </button>
          </div>
        </div>

        {/* Content - Make scrollable on mobile */}
        <div className="p-3 sm:p-6 overflow-auto max-h-[calc(92vh-180px)]">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-red-600 mx-auto mb-4"></div>
                <p className="text-gray-700 font-medium">Decrypting your seed phrases...</p>
              </div>
            </div>
          ) : seeds ? (
            <>
              {/* Security Warning Banner */}
              <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4 sm:p-6 mb-4 sm:mb-6">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 sm:w-6 sm:h-6 text-red-600 flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="text-base sm:text-lg font-bold text-red-700 mb-2">⚠️ CRITICAL SECURITY WARNING</h3>
                    <div className="text-red-800 text-sm space-y-1 font-medium">
                      {seeds.security_warning.split('\n').map((line, i) => (
                        <p key={i}>{line}</p>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Download Progress */}
              <div className="bg-gray-100 border-2 border-gray-300 rounded-xl p-3 sm:p-4 mb-4 sm:mb-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <span className="text-gray-900 font-semibold">Download Progress:</span>
                  <div className="flex items-center gap-4">
                    <div className={`flex items-center gap-2 ${algoDownloaded ? 'text-green-600' : 'text-gray-500'}`}>
                      {algoDownloaded ? <Check className="w-5 h-5" /> : <Download className="w-5 h-5" />}
                      <span className="font-semibold text-sm sm:text-base">Algorand</span>
                    </div>
                    <div className={`flex items-center gap-2 ${wdkDownloaded ? 'text-green-600' : 'text-gray-500'}`}>
                      {wdkDownloaded ? <Check className="w-5 h-5" /> : <Download className="w-5 h-5" />}
                      <span className="font-semibold text-sm sm:text-base">Multi-Chain</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3 mb-4 sm:mb-6">
                <button
                  onClick={() => setShowSeeds(!showSeeds)}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 sm:px-6 py-2 sm:py-3 rounded-xl font-bold text-white transition-all text-sm sm:text-base"
                >
                  {showSeeds ? <EyeOff className="w-4 h-4 sm:w-5 sm:h-5" /> : <Eye className="w-4 h-4 sm:w-5 sm:h-5" />}
                  {showSeeds ? 'Hide Seeds' : 'Reveal Seeds'}
                </button>
              </div>

              {/* Algorand Seed */}
              {seeds.algorand_seed && (
                <div className="bg-blue-50 border-2 border-blue-300 rounded-xl p-4 sm:p-6 mb-4 sm:mb-6">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-3">
                    <div>
                      <h3 className="text-lg sm:text-xl font-bold text-gray-900">🌐 Algorand Wallet</h3>
                      <p className="text-gray-700 text-sm font-medium">25-word recovery phrase</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleCopy(seeds.algorand_seed!, 'algo')}
                        className="p-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors border-2 border-gray-300"
                      >
                        {copiedAlgo ? <Check className="w-5 h-5 text-green-600" /> : <Copy className="w-5 h-5 text-gray-700" />}
                      </button>
                      <button
                        onClick={handleDownloadAlgorand}
                        disabled={algoDownloaded}
                        className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg font-bold transition-all text-sm sm:text-base ${
                          algoDownloaded
                            ? 'bg-green-600 text-white cursor-not-allowed border-2 border-green-700'
                            : 'bg-green-600 hover:bg-green-700 text-white border-2 border-green-700'
                        }`}
                      >
                        {algoDownloaded ? <Check className="w-4 h-4 sm:w-5 sm:h-5" /> : <Download className="w-4 h-4 sm:w-5 sm:h-5" />}
                        <span className="hidden sm:inline">{algoDownloaded ? 'Downloaded' : 'Download'}</span>
                      </button>
                    </div>
                  </div>
                  
                  <div className="relative">
                    <div className={`font-mono text-xs sm:text-sm p-3 sm:p-4 rounded-lg border-2 ${
                      showSeeds ? 'bg-white border-blue-400 text-gray-900' : 'bg-gray-100 border-gray-300'
                    }`}>
                      {showSeeds ? (
                        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                          {seeds.algorand_seed.split(' ').map((word, i) => (
                            <span key={i} className="text-blue-600 font-semibold">{i + 1}. {word}</span>
                          ))}
                        </div>
                      ) : (
                        <div className="text-gray-600 text-center py-4 font-medium">
                          Click "Reveal Seeds" to view your recovery phrase
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 text-sm text-gray-700 bg-white p-3 rounded-lg border-2 border-blue-200">
                    <p className="font-semibold">Address:</p>
                    <p className="font-mono text-xs sm:text-sm text-gray-900 break-all">{seeds.wallet_addresses?.algorand}</p>
                  </div>
                </div>
              )}

              {/* WDK Multi-Chain Seed */}
              {seeds.wdk_seed && (
                <div className="bg-purple-50 border-2 border-purple-300 rounded-xl p-4 sm:p-6 mb-4 sm:mb-6">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-4 gap-3">
                    <div>
                      <h3 className="text-lg sm:text-xl font-bold text-gray-900">🔗 Multi-Chain Wallet</h3>
                      <p className="text-gray-700 text-sm font-medium">12-word BIP39 phrase (Bitcoin, Ethereum, Polygon, TRON)</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleCopy(seeds.wdk_seed!, 'wdk')}
                        className="p-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors border-2 border-gray-300"
                      >
                        {copiedWdk ? <Check className="w-5 h-5 text-green-600" /> : <Copy className="w-5 h-5 text-gray-700" />}
                      </button>
                      <button
                        onClick={handleDownloadWDK}
                        disabled={wdkDownloaded}
                        className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg font-bold transition-all text-sm sm:text-base ${
                          wdkDownloaded
                            ? 'bg-green-600 text-white cursor-not-allowed border-2 border-green-700'
                            : 'bg-green-600 hover:bg-green-700 text-white border-2 border-green-700'
                        }`}
                      >
                        {wdkDownloaded ? <Check className="w-4 h-4 sm:w-5 sm:h-5" /> : <Download className="w-4 h-4 sm:w-5 sm:h-5" />}
                        <span className="hidden sm:inline">{wdkDownloaded ? 'Downloaded' : 'Download'}</span>
                      </button>
                    </div>
                  </div>
                  
                  <div className="relative">
                    <div className={`font-mono text-xs sm:text-sm p-3 sm:p-4 rounded-lg border-2 ${
                      showSeeds ? 'bg-white border-purple-400 text-gray-900' : 'bg-gray-100 border-gray-300'
                    }`}>
                      {showSeeds ? (
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                          {seeds.wdk_seed.split(' ').map((word, i) => (
                            <span key={i} className="text-purple-600 font-semibold">{i + 1}. {word}</span>
                          ))}
                        </div>
                      ) : (
                        <div className="text-gray-600 text-center py-4 font-medium">
                          Click "Reveal Seeds" to view your recovery phrase
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 space-y-2 text-sm text-gray-700 bg-white p-3 rounded-lg border-2 border-purple-200">
                    <p className="font-semibold">Supported Chains:</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {Object.entries(seeds.wallet_addresses || {})
                        .filter(([chain]) => chain !== 'algorand')
                        .map(([chain, address]) => (
                          <div key={chain} className="bg-gray-100 p-2 rounded border border-gray-300">
                            <p className="text-gray-600 text-xs uppercase font-bold">{chain}</p>
                            <p className="font-mono text-xs text-gray-900 truncate">{address}</p>
                          </div>
                        ))}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="text-center text-gray-700 py-12">
              <Shield className="w-16 h-16 mx-auto mb-4 opacity-50 text-gray-400" />
              <h3 className="text-xl font-bold mb-2 text-gray-900">No Seeds Available</h3>
              <p className="text-gray-600">Your wallet seeds could not be retrieved. Please contact support.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-100 border-t-2 border-gray-300 p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <p className="text-gray-700 text-sm font-medium">
              🔒 Seeds are decrypted in-memory and never stored unencrypted
            </p>
            <button
              onClick={onClose}
              className="bg-gray-700 hover:bg-gray-800 px-4 sm:px-6 py-2 sm:py-3 rounded-xl font-bold text-white transition-all text-sm sm:text-base"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default WalletRecoveryModal;