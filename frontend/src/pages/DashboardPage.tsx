// File: frontend/src/pages/DashboardPage.tsx
// 💎 TETHER WDK-INSPIRED PREMIUM DASHBOARD
// Beautiful wallet cards, smooth animations, persistent KYC banner

import React, { useState, useEffect } from 'react';
import {
  TrendingUp, DollarSign, Activity, RefreshCw, Shield, AlertTriangle,
  Bitcoin, Coins, Copy, Check, Eye, EyeOff, Download, Lock,
  ExternalLink, ArrowUpRight, ArrowDownLeft, Settings, LogOut, User
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { apiClient } from '../config/api';

// ============================================================================
// PREMIUM ASSET CARD COMPONENT
// ============================================================================

const AssetCard = ({ asset, onBuy, onSend }) => {
  const getGradient = (symbol: string) => {
    const gradients = {
      'BTC': 'from-orange-500 to-yellow-600',
      'ETH': 'from-gray-400 to-slate-600',
      'MATIC': 'from-purple-500 to-indigo-600',
      'USDT': 'from-green-500 to-emerald-600',
      'USDC': 'from-blue-500 to-cyan-600',
      'ALGO': 'from-purple-500 to-indigo-600'
    };
    return gradients[symbol] || 'from-gray-500 to-gray-600';
  };

  const getIcon = (symbol: string) => {
    switch (symbol) {
      case 'BTC': return <Bitcoin className="h-8 w-8" />;
      case 'ETH': return <Coins className="h-8 w-8" />;
      case 'MATIC': return <Coins className="h-8 w-8" />;
      default: return <DollarSign className="h-8 w-8" />;
    }
  };

  const balance = asset.balance || 0;
  const valueUsd = asset.value_usd || 0;
  const hasBalance = balance > 0;

  return (
    <div className="group relative bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl p-6 border border-gray-700/50 hover:border-blue-500/50 transition-all hover:shadow-xl hover:shadow-blue-500/10 transform hover:-translate-y-1">
      {/* Gradient overlay on hover */}
      <div className={`absolute inset-0 bg-gradient-to-br ${getGradient(asset.symbol)} opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity duration-300`} />
      
      <div className="relative">
        {/* Header */}
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

        {/* Asset Info */}
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

        {/* Action Buttons */}
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
// KYC PROMPT BANNER (Persistent, Color-coded)
// ============================================================================

const KYCPromptBanner = ({ kycStatus, cumulativeVolume, limit, urgency }) => {
  const [dismissed, setDismissed] = useState(false);

  // Don't show if verified or dismissed
  if (kycStatus === 'verified' || dismissed || urgency === 'none') {
    return null;
  }

  const remaining = Math.max(0, limit - cumulativeVolume);
  const percentUsed = (cumulativeVolume / limit) * 100;

  // Urgency-based styling
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
      icon: <AlertTriangle className="w-5 h-5" />,
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

  const config = urgencyConfig[urgency];

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
// PREMIUM WALLET ADDRESS DISPLAY
// ============================================================================

const WalletAddressCard = ({ address }) => {
  const [copied, setCopied] = useState(false);
  
  const shortenAddress = (addr: string) => {
    if (!addr) return '';
    return `${addr.slice(0, 7)}...${addr.slice(-5)}`;
  };

  const copyAddress = () => {
    navigator.clipboard.writeText(address);
    setCopied(true);
    toast.success('Address copied!');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-2xl p-6 backdrop-blur-sm hover:shadow-xl hover:shadow-blue-500/10 transition-all">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="text-sm text-gray-400 mb-1">Your Primary Wallet</div>
          <div className="flex items-center gap-3">
            <span className="text-white font-mono text-lg">{shortenAddress(address)}</span>
            <button
              onClick={copyAddress}
              className={`p-2 rounded-lg transition-all ${
                copied
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-800 hover:bg-gray-700 text-gray-400'
              }`}
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
        </div>
        
        {/* ✅ FIXED: Proper <a> tag structure */}
        <a
          href={`https://explorer.blockchain.com/address/${address}`}
          target="_blank"
          rel="noopener noreferrer"
          className="p-3 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors"
        >
          <ExternalLink className="h-5 w-5" />
        </a>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

const DashboardPage = () => {
  const { user, signOut } = useAuth();
  const [loading, setLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState(null);
  const [kycInfo, setKycInfo] = useState({
    status: 'not_started',
    cumulative_volume: 0,
    limit: 5000,
    urgency: 'none',
  });
  const [showProfileMenu, setShowProfileMenu] = useState(false);

  // Supported assets configuration
  const SUPPORTED_ASSETS = [
    { symbol: 'BTC', name: 'Bitcoin', decimals: 8, blockchain: 'Bitcoin' },
    { symbol: 'ETH', name: 'Ethereum', decimals: 18, blockchain: 'Ethereum' },
    { symbol: 'MATIC', name: 'Polygon', decimals: 18, blockchain: 'Polygon' },
    { symbol: 'USDT', name: 'Tether', decimals: 6, blockchain: 'Ethereum' },
    { symbol: 'USDC', name: 'USD Coin', decimals: 6, blockchain: 'Ethereum' },
  ];

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch portfolio balances
      const portfolioResponse = await apiClient.get('/api/v1/wallet/balances');
      setPortfolioData(portfolioResponse.data);
      
      // Fetch KYC status
      const kycResponse = await apiClient.get('/api/v1/users/kyc-status');
      setKycInfo(kycResponse.data);
      
    } catch (error) {
      console.error('Dashboard fetch error:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleBuyAsset = (asset) => {
    toast('Buy feature coming soon!');
    // TODO: Implement on-ramp
  };

  const handleSendAsset = (asset) => {
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

  const totalBalance = portfolioData?.total_usd || 0;
  const balances = portfolioData?.balances || {};
  const walletAddress = portfolioData?.wallet_address || '';

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

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-4 md:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 md:mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">Portfolio</h1>
            <p className="text-gray-400 text-sm md:text-base">Manage your multi-chain wallet</p>
          </div>

          <div className="relative">
            <button
              onClick={() => setShowProfileMenu(!showProfileMenu)}
              className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-white transition-colors"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
                {user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="text-sm hidden md:inline">{user?.email?.split('@')[0] || 'User'}</span>
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

        {/* KYC Banner */}
        <KYCPromptBanner
          kycStatus={kycInfo.status}
          cumulativeVolume={kycInfo.cumulative_volume}
          limit={kycInfo.limit}
          urgency={kycInfo.urgency}
        />

        {/* Wallet Address */}
        {walletAddress && (
          <div className="mb-6">
            <WalletAddressCard address={walletAddress} />
          </div>
        )}

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
                onClick={fetchDashboardData}
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
              {['Bitcoin', 'Ethereum', 'Polygon'].map(chain => (
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
            <span className="text-sm text-gray-400">{SUPPORTED_ASSETS.length} supported</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            {assetCards.map(asset => (
              <AssetCard
                key={asset.symbol}
                asset={asset}
                onBuy={() => handleBuyAsset(asset)}
                onSend={() => handleSendAsset(asset)}
              />
            ))}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-6 md:mb-8 backdrop-blur-sm">
          <h3 className="text-lg font-bold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: ArrowDownLeft, label: 'Buy', color: 'text-blue-400' },
              { icon: ArrowUpRight, label: 'Send', color: 'text-purple-400' },
              { icon: RefreshCw, label: 'Swap', color: 'text-green-400' },
              { icon: TrendingUp, label: 'Earn', color: 'text-yellow-400' },
            ].map(action => (
              <button 
                key={action.label}
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
            <button className="bg-white text-blue-600 px-6 py-3 rounded-xl font-semibold hover:bg-blue-50 transition-colors whitespace-nowrap shadow-lg hover:shadow-white/50">
              Send Money
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;