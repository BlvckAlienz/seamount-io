// File: frontend/src/pages/CollateralPage.tsx
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
  const [showManageModal, setShowManageModal] = useState(false);
  const [showCreateRepoModal, setShowCreateRepoModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [positions, setPositions] = useState<CollateralPosition[]>([]);
  const [tokenizedAssets, setTokenizedAssets] = useState<any[]>([]);

  // 📊 CALCULATED STATS FROM REAL DATA
  const totalLocked = positions
    .filter(p => p.status === 'active')
    .reduce((sum, p) => sum + p.current_value_usd, 0);

  const activePositions = positions.filter(p => p.status === 'active').length;

  const repoPositions = positions.filter(p => p.lock_type === 'repo' && p.status === 'active').length;

  // 🔄 FETCH COLLATERAL POSITIONS
  const fetchCollateralPositions = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/collateral/positions');
      if (response.data.success) {
        setPositions(response.data.positions || []);
      }
    } catch (error: any) {
      console.error('Failed to fetch collateral positions:', error);
      if (error.response?.status !== 404) {
        toast.error('Failed to load collateral positions');
      }
    } finally {
      setLoading(false);
    }
  };

  // 🔄 FETCH TOKENIZED ASSETS (for CreateRepoModal)
  const fetchTokenizedAssets = async () => {
    try {
      const response = await apiClient.get('/api/v1/tokenization/my-tokens');
      if (response.data.success) {
        setTokenizedAssets(response.data.tokens || []);
      }
    } catch (error) {
      console.error('Failed to fetch tokenized assets:', error);
    }
  };

  useEffect(() => {
    fetchCollateralPositions();
    fetchTokenizedAssets();
  }, []);

  return (
  <div className="flex min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
    <Sidebar />
    
    <main className="flex-1 p-4 md:p-8 pt-20 lg:pt-8">
        {/* Header */}
        <div className="mb-6 md:mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-2xl md:text-4xl font-bold text-white mb-2 flex items-center gap-3">
                <Shield className="h-10 w-10 text-orange-400" />
                Collateral Management
              </h1>
              <p className="text-gray-400 text-lg">
                Lock and manage your digital assets as collateral
              </p>
            </div>
            
            {/* Refresh Button */}
            <button
              onClick={() => {
                fetchCollateralPositions();
                fetchTokenizedAssets();
              }}
              disabled={loading}
              className="p-3 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh data"
            >
              <RefreshCw className={`h-5 w-5 text-gray-300 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* 📊 REAL DATA STATS */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 md:gap-6 mb-6 md:mb-8">
          {/* Total Locked Value */}
          <div className="bg-gradient-to-br from-orange-900/30 to-gray-800 rounded-xl p-6 border border-orange-500/30">
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 bg-orange-500/20 rounded-lg">
                <Shield className="h-5 w-5 text-orange-400" />
              </div>
              {loading && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-orange-400"></div>
              )}
            </div>
            <div className="text-orange-400 text-sm font-semibold mb-2">Total Locked</div>
            <div className="text-3xl font-bold text-white">
              ${totalLocked.toFixed(2)}
            </div>
          </div>

          {/* Active Positions */}
          <div className="bg-gradient-to-br from-blue-900/30 to-gray-800 rounded-xl p-6 border border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <TrendingUp className="h-5 w-5 text-blue-400" />
              </div>
              {loading && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
              )}
            </div>
            <div className="text-blue-400 text-sm font-semibold mb-2">Active Positions</div>
            <div className="text-3xl font-bold text-white">{activePositions}</div>
          </div>

          {/* Repo Trades */}
          <div className="bg-gradient-to-br from-green-900/30 to-gray-800 rounded-xl p-6 border border-green-500/30">
            <div className="flex items-center justify-between mb-2">
              <div className="p-2 bg-green-500/20 rounded-lg">
                <Target className="h-5 w-5 text-green-400" />
              </div>
              {loading && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-400"></div>
              )}
            </div>
            <div className="text-green-400 text-sm font-semibold mb-2">Active Repo Trades</div>
            <div className="text-3xl font-bold text-white">{repoPositions}</div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 md:gap-4 mb-6 md:mb-8">
          <button
            onClick={() => setShowManageModal(true)}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-orange-600 to-red-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-orange-500/30 transition-all"
          >
            <Shield className="h-5 w-5" />
            Manage Collateral
          </button>

          {/* 🚨 UPDATED BUTTON */}
          <button
            onClick={() => setShowCreateRepoModal(true)}
            className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-blue-500/30 transition-all"
          >
            <Plus className="h-5 w-5" />
            Create Repo Trade
          </button>
        </div>

        {/* Content: Empty State or Positions Table */}
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-center">
              <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-orange-500 mx-auto mb-4"></div>
              <p className="text-gray-400 text-lg">Loading collateral positions...</p>
            </div>
          </div>
        ) : positions.length === 0 ? (
          <div className="text-center py-16 bg-gray-800/30 rounded-xl border border-gray-700">
            <Shield className="h-20 w-20 text-gray-600 mx-auto mb-4" />
            <h3 className="text-2xl font-bold text-gray-400 mb-2">No Collateral Positions</h3>
            <p className="text-gray-500 mb-6">Lock assets to access liquidity or participate in repo markets</p>
            <button
              onClick={() => setShowCreateRepoModal(true)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-all"
            >
              Create Your First Repo Trade
            </button>
          </div>
        ) : (
          <div className="bg-gray-800/50 rounded-xl overflow-x-auto">
            <div className="p-6 border-b border-gray-700">
              <h2 className="text-xl font-bold text-white">Active Positions</h2>
            </div>
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Asset</th>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Type</th>
                  <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Quantity</th>
                  <th className="text-right text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Value</th>
                  <th className="text-center text-xs font-medium text-gray-400 uppercase tracking-wider py-3 px-4">Status</th>
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>

      {/* 🚨 MODALS */}
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