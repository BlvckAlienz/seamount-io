// File: frontend/src/pages/CollateralPage.tsx
// 📱 MOBILE-FIRST RESPONSIVE DESIGN - Platform Standard Format

import React, { useState, useEffect } from 'react';
import { Shield, Plus, TrendingUp, Target, RefreshCw } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import CollateralManagementModal from '@/components/modals/CollateralManagementModal';
import CreateRepoModal from '@/components/modals/CreateRepoModal';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

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

const CollateralPage: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [positions, setPositions] = useState<CollateralPosition[]>([]);
  const [tokenizedAssets, setTokenizedAssets] = useState<any[]>([]);
  const [showManageModal, setShowManageModal] = useState(false);
  const [showCreateRepoModal, setShowCreateRepoModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [positionsRes, assetsRes] = await Promise.all([
        apiClient.get('/api/v1/collateral/positions'),
        apiClient.get('/api/v1/tokenization/my-tokens')
      ]);

      if (positionsRes.data.success) {
        setPositions(positionsRes.data.positions || []);
      }

      if (assetsRes.data.success) {
        setTokenizedAssets(assetsRes.data.tokens || []);
      }
    } catch (error: any) {
      console.error('Failed to fetch collateral data:', error);
      if (error.response?.status !== 404) {
        toast.error('Failed to load data');
      }
    } finally {
      setLoading(false);
    }
  };

  // Calculate stats from real data
  const totalLocked = positions
    .filter(p => p.status === 'active')
    .reduce((sum, p) => sum + p.current_value_usd, 0);
  
  const activePositions = positions.filter(p => p.status === 'active').length;
  const repoPositions = positions.filter(p => p.lock_type === 'repo' && p.status === 'active').length;

  if (loading) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-orange-600"></div>
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
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 mb-2">
              <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-2 md:gap-3">
                <Shield className="h-6 w-6 md:h-8 md:w-8 text-orange-400" />
                <span>Collateral Management</span>
              </h1>
              <button
                onClick={fetchData}
                disabled={loading}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-white transition-colors disabled:opacity-50 self-start sm:self-auto"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                <span className="text-sm">Refresh</span>
              </button>
            </div>
            <p className="text-sm md:text-base text-gray-400">
              Unlock liquidity using your digital assets as collateral
            </p>
          </div>

          {/* Stats Cards - Responsive Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6 md:mb-8">
            <div className="bg-gradient-to-br from-orange-900/20 to-red-900/20 border border-orange-500/30 rounded-xl p-4 md:p-6">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Total Locked Value</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">
                ${totalLocked.toFixed(2)}
              </div>
              <div className="text-xs md:text-sm text-orange-400">USD</div>
            </div>

            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-4 md:p-6">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Active Positions</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">{activePositions}</div>
              <div className="text-xs md:text-sm text-blue-400">On-chain</div>
            </div>

            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-4 md:p-6 sm:col-span-2 lg:col-span-1">
              <div className="text-xs md:text-sm text-gray-400 mb-2">Active Repo Trades</div>
              <div className="text-3xl md:text-4xl font-bold text-white mb-2">{repoPositions}</div>
              <div className="text-xs md:text-sm text-green-400">Borrowing</div>
            </div>
          </div>

          {/* Quick Actions - Responsive */}
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <button
              onClick={() => setShowCreateRepoModal(true)}
              className="flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 px-4 md:px-6 py-3 rounded-lg text-white text-sm md:text-base font-semibold transition-all shadow-lg hover:shadow-xl flex-1 sm:flex-initial"
            >
              <Plus className="h-4 w-4 md:h-5 md:w-5" />
              Create Repo Trade
            </button>
          </div>

          {/* Positions Section */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-4 md:p-6">
            <h2 className="text-lg md:text-xl font-bold text-white mb-4">Active Collateral Positions</h2>

            {positions.length === 0 ? (
              <div className="text-center py-8 md:py-12">
                <Shield className="h-12 w-12 md:h-16 md:w-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg md:text-xl font-semibold text-gray-400 mb-2">No Active Positions</h3>
                <p className="text-sm md:text-base text-gray-500 mb-4">
                  Lock assets to access liquidity or participate in repo markets
                </p>
                <button
                  onClick={() => setShowCreateRepoModal(true)}
                  className="px-4 md:px-6 py-2 md:py-3 bg-blue-600 hover:bg-blue-700 text-white text-sm md:text-base font-semibold rounded-lg transition-colors"
                >
                  Create Your First Repo Trade
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
                        <th className="text-left text-xs font-medium text-gray-400 uppercase py-3 px-4">Type</th>
                        <th className="text-right text-xs font-medium text-gray-400 uppercase py-3 px-4">Quantity</th>
                        <th className="text-right text-xs font-medium text-gray-400 uppercase py-3 px-4">Value (USD)</th>
                        <th className="text-center text-xs font-medium text-gray-400 uppercase py-3 px-4">Status</th>
                        <th className="text-right text-xs font-medium text-gray-400 uppercase py-3 px-4">Actions</th>
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
                            <button
                              onClick={() => setShowManageModal(true)}
                              className="px-3 py-1 bg-orange-600 hover:bg-orange-700 rounded text-white text-sm font-medium transition-colors"
                            >
                              Manage
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Mobile Card View */}
                <div className="lg:hidden space-y-4">
                  {positions.map((position) => (
                    <div key={position.id} className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50">
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <h3 className="text-white font-bold text-lg">{position.asset_symbol || 'Unknown'}</h3>
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

                      <button
                        onClick={() => setShowManageModal(true)}
                        className="w-full py-2 bg-orange-600 hover:bg-orange-700 text-white font-semibold rounded-lg transition-colors"
                      >
                        Manage Position
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
      <CollateralManagementModal
        open={showManageModal}
        onOpenChange={setShowManageModal}
      />

      <CreateRepoModal
        open={showCreateRepoModal}
        onOpenChange={setShowCreateRepoModal}
        tokenizedAssets={tokenizedAssets}
      />
    </div>
  );
};

export default CollateralPage;