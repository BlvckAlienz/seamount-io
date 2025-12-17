// File: frontend/src/pages/TradingPage.tsx
// 📱 MOBILE-FIRST RESPONSIVE DESIGN - Platform Standard Format
// ✅ FIXED: Self-trade prevention with visual distinction

import React, { useState, useEffect } from 'react';
import { X, TrendingUp, ShoppingCart, Clock, Filter, Search, RefreshCw } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface AssetOffer {
  id: string;
  seller_id: string;
  asset_id: string;
  quantity: number;
  price_per_unit: number;
  total_value: number;
  payment_network: string;
  status: string;
  expires_at: string;
  published_at: string;
  tokenized_assets?: {
    symbol: string;
    name: string;
  };
}

const TradingPage = () => {
  const [loading, setLoading] = useState(true);
  const [offers, setOffers] = useState<AssetOffer[]>([]);
  const [filteredOffers, setFilteredOffers] = useState<AssetOffer[]>([]);
  const [selectedOffer, setSelectedOffer] = useState<AssetOffer | null>(null);
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [buyLoading, setBuyLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterNetwork, setFilterNetwork] = useState<string>('all');
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  useEffect(() => {
    // Get current user ID from auth
    const fetchUserAndOffers = async () => {
      try {
        const response = await apiClient.get('/api/v1/auth/me');
        console.log('🔍 DEBUG: Auth response:', response.data); // DEBUG
        
        // Try multiple possible user ID locations
        const userId = response.data?.id || response.data?.user_id || response.data?.user?.id;
        
        if (userId) {
          console.log('✅ DEBUG: Current user ID:', userId); // DEBUG
          setCurrentUserId(userId);
        } else {
          console.error('❌ DEBUG: No user ID found in response:', response.data);
        }
      } catch (error) {
        console.error('Failed to fetch user:', error);
      }
      fetchOffers();
    };
    
    fetchUserAndOffers();
  }, []);

  useEffect(() => {
    filterOffers();
  }, [offers, searchTerm, filterNetwork]);

  const fetchOffers = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/tokenization/offers', {
        params: { status: 'published' }
      });
      
      if (response.data.success) {
        setOffers(response.data.offers || []);
      }
    } catch (error) {
      console.error('Failed to fetch offers:', error);
      toast.error('Failed to load market offers');
    } finally {
      setLoading(false);
    }
  };

  const filterOffers = () => {
    let filtered = [...offers];

    // Search filter
    if (searchTerm) {
      filtered = filtered.filter(offer =>
        offer.tokenized_assets?.symbol?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        offer.tokenized_assets?.name?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Network filter
    if (filterNetwork !== 'all') {
      filtered = filtered.filter(offer => offer.payment_network === filterNetwork);
    }

    setFilteredOffers(filtered);
  };

  const handleBuy = async () => {
    if (!selectedOffer) return;

    // 🚨 Check if trying to buy own asset
    if (selectedOffer.seller_id === currentUserId) {
      toast.error('This is your own listing. You cannot purchase your own assets.', {
        duration: 4000,
        icon: '🏷️'
      });
      setShowBuyModal(false);
      setSelectedOffer(null);
      return;
    }

    try {
      setBuyLoading(true);
      const response = await apiClient.post('/api/v1/tokenization/execute-trade', {
        offer_id: selectedOffer.id,
        payment_network: selectedOffer.payment_network,
      });

      if (response.data.success) {
        toast.success('Trade executed successfully! DVP settlement in progress...');
        setShowBuyModal(false);
        setSelectedOffer(null);
        fetchOffers(); // Refresh offers
      } else {
        toast.error(response.data.message || 'Trade failed');
      }
    } catch (error: any) {
      console.error('Trade execution failed:', error);
      
      // Better error message handling
      const errorMsg = error.response?.data?.detail || 'Failed to execute trade';
      
      // Check for self-trading error from backend
      if (errorMsg.includes('your own listing') || errorMsg.includes('already selling')) {
        toast.error('This is your own listing. You cannot purchase your own assets.', {
          duration: 4000,
          icon: '🏷️'
        });
      } else {
        toast.error(errorMsg);
      }
    } finally {
      setBuyLoading(false);
    }
  };

  // Calculate market stats
  const totalOffers = offers.length;
  const totalValue = offers.reduce((sum, o) => sum + o.total_value, 0);
  const uniqueAssets = new Set(offers.map(o => o.tokenized_assets?.symbol)).size;
  const availableNetworks = [...new Set(offers.map(o => o.payment_network))];

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

      <div className="flex-1 overflow-y-auto p-4 md:p-6 pt-20 lg:pt-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-4 md:mb-6">
            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-2 md:gap-3 mb-2">
              <TrendingUp className="h-6 w-6 md:h-8 md:w-8 text-blue-400" />
              <span>Secondary Market</span>
            </h1>
            <p className="text-sm md:text-base text-gray-400">
              Buy tokenized securities with instant DVP settlement
            </p>
          </div>

          {/* Market Stats - Responsive Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4 md:p-6">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Active Offers</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">{totalOffers}</div>
              <div className="text-xs md:text-sm text-blue-400">Available now</div>
            </div>

            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4 md:p-6">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Total Market Value</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">
                ${totalValue.toFixed(2)}
              </div>
              <div className="text-xs md:text-sm text-green-400">USD</div>
            </div>

            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-4 md:p-6">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Unique Assets</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">{uniqueAssets}</div>
              <div className="text-xs md:text-sm text-purple-400">Securities</div>
            </div>

            <div className="bg-gradient-to-br from-orange-900/20 to-red-900/20 border border-orange-500/30 rounded-xl p-4 md:p-6">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Avg. Settlement</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">4m</div>
              <div className="text-xs md:text-sm text-orange-400">DVP Execution</div>
            </div>
          </div>

          {/* Search & Filter Bar */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-xl p-4 mb-6">
            <div className="flex flex-col sm:flex-row gap-3">
              {/* Search */}
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search by asset symbol or name..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 md:py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors"
                />
              </div>

              {/* Filter */}
              <div className="flex items-center gap-2">
                <Filter className="h-5 w-5 text-gray-400" />
                <select
                  value={filterNetwork}
                  onChange={(e) => setFilterNetwork(e.target.value)}
                  className="px-4 py-2 md:py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
                >
                  <option value="all">All Payment Networks</option>
                  {availableNetworks.map(network => (
                    <option key={network} value={network}>
                      {network === 'usdc_circle' ? 'USDC (Circle)' : network}
                    </option>
                  ))}
                </select>
              </div>

              {/* Refresh */}
              <button
                onClick={fetchOffers}
                className="flex items-center justify-center gap-2 px-4 py-2 md:py-3 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-white transition-colors"
              >
                <RefreshCw className="h-4 w-4" />
                <span className="hidden sm:inline">Refresh</span>
              </button>
            </div>
          </div>

          {/* Market Offers Section */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-4 md:p-6">
            <h2 className="text-lg md:text-xl font-bold text-white mb-4">Available Offers</h2>

            {filteredOffers.length === 0 ? (
              <div className="text-center py-8 md:py-12">
                <TrendingUp className="h-12 w-12 md:h-16 md:w-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg md:text-xl font-semibold text-gray-400 mb-2">
                  {searchTerm || filterNetwork !== 'all' ? 'No Matching Offers' : 'No Active Offers'}
                </h3>
                <p className="text-sm md:text-base text-gray-500">
                  {searchTerm || filterNetwork !== 'all'
                    ? 'Try adjusting your search or filter criteria'
                    : 'Check back later for new trading opportunities'}
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredOffers.map((offer) => {
                  const isOwnListing = offer.seller_id === currentUserId;
                  
                  // 🔍 DEBUG: Log comparison for first offer
                  if (filteredOffers.indexOf(offer) === 0) {
                    console.log('🔍 DEBUG: First offer comparison:', {
                      offerSellerId: offer.seller_id,
                      currentUserId: currentUserId,
                      isOwnListing: isOwnListing,
                      typesMatch: typeof offer.seller_id === typeof currentUserId
                    });
                  }
                  
                  return (
                    <div
                      key={offer.id}
                      className={`bg-gradient-to-br from-gray-800/50 to-gray-900/50 border rounded-xl p-4 transition-all cursor-pointer relative overflow-hidden ${
                        isOwnListing 
                          ? 'border-purple-500/50 hover:border-purple-400/70' 
                          : 'border-gray-700/50 hover:border-blue-500/50'
                      }`}
                      onClick={() => {
                        setSelectedOffer(offer);
                        setShowBuyModal(true);
                      }}
                    >
                      {/* 🎀 Ribbon for own listings */}
                      {isOwnListing && (
                        <div className="absolute top-0 right-0">
                          <div className="bg-gradient-to-br from-purple-600 to-pink-600 text-white text-xs font-bold px-3 py-1 shadow-lg transform rotate-0 translate-x-0 translate-y-0">
                            YOUR LISTING
                          </div>
                        </div>
                      )}

                      {/* Asset Info */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex-1">
                          <h3 className="text-lg font-bold text-white">
                            {offer.tokenized_assets?.symbol || 'Unknown'}
                          </h3>
                          <p className="text-xs text-gray-400">
                            {offer.tokenized_assets?.name || 'Asset'}
                          </p>
                        </div>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          isOwnListing 
                            ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' 
                            : 'bg-green-500/20 text-green-400'
                        }`}>
                          {isOwnListing ? 'Your Offer' : 'Live'}
                        </span>
                      </div>

                      {/* Quantity & Price */}
                      <div className="space-y-2 mb-3">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-400">Quantity</span>
                          <span className="text-sm font-semibold text-white">{offer.quantity}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-400">Price/Unit</span>
                          <span className="text-sm font-semibold text-white">${offer.price_per_unit.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between pt-2 border-t border-gray-700">
                          <span className="text-sm text-gray-400">Total Value</span>
                          <span className="text-base font-bold text-green-400">${offer.total_value.toFixed(2)}</span>
                        </div>
                      </div>

                      {/* Payment Network */}
                      <div className="mb-3">
                        <span className="text-xs text-gray-400">Payment: </span>
                        <span className="text-xs font-medium text-blue-400">
                          {offer.payment_network === 'usdc_circle' ? 'USDC (Circle)' : offer.payment_network}
                        </span>
                      </div>

                      {/* Expiry */}
                      <div className="flex items-center gap-1 text-xs text-gray-500 mb-3">
                        <Clock className="h-3 w-3" />
                        Expires: {new Date(offer.expires_at).toLocaleDateString()}
                      </div>

                      {/* Buy Button - Different for own listings */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (isOwnListing) {
                            toast.info('This is your listing. Use "My Assets" to manage it.', {
                              icon: '🏷️'
                            });
                          } else {
                            setSelectedOffer(offer);
                            setShowBuyModal(true);
                          }
                        }}
                        className={`w-full py-2 font-semibold rounded-lg transition-all flex items-center justify-center gap-2 ${
                          isOwnListing
                            ? 'bg-gradient-to-r from-purple-600/50 to-pink-600/50 hover:from-purple-600/70 hover:to-pink-600/70 text-purple-200 border border-purple-500/30'
                            : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 text-white shadow-lg hover:shadow-xl'
                        }`}
                      >
                        {isOwnListing ? (
                          <>
                            <Clock className="h-4 w-4" />
                            Your Listing
                          </>
                        ) : (
                          <>
                            <ShoppingCart className="h-4 w-4" />
                            Buy Now
                          </>
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Buy Confirmation Modal */}
      {showBuyModal && selectedOffer && (
        <div 
          className="fixed inset-0 bg-black/80 backdrop-blur-sm z-[70] flex items-center justify-center p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowBuyModal(false);
              setSelectedOffer(null);
            }
          }}
        >
          <div 
            className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-2xl max-w-lg w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-white">Confirm Purchase</h3>
                <button
                  onClick={() => {
                    setShowBuyModal(false);
                    setSelectedOffer(null);
                  }}
                  className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  <X className="h-5 w-5 text-gray-400" />
                </button>
              </div>
              
              <div className="space-y-4 mb-6">
                <div className="bg-gray-800/50 rounded-xl p-4">
                  <div className="text-sm text-gray-400 mb-1">Asset</div>
                  <div className="text-lg font-bold text-white">
                    {selectedOffer.tokenized_assets?.symbol} - {selectedOffer.tokenized_assets?.name}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-gray-800/50 rounded-xl p-4">
                    <div className="text-sm text-gray-400 mb-1">Quantity</div>
                    <div className="text-lg font-bold text-white">{selectedOffer.quantity}</div>
                  </div>
                  <div className="bg-gray-800/50 rounded-xl p-4">
                    <div className="text-sm text-gray-400 mb-1">Price/Unit</div>
                    <div className="text-lg font-bold text-white">${selectedOffer.price_per_unit.toFixed(2)}</div>
                  </div>
                </div>

                <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
                  <div className="text-sm text-gray-400 mb-1">Total Cost</div>
                  <div className="text-2xl font-bold text-white">${selectedOffer.total_value.toFixed(2)}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    Payment via {selectedOffer.payment_network === 'usdc_circle' ? 'USDC (Circle)' : selectedOffer.payment_network}
                  </div>
                </div>

                {/* DVP Settlement Info */}
                <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="h-4 w-4 text-green-400" />
                    <div className="text-sm font-semibold text-green-400">DVP Settlement</div>
                  </div>
                  <div className="text-xs text-gray-400">
                    Delivery vs Payment will execute atomically. Estimated settlement: ~4 minutes
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setShowBuyModal(false);
                    setSelectedOffer(null);
                  }}
                  className="flex-1 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBuy}
                  disabled={buyLoading}
                  className="flex-1 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 disabled:from-gray-700 disabled:to-gray-700 text-white font-semibold rounded-lg transition-all shadow-lg hover:shadow-xl disabled:cursor-not-allowed"
                >
                  {buyLoading ? (
                    <div className="flex items-center justify-center gap-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                      Executing DVP...
                    </div>
                  ) : (
                    'Confirm Purchase'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TradingPage;