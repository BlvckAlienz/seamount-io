// File: frontend/src/components/modals/PublishOfferModal.tsx
import React, { useState, useEffect } from 'react';
import { X, Plus, TrendingUp } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface PublishOfferModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tokenizedAssets?: any[];
}

export const PublishOfferModal: React.FC<PublishOfferModalProps> = ({
  open,
  onOpenChange,
  tokenizedAssets = [],
}) => {
  const [loading, setLoading] = useState(false);
  
  // Form state
  const [selectedAsset, setSelectedAsset] = useState('');
  const [quantity, setQuantity] = useState('');
  const [pricePerUnit, setPricePerUnit] = useState('');
  const [paymentNetwork, setPaymentNetwork] = useState('usdc_circle');
  const [expiresInHours, setExpiresInHours] = useState('168'); // 7 days default

  // Calculated values
  const [totalValue, setTotalValue] = useState(0);
  const [selectedAssetData, setSelectedAssetData] = useState<any>(null);

  useEffect(() => {
    if (selectedAsset && tokenizedAssets.length > 0) {
      const asset = tokenizedAssets.find(a => a.id === selectedAsset);
      setSelectedAssetData(asset);
    }
  }, [selectedAsset, tokenizedAssets]);

  useEffect(() => {
    if (quantity && pricePerUnit) {
      setTotalValue(parseFloat(quantity) * parseFloat(pricePerUnit));
    } else {
      setTotalValue(0);
    }
  }, [quantity, pricePerUnit]);

  const handlePublish = async () => {
    if (!selectedAsset || !quantity || !pricePerUnit) {
      toast.error('Please fill all required fields');
      return;
    }

    if (selectedAssetData && parseInt(quantity) > selectedAssetData.on_chain_balance) {
      toast.error(`Insufficient balance. You have ${selectedAssetData.on_chain_balance} available.`);
      return;
    }

    try {
      setLoading(true);
      
      const response = await apiClient.post('/api/v1/tokenization/publish-offer', {
        asset_id: selectedAsset,
        quantity: parseInt(quantity),
        price_per_unit: parseFloat(pricePerUnit),
        payment_network: paymentNetwork,
        expires_in_hours: parseInt(expiresInHours),
      });

      if (response.data.success) {
        toast.success('Offer published successfully!');
        onOpenChange(false);
        // Reset form
        setSelectedAsset('');
        setQuantity('');
        setPricePerUnit('');
      } else {
        toast.error(response.data.message || 'Failed to publish offer');
      }
    } catch (error: any) {
      console.error('Offer publication failed:', error);
      toast.error(error.response?.data?.detail || 'Failed to publish offer');
    } finally {
      setLoading(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-white">Publish Offer</h2>
            <p className="text-gray-400 text-sm mt-1">List your tokenized asset for sale</p>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Asset Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Select Asset <span className="text-red-400">*</span>
            </label>
            <select
              value={selectedAsset}
              onChange={(e) => setSelectedAsset(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
            >
              <option value="">Choose asset...</option>
              {tokenizedAssets.map(asset => (
                <option key={asset.id} value={asset.id}>
                  {asset.symbol} - {asset.name} (Available: {asset.on_chain_balance})
                </option>
              ))}
            </select>
            {selectedAssetData && (
              <div className="mt-2 text-xs text-gray-400">
                Current Price: ${selectedAssetData.current_price_usd} | Available: {selectedAssetData.on_chain_balance} units
              </div>
            )}
          </div>

          {/* Quantity */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Quantity <span className="text-red-400">*</span>
            </label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="Number of units to sell"
              min="1"
              max={selectedAssetData?.on_chain_balance || undefined}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          {/* Price Per Unit */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Price Per Unit (USD) <span className="text-red-400">*</span>
            </label>
            <input
              type="number"
              value={pricePerUnit}
              onChange={(e) => setPricePerUnit(e.target.value)}
              placeholder="0.00"
              step="0.01"
              min="0"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
            />
            {selectedAssetData && pricePerUnit && (
              <div className="mt-2 text-xs text-gray-400">
                Market Price: ${selectedAssetData.current_price_usd} | Your Price: ${pricePerUnit} 
                {parseFloat(pricePerUnit) > selectedAssetData.current_price_usd && (
                  <span className="text-yellow-400"> (+{((parseFloat(pricePerUnit) / selectedAssetData.current_price_usd - 1) * 100).toFixed(2)}%)</span>
                )}
              </div>
            )}
          </div>

          {/* Payment Network */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Payment Network
            </label>
            <select
              value={paymentNetwork}
              onChange={(e) => setPaymentNetwork(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
            >
              <option value="usdc_circle">USDC (Circle)</option>
              <option value="usdt_tron">USDT (Tron)</option>
              <option value="nibss_nip">NIBSS NIP (NGN)</option>
            </select>
          </div>

          {/* Expiry */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Expires In (Hours)
            </label>
            <select
              value={expiresInHours}
              onChange={(e) => setExpiresInHours(e.target.value)}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition-colors"
            >
              <option value="24">24 hours (1 day)</option>
              <option value="72">72 hours (3 days)</option>
              <option value="168">168 hours (7 days)</option>
              <option value="336">336 hours (14 days)</option>
              <option value="720">720 hours (30 days)</option>
            </select>
          </div>

          {/* Total Value */}
          {totalValue > 0 && (
            <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
              <div className="flex items-center gap-2 text-blue-400 mb-2">
                <TrendingUp className="h-5 w-5" />
                <span className="font-semibold">Order Summary</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400 text-sm">Total Value</span>
                  <span className="text-white font-bold">${totalValue.toFixed(2)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400 text-sm">Platform Fee (0.5%)</span>
                  <span className="text-gray-300">${(totalValue * 0.005).toFixed(2)}</span>
                </div>
                <div className="flex justify-between pt-2 border-t border-gray-700">
                  <span className="text-gray-400 text-sm">You'll Receive</span>
                  <span className="text-green-400 font-bold">${(totalValue * 0.995).toFixed(2)}</span>
                </div>
              </div>
            </div>
          )}

          {/* Publish Button */}
          <button
            onClick={handlePublish}
            disabled={loading || !selectedAsset || !quantity || !pricePerUnit}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>Processing...</>
            ) : (
              <>
                <Plus className="h-5 w-5" />
                Publish Offer
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PublishOfferModal;