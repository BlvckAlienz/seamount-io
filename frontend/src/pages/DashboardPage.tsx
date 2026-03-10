// File: frontend/src/pages/DashboardPage.tsx
// ✅ PORTFOLIO VIEW - With WalletDetailModal Integration

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  TrendingUp,
  Activity,
  RefreshCw,
  Shield,
  Wallet,
  Coins,
  Clock,
  Target,
  ArrowUpRight,
  ArrowDownToLine,
  Download
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
import ReceiveModal from '@/components/wallet/ReceiveModal';  // ✅ ADD THIS
import { TransactionHistoryModal } from '@/components/wallet/TransactionHistoryModal';
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
  const [xrpTotalUSD, setXrpTotalUSD] = useState<number>(0);
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
  const [showReceiveModal, setShowReceiveModal] = useState(false);  // ✅ ADD THIS
  const [showHistoryModal, setShowHistoryModal] = useState(false);
  
  const AUTO_CREATED_CHAINS = [
    { id: 'algorand', name: 'Algorand',   symbol: 'ALGO'  },
    { id: 'bitcoin',  name: 'Bitcoin',    symbol: 'BTC'   },
    { id: 'ethereum', name: 'Ethereum',   symbol: 'ETH'   },
    { id: 'polygon',  name: 'Polygon',    symbol: 'MATIC' },
    { id: 'tron',     name: 'TRON',       symbol: 'TRX'   },
    { id: 'solana',   name: 'Solana',     symbol: 'SOL'   },
    { id: 'xrp',      name: 'XRP Ledger', symbol: 'RLUSD' },  // ✅ NEW
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

    // XRP is custodial — check deposit-info for tag existence
    // If the endpoint responds (even without xrp_service), tag is assigned
    try {
      const [xrpDepositRes, xrpBalRes] = await Promise.all([
        apiClient.get('/api/v1/xrp/deposit-info'),
        apiClient.get('/api/v1/xrp/balances'),
      ]);

      if (xrpDepositRes.data?.success && xrpDepositRes.data?.destination_tag) {
        setMultiChainWallets(prev => ({
          ...prev,
          xrp: { address: `tag:${xrpDepositRes.data.destination_tag}` }
        }));
      }

      if (xrpBalRes.data?.success) {
        const b = xrpBalRes.data.balances;
        // XRP price approximated at $0.50 for display — good enough for card
        const total =
          parseFloat(b.RLUSD || '0') +
          parseFloat(b.USDC  || '0') +
          parseFloat(b.XRP   || '0') * 0.5;
        setXrpTotalUSD(parseFloat(total.toFixed(2)));
      }
    } catch {
      // XRP not set up yet — card shows as "not_created" which is fine
    }
  };

  const calculateChainBalance = (chain: string) => {
    if (chain === 'xrp') return xrpTotalUSD;  // ✅ from internal balances
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
      // XRP: route to setup page; others: show error
      if (chain === 'xrp') {
        navigate('/xrp');
      } else {
        toast.error(`${chain} wallet not created yet`);
      }
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
            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-2 md:gap-3 mb-2">
              <Wallet className="h-6 w-6 md:h-8 md:w-8 text-green-400" />
              <span>Smart Wallets</span>
            </h1>
            <p className="text-sm md:text-base text-gray-400">Fund with local currency. Trade and earn in USD</p>
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
              onClick={() => setShowReceiveModal(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-3 md:px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors"
            >
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">Receive</span>
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

            <button 
              onClick={() => setShowHistoryModal(true)}
              className="flex items-center gap-2 bg-cyan-600 hover:bg-cyan-700 px-3 md:px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors"
            >
              <Clock className="h-4 w-4" />
              <span className="hidden sm:inline">History</span>
            </button>
          </div>

          {/* KYC Banner */}
          <KYCPromptBanner 
            kycStatus={kycInfo.status} 
            cumulativeVolume={kycInfo.cumulative_volume} 
            limit={kycInfo.limit} 
            urgency={kycInfo.urgency} 
          />

          {/* Tron Activation Banner */}
          {multiChainWallets?.['tron']?.address && calculateChainBalance('tron') === 0 && (
            <div className="mb-6 rounded-2xl border border-cyan-500/30 bg-gradient-to-r from-cyan-900/20 to-purple-900/20 backdrop-blur-sm p-4">
              <div className="flex items-start gap-3">
                <div className="p-3 rounded-xl bg-gradient-to-br from-cyan-500 to-purple-600 text-white shadow-lg">
                  <span className="text-2xl">⚡</span>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-purple-400">
                    Activate Your Tron Wallet
                  </h3>
                  <p className="text-sm text-gray-300 mt-1">
                    Tron wallets need at least <span className="text-cyan-400 font-bold">1 TRX</span> to activate.  
                    Without activation, you cannot send TRX or USDT.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Balance Cards */}
          {/* Multi-Chain Wallets */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-4 md:p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg md:text-xl font-bold text-white">Multi-Chain Wallets</h2>
              <span className="text-xs md:text-sm text-gray-400">{createdChains} of 7 created</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3 md:gap-4">
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
          onOpenWithdrawModal={() => setShowWithdrawModal(true)}  // ✅ ADD THIS
          onOpenReceiveModal={() => setShowReceiveModal(true)}    // ✅ ADD THIS
        />
      )}
      <FundWalletModal open={showFundModal} onOpenChange={setShowFundModal} />
      <WithdrawModal open={showWithdrawModal} onOpenChange={setShowWithdrawModal} />
      <SendForm open={showSendModal} onOpenChange={setShowSendModal} />
      <SwapModal open={showSwapModal} onOpenChange={setShowSwapModal} />
      <EarnModal open={showEarnModal} onOpenChange={setShowEarnModal} />
      <ReceiveModal 
        isOpen={showReceiveModal} 
        onClose={() => {
          setShowReceiveModal(false);
          console.log('🔍 Debug - Closing ReceiveModal');
        }}
        preselectedChain={selectedChain || undefined}
        walletAddresses={(() => {
          const addresses = Object.fromEntries(
            Object.entries(multiChainWallets).map(([chain, data]: [string, any]) => [
              chain,
              data?.address || ''
            ])
          );
          console.log('🔍 Debug - Wallet addresses being passed:', addresses);
          console.log('🔍 Debug - Preselected chain:', selectedChain);
          return addresses;
        })()}
      />
      <TransactionHistoryModal 
        isOpen={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
      />
    </div>
  );
};

export default DashboardPage;