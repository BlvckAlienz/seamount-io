import React, { useState, useEffect } from 'react';
import { Briefcase, TrendingUp } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import { apiClient } from '@/config/api';
import { formatCurrencyUSD } from '@/utils/formatters';

const MyAssetsPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [ownedAssets, setOwnedAssets] = useState<any[]>([]);
  
  useEffect(() => {
    fetchOwnedAssets();
  }, []);
  
  const fetchOwnedAssets = async () => {
    try {
      const response = await apiClient.get('/api/v1/tokenization/my-purchases');
      if (response.data.success) {
        setOwnedAssets(response.data.assets);
      }
    } catch (error) {
      console.error('Failed to fetch owned assets:', error);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="flex h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      <Sidebar />
      
      <div className="flex-1 overflow-y-auto p-6 pt-20 lg:pt-6">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-white mb-6 flex items-center gap-3">
            <Briefcase className="h-8 w-8 text-green-400" />
            My Purchased Assets
          </h1>
          
          {loading ? (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-green-600"></div>
            </div>
          ) : ownedAssets.length === 0 ? (
            <div className="text-center py-12">
              <Briefcase className="h-16 w-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-400 mb-2">No Assets Yet</h3>
              <p className="text-gray-500">Browse the market to purchase your first tokenized asset</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {ownedAssets.map((asset) => (
                <div key={asset.id} className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
                  {asset.image_url && (
                    <img src={asset.image_url} alt={asset.symbol} className="w-full h-48 object-cover rounded-lg mb-4" />
                  )}
                  <h3 className="text-xl font-bold text-white mb-2">{asset.symbol}</h3>
                  <p className="text-gray-400 text-sm mb-4">{asset.name}</p>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Quantity Owned</span>
                      <span className="text-white font-bold">{asset.quantity}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Purchase Price</span>
                      <span className="text-white">{formatCurrencyUSD(asset.purchase_price)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400 text-sm">Current Value</span>
                      <span className="text-green-400 font-bold">{formatCurrencyUSD(asset.current_value)}</span>
                    </div>
                    <div className="flex justify-between pt-2 border-t border-gray-700">
                      <span className="text-gray-400 text-sm">P&L</span>
                      <span className={asset.current_value > asset.purchase_price ? 'text-green-400' : 'text-red-400'}>
                        {formatCurrencyUSD(asset.current_value - asset.purchase_price)}
                      </span>
                    </div>
                  </div>
                  
                  <button className="w-full mt-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg">
                    Sell Asset
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MyAssetsPage;