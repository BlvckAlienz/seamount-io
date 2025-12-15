// File: frontend/src/components/modals/MarketOffersModal.tsx
import React, { useState, useEffect } from 'react';
import { X, TrendingUp, ShoppingCart, Clock, Filter } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface MarketOffersModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

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

export const MarketOffersModal: React.FC<MarketOffersModalProps> = ({
  open,
  onOpenChange,
}) => {
  const [loading, setLoading] = useState(true);
  const [offers, setOffers] = useState<AssetOffer[]>([]);
  const [selectedOffer, setSelectedOffer] = useState<AssetOffer | null>(null);
  const [showBuyModal, setShowBuyModal] = useState(false);
  const [buyLoading, setBuyLoading] = useState(false);

  useEffect(() => {
    if (open) {
      fetchOffers();
    }
  }, [open]);

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

  const handleBuy = async () => {
    if (!selectedOffer) return;

    try {
      setBuyLoading(true);
      const response = await apiClient.post('/api/v1/tokenization/execute-trade', {
        offer_id: selectedOffer.id,
        payment_network: selectedOffer.payment_network,
      });

      if (response.data.success) {
        toast.success('Trade executed successfully!');
        setShowBuyModal(false);
        setSelectedOffer(null);
        fetchOffers();
      } else {
        toast.error(response.data.message || 'Trade failed');
      }
    } catch (error: any) {
      console.error('Trade execution failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to execute trade');
    } finally {
      setBuyLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-2xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <TrendingUp className="h-6 w-6 text-blue-400" />
              Secondary Market
            </h2>
            <p className="text-gray-400 text-sm mt-1">Available tokenized asset offers</p>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-500"></div>
            </div>
          ) : offers.length === 0 ? (
            <div className="text-center py-12">
              <TrendingUp className="h-16 w-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-400 mb-2">No Active Offers</h3>
              <p className="text-gray-500">No tokenized assets available for purchase</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Market Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4">
                  <div className="text-2xl font-bold text-white mb-1">{offers.length}</div>
                  <div className="text-sm text-gray-400">Active Offers</div>
                </div>
                <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4">
                  <div className="text-2xl font-bold text-white mb-1">
                    ${offers.reduce((sum, o) => sum + o.total_value, 0).toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-400">Total Value</div>
                </div>
                <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-4">
                  <div className="text-2xl font-bold text-white mb-1">
                    {new Set(offers.map(o => o.tokenized_assets?.symbol)).size}
                  </div>
                  <div className="text-sm text-gray-400">Unique Assets</div>
                </div>
              </div>

              {/* Offers Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {offers.map((offer) => (
                  <div
                    key={offer.id}
                    className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-xl p-4 hover:border-blue-500/50 transition-all cursor-pointer"
                    onClick={() => {
                      setSelectedOffer(offer);
                      setShowBuyModal(true);
                    }}
                  >
                    {/* Asset Info */}
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-lg font-bold text-white">
                          {offer.tokenized_assets?.symbol || 'Unknown'}
                        </h3>
                        <p className="text-xs text-gray-400">
                          {offer.tokenized_assets?.name || 'Asset'}
                        </p>
                      </div>
                      <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs font-medium">
                        Live
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
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Clock className="h-3 w-3" />
                      Expires: {new Date(offer.expires_at).toLocaleDateString()}
                    </div>

                    {/* Buy Button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedOffer(offer);
                        setShowBuyModal(true);
                      }}
                      className="w-full mt-3 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                      <ShoppingCart className="h-4 w-4" />
                      Buy Now
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
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
              <h3 className="text-xl font-bold text-white mb-4">Confirm Purchase</h3>
              
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
                  className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 text-white font-semibold rounded-lg transition-colors"
                >
                  {buyLoading ? 'Processing...' : 'Confirm Purchase'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MarketOffersModal;