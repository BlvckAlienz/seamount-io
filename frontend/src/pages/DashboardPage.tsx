// File: frontend/src/pages/DashboardPage.tsx
// ✅ COMPLETE VERSION - Ready for production

import React, { useState, useEffect } from 'react';
import {
  TrendingUp, Activity, RefreshCw, Shield, AlertTriangle,
  Copy, Check, ExternalLink, ArrowUpRight, LogOut, User,
  ArrowDownLeft, RefreshCw as SwapIcon, Key
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { apiClient } from '../config/api';
import NigerianUserBanner from '../components/layout/NigerianUserBanner';
import ChainWalletCard from '../components/wallet/ChainWalletCard';
import WalletDetailModal from '../components/wallet/WalletDetailModal';
import WalletCreationStatusBanner from '../components/wallet/WalletCreationStatusBanner';

// KYC Banner Component
interface KYCPromptBannerProps {
  kycStatus: string;
  cumulativeVolume: number;
  limit: number;
  urgency: string;
}

const KYCPromptBanner: React.FC<KYCPromptBannerProps> = ({
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
        <div className={config.text}>{config.icon}</div>
        <div className="flex-1">
          <h3 className={`font-semibold mb-1 ${config.text}`}>{config.title}</h3>
          <p className={`text-sm mb-3 ${config.text}`}>{config.message}</p>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-3">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                urgency === 'critical' ? 'bg-red-600' :
                urgency === 'warning' ? 'bg-orange-500' : 'bg-blue-500'
              }`}
              style={{ width: `${Math.min(100, percentUsed)}%` }}
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.location.href = '/onboarding'}
              className={`px-4 py-2 rounded-lg font-medium transition-all shadow-lg ${
                urgency === 'critical' 
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : urgency === 'warning'
                  ? 'bg-orange-500 hover:bg-orange-600 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              {config.action}
            </button>
            {config.dismissible && (
              <button onClick={() => setDismissed(true)} className={`text-sm ${config.text} hover:underline`}>
                Remind me later
              </button>
            )}
          </div>
        </div>
        {config.dismissible && (
          <button onClick={() => setDismissed(true)} className={`${config.text} hover:opacity-70`}>
            <Check className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
};

// Main Dashboard Component
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
  const [multiChainWallets, setMultiChainWallets] = useState<any>({});
  const [selectedChain, setSelectedChain] = useState<string | null>(null);
  const [showWalletModal, setShowWalletModal] = useState(false);
  const [walletCreationStatus, setWalletCreationStatus] = useState<any>(null);
  
  const SUPPORTED_CHAINS = [
  { id: 'bitcoin', name: 'Bitcoin', symbol: 'BTC' },
  { id: 'ethereum', name: 'Ethereum', symbol: 'ETH' },
  { id: 'polygon', name: 'Polygon', symbol: 'MATIC' },
  { id: 'algorand', name: 'Algorand', symbol: 'ALGO' },
  { id: 'tron', name: 'TRON', symbol: 'TRX' } // ✅ Newly added
  // { id: 'arbitrum', name: 'Arbitrum', symbol: 'ETH' }, // ❌ Commented out
  // { id: 'ton', name: 'TON', symbol: 'TON' }, // ❌ Commented out  
  // { id: 'solana', name: 'Solana', symbol: 'SOL' } // ❌ Commented out
];

  // Add this useEffect to verify chain integration
  useEffect(() => {
    const verifyChainIntegration = async () => {
      try {
        const response = await apiClient.get('/api/v1/wallet/multi-chain-status');
        const chains = Object.keys(response.data.wallets || {});
        
        console.log('✅ ACTIVE CHAINS:', chains);
        
        // Verify we have all 8 chains
        const expectedChains = ['algorand', 'bitcoin', 'ethereum', 'polygon', 'arbitrum', 'ton', 'tron', 'solana'];
        const missingChains = expectedChains.filter(chain => !chains.includes(chain));
        
        if (missingChains.length > 0) {
          console.warn('⚠️ Missing chains:', missingChains);
        } else {
          console.log('🎯 ALL 8 CHAINS ACTIVE!');
        }
      } catch (error) {
        console.error('Chain verification failed:', error);
      }
    };
    
    if (user) {
      verifyChainIntegration();
    }
  }, [user]);

  useEffect(() => {
    if (user && userProfile) {
      fetchPortfolioData();
      fetchKYCStatus();
      fetchMultiChainWallets();
      fetchWalletCreationStatus();
    }
  }, [user, userProfile]);

  const fetchWalletCreationStatus = async () => {
    try {
      const response = await apiClient.get('/api/v1/wallet-creation/status');
      if (response.data.success) {
        setWalletCreationStatus(response.data);
      }
    } catch (error) {
      console.error('Failed to fetch wallet creation status:', error);
    }
  };

  const handleRetrySuccess = () => {
    fetchWalletCreationStatus();
    fetchMultiChainWallets();
    fetchPortfolioData();
  };

  const fetchMultiChainWallets = async () => {
    try {
      const response = await apiClient.get('/api/v1/wallet-creation/status');
      if (response.data.success) {
        // Extract wallets from the status response
        const wallets = {};
        Object.entries(response.data.chains || {}).forEach(([chain, data]: [string, any]) => {
          if (data.address) {
            wallets[chain] = { address: data.address };
          }
        });
        setMultiChainWallets(wallets);
      }
    } catch (error) {
      console.error('Multi-chain wallet status fetch failed:', error);
      setMultiChainWallets({});
    }
  };

  const getAssetChain = (symbol: string) => {
    const chainMap: { [key: string]: string } = {
      'ALGO': 'algorand', 'USDCa': 'algorand', 'USDT': 'algorand', 
      'goBTC': 'algorand', 'goETH': 'algorand', 'BTC': 'bitcoin',
      'ETH': 'ethereum', 'MATIC': 'polygon'
    };
    return chainMap[symbol] || 'algorand';
  };

  const calculateChainBalance = (chain: string) => {
    if (!portfolioData?.assets) return 0;
    return portfolioData.assets
      .filter((asset: any) => getAssetChain(asset.symbol) === chain)
      .reduce((total: number, asset: any) => total + (asset.usd_value || 0), 0);
  };

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
      if (userProfile?.algorand_address) {
        setPortfolioData({ success: true, total_usd: 0, assets: [], wallet_address: userProfile.algorand_address });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleWalletCardClick = (chain: string) => {
    if (multiChainWallets[chain]?.address) {
      setSelectedChain(chain);
      setShowWalletModal(true);
    } else {
      toast.error(`${chain} wallet not created yet`);
    }
  };

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
    }
  };

  const handleVerifyKYC = async () => {
    try {
      const kycResponse = await apiClient.get('/api/v1/users/kyc-status');
      if (kycResponse.data.status === 'verified' || kycResponse.data.status === 'approved') {
        toast.success('Your account is already verified!');
        return;
      }
      window.location.href = '/onboarding';
    } catch (error) {
      console.error('KYC verification error:', error);
      toast.error('Unable to start verification process');
    }
  };

  const handleViewSeedPhrases = () => {
    window.location.href = '/wallet-recovery';
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
  const createdChains = Object.keys(multiChainWallets).filter(chain => multiChainWallets[chain]?.address).length;

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
        <div className="mb-6 md:mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">Portfolio</h1>
            <p className="text-gray-400 text-sm md:text-base">Manage your multi-chain wallet</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => toast.info('Send functionality coming soon!')} className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white font-medium transition-colors">
              <ArrowUpRight className="h-4 w-4" />Send
            </button>
            <button onClick={() => toast.info('Swap functionality coming soon!')} className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg text-white font-medium transition-colors">
              <SwapIcon className="h-4 w-4" />Swap
            </button>
            <button onClick={() => toast.info('Earn functionality coming soon!')} className="flex items-center gap-2 bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded-lg text-white font-medium transition-colors">
              <TrendingUp className="h-4 w-4" />Earn
            </button>
            <div className="relative">
              <button onClick={() => setShowProfileMenu(!showProfileMenu)} className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-lg text-white transition-colors">
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold">
                  {userProfile?.first_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
                </div>
                <span className="text-sm hidden md:inline">{userProfile?.first_name || user?.email?.split('@')[0] || 'User'}</span>
              </button>
              {showProfileMenu && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowProfileMenu(false)} />
                  <div className="absolute right-0 mt-2 w-56 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
                    <button onClick={handleViewSeedPhrases} className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors">
                      <Key className="h-4 w-4" />
                      <span>Recovery Phrases</span>
                    </button>
                    <button onClick={handleVerifyKYC} className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors">
                      <Shield className="h-4 w-4" />
                      <span>Verify</span>
                    </button>
                    <button onClick={handleLogout} className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-red-400 transition-colors rounded-b-lg">
                      <LogOut className="h-4 w-4" />
                      <span>Logout</span>
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        <NigerianUserBanner />
        
        {walletCreationStatus && !walletCreationStatus.overall_complete && (
          <WalletCreationStatusBanner status={walletCreationStatus} onRetrySuccess={handleRetrySuccess} />
        )}

        <KYCPromptBanner kycStatus={kycInfo.status} cumulativeVolume={kycInfo.cumulative_volume} limit={kycInfo.limit} urgency={kycInfo.urgency} />

        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-6 md:mb-8 backdrop-blur-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">Multi-Chain Wallets</h2>
            <span className="text-sm text-gray-400">{createdChains} of {SUPPORTED_CHAINS.length} created</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {SUPPORTED_CHAINS.map(chain => (
              <ChainWalletCard key={chain.id} chain={chain.id} address={multiChainWallets[chain.id]?.address || ''} balance={calculateChainBalance(chain.id)} status={multiChainWallets[chain.id]?.address ? 'created' : 'not_created'} onCardClick={() => handleWalletCardClick(chain.id)} />
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
          <div className="lg:col-span-2 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-2xl p-6 backdrop-blur-sm hover:shadow-xl hover:shadow-blue-500/10 transition-all">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-sm text-gray-400 mb-1">Total Balance</div>
                <div className="text-3xl md:text-4xl font-bold text-white">${totalBalance.toFixed(2)}</div>
              </div>
              <button onClick={fetchPortfolioData} className="p-3 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors hover:rotate-180 duration-300">
                <RefreshCw className="h-5 w-5" />
              </button>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-green-400 animate-pulse" />
              <span className="text-green-400">Live Multi-Chain Balances</span>
            </div>
          </div>
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 backdrop-blur-sm">
            <div className="text-sm text-gray-400 mb-2">Networks</div>
            <div className="text-2xl font-bold text-white mb-4">Multi-Chain</div>
            <div className="space-y-2">
              {SUPPORTED_CHAINS.map(chain => (
                <div key={chain.id} className="flex items-center gap-2 text-xs text-gray-400">
                  <div className={`w-2 h-2 rounded-full ${multiChainWallets[chain.id]?.address ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`}></div>
                  {chain.name}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-6 md:mb-8 backdrop-blur-sm">
          <h3 className="text-lg font-bold text-white mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[
              { icon: ArrowUpRight, label: 'Send', color: 'text-green-400', action: () => toast.info('Send functionality coming soon!') },
              { icon: SwapIcon, label: 'Swap', color: 'text-purple-400', action: () => toast.info('Swap feature coming soon!') },
              { icon: TrendingUp, label: 'Earn', color: 'text-yellow-400', action: () => toast.info('Yield farming coming soon!') },
            ].map(action => (
              <button key={action.label} onClick={action.action} className="flex flex-col items-center gap-2 p-4 rounded-xl bg-gray-800 hover:bg-gray-700 transition-all hover:scale-105">
                <action.icon className={`h-6 w-6 ${action.color}`} />
                <span className="text-sm text-gray-300">{action.label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white hover:shadow-2xl hover:shadow-blue-500/50 transition-all">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h3 className="text-xl font-bold mb-2">Cross-Border Payments</h3>
              <p className="text-blue-100 text-sm mb-3">Send money globally at 2.9% fee vs 8% traditional (5.1% savings!)</p>
              <div className="flex flex-wrap items-center gap-4 text-xs">
                <span className="flex items-center gap-1"><Activity className="h-3 w-3" />Sub-5s settlement</span>
                <span className="flex items-center gap-1"><Shield className="h-3 w-3" />Bank-grade security</span>
              </div>
            </div>
            <button onClick={() => toast.info('Cross-border payments coming soon!')} className="bg-white text-blue-600 px-6 py-3 rounded-xl font-semibold hover:bg-blue-50 transition-colors whitespace-nowrap shadow-lg">
              Send Money
            </button>
          </div>
        </div>
      </div>

      {selectedChain && (
        <WalletDetailModal isOpen={showWalletModal} onClose={() => { setShowWalletModal(false); setSelectedChain(null); }} chain={selectedChain} chainName={SUPPORTED_CHAINS.find(c => c.id === selectedChain)?.name || selectedChain} address={multiChainWallets[selectedChain]?.address || ''} balance={calculateChainBalance(selectedChain)} />
      )}
    </div>
  );
};

export default DashboardPage;