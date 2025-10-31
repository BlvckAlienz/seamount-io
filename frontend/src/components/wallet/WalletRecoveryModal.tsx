// File: frontend/src/components/wallet/WalletRecoveryModal.tsx
// 🔐 BEAUTIFUL WALLET RECOVERY MODAL WITH BACKUP VERIFICATION

import React, { useState, useEffect } from 'react';
import { X, Download, Check, AlertTriangle, Copy, Eye, EyeOff, Shield } from 'lucide-react';
import toast from 'react-hot-toast';
import { apiClient } from '../../config/api';

interface RecoverySeeds {
  algorand_seed?: string;
  wdk_seed?: string;
  wallet_addresses: { [key: string]: string };
  security_warning: string;
  backup_instructions: string;
  algorand_info?: any;
  wdk_info?: any;
}

interface WalletRecoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const WalletRecoveryModal: React.FC<WalletRecoveryModalProps> = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [seeds, setSeeds] = useState<RecoverySeeds | null>(null);
  const [showSeeds, setShowSeeds] = useState(false);
  const [verificationStep, setVerificationStep] = useState(1);
  const [testInput, setTestInput] = useState('');
  const [verified, setVerified] = useState(false);
  const [copiedAlgo, setCopiedAlgo] = useState(false);
  const [copiedWdk, setCopiedWdk] = useState(false);

  useEffect(() => {
    if (isOpen) {
      fetchSeeds();
    }
  }, [isOpen]);

  const fetchSeeds = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/seeds/recovery');
      
      if (response.data.success) {
        setSeeds(response.data);
        toast.success('✅ Seed phrases decrypted successfully');
      } else {
        toast.error(response.data.error || 'Failed to retrieve seeds');
      }
    } catch (error: any) {
      console.error('Seed recovery error:', error);
      const errorMsg = error.response?.data?.detail || 'Failed to retrieve seed phrases';
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!seeds) return;

    const content = `
SEAMOUNT WALLET RECOVERY SEEDS
===============================
⚠️ CRITICAL: KEEP THIS FILE SECURE
Generated: ${new Date().toISOString()}

🌐 ALGORAND WALLET
------------------
Seed Phrase: ${seeds.algorand_seed || 'N/A'}
Address: ${seeds.wallet_addresses?.algorand || 'N/A'}
Compatible Wallets: Pera Wallet, Defly Wallet, AlgoSigner

🔗 MULTI-CHAIN WALLET (WDK)
---------------------------
Seed Phrase: ${seeds.wdk_seed || 'N/A'}
Supported Chains: Bitcoin, Ethereum, Polygon, TRON

Addresses:
${Object.entries(seeds.wallet_addresses || {})
  .filter(([chain]) => chain !== 'algorand')
  .map(([chain, address]) => `  ${chain.toUpperCase()}: ${address}`)
  .join('\n')}

Compatible Wallets: MetaMask, Trust Wallet, Ledger, Trezor

⚠️ SECURITY WARNING
-------------------
${seeds.security_warning}

📋 BACKUP INSTRUCTIONS
----------------------
${seeds.backup_instructions}
    `.trim();

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seamount-wallet-recovery-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast.success('✅ Recovery file downloaded');
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

  const handleVerifyBackup = () => {
    if (!seeds) return;

    const normalizeWords = (phrase: string) => 
      phrase.toLowerCase().trim().replace(/\s+/g, ' ');

    const algoMatch = seeds.algorand_seed && 
      normalizeWords(testInput) === normalizeWords(seeds.algorand_seed);
    
    const wdkMatch = seeds.wdk_seed && 
      normalizeWords(testInput) === normalizeWords(seeds.wdk_seed);

    if (algoMatch || wdkMatch) {
      setVerified(true);
      toast.success('✅ Backup verified! You stored it correctly.');
    } else {
      toast.error('❌ Phrases don\'t match. Please try again.');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden border border-red-500/30 shadow-2xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-red-600 to-orange-600 p-6 border-b border-red-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-3 rounded-lg">
                <Shield className="w-8 h-8 text-white" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">🔐 Wallet Recovery Seeds</h2>
                <p className="text-red-100 text-sm">CRITICAL: Store these safely offline</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/20 rounded-lg transition-colors text-white"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="p-6 overflow-auto max-h-[calc(90vh-120px)]">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mx-auto mb-4"></div>
                <p className="text-gray-400">Decrypting your seed phrases...</p>
              </div>
            </div>
          ) : seeds ? (
            <>
              {/* Security Warning Banner */}
              <div className="bg-red-900/20 border border-red-500/50 rounded-xl p-6 mb-6">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0 mt-1" />
                  <div>
                    <h3 className="text-lg font-bold text-red-400 mb-2">⚠️ CRITICAL SECURITY WARNING</h3>
                    <div className="text-red-200 text-sm space-y-1">
                      {seeds.security_warning.split('\n').map((line, i) => (
                        <p key={i}>{line}</p>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-wrap gap-3 mb-6">
                <button
                  onClick={() => setShowSeeds(!showSeeds)}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-semibold text-white transition-all"
                >
                  {showSeeds ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  {showSeeds ? 'Hide Seeds' : 'Reveal Seeds'}
                </button>
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-6 py-3 rounded-xl font-semibold text-white transition-all"
                >
                  <Download className="w-5 h-5" />
                  Download Backup
                </button>
              </div>

              {/* Algorand Seed */}
              {seeds.algorand_seed && (
                <div className="bg-gray-800/50 rounded-xl p-6 mb-6 border border-gray-700">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-white">🌐 Algorand Wallet</h3>
                      <p className="text-gray-400 text-sm">25-word recovery phrase</p>
                    </div>
                    <button
                      onClick={() => handleCopy(seeds.algorand_seed!, 'algo')}
                      className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                    >
                      {copiedAlgo ? <Check className="w-5 h-5 text-green-400" /> : <Copy className="w-5 h-5 text-gray-400" />}
                    </button>
                  </div>
                  
                  <div className="relative">
                    <div className={`font-mono text-sm p-4 rounded-lg border ${
                      showSeeds ? 'bg-gray-900 border-blue-500/50 text-white' : 'bg-gray-900 border-gray-700'
                    }`}>
                      {showSeeds ? (
                        <div className="grid grid-cols-5 gap-2">
                          {seeds.algorand_seed.split(' ').map((word, i) => (
                            <span key={i} className="text-blue-400">{i + 1}. {word}</span>
                          ))}
                        </div>
                      ) : (
                        <div className="text-gray-500 text-center py-4">
                          Click "Reveal Seeds" to view your recovery phrase
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 text-sm text-gray-400">
                    <p><strong>Address:</strong> <span className="font-mono text-gray-300">{seeds.wallet_addresses?.algorand}</span></p>
                    <p><strong>Compatible Wallets:</strong> Pera Wallet, Defly Wallet, AlgoSigner</p>
                  </div>
                </div>
              )}

              {/* WDK Multi-Chain Seed */}
              {seeds.wdk_seed && (
                <div className="bg-gray-800/50 rounded-xl p-6 mb-6 border border-gray-700">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-white">🔗 Multi-Chain Wallet</h3>
                      <p className="text-gray-400 text-sm">12-word BIP39 phrase (Bitcoin, Ethereum, Polygon, TRON)</p>
                    </div>
                    <button
                      onClick={() => handleCopy(seeds.wdk_seed!, 'wdk')}
                      className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
                    >
                      {copiedWdk ? <Check className="w-5 h-5 text-green-400" /> : <Copy className="w-5 h-5 text-gray-400" />}
                    </button>
                  </div>
                  
                  <div className="relative">
                    <div className={`font-mono text-sm p-4 rounded-lg border ${
                      showSeeds ? 'bg-gray-900 border-purple-500/50 text-white' : 'bg-gray-900 border-gray-700'
                    }`}>
                      {showSeeds ? (
                        <div className="grid grid-cols-4 gap-2">
                          {seeds.wdk_seed.split(' ').map((word, i) => (
                            <span key={i} className="text-purple-400">{i + 1}. {word}</span>
                          ))}
                        </div>
                      ) : (
                        <div className="text-gray-500 text-center py-4">
                          Click "Reveal Seeds" to view your recovery phrase
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 space-y-2 text-sm text-gray-400">
                    <p><strong>Supported Chains:</strong></p>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(seeds.wallet_addresses || {})
                        .filter(([chain]) => chain !== 'algorand')
                        .map(([chain, address]) => (
                          <div key={chain} className="bg-gray-900 p-2 rounded">
                            <p className="text-gray-500 text-xs uppercase">{chain}</p>
                            <p className="font-mono text-xs text-gray-300 truncate">{address}</p>
                          </div>
                        ))}
                    </div>
                    <p><strong>Compatible Wallets:</strong> MetaMask, Trust Wallet, Ledger, Trezor</p>
                  </div>
                </div>
              )}

              {/* Backup Verification Test */}
              <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-xl p-6">
                <h3 className="text-xl font-bold text-white mb-4">
                  {verified ? '✅ Backup Verified!' : '📝 Test Your Backup'}
                </h3>
                
                {verified ? (
                  <div className="text-green-400 flex items-center gap-2">
                    <Check className="w-6 h-6" />
                    <span>You've successfully verified your backup! Your seeds are stored correctly.</span>
                  </div>
                ) : (
                  <>
                    <p className="text-gray-400 mb-4">
                      To ensure you've backed up correctly, paste one of your seed phrases below:
                    </p>
                    <textarea
                      value={testInput}
                      onChange={(e) => setTestInput(e.target.value)}
                      placeholder="Paste your seed phrase here..."
                      className="w-full bg-gray-900 border border-gray-700 rounded-lg p-4 text-white font-mono text-sm mb-4 h-24"
                    />
                    <button
                      onClick={handleVerifyBackup}
                      disabled={!testInput.trim()}
                      className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-3 rounded-xl font-semibold text-white transition-all"
                    >
                      Verify Backup
                    </button>
                  </>
                )}
              </div>

              {/* Backup Instructions */}
              <div className="mt-6 bg-gray-800/50 rounded-xl p-6 border border-gray-700">
                <h3 className="text-lg font-bold text-white mb-3">📋 Backup Instructions</h3>
                <div className="text-gray-400 text-sm space-y-2">
                  {seeds.backup_instructions.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="text-center text-gray-400 py-12">
              <Shield className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <h3 className="text-xl font-semibold mb-2">No Seeds Available</h3>
              <p>Your wallet seeds could not be retrieved. Please contact support.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-gray-800/50 border-t border-gray-700 p-6">
          <div className="flex items-center justify-between">
            <p className="text-gray-400 text-sm">
              🔒 Seeds are decrypted in-memory and never stored unencrypted
            </p>
            <button
              onClick={onClose}
              className="bg-gray-700 hover:bg-gray-600 px-6 py-3 rounded-xl font-semibold text-white transition-all"
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