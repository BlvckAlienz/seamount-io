// File: frontend/src/pages/TokenizationMarketPage.tsx
// 📱 MOBILE-FIRST RESPONSIVE DESIGN

import React, { useState, useEffect } from 'react';
import { TrendingUp, Plus, RefreshCw, Coins } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import ConvertAssetModal from '@/components/modals/ConvertAssetModal';
import PublishOfferModal from '@/components/modals/PublishOfferModal';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import { formatCurrencyUSD, formatCurrencyWithDecimals } from '@/utils/formatters';

const TokenizationMarketPage = () => {
  const [loading, setLoading] = useState(true);
  const [tokenizedAssets, setTokenizedAssets] = useState<any[]>([]);
  const [offers, setOffers] = useState<any[]>([]);
  const [showConvertModal, setShowConvertModal] = useState(false);
  const [showPublishModal, setShowPublishModal] = useState(false);

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

      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-4 md:mb-6">
            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-2 md:gap-3 mb-2">
              <TrendingUp className="h-6 w-6 md:h-8 md:w-8 text-green-400" />
              <span>Tokenization Market</span>
            </h1>
            <p className="text-sm md:text-base text-gray-400">Tokenize traditional assets. Sell to retail investors</p>
          </div>

          {/* Quick Actions - Responsive */}
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <button
              onClick={() => setShowConvertModal(true)}
              className="flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 px-4 md:px-6 py-3 rounded-lg text-white text-sm md:text-base font-semibold transition-colors flex-1 sm:flex-initial"
            >
              <RefreshCw className="h-4 w-4 md:h-5 md:w-5" />
              Convert Asset
            </button>
            <button
              onClick={() => setShowPublishModal(true)}
              className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 px-4 md:px-6 py-3 rounded-lg text-white text-sm md:text-base font-semibold transition-colors flex-1 sm:flex-initial"
            >
              <Plus className="h-4 w-4 md:h-5 md:w-5" />
              Publish Offer
            </button>
          </div>

          {/* Stats Cards - Responsive Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6 md:mb-8">
            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4 md:p-6">
              <div className="text-xs md:text-sm text-gray-400 mb-2">My Tokenized Assets</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">{tokenizedAssets.length}</div>
              <div className="text-xs md:text-sm text-green-400">Active on-chain</div>
            </div>

            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4 md:p-6">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Market Offers</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">{offers.length}</div>
              <div className="text-xs md:text-sm text-blue-400">Available to buy</div>
            </div>

            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-4 md:p-6 sm:col-span-2 lg:col-span-1">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Total Market Value</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">
                {formatCurrencyUSD(offers.reduce((sum, o) => sum + o.total_value, 0))}
              </div>
              <div className="text-xs md:text-sm text-purple-400">USD</div>
            </div>
          </div>

          {/* My Assets Section */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-4 md:p-6 mb-8">
            <h2 className="text-lg md:text-xl font-bold text-white mb-4">My Tokenized Assets</h2>
            
            {tokenizedAssets.length === 0 ? (
              <div className="text-center py-8 md:py-12">
                <Coins className="h-12 w-12 md:h-16 md:w-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg md:text-xl font-semibold text-gray-400 mb-2">No Assets Yet</h3>
                <p className="text-sm md:text-base text-gray-500 mb-4">Convert your first traditional asset to get started</p>
                <button
                  onClick={() => setShowConvertModal(true)}
                  className="px-4 md:px-6 py-2 md:py-3 bg-green-600 hover:bg-green-700 text-white text-sm md:text-base font-semibold rounded-lg transition-colors"
                >
                  Convert Asset
                </button>
              </div>
            ) : (
              <>
                {/* Desktop Table View */}
                <div className="hidden lg:block overflow-x-auto">
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
                            <span className="text-white">{formatCurrencyWithDecimals(asset.current_price_usd || 0)}</span>
                          </td>
                          <td className="py-4 px-4 text-right">
                            <span className="text-white font-bold">
                              {formatCurrencyUSD(asset.on_chain_balance * asset.current_price_usd)}
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

                {/* Mobile Card View */}
                <div className="lg:hidden space-y-4">
                  {tokenizedAssets.map((asset) => (
                    <div key={asset.id} className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="text-white font-bold text-lg">{asset.symbol}</h3>
                          <p className="text-gray-400 text-sm">{asset.name}</p>
                        </div>
                        <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs font-medium">
                          On-Chain
                        </span>
                      </div>
                      
                      <div className="space-y-2 mb-4">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-400">Custodian</span>
                          <span className="text-white font-medium">
                            {asset.custodian_id?.split('-').pop()?.toUpperCase() || 'Unknown'}
                          </span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-400">Total Supply</span>
                          <span className="text-white font-medium">{asset.total_supply}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-400">On Chain</span>
                          <span className="text-green-400 font-medium">{asset.on_chain_balance}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-400">Price/Unit</span>
                          <span className="text-white font-medium">{formatCurrencyWithDecimals(asset.current_price_usd || 0)}</span>
                        </div>
                        <div className="flex justify-between text-sm pt-2 border-t border-gray-700">
                          <span className="text-gray-400">Total Value</span>
                          <span className="text-white font-bold">
                            {formatCurrencyUSD(asset.on_chain_balance * asset.current_price_usd)}
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => setShowPublishModal(true)}
                        className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                      >
                        Sell Asset
                      </button>
                    </div>
                  ))}
                </div>
              </>
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
    </div>
  );
};

export default TokenizationMarketPage;