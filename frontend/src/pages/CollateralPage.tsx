// File: frontend/src/pages/CollateralPage.tsx
import React, { useState, useEffect } from 'react';
import { Shield, Plus, Target, Activity } from 'lucide-react';
import Sidebar from '@/components/layout/Sidebar';
import CreateRepoModal from '@/components/modals/CreateRepoModal';
import CollateralManagementModal from '@/components/modals/CollateralManagementModal';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

const CollateralPage = () => {
  const [loading, setLoading] = useState(true);
  const [tokenizedAssets, setTokenizedAssets] = useState<any[]>([]);
  const [repos, setRepos] = useState<any[]>([]);
  const [collateralSummary, setCollateralSummary] = useState<any>(null);
  const [showCreateRepoModal, setShowCreateRepoModal] = useState(false);
  const [showManageModal, setShowManageModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // ✅ Use allSettled to handle individual failures gracefully
      const [assetsRes, reposRes, summaryRes] = await Promise.allSettled([
        apiClient.get('/api/v1/tokenization/my-assets'),
        apiClient.get('/api/v1/tokenization/my-repos'),
        apiClient.get('/api/v1/collateral/summary')
      ]);

      // ✅ Handle successful responses
      if (assetsRes.status === 'fulfilled' && assetsRes.value.data.success) {
        setTokenizedAssets(assetsRes.value.data.assets || []);
      }

      if (reposRes.status === 'fulfilled' && reposRes.value.data.success) {
        setRepos(reposRes.value.data.repos || []);
      } else if (reposRes.status === 'rejected') {
        console.warn('⚠️ Repos endpoint failed:', reposRes.reason);
        setRepos([]); // Set empty array, don't crash page
      }

      if (summaryRes.status === 'fulfilled' && summaryRes.value.data.success) {
        setCollateralSummary(summaryRes.value.data.summary);
      }
    } catch (error) {
      console.error('Failed to fetch collateral data:', error);
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
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-orange-600"></div>
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
              <Shield className="h-8 w-8 text-orange-400" />
              Collateral Management
            </h1>
            <p className="text-gray-400">Borrow against tokenized assets & manage positions</p>
          </div>

          {/* Quick Actions */}
          <div className="flex gap-3 mb-6">
            <button
              onClick={() => setShowCreateRepoModal(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg text-white font-semibold transition-colors"
            >
              <Plus className="h-5 w-5" />
              Create Repo Trade
            </button>
            <button
              onClick={() => setShowManageModal(true)}
              className="flex items-center gap-2 bg-orange-600 hover:bg-orange-700 px-6 py-3 rounded-lg text-white font-semibold transition-colors"
            >
              <Target className="h-5 w-5" />
              Manage Collateral
            </button>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-gradient-to-br from-orange-900/20 to-yellow-900/20 border border-orange-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">Total Positions</div>
              <div className="text-4xl font-bold text-white mb-2">
                {collateralSummary?.total_positions || 0}
              </div>
              <div className="text-sm text-orange-400">Active locks</div>
            </div>

            <div className="bg-gradient-to-br from-green-900/20 to-emerald-900/20 border border-green-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">Total Value</div>
              <div className="text-4xl font-bold text-white mb-2">
                ${collateralSummary?.total_value_usd?.toFixed(2) || '0.00'}
              </div>
              <div className="text-sm text-green-400">USD</div>
            </div>

            <div className="bg-gradient-to-br from-blue-900/20 to-cyan-900/20 border border-blue-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">Repo Trades</div>
              <div className="text-4xl font-bold text-white mb-2">{repos.length}</div>
              <div className="text-sm text-blue-400">Active</div>
            </div>

            <div className="bg-gradient-to-br from-purple-900/20 to-pink-900/20 border border-purple-500/30 rounded-xl p-6">
              <div className="text-sm text-gray-400 mb-2">DVP Settlements</div>
              <div className="text-4xl font-bold text-white mb-2">
                {collateralSummary?.dvp_positions || 0}
              </div>
              <div className="text-sm text-purple-400">Pending</div>
            </div>
          </div>

          {/* Active Repo Trades */}
          <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 border border-gray-700/50 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Active Repo Trades</h2>
              <button
                onClick={() => setShowCreateRepoModal(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
              >
                Create New
              </button>
            </div>

            {repos.length === 0 ? (
              <div className="text-center py-12">
                <Activity className="h-16 w-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-400 mb-2">No Active Repos</h3>
                <p className="text-gray-500 mb-4">Borrow cash against your tokenized assets</p>
                <button
                  onClick={() => setShowCreateRepoModal(true)}
                  className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
                >
                  Create Repo Trade
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {repos.map((repo) => (
                  <div key={repo.id} className="bg-gradient-to-br from-blue-900/20 to-purple-900/20 border border-blue-500/30 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full font-medium">
                        {repo.status}
                      </span>
                      <span className="text-xs text-gray-400">
                        {new Date(repo.maturity_time).toLocaleDateString()}
                      </span>
                    </div>
                    
                    <div className="mb-3">
                      <div className="text-sm text-gray-400 mb-1">Loan Amount</div>
                      <div className="text-xl font-bold text-white">${repo.loan_amount_usd?.toFixed(2)}</div>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 mb-3">
                      <div>
                        <div className="text-xs text-gray-400 mb-1">LTV</div>
                        <div className="text-sm font-semibold text-green-400">
                          {repo.loan_to_value_ratio?.toFixed(2)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-400 mb-1">Rate</div>
                        <div className="text-sm font-semibold text-white">
                          {repo.repo_rate_percentage?.toFixed(2)}%
                        </div>
                      </div>
                    </div>
                    
                    <div className="pt-3 border-t border-gray-700/50">
                      <div className="text-xs text-gray-400 mb-1">Repurchase Amount</div>
                      <div className="text-base font-bold text-white">
                        ${repo.repurchase_amount?.toFixed(2)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Modals */}
      <CreateRepoModal 
        open={showCreateRepoModal} 
        onOpenChange={setShowCreateRepoModal}
        tokenizedAssets={tokenizedAssets}
      />
      <CollateralManagementModal 
        open={showManageModal} 
        onOpenChange={setShowManageModal}
      />
    </div>
  );
};

export default CollateralPage;