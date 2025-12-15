// File: frontend/src/pages/DashboardPage.tsx
// ✅ CLEANED UP - Sidebar-driven architecture

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  Activity,
  RefreshCw,
  Shield,
  Coins,
  Plus,
  Target,
  ArrowUpRight,
  ArrowDownToLine,
  Key,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import Sidebar from '@/components/layout/Sidebar';
import ChainWalletCard from '@/components/wallet/ChainWalletCard';
import { FundWalletModal } from '@/components/wallet/FundWalletModal';
import { WithdrawModal } from '@/components/wallet/WithdrawModal';
import { SendForm } from '@/components/payments/SendForm';
import { SwapModal } from '@/components/modals/SwapModal';
import { EarnModal } from '@/components/modals/EarnModal';
import CreateRepoModal from '@/components/modals/CreateRepoModal';
import ConvertAssetModal from '@/components/modals/ConvertAssetModal';
import PublishOfferModal from '@/components/modals/PublishOfferModal';
import CollateralManagementModal from '@/components/modals/CollateralManagementModal';
import MarketOffersModal from '@/components/modals/MarketOffersModal';

// KYC Banner Component (unchanged from previous version)
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
  const [tokenizedAssets, setTokenizedAssets] = useState<any[]>([]);

  // Modal states
  const [showFundModal, setShowFundModal] = useState(false);
  const [showSendModal, setShowSendModal] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [showSwapModal, setShowSwapModal] = useState(false);
  const [showEarnModal, setShowEarnModal] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showCreateRepoModal, setShowCreateRepoModal] = useState(false);
  const [showConvertAssetModal, setShowConvertAssetModal] = useState(false);
  const [showPublishOfferModal, setShowPublishOfferModal] = useState(false);
  const [showCollateralModal, setShowCollateralModal] = useState(false);
  const [showMarketModal, setShowMarketModal] = useState(false);
  const { signOut } = useAuth();
  
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
      fetchTokenizedAssets();
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

  const fetchTokenizedAssets = async () => {
    try {
      const response = await apiClient.get('/api/v1/tokenization/my-assets');
      if (response.data.success) {
        setTokenizedAssets(response.data.assets || []);
      }
    } catch (error) {
      console.error('Failed to fetch tokenized assets:', error);
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
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <ArrowDownToLine className="h-4 w-4" />
              Fund
            </button>
            
            <button 
              onClick={() => setShowSendModal(true)} 
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <ArrowUpRight className="h-4 w-4" />
              Send
            </button>
            
            <button 
              onClick={() => setShowSwapModal(true)}
              className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Swap
            </button>
            
            <button 
              onClick={() => setShowEarnModal(true)}
              className="flex items-center gap-2 bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <TrendingUp className="h-4 w-4" />
              Earn
            </button>
            
            <button 
              onClick={() => setShowWithdrawModal(true)}
              className="flex items-center gap-2 bg-red-600 hover:bg-red-700 px-4 py-2 rounded-lg text-white font-medium transition-colors"
            >
              <ArrowDownToLine className="h-4 w-4" />
              Withdraw
            </button>
          </div>

          {/* 👤 USER MENU - Desktop & Mobile */}
          <div className="ml-auto relative">
            <button 
              onClick={() => setShowProfileMenu(!showProfileMenu)} 
              className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 px-3 py-2 rounded-lg text-white transition-colors border border-gray-700"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0">
                {userProfile?.first_name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase() || 'U'}
              </div>
              <span className="hidden sm:inline text-sm">
                {userProfile?.first_name || user?.email?.split('@')[0] || 'User'}
              </span>
            </button>
            
            {/* 📋 DROPDOWN MENU */}
            {showProfileMenu && (
              <>
                {/* Backdrop */}
                <div className="fixed inset-0 z-40" onClick={() => setShowProfileMenu(false)} />
                
                {/* Menu */}
                <div className="absolute right-0 mt-2 w-64 bg-gray-800 border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                  {/* User Info Header */}
                  <div className="px-4 py-3 bg-gradient-to-r from-blue-600 to-purple-600 border-b border-gray-700">
                    <div className="text-white font-semibold">
                      {userProfile?.first_name || 'User'}
                    </div>
                    <div className="text-blue-100 text-xs">
                      {user?.email}
                    </div>
                  </div>

                  {/* Menu Items */}
                  <div className="py-2">
                    {/* Recovery Phrases */}
                    <button 
                      onClick={() => {
                        setShowProfileMenu(false);
                        navigate('/wallet-recovery');
                      }} 
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors text-left"
                    >
                      <Key className="h-4 w-4 text-orange-400" />
                      <div>
                        <div className="text-sm font-medium">Recovery Phrases</div>
                        <div className="text-xs text-gray-500">View your seed phrases</div>
                      </div>
                    </button>

                    {/* Verify KYC */}
                    <button 
                      onClick={() => {
                        setShowProfileMenu(false);
                        navigate('/onboarding');
                      }} 
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-gray-300 transition-colors text-left"
                    >
                      <Shield className="h-4 w-4 text-green-400" />
                      <div>
                        <div className="text-sm font-medium">Verify Identity</div>
                        <div className="text-xs text-gray-500">Complete KYC verification</div>
                      </div>
                    </button>

                    {/* Admin Dashboard (only if admin) */}
                    {userProfile?.is_admin && (
                      <button 
                        onClick={() => {
                          setShowProfileMenu(false);
                          navigate('/admin');
                        }} 
                        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-yellow-400 transition-colors text-left border-t border-gray-700"
                      >
                        <Shield className="h-4 w-4" />
                        <div>
                          <div className="text-sm font-medium">Admin Dashboard</div>
                          <div className="text-xs text-yellow-500">Platform management</div>
                        </div>
                      </button>
                    )}

                    {/* Logout */}
                    <button 
                      onClick={() => {
                        setShowProfileMenu(false);
                        signOut();
                      }} 
                      className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-700 text-red-400 transition-colors text-left border-t border-gray-700"
                    >
                      <LogOut className="h-4 w-4" />
                      <div>
                        <div className="text-sm font-medium">Logout</div>
                        <div className="text-xs text-red-500">Sign out of your account</div>
                      </div>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Tokenization Quick Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {/* Tokenized Assets Card */}
            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Coins className="h-5 w-5 text-green-400" />
                </div>
                <span className="text-xs text-green-400 font-medium">Active</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">{tokenizedAssets.length}</div>
              <div className="text-sm text-gray-400">Tokenized Assets</div>
            </div>

            {/* Active Repos Card */}
            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <RefreshCw className="h-5 w-5 text-blue-400" />
                </div>
                <span className="text-xs text-blue-400 font-medium">Live</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">0</div>
              <div className="text-sm text-gray-400">Repo Loans</div>
            </div>

            {/* DVP Settlements Card */}
            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <Activity className="h-5 w-5 text-purple-400 animate-pulse" />
                </div>
                <span className="text-xs text-purple-400 font-medium">Sub-5s</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">~4.2s</div>
              <div className="text-sm text-gray-400">Avg Settlement</div>
            </div>

            {/* Collateral LTV Card */}
            <div className="bg-gradient-to-br from-orange-900/20 to-yellow-900/20 border border-orange-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-orange-500/20 rounded-lg">
                  <Target className="h-5 w-5 text-orange-400" />
                </div>
                <span className="text-xs text-orange-400 font-medium">Healthy</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">--</div>
              <div className="text-sm text-gray-400">Average LTV</div>
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
                  <div className="text-xs md:text-sm text-gray-400 mb-1">Total Balance</div>
                  <div className="text-2xl md:text-4xl font-bold text-white">${totalBalance.toFixed(2)}</div>
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
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">Multi-Chain Wallets</h2>
              <span className="text-sm text-gray-400">{createdChains} of 5 created</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 md:gap-4">
              {AUTO_CREATED_CHAINS.map(chain => (
                <ChainWalletCard 
                  key={chain.id} 
                  chain={chain.id} 
                  address={multiChainWallets[chain.id]?.address || ''} 
                  balance={calculateChainBalance(chain.id)} 
                  status={multiChainWallets[chain.id]?.address ? 'created' : 'not_created'} 
                  onCardClick={() => {}} 
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* All Modals */}
      <FundWalletModal open={showFundModal} onOpenChange={setShowFundModal} />
      <WithdrawModal open={showWithdrawModal} onOpenChange={setShowWithdrawModal} />
      <SendForm open={showSendModal} onOpenChange={setShowSendModal} />
      <SwapModal open={showSwapModal} onOpenChange={setShowSwapModal} />
      <EarnModal open={showEarnModal} onOpenChange={setShowEarnModal} />
      <CreateRepoModal 
        open={showCreateRepoModal} 
        onOpenChange={setShowCreateRepoModal}
        tokenizedAssets={tokenizedAssets}
      />
      <ConvertAssetModal 
        open={showConvertAssetModal} 
        onOpenChange={setShowConvertAssetModal}
      />
      <PublishOfferModal 
        open={showPublishOfferModal} 
        onOpenChange={setShowPublishOfferModal}
        tokenizedAssets={tokenizedAssets}
      />
      <CollateralManagementModal 
        open={showCollateralModal} 
        onOpenChange={setShowCollateralModal}
      />
      <MarketOffersModal 
        open={showMarketModal} 
        onOpenChange={setShowMarketModal}
      />
    </div>
  );
};

export default DashboardPage;