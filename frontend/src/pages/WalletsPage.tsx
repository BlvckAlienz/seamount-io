// File: frontend/src/pages/WalletsPage.tsx
import React, { useState, useEffect } from 'react';
import { Wallet, ArrowDownToLine, ArrowUpRight, RefreshCw } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import ChainWalletCard from '@/components/wallet/ChainWalletCard';
import WalletDetailModal from '@/components/wallet/WalletDetailModal';
import { FundWalletModal } from '@/components/wallet/FundWalletModal';
import { WithdrawModal } from '@/components/wallet/WithdrawModal';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

const WalletsPage = () => {
  const [loading, setLoading] = useState(true);
  const [portfolioData, setPortfolioData] = useState<any>(null);
  const [multiChainWallets, setMultiChainWallets] = useState<any>({});
  const [selectedChain, setSelectedChain] = useState<string | null>(null);
  const [showWalletModal, setShowWalletModal] = useState(false);
  const [showFundModal, setShowFundModal] = useState(false);
  const [showWithdrawModal, setShowWithdrawModal] = useState(false);

  const AUTO_CREATED_CHAINS = [
    { id: 'algorand', name: 'Algorand', symbol: 'ALGO' },
    { id: 'bitcoin', name: 'Bitcoin', symbol: 'BTC' },
    { id: 'ethereum', name: 'Ethereum', symbol: 'ETH' },
    { id: 'polygon', name: 'Polygon', symbol: 'MATIC' },
    { id: 'tron', name: 'TRON', symbol: 'TRX' },
  ];

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [balances, wallets] = await Promise.all([
        apiClient.get('/api/v1/wallet/balances'),
        apiClient.get('/api/v1/wallet-creation/status')
      ]);

      if (balances.data.success) {
        setPortfolioData({
          total_usd: balances.data.total_usd,
          assets: balances.data.assets,
        });
      }

      if (wallets.data.success) {
        const walletsMap: Record<string, any> = {};
        Object.entries(wallets.data.chains || {}).forEach(([chain, data]: [string, any]) => {
          if (data.address) {
            walletsMap[chain] = { address: data.address };
          }
        });
        setMultiChainWallets(walletsMap);
      }
    } catch (error) {
      console.error('Failed to fetch wallet data:', error);
      toast.error('Failed to load wallet data');
    } finally {
      setLoading(false);
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

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />

      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
              <Wallet className="h-8 w-8 text-blue-400" />
              Multi-Chain Wallets
            </h1>
            <p className="text-gray-400">Manage your 5 blockchain wallets</p>
          </div>

          {/* Quick Actions */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={() => setShowFundModal(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg text-white font-semibold transition-colors"
            >
              <ArrowDownToLine className="h-5 w-5" />
              Fund Wallet
            </button>
            <button
              onClick={() => setShowWithdrawModal(true)}
              className="flex items-center gap-2 bg-red-600 hover:bg-red-700 px-6 py-3 rounded-lg text-white font-semibold transition-colors"
            >
              <ArrowUpRight className="h-5 w-5" />
              Withdraw
            </button>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 px-6 py-3 rounded-lg text-white font-semibold transition-colors"
            >
              <RefreshCw className="h-5 w-5" />
              Refresh
            </button>
          </div>

          {/* Total Balance Card */}
          <div className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-2xl p-6 mb-8">
            <div className="text-sm text-gray-400 mb-2">Total Balance Across All Chains</div>
            <div className="text-5xl font-bold text-white mb-4">
              ${portfolioData?.total_usd?.toFixed(2) || '0.00'}
            </div>
            <div className="text-sm text-green-400">
              {Object.keys(multiChainWallets).length} / 5 wallets active
            </div>
          </div>

          {/* Wallet Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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

      {/* Modals */}
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
    </div>
  );
};

export default WalletsPage;