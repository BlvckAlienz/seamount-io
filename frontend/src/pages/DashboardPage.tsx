// File: frontend/src/pages/DashboardPage.tsx
// ✅ PRODUCTION READY: Multi-chain WDK integration + All requested UI improvements

import React, { useState, useEffect } from 'react';
import {
  TrendingUp, DollarSign, Activity, RefreshCw, Shield, AlertTriangle,
  Bitcoin, Coins, Copy, Check, Eye, EyeOff, Download, Lock,
  ExternalLink, ArrowUpRight, ArrowDownLeft, Settings, LogOut, User, QrCode,
  Wallet, Plus, Key, ArrowDownLeft as ReceiveIcon
} from 'lucide-react';
import { KYCBanner } from '../components/onboarding/KYCBanner';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { apiClient } from '../config/api';
import { portfolioService } from '../services/portfolio';
import NigerianUserBanner from '../components/layout/NigerianUserBanner';
import ReceiveModal from '../components/payments/ReceiveModal';
import QRCodeGenerator from '../components/QRCodeGenerator';
import CreateWalletModal from '../components/wallet/CreateWalletModal';

// ============================================================================
// KYC PROMPT BANNER (Phase 2 - Color-coded urgency)
// ============================================================================

interface KYCBannerProps {
  kycStatus: string;
  cumulativeVolume: number;
  limit: number;
  urgency: string;
}

const KYCPromptBanner: React.FC<KYCBannerProps> = ({
  kycStatus,
  cumulativeVolume,
  limit,
  urgency,
}) => {
  const [dismissed, setDismissed] = useState(false);
  
  if (kycStatus === 'verified' || kycStatus === 'approved' || dismissed || urgency === 'none') {
    return null;
  }
  
  const remaining = Math.max(0, limit - cumulativeVolume);
  const percentUsed = (cumulativeVolume / limit) * 100;
  
  const urgencyConfig = {
    info: {
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800',
      text: 'text-blue-800 dark:text-blue-200',
      icon: <AlertTriangle className="w-5 h-5" />,
      title: '💡 Unlock Unlimited Transactions',
      message: `You've used $${cumulativeVolume.toFixed(2)} of your $${limit} limit. Verify your identity to remove all limits.`,
      action: 'Verify Now',
      dismissible: true,
    },
    warning: {
      bg: 'bg-orange-50 dark:bg-orange-900/20',
      border: 'border-orange-200 dark:border-orange-800',
      text: 'text-orange-800 dark:text-orange-200',
      icon: <AlertTriangle className="w-5 w-5" />,
      title: '⚠️ Approaching Transaction Limit',
      message: `Only $${remaining.toFixed(2)} remaining. Complete KYC verification to continue transacting.`,
      action: 'Complete KYC',
      dismissible: false,
    },
    critical: {
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      text: 'text-red-800 dark:text-red-200',
      icon: <Shield className="w-5 h-5" />,
      title: '🚨 Transaction Limit Reached',
      message: `You've reached your $${limit} limit. Verify your identity to continue.`,
      action: 'Verify Now (Required)',
      dismissible: false,
    },
  };
  
  const config = urgencyConfig[urgency as keyof typeof urgencyConfig] || urgencyConfig.info;
  
  return (
    <div className={`rounded-2xl border p-4 mb-6 ${config.bg} ${config.border} backdrop-blur-sm animate-in slide-in-from-top duration-500`}>
      <div className="flex items-start gap-3">
        <div className={config.text}>
          {config.icon}
        </div>
        
        <div className="flex-1">
          <h3 className={`font-semibold mb-1 ${config.text}`}>
            {config.title}
          </h3>
          
          <p className={`text-sm mb-3 ${config.text}`}>
            {config.message}
          </p>
          
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-3">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                urgency === 'critical' ? 'bg-red-600' :
                urgency === 'warning' ? 'bg-orange-500' :
                'bg-blue-500'
              }`}
              style={{ width: `${Math.min(100, percentUsed)}%` }}
            />
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.location.href = '/onboarding'}
              className={`px-4 py-2 rounded-lg font-medium transition-all shadow-lg ${
                urgency === 'critical' 
                  ? 'bg-red-600 hover:bg-red-700 text-white hover:shadow-red-500/50'
                  : urgency === 'warning'
                  ? 'bg-orange-500 hover:bg-orange-600 text-white hover:shadow-orange-500/50'
                  : 'bg-blue-500 hover:bg-blue-600 text-white hover:shadow-blue-500/50'
              }`}
            >
              {config.action}
            </button>
            
            {config.dismissible && (
              <button
                onClick={() => setDismissed(true)}
                className={`text-sm ${config.text} hover:underline`}
              >
                Remind me later
              </button>
            )}
          </div>
        </div>
        
        {config.dismissible && (
          <button
            onClick={() => setDismissed(true)}
            className={`${config.text} hover:opacity-70`}
          >
            <Check className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// MULTI-CHAIN WALLET CARD COMPONENT (UPDATED WITH PROPER ICONS & BUTTONS)
// ============================================================================

interface ChainWalletCardProps {
  chain: string;
  address: string;
  balance: number;
  status: 'created' | 'pending' | 'not_created';
  onView: () => void;
  onBuy: () => void;
}

const ChainWalletCard: React.FC<ChainWalletCardProps> = ({ 
  chain, 
  address, 
  balance, 
  status, 
  onView,
  onBuy
}) => {
  const getChainConfig = (chain: string) => {
    const configs = {
      bitcoin: {
        name: 'Bitcoin',
        icon: 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/bitcoin.png',
        color: 'from-orange-500 to-yellow-600',
        symbol: 'BTC',
        explorer: `https://blockstream.info/address/${address}`
      },
      ethereum: {
        name: 'Ethereum', 
        icon: 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/ethereum.png',
        color: 'from-gray-400 to-slate-600',
        symbol: 'ETH',
        explorer: `https://etherscan.io/address/${address}`
      },
      polygon: {
        name: 'Polygon',
        icon: 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/polygon.png',
        color: 'from-purple-500 to-indigo-600',
        symbol: 'MATIC',
        explorer: `https://polygonscan.com/address/${address}`
      },
      algorand: {
        name: 'Algorand',
        icon: 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/algorand.png',
        color: 'from-blue-500 to-cyan-600',
        symbol: 'ALGO',
        explorer: `https://algoexplorer.io/address/${address}`
      }
    };
    return configs[chain as keyof typeof configs] || configs.algorand;
  };

  const config = getChainConfig(chain);
  const [copied, setCopied] = useState(false);

  const copyAddress = () => {
    if (!address) {
      toast.error('No address available');
      return;
    }
    navigator.clipboard.writeText(address);
    setCopied(true);
    toast.success(`${config.name} address copied!`);
    setTimeout(() => setCopied(false), 2000);
  };

  if (status === 'not_created') {
    return (
      <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all">
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
          <div className="text-gray-400 text-sm">Create wallet to start using</div>
        </div>

        <button
          onClick={onBuy}
          className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-3 px-4 rounded-lg font-medium transition-all hover:shadow-lg hover:shadow-blue-500/50"
        >
          <Plus className="h-4 w-4" />
          Create {config.name} Wallet
        </button>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-xl hover:shadow-blue-500/10 transform hover:-translate-y-1">
      <div className="flex items-start justify-between mb-4">
        <div className={`p-3 rounded-xl bg-gradient-to-br ${config.color} text-white shadow-lg`}>
          <img src={config.icon} alt={config.name} className="w-6 h-6" />
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-white">
            {balance > 0 ? `$${balance.toFixed(2)}` : '$0.00'}
          </div>
          <div className="text-sm text-gray-400">
            {status === 'pending' ? 'Creating...' : 'Ready'}
          </div>
        </div>
      </div>

      <div className="mb-4">
        <div className="text-white font-semibold">{config.name}</div>
        <div className="text-gray-400 text-sm flex items-center gap-2">
          {address ? (
            <>
              <span className="truncate">{address.slice(0, 8)}...{address.slice(-6)}</span>
              <button onClick={copyAddress} className="hover:text-blue-400">
                {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              </button>
            </>
          ) : (
            <span className="text-gray-500">No address</span>
          )}
        </div>
      </div>

      {/* ✅ UPDATED: View & Buy buttons */}
      <div className="flex gap-2">
        <button
          onClick={onView}
          className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-all hover:shadow-lg hover:shadow-blue-500/50"
        >
          <ExternalLink className="h-4 w-4" />
          View
        </button>
        <button
          onClick={onBuy}
          className="flex-1 flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-all hover:shadow-lg hover:shadow-green-500/50"
        >
          <ArrowDownLeft className="h-4 w-4" />
          Buy
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// ASSET CARD COMPONENT (Updated for multi-chain)
// ============================================================================

interface AssetCardProps {
  asset: any;
  onBuy: () => void;
  onSend: () => void;
}

const AssetCard: React.FC<AssetCardProps> = ({ asset, onBuy, onSend }) => {
  const getGradient = (symbol: string) => {
    const gradients: { [key: string]: string } = {
      'ALGO': 'from-purple-500 to-indigo-600',
      'USDT': 'from-green-500 to-emerald-600',
      'USDCa': 'from-blue-500 to-cyan-600',
      'goBTC': 'from-orange-500 to-yellow-600',
      'goETH': 'from-gray-400 to-slate-600',
      'BTC': 'from-orange-500 to-yellow-600',
      'ETH': 'from-gray-400 to-slate-600',
      'MATIC': 'from-purple-500 to-indigo-600',
    };
    return gradients[symbol] || 'from-gray-500 to-gray-600';
  };

  const getIcon = (symbol: string) => {
    const iconMap: { [key: string]: string } = {
      'BTC': 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/bitcoin.png',
      'goBTC': 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/bitcoin.png',
      'ETH': 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/ethereum.png',
      'goETH': 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/ethereum.png',
      'ALGO': 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/algorand.png',
      'MATIC': 'https://raw.githubusercontent.com/BlvckAlienz/seamount-io/main/frontend/public/icons/polygon.png',
    };

    const iconUrl = iconMap[symbol];
    if (iconUrl) {
      return <img src={iconUrl} alt={symbol} className="h-8 w-8" />;
    }

    // Fallback to Lucide icons
    switch (symbol) {
      case 'USDT':
      case 'USDCa':
        return <DollarSign className="h-8 w-8" />;
      default:
        return <Coins className="h-8 w-8" />;
    }
  };

  const balance = asset.balance || 0;
  const valueUsd = asset.value_usd || 0;
  const hasBalance = balance > 0;

  return (
    <div className="group relative bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-xl hover:shadow-blue-500/10 transform hover:-translate-y-1">
      <div className={`absolute inset-0 bg-gradient-to-br ${getGradient(asset.symbol)} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity duration-300`} />
      
      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <div className={`p-3 rounded-xl bg-gradient-to-br ${getGradient(asset.symbol)} text-white shadow-lg`}>
            {getIcon(asset.symbol)}
          </div>
          <div className="text-right">
            <div className={`text-2xl font-bold ${hasBalance ? 'text-white' : 'text-gray-500'}`}>
              ${valueUsd.toFixed(2)}
            </div>
            <div className="text-sm text-gray-400">≈ {balance.toFixed(6)}</div>
          </div>
        </div>

        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-white font-semibold">{asset.name}</div>
            <div className="text-gray-400 text-sm">{asset.symbol}</div>
          </div>
          <div className="text-right">
            <div className="text-gray-400 text-sm">${asset.price_usd?.toFixed(2) || '0.00'}</div>
            <div className="text-xs text-green-400">+0.00%</div>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onBuy}
            className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2 px-3 rounded-lg text-sm font-medium transition-all hover:shadow-lg hover:shadow-blue-500/50"
          >
            <ArrowDownLeft className="h-4 w-4" />
            Buy
          </button>
          <button
            onClick={onSend}
            disabled={!hasBalance}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
              hasBalance
                ? 'bg-gray-700 hover:bg-gray-600 text-white hover:shadow-lg'
                : 'bg-gray-800 text-gray-500 cursor-not-allowed'
            }`}
          >
            <ArrowUpRight className="h-4 w-4" />
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MNEMONIC BACKUP MODAL (Keep existing logic)
// ============================================================================

interface MnemonicBackupModalProps {
  mnemonic: string;
  walletAddress: string;
  onComplete: () => void;
}

const MnemonicBackupModal: React.FC<MnemonicBackupModalProps> = ({
  mnemonic,
  walletAddress,
  onComplete
}) => {
  const [step, setStep] = useState(1);
  const [showMnemonic, setShowMnemonic] = useState(false);
  const [verificationWords, setVerificationWords] = useState<number[]>([]);
  const [userInputs, setUserInputs] = useState<{ [key: number]: string }>({});
  const [copied, setCopied] = useState(false);

  const words = mnemonic.split(' ');

  useEffect(() => {
    const positions: number[] = [];
    while (positions.length < 3) {
      const pos = Math.floor(Math.random() * 25);
      if (!positions.includes(pos)) positions.push(pos);
    }
    setVerificationWords(positions.sort((a, b) => a - b));
  }, []);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(mnemonic);
    setCopied(true);
    toast.success('Recovery phrase copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadMnemonic = () => {
    const blob = new Blob([
      `Seamount Wallet Recovery Phrase\n\n`,
      `Wallet Address: ${walletAddress}\n\n`,
      `Recovery Phrase:\n${mnemonic}\n\n`,
      `⚠️ KEEP THIS SAFE! Never share with anyone.`
    ], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'seamount-recovery-phrase.txt';
    a.click();
    toast.success('Recovery phrase downloaded!');
  };

  const verifyWords = () => {
    const allCorrect = verificationWords.every(pos =>
      userInputs[pos]?.toLowerCase().trim() === words[pos].toLowerCase()
    );
    
    if (allCorrect) {
      toast.success('Verification successful! 🎉');
      onComplete();
    } else {
      toast.error('Incorrect words. Please check and try again.');
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-2xl w-full p-8 border border-blue-500/30 shadow-2xl">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-white mb-2">Secure Your Wallet</h2>
          <p className="text-gray-400">Back up your recovery phrase to protect your funds</p>
        </div>

        {step === 1 && (
          <div className="space-y-6">
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
              <div className="flex items-center gap-3 text-yellow-400 mb-2">
                <Shield className="h-5 w-5" />
                <span className="font-semibold">Security Warning</span>
              </div>
              <p className="text-yellow-300 text-sm">
                Never share your recovery phrase! Anyone with these words can steal your funds.
              </p>
            </div>

            <div className="bg-gray-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-white font-semibold">Your Recovery Phrase</h3>
                <button
                  onClick={() => setShowMnemonic(!showMnemonic)}
                  className="flex items-center gap-2 text-blue-400 hover:text-blue-300 text-sm"
                >
                  {showMnemonic ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  {showMnemonic ? 'Hide' : 'Show'}
                </button>
              </div>

              {showMnemonic ? (
                <div className="grid grid-cols-3 gap-3 mb-4">
                  {words.map((word, index) => (
                    <div key={index} className="bg-gray-700 rounded-lg p-3 text-center">
                      <span className="text-gray-400 text-xs mr-1">{index + 1}.</span>
                      <span className="text-white font-medium">{word}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-3 gap-3 mb-4">
                  {words.map((_, index) => (
                    <div key={index} className="bg-gray-700 rounded-lg p-3 text-center">
                      <span className="text-gray-400 text-xs mr-1">{index + 1}.</span>
                      <span className="text-gray-600">•••••</span>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={copyToClipboard}
                  className="flex-1 flex items-center justify-center gap-2 bg-gray-700 hover:bg-gray-600 text-white py-2.5 rounded-lg font-medium transition-colors"
                >
                  {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
                <button
                  onClick={downloadMnemonic}
                  className="flex-1 flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-lg font-medium transition-colors"
                >
                  <Download className="h-4 w-4" />
                  Download
                </button>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep(2)}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-semibold transition-colors"
              >
                I've Saved It Securely
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <div className="text-center">
              <h3 className="text-xl font-bold text-white mb-2">Verify Your Recovery Phrase</h3>
              <p className="text-gray-400">Enter the words below to confirm you saved them correctly</p>
            </div>

            <div className="space-y-4">
              {verificationWords.map((position, index) => (
                <div key={position} className="bg-gray-800 rounded-xl p-4">
                  <label className="block text-gray-400 text-sm mb-2">
                    Word #{position + 1}
                  </label>
                  <input
                    type="text"
                    value={userInputs[position] || ''}
                    onChange={(e) => setUserInputs(prev => ({
                      ...prev,
                      [position]: e.target.value
                    }))}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-colors"
                    placeholder={`Enter word #${position + 1}`}
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-3 rounded-lg font-medium transition-colors"
              >
                Back
              </button>
              <button
                onClick={verifyWords}
                className="flex-1 bg-green-600 hover:bg-green-700 text-white py-3 rounded-lg font-semibold transition-colors"
              >
                Verify & Complete
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT - PRODUCTION READY WITH ALL FIXES
// ============================================================================

const DashboardPage = () => {
  const { user, userProfile, signOut } = useAuth();
  const [loading, setLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [kycInfo, setKycInfo] = useState({
    status: 'not_started',
    cumulative_volume: 0,
    limit: 5000,
    urgency: 'none',
  });
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showMnemonicModal, setShowMnemonicModal] = useState(false);
  const [pendingMnemonic, setPendingMnemonic] = useState<string | null>(null);
  const [walletAddress, setWalletAddress] = useState<string>('');
  const [showReceiveModal, setShowReceiveModal] = useState(false);
  const [showCreateWalletModal, setShowCreateWalletModal] = useState(false);
  const [multiChainWallets, setMultiChainWallets] = useState<any>({});
  
  // Supported chains for wallet creation
  const SUPPORTED_CHAINS = [
    { id: 'bitcoin', name: 'Bitcoin', symbol: 'BTC' },
    { id: 'ethereum', name: 'Ethereum', symbol: 'ETH' },
    { id: 'polygon', name: 'Polygon', symbol: 'MATIC' },
    { id: 'algorand', name: 'Algorand', symbol: 'ALGO' }
  ];

  // Supported assets configuration
  const SUPPORTED_ASSETS = [
    { symbol: 'ALGO', name: 'Algorand', decimals: 6, blockchain: 'Algorand' },
    { symbol: 'USDT', name: 'Tether', decimals: 6, blockchain: 'Algorand' },
    { symbol: 'USDCa', name: 'USD Coin', decimals: 6, blockchain: 'Algorand' },
    { symbol: 'goBTC', name: 'Wrapped Bitcoin', decimals: 8, blockchain: 'Algorand' },
    { symbol: 'goETH', name: 'Wrapped Ethereum', decimals: 8, blockchain: 'Algorand' },
    { symbol: 'BTC', name: 'Bitcoin', decimals: 8, blockchain: 'Bitcoin' },
    { symbol: 'ETH', name: 'Ethereum', decimals: 18, blockchain: 'Ethereum' },
    { symbol: 'MATIC', name: 'Polygon', decimals: 18, blockchain: 'Polygon' },
  ];

  useEffect(() => {
    if (user && userProfile) {
      fetchPortfolioData();
      fetchKYCStatus();
      fetchMultiChainWallets();
    }
  }, [user, userProfile]);

  // ✅ FIXED: Fetch multi-chain wallet status
  const fetchMultiChainWallets = async () => {
    try {
      const response = await apiClient.get('/api/v1/wallet/multi-chain-status');
      if (response.data.success) {
        setMultiChainWallets(response.data.wallets || {});
      }
    } catch (error) {
      console.error('Multi-chain wallet status fetch failed:', error);
      setMultiChainWallets({});
    }
  };

  // ✅ FIXED: Map assets to chains properly for balance calculation
  const getAssetChain = (symbol: string) => {
    const chainMap: { [key: string]: string } = {
      'ALGO': 'algorand',
      'USDCa': 'algorand',
      'USDT': 'algorand', 
      'goBTC': 'algorand',
      'goETH': 'algorand',
      'BTC': 'bitcoin',
      'ETH': 'ethereum',
      'MATIC': 'polygon'
    };
    return chainMap[symbol] || 'algorand';
  };

  // ✅ FIXED: Proper balance calculation for wallet cards
  const calculateChainBalance = (chain: string) => {
    if (!portfolioData?.assets) return 0;
    
    const chainAssets = portfolioData.assets.filter((asset: any) => {
      const assetChain = getAssetChain(asset.symbol);
      return assetChain === chain;
    });
    
    return chainAssets.reduce((total: number, asset: any) => {
      return total + (asset.usd_value || 0);
    }, 0);
  };

  // ✅ UPDATED: Fetch portfolio data including multi-chain balances
  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      
      const response = await apiClient.get('/api/v1/wallet/balances');
      
      if (response.data.success) {
        setPortfolioData({
          total_usd: response.data.total_usd,
          assets: response.data.assets,
          timestamp: response.data.timestamp
        });
        
        if (response.data.wallet_addresses) {
          setMultiChainWallets(response.data.wallet_addresses);
        }
      }
      
    } catch (error: any) {
      console.error('Portfolio fetch error:', error);
      
      // Fallback to Algorand-only if multi-chain fails
      if (userProfile?.algorand_address) {
        setWalletAddress(userProfile.algorand_address);
        setPortfolioData({
          success: true,
          total_usd: 0,
          assets: [],
          wallet_address: userProfile.algorand_address
        });
      }
      
    } finally {
      setLoading(false);
    }
  };

  // ✅ NEW: Create multi-chain wallet
  const createMultiChainWallet = async (chains?: string[]) => {
    try {
      setLoading(true);
      const response = await apiClient.post('/api/v1/wallet/create-multi-chain', {
        chains: chains || ['bitcoin', 'ethereum', 'polygon', 'algorand']
      });

      if (response.data.success) {
        toast.success(`Wallets created on ${response.data.total_chains} chains!`);
        setMultiChainWallets(response.data.wallets);
        
        if (response.data.mnemonic) {
          setPendingMnemonic(response.data.mnemonic);
          setShowMnemonicModal(true);
        }
        
        fetchPortfolioData();
      }
    } catch (error: any) {
      console.error('Multi-chain wallet creation failed:', error);
      toast.error(error.response?.data?.error || 'Failed to create wallets');
    } finally {
      setLoading(false);
    }
  };

  // ✅ NEW: Create single chain wallet
  const createSingleChainWallet = async (chain: string) => {
    try {
      setLoading(true);
      const response = await apiClient.post(`/api/v1/wallet/${chain}/create`);

      if (response.data.success) {
        toast.success(`${chain.toUpperCase()} wallet created!`);
        setMultiChainWallets((prev: any) => ({
          ...prev,
          [chain]: response.data.wallet
        }));
        fetchPortfolioData();
      }
    } catch (error: any) {
      console.error(`${chain} wallet creation failed:`, error);
      toast.error(error.response?.data?.error || `Failed to create ${chain} wallet`);
    } finally {
      setLoading(false);
    }
  };

  // ✅ NEW: Handler functions for wallet card actions
  const handleViewChain = (chain: string, address: string) => {
    if (!address) {
      toast.error('No wallet address found');
      return;
    }

    const explorers: { [key: string]: string } = {
      bitcoin: `https://blockstream.info/address/${address}`,
      ethereum: `https://etherscan.io/address/${address}`,
      polygon: `https://polygonscan.com/address/${address}`,
      algorand: `https://algoexplorer.io/address/${address}`
    };

    const explorerUrl = explorers[chain];
    if (explorerUrl) {
      window.open(explorerUrl, '_blank');
    } else {
      toast.error('Explorer not available for this chain');
    }
  };

  const handleBuyChain = async (chain: string, chainName: string) => {
    try {
      // If wallet doesn't exist, create it first
      if (!multiChainWallets[chain]?.address) {
        await createSingleChainWallet(chain);
      }

      // Get the native asset for the chain
      const nativeAssets: { [key: string]: string } = {
        bitcoin: 'BTC',
        ethereum: 'ETH',
        polygon: 'MATIC',
        algorand: 'ALGO'
      };

      const asset = nativeAssets[chain];
      if (!asset) {
        toast.error('Unsupported chain for buying');
        return;
      }

      // Trigger buy flow for the native asset
      const response = await apiClient.post('/api/v1/payments/on-ramp/ngn', {
        user_id: userProfile?.id,
        user_email: userProfile?.email,
        amount_fiat: 10000,
        currency: "NGN",
        asset: asset
      });
      
      if (response.data.payment_url) {
        window.location.href = response.data.payment_url;
      } else {
        toast.error('Payment initialization failed');
      }
    } catch (error) {
      console.error('Buy chain error:', error);
      toast.error('Failed to initiate purchase');
    }
  };

  // Keep existing functions
  const fetchKYCStatus = async () => {
    try {
      const response = await apiClient.get('/api/v1/users/kyc-status');
      if (response.data) {
        setKycInfo({
          status: response.data.status || 'not_started',
          cumulative_volume: response.data.cumulative_volume || 0,
          limit: response.data.limit || 5000,
          urgency: response.data.urgency || 'none',
        });
      }
    } catch (error) {
      console.error('KYC status fetch failed:', error);
      setKycInfo({
        status: 'not_started',
        cumulative_volume: 0,
        limit: 5000,
        urgency: 'none',
      });
    }
  };

  const handleMnemonicBackupComplete = () => {
    localStorage.setItem('mnemonic_backed_up', 'true');
    setShowMnemonicModal(false);
    setPendingMnemonic(null);
    toast.success('Wallet secured successfully! 🎉');
    fetchPortfolioData();
  };

  const handleBuyAsset = async (asset: any) => {
    try {
      const response = await apiClient.post('/api/v1/payments/on-ramp/ngn', {
        user_id: userProfile?.id,
        user_email: userProfile?.email,
        amount_fiat: 10000,
        currency: "NGN",
        asset: asset.symbol
      });
      
      if (response.data.payment_url) {
        window.location.href = response.data.payment_url;
      }
    } catch (error) {
      console.error('Buy asset error:', error);
      toast.error("Payment initialization failed");
    }
  };

  const handleSendAsset = (asset: any) => {
    if (asset.balance <= 0) {
      toast.error('Insufficient balance');
      return;
    }
    window.location.href = `/send?asset=${asset.symbol}&balance=${asset.balance}`;
  };

  const handleVerifyKYC = async () => {
    try {
      // Check current KYC status first
      const kycResponse = await apiClient.get('/api/v1/users/kyc-status');
      
      if (kycResponse.data.status === 'verified' || kycResponse.data.status === 'approved') {
        toast.success('Your account is already verified!');
        return;
      }
      
      // Redirect to KYC onboarding
      window.location.href = '/onboarding';
      
    } catch (error) {
      console.error('KYC verification error:', error);
      toast.error('Unable to start verification process');
    }
  };

  const handleLogout = async () => {
    try {
      await signOut();
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Logout failed');
    }
  };

  const totalBalance = portfolioData?.total_usd || 0;
  const balances = portfolioData?.balances || {};

  // Build asset cards with live data
  const assetCards = SUPPORTED_ASSETS.map(asset => {
    const balance = balances[asset.symbol] || 0;
    const price = portfolioData?.prices?.[asset.symbol] || 0;
    const value_usd = balance * price;

    return {
      ...asset,
      balance,
      price_usd: price,
      value_usd
    };
  });

  // Calculate created chains count
  const createdChains = Object.keys(multiChainWallets).filter(chain => 
    multiChainWallets[chain]?.address
  ).length;

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading your portfolio...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 md:mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">Portfolio</h1>
            <p className="text-gray-400 text-sm md:text-base">Manage your multi-chain wallet</p>
          </div>

          {/* ✅ UPDATED: Header Buttons - Create Wallet, Send, Swap, Earn */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCreateWalletModal(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <Key className="h-4 w-4" />
              Create Wallet
            </button>

            <button
              onClick={() => toast.info('Send functionality coming soon!')}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <ArrowUpRight className="h-4 w-4" />
              Send
            </button>

            <button
              onClick={() => toast.info('Swap functionality coming soon!')}
              className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Swap
            </button>

            <button
              onClick={() => toast.info('Earn functionality coming soon!')}
              className="flex items-center gap-2 bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <TrendingUp className="h-4 w-4" />
              Earn
            </button>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-white transition-colors"
              >
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
                  {userProfile?.first_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
                </div>
                <span className="text-sm hidden md:inline">{userProfile?.first_name || user?.email?.split('@')[0] || 'User'}</span>
              </button>

              {showProfileMenu && (
                <>
                  <div 
                    className="fixed inset-0 z-40" 
                    onClick={() => setShowProfileMenu(false)}
                  />
                  <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 backdrop-blur-xl">
                    <button
                      onClick={handleVerifyKYC}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors rounded-t-lg"
                    >
                      <Shield className="h-4 w-4" />
                      <span>Verify</span>
                    </button>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-red-400 transition-colors rounded-b-lg"
                    >
                      <LogOut className="h-4 w-4" />
                      <span>Logout</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Nigerian User Banner */}
        <NigerianUserBanner />

        {/* KYC Banner */}
        <KYCPromptBanner
          kycStatus={kycInfo.status}
          cumulativeVolume={kycInfo.cumulative_volume}
          limit={kycInfo.limit}
          urgency={kycInfo.urgency}
        />

        {/* Multi-Chain Wallet Status */}
        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-6 md:mb-8 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">Multi-Chain Wallets</h2>
            <span className="text-sm text-gray-400">
              {createdChains} of {SUPPORTED_CHAINS.length} created
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {SUPPORTED_CHAINS.map(chain => (
              <ChainWalletCard
                key={chain.id}
                chain={chain.id}
                address={multiChainWallets[chain.id]?.address || ''}
                balance={calculateChainBalance(chain.id)} // ✅ FIXED: Proper balance calculation
                status={multiChainWallets[chain.id]?.address ? 'created' : 'not_created'}
                onView={() => handleViewChain(chain.id, multiChainWallets[chain.id]?.address)}
                onBuy={() => handleBuyChain(chain.id, chain.name)}
              />
            ))}
          </div>
        </div>

        {/* Balance Cards */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
          {/* Total Balance */}
          <div className="lg:col-span-2 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-2xl p-6 backdrop-blur-sm hover:shadow-xl hover:shadow-blue-500/10 transition-all">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-sm text-gray-400 mb-1">Total Balance</div>
                <div className="text-3xl md:text-4xl font-bold text-white">${totalBalance.toFixed(2)}</div>
              </div>
              <button
                onClick={fetchPortfolioData}
                className="p-3 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors hover:rotate-180 duration-300"
              >
                <RefreshCw className="h-5 w-5" />
              </button>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-green-400 animate-pulse" />
              <span className="text-green-400">Live Multi-Chain Balances</span>
            </div>
          </div>

          {/* Network Status */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 backdrop-blur-sm">
            <div className="text-sm text-gray-400 mb-2">Networks</div>
            <div className="text-2xl font-bold text-white mb-4">Multi-Chain</div>
            <div className="space-y-2">
              {SUPPORTED_CHAINS.map(chain => (
                <div key={chain.id} className="flex items-center gap-2 text-xs text-gray-400">
                  <div className={`w-2 h-2 rounded-full ${
                    multiChainWallets[chain.id]?.address ? 'bg-green-400 animate-pulse' : 'bg-gray-600'
                  }`}></div>
                  {chain.name}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Assets Grid */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">Your Assets</h2>
            <span className="text-sm text-gray-400">
              {portfolioData?.assets?.length || SUPPORTED_ASSETS.length} assets
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            {portfolioData?.assets && portfolioData.assets.length > 0 ? (
              portfolioData.assets.map((asset: any) => (
                <AssetCard
                  key={`${asset.chain}-${asset.symbol}`}
                  asset={{
                    symbol: asset.symbol || 'UNKNOWN',
                    name: asset.name || asset.symbol,
                    balance: asset.balance || 0,
                    price_usd: asset.price_usd || 0,
                    value_usd: asset.usd_value || 0,
                    chain: asset.chain
                  }}
                  onBuy={() => handleBuyAsset(asset)}
                  onSend={() => handleSendAsset(asset)}
                />
              ))
            ) : (
              assetCards.map(asset => (
                <AssetCard
                  key={asset.symbol}
                  asset={asset}
                  onBuy={() => handleBuyAsset(asset)}
                  onSend={() => handleSendAsset(asset)}
                />
              ))
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-6 md:mb-8 backdrop-blur-sm">
          <h3 className="text-lg font-bold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: ArrowDownLeft, label: 'Buy', color: 'text-blue-400', action: () => toast.info('Select an asset above to buy') },
              { icon: ArrowUpRight, label: 'Send', color: 'text-purple-400', action: () => toast.info('Select an asset above to send') },
              { icon: RefreshCw, label: 'Swap', color: 'text-green-400', action: () => toast.info('Swap feature coming soon!') },
              { icon: TrendingUp, label: 'Earn', color: 'text-yellow-400', action: () => toast.info('Yield farming coming soon!') },
            ].map(action => (
              <button 
                key={action.label}
                onClick={action.action}
                className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-800 hover:bg-gray-700 transition-all hover:scale-105"
              >
                <action.icon className={`h-6 w-6 ${action.color}`} />
                <span className="text-sm text-gray-300">{action.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Cross-Border CTA */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white hover:shadow-2xl hover:shadow-blue-500/50 transition-all">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h3 className="text-xl font-bold mb-2">Cross-Border Payments</h3>
              <p className="text-blue-100 text-sm mb-3">
                Send money globally at 2.9% fee vs 8% traditional (5.1% savings!)
              </p>
              <div className="flex flex-wrap items-center gap-4 text-xs">
                <span className="flex items-center gap-1">
                  <Activity className="h-3 w-3" />
                  Sub-5s settlement
                </span>
                <span className="flex items-center gap-1">
                  <Shield className="h-3 w-3" />
                  Bank-grade security
                </span>
              </div>
            </div>
            <button 
              onClick={() => toast.info('Cross-border payments coming soon!')}
              className="bg-white text-blue-600 px-6 py-3 rounded-xl font-semibold hover:bg-blue-50 transition-colors whitespace-nowrap shadow-lg hover:shadow-white/50"
            >
              Send Money
            </button>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showMnemonicModal && pendingMnemonic && (
        <MnemonicBackupModal
          mnemonic={pendingMnemonic}
          walletAddress={walletAddress}
          onComplete={handleMnemonicBackupComplete}
        />
      )}

      {showReceiveModal && (
        <ReceiveModal onClose={() => setShowReceiveModal(false)} />
      )}

      {/* Multi-chain Wallet Creation Modal */}
      {showCreateWalletModal && (
        <CreateWalletModal
          isOpen={showCreateWalletModal}
          onClose={() => setShowCreateWalletModal(false)}
          onWalletCreated={(wallets) => {
            setMultiChainWallets(wallets);
            fetchPortfolioData();
            toast.success('Multi-chain wallets created successfully! 🎉');
          }}
          existingWallets={multiChainWallets}
        />
      )}
    </div>
  );
};

export default DashboardPage;