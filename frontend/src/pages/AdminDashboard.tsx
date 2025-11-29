// File: frontend/src/pages/AdminDashboard.tsx
/**
 * Admin Transaction Dashboard
 * 🚨 Only accessible to verified admins (is_admin=true + role='tribe')
 */

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, AlertTriangle, DollarSign, Activity, 
  Users, RefreshCw, Clock, CheckCircle, XCircle 
} from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

interface TransactionMetrics {
  total_transactions: number;
  success_count: number;
  failed_count: number;
  success_rate: number;
  total_volume_usd: number;
  avg_transaction_size: number;
}

interface FailedTransaction {
  transaction_id: string;
  user_email: string;
  user_name: string;
  type: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  failure_reason: string;
}

export const AdminDashboard: React.FC = () => {
  const { user, userProfile } = useAuth();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<TransactionMetrics | null>(null);
  const [failedTxs, setFailedTxs] = useState<FailedTransaction[]>([]);
  const [liveFeed, setLiveFeed] = useState<any[]>([]);
  const [timeRange, setTimeRange] = useState(24); // hours
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // ============================================================================
  // ACCESS CONTROL (Frontend guard)
  // ============================================================================
  useEffect(() => {
    console.log('🔍 ADMIN DEBUG:', {
      userProfile,
      is_admin: userProfile?.is_admin,
      role: userProfile?.role,
      email: userProfile?.email
    });
    
    if (!userProfile?.is_admin) {
      console.error('❌ Admin check failed - redirecting');
      toast.error('Admin access required');
      navigate('/dashboard');
    } else {
      console.log('✅ Admin check passed!');
    }
  }, [userProfile, navigate]);
  
  // ============================================================================
  // DATA FETCHING
  // ============================================================================
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch overview metrics
      const overviewRes = await apiClient.get(`/api/v1/admin/transactions/overview?hours=${timeRange}`);
      if (overviewRes.data.success) {
        setMetrics(overviewRes.data.metrics);
      }
      
      // Fetch failed transactions
      const failedRes = await apiClient.get('/api/v1/admin/transactions/failed?limit=20');
      if (failedRes.data.success) {
        setFailedTxs(failedRes.data.failed_transactions);
      }
      
      // Fetch live feed
      const feedRes = await apiClient.get('/api/v1/admin/transactions/live-feed?limit=15');
      if (feedRes.data.success) {
        setLiveFeed(feedRes.data.transactions);
      }
      
    } catch (error: any) {
      console.error('Admin dashboard error:', error);
      if (error.response?.status === 403) {
        toast.error('Admin access denied');
        navigate('/dashboard');
      } else {
        toast.error('Failed to load admin data');
      }
    } finally {
      setLoading(false);
    }
  };
  
  useEffect(() => {
    fetchDashboardData();
  }, [timeRange]);
  
  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      fetchDashboardData();
    }, 30000);
    
    return () => clearInterval(interval);
  }, [autoRefresh, timeRange]);
  
  // ============================================================================
  // RENDER
  // ============================================================================
  if (loading && !metrics) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        
        {/* ========== HEADER ========== */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Admin Dashboard</h1>
            <p className="text-gray-400">Transaction Monitoring & Analytics</p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Time range selector */}
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className="bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700"
            >
              <option value={24}>Last 24 hours</option>
              <option value={48}>Last 48 hours</option>
              <option value={168}>Last 7 days</option>
            </select>
            
            {/* Auto-refresh toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 rounded-lg transition-colors ${
                autoRefresh 
                  ? 'bg-green-600 hover:bg-green-700 text-white' 
                  : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
              }`}
            >
              <RefreshCw className={`h-5 w-5 ${autoRefresh ? 'animate-spin' : ''}`} />
            </button>
            
            {/* Manual refresh */}
            <button
              onClick={fetchDashboardData}
              className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-white transition-colors"
            >
              Refresh Now
            </button>
          </div>
        </div>
        
        {/* ========== METRICS CARDS ========== */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          
          {/* Total Transactions */}
          <div className="bg-gradient-to-br from-blue-900/20 to-blue-800/20 border border-blue-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <Activity className="h-8 w-8 text-blue-400" />
              <span className="text-sm text-gray-400">{timeRange}h</span>
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              {metrics?.total_transactions.toLocaleString() || 0}
            </div>
            <div className="text-sm text-gray-400">Total Transactions</div>
          </div>
          
          {/* Success Rate */}
          <div className="bg-gradient-to-br from-green-900/20 to-green-800/20 border border-green-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <CheckCircle className="h-8 w-8 text-green-400" />
              <span className="text-sm text-green-400">
                {metrics?.success_count || 0} completed
              </span>
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              {metrics?.success_rate.toFixed(1) || 0}%
            </div>
            <div className="text-sm text-gray-400">Success Rate</div>
          </div>
          
          {/* Total Volume */}
          <div className="bg-gradient-to-br from-purple-900/20 to-purple-800/20 border border-purple-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className="h-8 w-8 text-purple-400" />
              <span className="text-sm text-gray-400">USD</span>
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              ${(metrics?.total_volume_usd || 0).toLocaleString(undefined, {maximumFractionDigits: 0})}
            </div>
            <div className="text-sm text-gray-400">Total Volume</div>
          </div>
          
          {/* Failed Transactions */}
          <div className="bg-gradient-to-br from-red-900/20 to-red-800/20 border border-red-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <XCircle className="h-8 w-8 text-red-400" />
              <span className="text-sm text-red-400">
                {((metrics?.failed_count || 0) / (metrics?.total_transactions || 1) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              {metrics?.failed_count || 0}
            </div>
            <div className="text-sm text-gray-400">Failed Transactions</div>
          </div>
        </div>
        
        {/* ========== FAILED TRANSACTIONS TABLE ========== */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-red-400" />
            Recent Failed Transactions
          </h2>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700">
                  <th className="pb-3 px-4">User</th>
                  <th className="pb-3 px-4">Type</th>
                  <th className="pb-3 px-4">Amount</th>
                  <th className="pb-3 px-4">Time</th>
                  <th className="pb-3 px-4">Reason</th>
                </tr>
              </thead>
              <tbody>
                {failedTxs.map((tx) => (
                  <tr key={tx.transaction_id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                    <td className="py-3 px-4">
                      <div className="text-white font-medium">{tx.user_name}</div>
                      <div className="text-sm text-gray-400">{tx.user_email}</div>
                    </td>
                    <td className="py-3 px-4 text-gray-300 capitalize">
                      {tx.type.replace('_', ' ')}
                    </td>
                    <td className="py-3 px-4 text-white font-mono">
                      {tx.amount.toFixed(2)} {tx.currency}
                    </td>
                    <td className="py-3 px-4 text-gray-400 text-sm">
                      {new Date(tx.created_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-red-400 text-sm">
                      {tx.failure_reason || 'Unknown error'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        
        {/* ========== LIVE FEED ========== */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Activity className="h-6 w-6 text-blue-400 animate-pulse" />
            Live Transaction Feed
          </h2>
          
          <div className="space-y-3">
            {liveFeed.map((tx) => (
              <div 
                key={tx.id} 
                className="bg-gray-900/50 rounded-lg p-4 flex items-center justify-between hover:bg-gray-900/70 transition-colors"
              >
                <div className="flex items-center gap-4 flex-1">
                  <div className={`w-3 h-3 rounded-full ${
                    tx.status === 'completed' ? 'bg-green-400 animate-pulse' :
                    tx.status === 'failed' ? 'bg-red-400' :
                    'bg-yellow-400 animate-pulse'
                  }`}></div>
                  
                  <div className="flex-1">
                    <div className="text-white font-medium">{tx.user_email}</div>
                    <div className="text-sm text-gray-400">{tx.type}</div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-white font-mono">{tx.amount.toFixed(2)} {tx.currency}</div>
                    <div className="text-xs text-gray-400">
                      {new Date(tx.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
        
      </div>
    </div>
  );
};

export default AdminDashboard;