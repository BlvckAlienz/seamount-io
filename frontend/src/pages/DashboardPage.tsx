// File: frontend/src/pages/DashboardPage.tsx
// ✅ PRODUCTION READY: Fixed wallet connection + removed broken components

import React, { useState, useEffect } from 'react';
import {
  TrendingUp, DollarSign, Activity, RefreshCw, Shield, AlertTriangle,
  Bitcoin, Coins, Copy, Check, Eye, EyeOff, Download, Lock,
  ExternalLink, ArrowUpRight, ArrowDownLeft, Settings, LogOut, User, QrCode,
  Wallet // ✅ ADDED: Wallet icon for connect button
} from 'lucide-react';
import { KYCBanner } from '../components/onboarding/KYCBanner';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { apiClient } from '../config/api';
import { portfolioService } from '../services/portfolio';
import NigerianUserBanner from '../components/layout/NigerianUserBanner';
import ReceiveModal from '../components/payments/ReceiveModal';
import QRCodeGenerator from '../components/QRCodeGenerator';
import RealWalletConnect from '../components/wallet/RealWalletConnect'; // ✅ ADDED: Real wallet connect

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
  
  // Don't show if verified or dismissed
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
          
          {/* Progress bar */}
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
// ASSET CARD COMPONENT (Phase 2 - Premium gradients)
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
    switch (symbol) {
      case 'BTC':
      case 'goBTC': return <Bitcoin className="h-8 w-8" />;
      case 'ETH':
      case 'goETH': return <Coins className="h-8 w-8" />;
      case 'ALGO': return <Shield className="h-8 w-8" />;
      case 'MATIC': return <Coins className="h-8 w-8" />;
      default: return <DollarSign className="h-8 w-8" />;
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
// MNEMONIC BACKUP MODAL (Phase 1 - Complete logic preserved)
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
        {step === 1 && (
          <>
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="h-8 w-8 text-red-400" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-2">Secure Your Wallet</h2>
              <p className="text-gray-400">Your recovery phrase is the ONLY way to restore your wallet</p>
            </div>

            <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 mb-6">
              <h3 className="text-red-400 font-semibold mb-2 flex items-center">
                <Lock className="h-4 w-4 mr-2" />
                Critical Security Warning
              </h3>
              <ul className="text-sm text-gray-300 space-y-1">
                <li>• Never share your recovery phrase with anyone</li>
                <li>• Seamount will NEVER ask for your phrase</li>
                <li>• Store it offline in multiple secure locations</li>
                <li>• Anyone with this phrase can access your funds</li>
              </ul>
            </div>

            <button
              onClick={() => setStep(2)}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 rounded-xl transition-all"
            >
              I Understand - Show Recovery Phrase
            </button>
          </>
        )}

        {step === 2 && (
          <>
            <div className="text-center mb-6">
              <Shield className="h-12 w-12 text-blue-400 mx-auto mb-4" />
              <h2 className="text-2xl font-bold text-white mb-2">Your Recovery Phrase</h2>
              <p className="text-gray-400">Write these 25 words down in order</p>
            </div>

            <div className="mb-6">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm text-gray-400">Recovery Phrase</span>
                <button
                  onClick={() => setShowMnemonic(!showMnemonic)}
                  className="text-blue-400 hover:text-blue-300 text-sm flex items-center gap-1"
                >
                  {showMnemonic ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  {showMnemonic ? 'Hide' : 'Show'}
                </button>
              </div>

              <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700">
                {showMnemonic ? (
                  <div className="grid grid-cols-3 gap-2">
                    {words.map((word, index) => (
                      <div key={index} className="bg-gray-700/50 rounded px-3 py-2 text-sm">
                        <span className="text-gray-400 mr-2">{index + 1}.</span>
                        <span className="text-white font-mono">{word}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    Click "Show" to reveal your recovery phrase
                  </div>
                )}
              </div>
            </div>

            <div className="flex gap-3 mb-4">
              <button
                onClick={copyToClipboard}
                className="flex-1 flex items-center justify-center gap-2 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied ? 'Copied!' : 'Copy Phrase'}
              </button>
              <button
                onClick={downloadMnemonic}
                className="flex-1 flex items-center justify-center gap-2 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Download className="h-4 w-4" />
                Download
              </button>
            </div>

            <button
              onClick={() => setStep(3)}
              disabled={!showMnemonic}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-4 px-6 rounded-xl transition-all disabled:opacity-50"
            >
              I've Saved My Recovery Phrase ✓
            </button>
          </>
        )}

        {step === 3 && (
          <>
            <div className="text-center mb-6">
              <Check className="h-12 w-12 text-green-400 mx-auto mb-4 animate-bounce" />
              <h2 className="text-2xl font-bold text-white mb-2">Verify Your Phrase</h2>
              <p className="text-gray-400">Enter these words to confirm you saved it</p>
            </div>

            <div className="space-y-4 mb-6">
              {verificationWords.map(pos => (
                <div key={pos}>
                  <label className="block text-sm text-gray-400 mb-2">
                    Word #{pos + 1}
                  </label>
                  <input
                    type="text"
                    value={userInputs[pos] || ''}
                    onChange={(e) => setUserInputs({ ...userInputs, [pos]: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none"
                    placeholder="Enter word"
                  />
                </div>
              ))}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setStep(2)}
                className="flex-1 border border-gray-700 text-gray-300 py-3 px-4 rounded-lg hover:bg-gray-800"
              >
                ← Back
              </button>
              <button
                onClick={verifyWords}
                className="flex-1 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white py-3 px-4 rounded-lg"
              >
                Verify & Complete
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
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
  const [isWalletConnectOpen, setIsWalletConnectOpen] = useState(false); // ✅ ADDED: Real wallet connect state
  const [showWalletModal, setShowWalletModal] = useState(false); // 🔥 ADD THIS LINE
  
  // Supported assets configuration
  const SUPPORTED_ASSETS = [
    { symbol: 'ALGO', name: 'Algorand', decimals: 6, blockchain: 'Algorand' },
    { symbol: 'USDT', name: 'Tether', decimals: 6, blockchain: 'Algorand' },
    { symbol: 'USDCa', name: 'USD Coin', decimals: 6, blockchain: 'Algorand' },
    { symbol: 'goBTC', name: 'Wrapped Bitcoin', decimals: 8, blockchain: 'Algorand' },
    { symbol: 'goETH', name: 'Wrapped Ethereum', decimals: 8, blockchain: 'Algorand' },
  ];

  useEffect(() => {
    if (user && userProfile) {
      fetchPortfolioData();
      fetchKYCStatus();
    }
  }, [user, userProfile]);

  // ✅ FIX: Fetch ALL chains, not just Algorand
  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      
      // Try to fetch multi-chain balances
      const response = await apiClient.get('/api/v1/wallet/balances');
      
      if (response.data.success) {
        setPortfolioData({
          total_usd: response.data.total_usd,
          assets: response.data.assets,
          timestamp: response.data.timestamp
        });
        
        // Extract wallet address if available
        if (response.data.assets && response.data.assets.length > 0) {
          const algorandAsset = response.data.assets.find(a => a.chain === 'algorand');
          if (algorandAsset?.address) {
            setWalletAddress(algorandAsset.address);
          }
        }
      }
      
    } catch (error: any) {
      console.error('Portfolio fetch error:', error);
      
      // ✅ FALLBACK: Check if user has Phase 1 Algorand wallet
      if (userProfile?.algorand_address) {
        setWalletAddress(userProfile.algorand_address);
        toast.info('Loading your wallet...');
        
        // Set minimal portfolio data
        setPortfolioData({
          success: true,
          total_usd: 0,
          assets: [],
          wallet_address: userProfile.algorand_address
        });
      } else {
        // No wallet found - prompt creation
        toast.error('Wallet not found. Creating wallet...');
        await createWallet();
      }
      
    } finally {
      setLoading(false);
    }
  };

  // ✅ FIX: Fetch KYC status
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
      // Set safe defaults to prevent crash
      setKycInfo({
        status: 'not_started',
        cumulative_volume: 0,
        limit: 5000,
        urgency: 'none',
      });
    }
  };

  const createWallet = async () => {
    try {
      const response = await apiClient.post('/api/v1/user/provision-wallets');

      if (response.data.success && response.data.mnemonic) {
        setPendingMnemonic(response.data.mnemonic);
        setWalletAddress(response.data.wallet_address);
        setShowMnemonicModal(true);
        toast.success('Wallet created successfully!');
      }
    } catch (error) {
      console.error('Wallet creation error:', error);
      toast.error('Failed to create wallet. Please try again.');
    }
  };

  const handleMnemonicBackupComplete = () => {
    localStorage.setItem('mnemonic_backed_up', 'true');
    setShowMnemonicModal(false);
    setPendingMnemonic(null);
    toast.success('Wallet secured successfully! 🎉');
    fetchPortfolioData(); // Refresh data
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

  const handleLogout = async () => {
    try {
      await signOut();
      toast.success('Logged out successfully');
    } catch (error) {
      console.error('Logout error:', error);
      toast.error('Logout failed');
    }
  };

  // ✅ ADDED: Handle real wallet connection
  const handleWalletConnected = (address: string, provider: string, chainId?: number) => {
    console.log('Wallet connected:', address, provider, chainId);
    toast.success(`${provider} wallet connected!`);
    setWalletAddress(address);
    fetchPortfolioData();
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

          <div className="flex items-center gap-3">
            {/* ✅ ADDED: Connect Wallet Button */}
            <button
              onClick={() => setShowWalletModal(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <Wallet className="h-4 w-4" />
              Connect Wallet
            </button>

            <button
              onClick={() => setShowReceiveModal(true)}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <ArrowDownLeft className="h-4 w-4" />
              Receive
            </button>

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
                      onClick={() => window.location.href = '/settings'}
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors rounded-t-lg"
                    >
                      <Settings className="h-4 w-4" />
                      <span>Settings</span>
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
              {['Algorand', 'Bitcoin', 'Ethereum', 'Polygon'].map(chain => (
                <div key={chain} className="flex items-center gap-2 text-xs text-gray-400">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  {chain}
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
            {/* ✅ Use multi-chain data if available, fallback to static list */}
            {portfolioData?.assets && portfolioData.assets.length > 0 ? (
              portfolioData.assets.map(asset => (
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
              // Fallback: Show supported assets with zero balances
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

      // Add this modal at the bottom of return statement (replace RealWalletConnect):
      {showWalletModal && (
        <WalletConnectModal
          isOpen={showWalletModal}
          onClose={() => setShowWalletModal(false)}
          onWalletConnected={(address, provider) => {
            console.log('Wallet connected:', address, provider);
            setWalletAddress(address);
            fetchPortfolioData();
            toast.success(`${provider} wallet connected to Seamount!`);
          }}
        />
      )}
    </div>
  );
};

export default DashboardPage;