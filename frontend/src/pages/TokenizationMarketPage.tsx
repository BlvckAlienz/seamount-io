// File: frontend/src/pages/TokenizationMarketPage.tsx
import React, { useState, useEffect } from 'react';
import { TrendingUp, Plus, RefreshCw, ShoppingCart } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import ConvertAssetModal from '@/components/modals/ConvertAssetModal';
import PublishOfferModal from '@/components/modals/PublishOfferModal';
import MarketOffersModal from '@/components/modals/MarketOffersModal';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

const TokenizationMarketPage = () => {
  const [loading, setLoading] = useState(true);
  const [tokenizedAssets, setTokenizedAssets] = useState<any[]>([]);
  const [offers, setOffers] = useState<any[]>([]);
  const [showConvertModal, setShowConvertModal] = useState(false);
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [showMarketModal, setShowMarketModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [assetsRes, offersRes] = await Promise.all([
        apiClient.get('/api/v1/tokenization/my-assets'),
        apiClient.get('/api/v1/tokenization/offers', { params: { status: 'published' } })
      ]);

      if (assetsRes.data.success) {
        setTokenizedAssets(assetsRes.data.assets || []);
      }

      if (offersRes.data.success) {
        setOffers(offersRes.data.offers || []);
      }
    } catch (error) {
      console.error('Failed to fetch tokenization data:', error);
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-green-600"></div>
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
              <TrendingUp className="h-8 w-8 text-green-400" />
              Tokenization Market
            </h1>
            <p className="text-gray-400">Convert traditional assets & trade tokenized securities</p>
          </div>

          {/* Quick Actions */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={() => setShowConvertModal(true)}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 px-6 py-3 rounded-lg text-white font-semibold transition-colors"
            >
              <RefreshCw className="h-5 w-5" />
              Convert Asset
            </button>
            <button
              onClick={() => setShowPublishModal(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg text-white font-semibold transition-colors"
            >
              <Plus className="h-5 w-5" />
              Publish Offer
            </button>
            <button
              onClick={() => setShowMarketModal(true)}
              className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-6 py-3 rounded-lg text-white font-semibold transition-colors"
            >
              <ShoppingCart className="h-5 w-5" />
              Browse Market
            </button>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">My Tokenized Assets</div>
              <div className="text-4xl font-bold text-white mb-2">{tokenizedAssets.length}</div>
              <div className="text-sm text-green-400">Active on-chain</div>
            </div>

            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">Market Offers</div>
              <div className="text-4xl font-bold text-white mb-2">{offers.length}</div>
              <div className="text-sm text-blue-400">Available to buy</div>
            </div>

            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">Total Market Value</div>
              <div className="text-4xl font-bold text-white mb-2">
                ${offers.reduce((sum, o) => sum + o.total_value, 0).toFixed(2)}
              </div>
              <div className="text-sm text-purple-400">USD</div>
            </div>
          </div>

          {/* My Assets Table */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6 mb-8">
            <h2 className="text-xl font-bold text-white mb-4">My Tokenized Assets</h2>
            
            {tokenizedAssets.length === 0 ? (
              <div className="text-center py-12">
                <RefreshCw className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-400 mb-2">No Assets Yet</h3>
                <p className="text-gray-500 mb-4">Convert your first traditional asset to get started</p>
                <button
                  onClick={() => setShowConvertModal(true)}
                  className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg transition-colors"
                >
                  Convert Asset
                </button>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-700">
                      <th className="text-left text-xs font-medium text-gray-400 uppercase py-3 px-4">Asset</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase py-3 px-4">Custodian</th>
                      <th className="text-right text-xs font-medium text-gray-400 uppercase py-3 px-4">Total Supply</th>
                      <th className="text-right text-xs font-medium text-gray-400 uppercase py-3 px-4">On Chain</th>
                      <th className="text-right text-xs font-medium text-gray-400 uppercase py-3 px-4">Price</th>
                      <th className="text-right text-xs font-medium text-gray-400 uppercase py-3 px-4">Value</th>
                      <th className="text-right text-xs font-medium text-gray-400 uppercase py-3 px-4">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tokenizedAssets.map((asset) => (
                      <tr key={asset.id} className="border-b border-gray-700/50 hover:bg-gray-800/30 transition-colors">
                        <td className="py-4 px-4">
                          <div>
                            <div className="text-white font-medium">{asset.symbol}</div>
                            <div className="text-xs text-gray-400">{asset.name}</div>
                          </div>
                        </td>
                        <td className="py-4 px-4">
                          <span className="text-gray-300">{asset.custodian_id?.split('-').pop()?.toUpperCase() || 'Unknown'}</span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <span className="text-white font-medium">{asset.total_supply}</span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <span className="text-green-400 font-medium">{asset.on_chain_balance}</span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <span className="text-white">${asset.current_price_usd?.toFixed(2)}</span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <span className="text-white font-bold">
                            ${(asset.on_chain_balance * asset.current_price_usd).toFixed(2)}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-right">
                          <button
                            onClick={() => setShowPublishModal(true)}
                            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white text-sm font-medium transition-colors"
                          >
                            Sell
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      <ConvertAssetModal open={showConvertModal} onOpenChange={setShowConvertModal} />
      <PublishOfferModal 
        open={showPublishModal} 
        onOpenChange={setShowPublishModal}
        tokenizedAssets={tokenizedAssets}
      />
      <MarketOffersModal open={showMarketModal} onOpenChange={setShowMarketModal} />
    </div>
  );
};

export default TokenizationMarketPage;