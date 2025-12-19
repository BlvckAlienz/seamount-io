// File: frontend/src/pages/DashboardPage.tsx
// ✅ PORTFOLIO VIEW - With WalletDetailModal Integration

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  Activity,
  RefreshCw,
  Shield,
  Coins,
  Target,
  ArrowUpRight,
  ArrowDownToLine,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import Sidebar from '@/components/layout/Sidebar';
import ChainWalletCard from '@/components/wallet/ChainWalletCard';
import WalletDetailModal from '@/components/wallet/WalletDetailModal';
import { FundWalletModal } from '@/components/wallet/FundWalletModal';
import { WithdrawModal } from '@/components/wallet/WithdrawModal';
import { SendForm } from '@/components/payments/SendForm';
import { SwapModal } from '@/components/modals/SwapModal';
import { EarnModal } from '@/components/modals/EarnModal';
import { formatCurrencyUSD } from '@/utils/formatters';

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
  
  return (
    <div className="rounded-2xl border border-orange-500/30 bg-orange-900/20 p-4 mb-6 backdrop-blur-sm">
      <div className="flex items-start gap-3">
        <Shield className="w-5 h-5 text-orange-400" />
        <div className="flex-1">
          <h3 className="font-semibold text-orange-200 mb-1">Complete KYC Verification</h3>
          <p className="text-sm text-orange-300 mb-3">
            ${remaining.toFixed(2)} remaining before verification required
          </p>
          <button
            onClick={() => window.location.href = '/onboarding'}
            className="px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition-all"
          >
            Verify Now
          </button>
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component
const DashboardPage = () => {
  const { user, userProfile } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [kycInfo, setKycInfo] = useState({
    status: 'not_started',
    cumulative_volume: 0,
    limit: 5000,
    urgency: 'none',
  });
  const [multiChainWallets, setMultiChainWallets] = useState<any>({});
  const [collateralStats, setCollateralStats] = useState({
    activePositions: 0,
    totalValue: 0,
    repoTrades: 0,
  });

  // Wallet modal states
  const [selectedChain, setSelectedChain] = useState<string | null>(null);
  const [showWalletModal, setShowWalletModal] = useState(false);

  // Payment modal states
  const [showFundModal, setShowFundModal] = useState(false);
  const [showSendModal, setShowSendModal] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [showSwapModal, setShowSwapModal] = useState(false);
  const [showEarnModal, setShowEarnModal] = useState(false);
  
  const AUTO_CREATED_CHAINS = [
    { id: 'algorand', name: 'Algorand', symbol: 'ALGO' },
    { id: 'bitcoin', name: 'Bitcoin', symbol: 'BTC' },
    { id: 'ethereum', name: 'Ethereum', symbol: 'ETH' },
    { id: 'polygon', name: 'Polygon', symbol: 'MATIC' },
    { id: 'tron', name: 'TRON', symbol: 'TRX' },
  ];

  useEffect(() => {
    if (user && userProfile) {
      fetchPortfolioData();
      fetchKYCStatus();
      fetchMultiChainWallets();
      fetchCollateralStats();
    }
  }, [user, userProfile]);

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
      }
    } catch (error: any) {
      console.error('Portfolio fetch error:', error);
      toast.error('Failed to load portfolio data');
    } finally {
      setLoading(false);
    }
  };

  const fetchCollateralStats = async () => {
    try {
      const response = await apiClient.get('/api/v1/collateral/positions');
      if (response.data.success) {
        const positions = response.data.positions || [];
        setCollateralStats({
          activePositions: positions.filter((p: any) => p.status === 'active').length,
          totalValue: positions.reduce((sum: number, p: any) => sum + p.current_value_usd, 0),
          repoTrades: positions.filter((p: any) => p.lock_type === 'repo').length,
        });
      }
    } catch (error) {
      console.error('Failed to fetch collateral stats:', error);
    }
  };

  const fetchKYCStatus = async () => {
    try {
      const response = await apiClient.get('/api/v1/kyc/kyc-status');
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

  const fetchMultiChainWallets = async () => {
    try {
      const response = await apiClient.get('/api/v1/wallet-creation/status');
      if (response.data.success) {
        const wallets: Record<string, any> = {};
        Object.entries(response.data.chains || {}).forEach(([chain, data]: [string, any]) => {
          if (data.address) {
            wallets[chain] = { address: data.address };
          }
        });
        setMultiChainWallets(wallets);
      }
    } catch (error) {
      console.error('Failed to fetch wallets:', error);
    }
  };

  const calculateChainBalance = (chain: string) => {
    if (!portfolioData?.assets) return 0;
    return portfolioData.assets
      .filter((asset: any) => asset.chain === chain)
      .reduce((total: number, asset: any) => total + (asset.usd_value || 0), 0);
  };

  const handleWalletCardClick = (chain: string) => {
    if (multiChainWallets[chain]?.address) {
      setSelectedChain(chain);
      setShowWalletModal(true);
    } else {
      toast.error(`${chain} wallet not created yet`);
    }
  };

  const totalBalance = portfolioData?.total_usd || 0;
  const createdChains = Object.keys(multiChainWallets).filter(chain => multiChainWallets[chain]?.address).length;

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-400">Loading your portfolio...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      
      {/* Main Content - Mobile padding adjusted */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-4 md:mb-6">
            <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">Portfolio Overview</h1>
            <p className="text-sm md:text-base text-gray-400">Manage your tokenized securities & digital assets</p>
          </div>

          {/* Quick Action Buttons */}
          <div className="flex flex-wrap gap-2 mb-6">
            <button 
              onClick={() => setShowFundModal(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-3 md:px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors"
            >
              <ArrowDownToLine className="h-4 w-4" />
              <span className="hidden sm:inline">Fund</span>
            </button>
            
            <button 
              onClick={() => setShowSendModal(true)} 
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-3 md:px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors"
            >
              <ArrowUpRight className="h-4 w-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
            
            <button 
              onClick={() => setShowSwapModal(true)}
              className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-3 md:px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              <span className="hidden sm:inline">Swap</span>
            </button>
            
            <button 
              onClick={() => setShowEarnModal(true)}
              className="flex items-center gap-2 bg-yellow-600 hover:bg-yellow-700 px-3 md:px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors"
            >
              <TrendingUp className="h-4 w-4" />
              <span className="hidden sm:inline">Earn</span>
            </button>
            
            <button 
              onClick={() => setShowWithdrawModal(true)}
              className="flex items-center gap-2 bg-red-600 hover:bg-red-700 px-3 md:px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors"
            >
              <ArrowDownToLine className="h-4 w-4" />
              <span className="hidden sm:inline">Withdraw</span>
            </button>
          </div>

          {/* 🆕 COLLATERAL QUICK STATS - Replaces old cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            {/* Active Positions Card */}
            <div className="bg-gradient-to-br from-orange-900/20 to-yellow-900/20 border border-orange-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-orange-500/20 rounded-lg">
                  <Shield className="h-5 w-5 text-orange-400" />
                </div>
                <span className="text-xs text-orange-400 font-medium">Live</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">{collateralStats.activePositions}</div>
              <div className="text-sm text-gray-400">Active Positions</div>
            </div>

            {/* Total Value Card */}
            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Coins className="h-5 w-5 text-green-400" />
                </div>
                <span className="text-xs text-green-400 font-medium">USD</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">{formatCurrencyUSD(collateralStats.totalValue)}</div>
              <div className="text-sm text-gray-400">Total Assets Value</div>
            </div>

            {/* Repo Trades Card */}
            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Target className="h-5 w-5 text-blue-400" />
                </div>
                <span className="text-xs text-blue-400 font-medium">Active</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">{collateralStats.repoTrades}</div>
              <div className="text-sm text-gray-400">Repo Trades</div>
            </div>
          </div>

          {/* KYC Banner */}
          <KYCPromptBanner 
            kycStatus={kycInfo.status} 
            cumulativeVolume={kycInfo.cumulative_volume} 
            limit={kycInfo.limit} 
            urgency={kycInfo.urgency} 
          />

          {/* Balance Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
            <div className="lg:col-span-2 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-xl md:rounded-2xl p-4 md:p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs md:text-sm text-gray-400 mb-1">Total Crypto Balance</div>
                  <div className="text-2xl md:text-4xl font-bold text-white">{formatCurrencyUSD(totalBalance)}</div>
                </div>
                <button onClick={fetchPortfolioData} className="p-3 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors">
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
              <div className="text-2xl font-bold text-white mb-4">{createdChains} / 5 Active</div>
              <div className="space-y-2">
                {AUTO_CREATED_CHAINS.map(chain => (
                  <div key={chain.id} className="flex items-center gap-2 text-xs text-gray-400">
                    <div className={`w-2 h-2 rounded-full ${multiChainWallets[chain.id]?.address ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`}></div>
                    {chain.name}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Multi-Chain Wallets */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-4 md:p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg md:text-xl font-bold text-white">Multi-Chain Wallets</h2>
              <span className="text-xs md:text-sm text-gray-400">{createdChains} of 5 created</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3 md:gap-4">
              {AUTO_CREATED_CHAINS.map(chain => (
                <ChainWalletCard 
                  key={chain.id} 
                  chain={chain.id} 
                  address={multiChainWallets[chain.id]?.address || ''} 
                  balance={calculateChainBalance(chain.id)} 
                  status={multiChainWallets[chain.id]?.address ? 'created' : 'not_created'} 
                  onCardClick={() => handleWalletCardClick(chain.id)} 
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* All Modals */}
      {selectedChain && (
        <WalletDetailModal
          isOpen={showWalletModal}
          onClose={() => {
            setShowWalletModal(false);
            setSelectedChain(null);
          }}
          chain={selectedChain}
          chainName={AUTO_CREATED_CHAINS.find(c => c.id === selectedChain)?.name || selectedChain}
          address={multiChainWallets[selectedChain]?.address || ''}
          balance={calculateChainBalance(selectedChain)}
          onOpenFundModal={() => setShowFundModal(true)}
        />
      )}
      <FundWalletModal open={showFundModal} onOpenChange={setShowFundModal} />
      <WithdrawModal open={showWithdrawModal} onOpenChange={setShowWithdrawModal} />
      <SendForm open={showSendModal} onOpenChange={setShowSendModal} />
      <SwapModal open={showSwapModal} onOpenChange={setShowSwapModal} />
      <EarnModal open={showEarnModal} onOpenChange={setShowEarnModal} />
    </div>
  );
};

export default DashboardPage;