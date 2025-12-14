// File: frontend/src/pages/DashboardPage.tsx
// 🔄 REDESIGNED - Sidebar layout, removed external wallet cards

import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  Activity,
  RefreshCw,
  Shield,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownToLine,
  Target,
  Coins,    // ➕ New
  Plus,     // ➕ New
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';  // ➕ New
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
import MarketTerminalModal from '@/components/market/MarketTerminalModal';
import CreateRepoModal from '@/components/modals/CreateRepoModal';

// KYC Banner Component (unchanged)
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
        <AlertTriangle className="w-5 h-5 text-orange-400" />
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

  // Modal states
  const [showFundModal, setShowFundModal] = useState(false);
  const [showSendModal, setShowSendModal] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);
  const [showSwapModal, setShowSwapModal] = useState(false);
  const [showEarnModal, setShowEarnModal] = useState(false);
  const [showMarketTerminal, setShowMarketTerminal] = useState(false);
  const [showCreateRepoModal, setShowCreateRepoModal] = useState(false);
  const [tokenizedAssets, setTokenizedAssets] = useState<any[]>([]);

  // ✅ ONLY Auto-created chains (removed Base, Celo, BaseCAMP)
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
      fetchTokenizedAssets();  // ➕ New
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
        setTokenizedAssets(response.data.data.assets || []);
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
      {/* ✅ NEW: Sidebar */}
      <Sidebar />

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-white mb-2">Portfolio Overview</h1>
            <p className="text-gray-400">Manage your multi-chain digital assets</p>
          </div>

          {/* Action Buttons */}
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

          {/* ========== TOKENIZATION QUICK STATS ========== */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            {/* Tokenized Assets Card */}
            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Coins className="h-5 w-5 text-green-400" />
                </div>
                <span className="text-xs text-green-400 font-medium">+12.5%</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">3</div>
              <div className="text-sm text-gray-400">Tokenized Assets</div>
            </div>

            {/* Active Repos Card */}
            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <RefreshCw className="h-5 w-5 text-blue-400" />
                </div>
                <span className="text-xs text-blue-400 font-medium">1 Active</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">$1,050</div>
              <div className="text-sm text-gray-400">Repo Loans</div>
            </div>

            {/* DVP Settlements Card */}
            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-4 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <Activity className="h-5 w-5 text-purple-400 animate-pulse" />
                </div>
                <span className="text-xs text-purple-400 font-medium">Live</span>
              </div>
              <div className="text-2xl font-bold text-white mb-1">4.2s</div>
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
              <div className="text-2xl font-bold text-white mb-1">65%</div>
              <div className="text-sm text-gray-400">Average LTV</div>
            </div>
          </div>

          {/* ========== TOKENIZATION HUB ========== */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-1">
                  <Coins className="h-6 w-6 text-green-400" />
                  Tokenized Securities
                </h2>
                <p className="text-gray-400 text-sm">Digital twins of traditional assets</p>
              </div>
              <button
                onClick={() => navigate('/tokenization/convert')}
                className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg font-medium text-white transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                Convert Asset
              </button>
            </div>

            {/* Tokenized Assets Table */}
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700/50">
                    <th className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Asset</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Custodian</th>
                    <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">In Custody</th>
                    <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">On Chain</th>
                    <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Value (USD)</th>
                    <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {/* Example Row - Replace with actual data */}
                  <tr className="border-b border-gray-700/30 hover:bg-gray-800/30 transition-colors">
                    <td className="py-4 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-600 flex items-center justify-center">
                          <span className="text-white font-bold text-sm">DC</span>
                        </div>
                        <div>
                          <div className="text-white font-medium">DANGCEM</div>
                          <div className="text-xs text-gray-400">Dangote Cement Plc</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="text-gray-300">CSCS</span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <span className="text-white font-medium">1,000</span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <span className="text-green-400 font-medium">1,000</span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <span className="text-white font-bold">$45,000</span>
                    </td>
                    <td className="py-4 px-4 text-right">
                      <button className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white text-sm font-medium transition-colors">
                        Trade
                      </button>
                    </td>
                  </tr>
                  
                  {/* Empty State */}
                  <tr>
                    <td colSpan={6} className="py-8 text-center">
                      <div className="text-gray-400 mb-3">No tokenized assets yet</div>
                      <button
                        onClick={() => navigate('/tokenization/convert')}
                        className="text-green-400 hover:text-green-300 font-medium text-sm transition-colors"
                      >
                        Convert your first asset →
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* ========== ACTIVE REPO TRADES ========== */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-1">
                  <RefreshCw className="h-6 w-6 text-blue-400" />
                  Active Repo Trades
                </h2>
                <p className="text-gray-400 text-sm">Borrow against your tokenized assets</p>
              </div>
              <button
                onClick={() => setShowCreateRepoModal(true)}  // ✅ Updated
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg font-medium text-white transition-colors"
              >
                <Plus className="h-4 w-4" />
                Create Repo
              </button>
            </div>

            {/* Repo Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Example Repo Card - Replace with actual data */}
              <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full font-medium">Active</span>
                  <span className="text-xs text-gray-400">Matures in 29d</span>
                </div>
                
                <div className="mb-3">
                  <div className="text-sm text-gray-400 mb-1">Collateral</div>
                  <div className="text-lg font-bold text-white">25 DANGCEM</div>
                </div>
                
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <div className="text-xs text-gray-400 mb-1">Loan</div>
                    <div className="text-sm font-semibold text-white">$1,050</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400 mb-1">LTV</div>
                    <div className="text-sm font-semibold text-green-400">65%</div>
                  </div>
                </div>
                
                <div className="pt-3 border-t border-gray-700/50">
                  <div className="text-xs text-gray-400 mb-1">Repurchase Amount</div>
                  <div className="text-base font-bold text-white">$1,053.88</div>
                </div>
              </div>

              {/* Empty State Card */}
              <div className="bg-gray-800/30 border border-dashed border-gray-700 rounded-xl p-6 flex flex-col items-center justify-center min-h-[200px]">
                <RefreshCw className="h-12 w-12 text-gray-600 mb-3" />
                <div className="text-gray-400 text-sm text-center mb-3">No active repos</div>
                <button
                  onClick={() => navigate('/collateral/create-repo')}
                  className="text-blue-400 hover:text-blue-300 font-medium text-sm transition-colors"
                >
                  Create your first repo →
                </button>
              </div>
            </div>
          </div>

          {/* KYC Banner */}
          <KYCPromptBanner 
            kycStatus={kycInfo.status} 
            cumulativeVolume={kycInfo.cumulative_volume} 
            limit={kycInfo.limit} 
            urgency={kycInfo.urgency} 
          />

          {/* Market Terminal Preview */}
          <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-2xl p-6 mb-6 backdrop-blur-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-white flex items-center gap-2 mb-2">
                  <TrendingUp className="h-6 w-6 text-blue-400" />
                  Live Market Terminal
                </h2>
                <p className="text-gray-400 text-sm">Real-time market data & analytics</p>
              </div>
              <button
                onClick={() => setShowMarketTerminal(true)}
                className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-xl font-bold text-white transition-all"
              >
                <Activity className="h-5 w-5" />
                Open Terminal
              </button>
            </div>
          </div>

          {/* Balance Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="lg:col-span-2 bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-2xl p-6 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-sm text-gray-400 mb-1">Total Balance</div>
                  <div className="text-4xl font-bold text-white">${totalBalance.toFixed(2)}</div>
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

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
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

          {/* Cross-Border Banner */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold mb-2">Cross-Border Payments</h3>
                <p className="text-blue-100 text-sm mb-3">Send money globally at 1.2% fee vs 8% traditional</p>
                <div className="flex flex-wrap items-center gap-4 text-xs">
                  <span className="flex items-center gap-1"><Activity className="h-3 w-3" />Sub-5s settlement</span>
                  <span className="flex items-center gap-1"><Shield className="h-3 w-3" />Bank-grade security</span>
                </div>
              </div>
              <button onClick={() => setShowSendModal(true)} className="bg-white text-blue-600 px-6 py-3 rounded-xl font-semibold hover:bg-blue-50 transition-colors">
                Send Money
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      <FundWalletModal open={showFundModal} onOpenChange={setShowFundModal} />
      <WithdrawModal open={showWithdrawModal} onOpenChange={setShowWithdrawModal} />
      <SendForm open={showSendModal} onOpenChange={setShowSendModal} />
      <SwapModal open={showSwapModal} onOpenChange={setShowSwapModal} />
      <EarnModal open={showEarnModal} onOpenChange={setShowEarnModal} />
      <MarketTerminalModal isOpen={showMarketTerminal} onClose={() => setShowMarketTerminal(false)} />
      <CreateRepoModal 
        open={showCreateRepoModal} 
        onOpenChange={setShowCreateRepoModal}
        tokenizedAssets={tokenizedAssets}
      />
      
    </div>
  );
};

export default DashboardPage;