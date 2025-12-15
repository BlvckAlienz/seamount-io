// File: frontend/src/components/modals/CollateralManagementModal.tsx
// 📱 MOBILE-FIRST RESPONSIVE DESIGN

import React, { useState, useEffect } from 'react';
import { X, Shield, TrendingUp, Target, RefreshCw, Coins } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

interface CollateralManagementModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface CollateralPosition {
  id: string;
  asset_id: string;
  locked_quantity: number;
  current_value_usd: number;
  lock_type: string;
  related_trade_id: string;
  status: string;
  created_at: string;
  asset_symbol?: string;
  asset_name?: string;
}

export const CollateralManagementModal: React.FC<CollateralManagementModalProps> = ({
  open,
  onOpenChange,
}) => {
  const [loading, setLoading] = useState(true);
  const [positions, setPositions] = useState<CollateralPosition[]>([]);
  const [selectedPosition, setSelectedPosition] = useState<CollateralPosition | null>(null);

  useEffect(() => {
    if (open) {
      fetchCollateralPositions();
    }
  }, [open]);

  const fetchCollateralPositions = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/collateral/positions');
      if (response.data.success) {
        setPositions(response.data.positions || []);
      }
    } catch (error) {
      console.error('Failed to fetch collateral positions:', error);
      toast.error('Failed to load collateral positions');
    } finally {
      setLoading(false);
    }
  };

  const handleRelease = async (positionId: string) => {
    try {
      const response = await apiClient.post(`/api/v1/collateral/release/${positionId}`);
      if (response.data.success) {
        toast.success('Collateral released successfully');
        fetchCollateralPositions();
      }
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to release collateral');
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700 rounded-2xl w-full max-w-6xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 md:p-6 border-b border-gray-700 sticky top-0 bg-gray-900/95 backdrop-blur-sm z-10">
          <div>
            <h2 className="text-xl md:text-2xl font-bold text-white flex items-center gap-2">
              <Shield className="h-5 w-5 md:h-6 md:w-6 text-orange-400" />
              <span>Collateral Management</span>
            </h2>
            <p className="text-gray-400 text-xs md:text-sm mt-1">View and manage locked assets</p>
          </div>
          <button
            onClick={() => onOpenChange(false)}
            className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-400" />
          </button>
        </div>

        <div className="p-4 md:p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-orange-500"></div>
            </div>
          ) : positions.length === 0 ? (
            <div className="text-center py-8 md:py-12">
              <Shield className="h-12 w-12 md:h-16 md:w-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg md:text-xl font-semibold text-gray-400 mb-2">No Active Collateral</h3>
              <p className="text-sm md:text-base text-gray-500">You don't have any locked collateral positions</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Summary Cards - Responsive Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                <div className="bg-gradient-to-br from-orange-900/20 to-yellow-900/20 border border-orange-500/30 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="p-2 bg-orange-500/20 rounded-lg">
                      <Shield className="h-5 w-5 text-orange-400" />
                    </div>
                  </div>
                  <div className="text-2xl md:text-3xl font-bold text-white mb-1">
                    {positions.filter(p => p.status === 'active').length}
                  </div>
                  <div className="text-xs md:text-sm text-gray-400">Active Positions</div>
                </div>

                <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <div className="p-2 bg-green-500/20 rounded-lg">
                      <Coins className="h-5 w-5 text-green-400" />
                    </div>
                  </div>
                  <div className="text-2xl md:text-3xl font-bold text-white mb-1">
                    ${positions.reduce((sum, p) => sum + p.current_value_usd, 0).toFixed(2)}
                  </div>
                  <div className="text-xs md:text-sm text-gray-400">Total Value</div>
                </div>

                <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4 sm:col-span-2 lg:col-span-1">
                  <div className="flex items-center justify-between mb-2">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                      <Target className="h-5 w-5 text-blue-400" />
                    </div>
                  </div>
                  <div className="text-2xl md:text-3xl font-bold text-white mb-1">
                    {positions.filter(p => p.lock_type === 'repo').length}
                  </div>
                  <div className="text-xs md:text-sm text-gray-400">Repo Trades</div>
                </div>
              </div>

              {/* Desktop Table View */}
              <div className="hidden lg:block bg-gray-800/50 rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Asset</th>
                        <th className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Type</th>
                        <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Quantity</th>
                        <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Value</th>
                        <th className="text-center text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Status</th>
                        <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((position) => (
                        <tr key={position.id} className="border-b border-gray-700/50 hover:bg-gray-800/30 transition-colors">
                          <td className="py-4 px-4">
                            <div>
                              <div className="text-white font-medium">{position.asset_symbol || 'Unknown'}</div>
                              <div className="text-xs text-gray-400">{position.asset_name || 'Asset'}</div>
                            </div>
                          </td>
                          <td className="py-4 px-4">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              position.lock_type === 'repo' 
                                ? 'bg-blue-500/20 text-blue-400' 
                                : 'bg-purple-500/20 text-purple-400'
                            }`}>
                              {position.lock_type.toUpperCase()}
                            </span>
                          </td>
                          <td className="py-4 px-4 text-right">
                            <span className="text-white font-medium">{position.locked_quantity}</span>
                          </td>
                          <td className="py-4 px-4 text-right">
                            <span className="text-white font-bold">${position.current_value_usd.toFixed(2)}</span>
                          </td>
                          <td className="py-4 px-4 text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              position.status === 'active'
                                ? 'bg-green-500/20 text-green-400'
                                : 'bg-gray-500/20 text-gray-400'
                            }`}>
                              {position.status}
                            </span>
                          </td>
                          <td className="py-4 px-4 text-right">
                            {position.status === 'active' && position.lock_type !== 'repo' && (
                              <button
                                onClick={() => handleRelease(position.id)}
                                className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-white text-sm font-medium transition-colors"
                              >
                                Release
                              </button>
                            )}
                            {position.lock_type === 'repo' && (
                              <button
                                onClick={() => setSelectedPosition(position)}
                                className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-white text-sm font-medium transition-colors"
                              >
                                View Repo
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Mobile Card View */}
              <div className="lg:hidden space-y-4">
                {positions.map((position) => (
                  <div key={position.id} className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="text-white font-bold">{position.asset_symbol || 'Unknown'}</h3>
                        <p className="text-gray-400 text-sm">{position.asset_name || 'Asset'}</p>
                      </div>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        position.status === 'active'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-gray-500/20 text-gray-400'
                      }`}>
                        {position.status}
                      </span>
                    </div>

                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Type</span>
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          position.lock_type === 'repo' 
                            ? 'bg-blue-500/20 text-blue-400' 
                            : 'bg-purple-500/20 text-purple-400'
                        }`}>
                          {position.lock_type.toUpperCase()}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-400">Quantity</span>
                        <span className="text-white font-medium">{position.locked_quantity}</span>
                      </div>
                      <div className="flex justify-between text-sm pt-2 border-t border-gray-700">
                        <span className="text-gray-400">Value</span>
                        <span className="text-white font-bold">${position.current_value_usd.toFixed(2)}</span>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      {position.status === 'active' && position.lock_type !== 'repo' && (
                        <button
                          onClick={() => handleRelease(position.id)}
                          className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors"
                        >
                          Release
                        </button>
                      )}
                      {position.lock_type === 'repo' && (
                        <button
                          onClick={() => setSelectedPosition(position)}
                          className="flex-1 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                        >
                          View Repo
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Refresh Button */}
              <button
                onClick={fetchCollateralPositions}
                className="w-full py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh Positions
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CollateralManagementModal;