// File: frontend/src/pages/AdminDashboard.tsx
// ✅ PRODUCTION-READY VERSION v2.0 - Complete Admin Dashboard
// 🎯 Features: Real-time metrics, Revenue tracking, Export to CSV, Auto-refresh
// 🚀 ALL IMPROVEMENTS IMPLEMENTED - Ready for deployment

import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, AlertTriangle, DollarSign, Activity, 
  Users, RefreshCw, Clock, CheckCircle, XCircle, ArrowLeft
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

interface RevenueData {
  revenue_summary: {
    total_collected: number;
    total_owed: number;
    collection_rate: number;
    net_position: number;
    total_transactions: number;
    avg_transaction_value: number;
  };
  uncollected_fees: {
    total_usd: number;
    count: number;
    by_chain: Record<string, number>;
  };
  revenue_by_date: Record<string, {
    revenue: number;
    transactions: number;
    avg_value: number;
  }>;
}

export const AdminDashboard: React.FC = () => {
  const { user, userProfile } = useAuth();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<TransactionMetrics | null>(null);
  const [failedTxs, setFailedTxs] = useState<FailedTransaction[]>([]);
  const [liveFeed, setLiveFeed] = useState<any[]>([]);
  const [timeRange, setTimeRange] = useState(24);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [revenueData, setRevenueData] = useState<RevenueData | null>(null);
  const [showRevenueModal, setShowRevenueModal] = useState(false);
  
  // Access control
  useEffect(() => {
    if (userProfile && !userProfile.is_admin) {
      toast.error('Admin access required');
      navigate('/dashboard');
    }
  }, [userProfile, navigate]);
  
  // Export data to CSV
  const exportToCSV = (data: any[], filename: string) => {
    if (!data || data.length === 0) {
      toast.error('No data to export');
      return;
    }
    
    // Get headers from first object
    const headers = Object.keys(data[0]);
    
    // Create CSV content
    const csvContent = [
      headers.join(','),
      ...data.map(row => 
        headers.map(header => {
          const value = row[header];
          // Escape commas and quotes
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`;
          }
          return value;
        }).join(',')
      )
    ].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    toast.success('Export successful!');
  };
  
  // Data fetching
  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      console.log('🔍 [Admin] Fetching dashboard data for hours:', timeRange);
      
      // Fetch overview metrics
      const overviewRes = await apiClient.get(`/api/v1/admin/transactions/overview?hours=${timeRange}`);
      console.log('📊 [Admin] Overview response:', overviewRes.data);
      
      if (overviewRes.data.success) {
        setMetrics(overviewRes.data.metrics);
        console.log('✅ [Admin] Metrics set:', overviewRes.data.metrics);
      }
      
      // Fetch failed transactions
      const failedRes = await apiClient.get('/api/v1/admin/transactions/failed?limit=20');
      console.log('🚨 [Admin] Failed txs response:', failedRes.data);
      
      if (failedRes.data.success) {
        setFailedTxs(failedRes.data.failed_transactions);
      }
      
      // Fetch live feed
      const feedRes = await apiClient.get('/api/v1/admin/transactions/live-feed?limit=15');
      console.log('📡 [Admin] Live feed response:', feedRes.data);
      
      if (feedRes.data.success) {
        setLiveFeed(feedRes.data.transactions);
      }
      
      // Fetch revenue summary
      const revenueRes = await apiClient.get('/api/v1/admin/revenue/summary?days=30');
      console.log('💰 [Admin] Revenue response:', revenueRes.data);

      if (revenueRes.data.success) {
        setRevenueData(revenueRes.data);
      }

    } catch (error: any) {
      console.error('❌ [Admin] Dashboard error:', error);
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
        
        {/* HEADER */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            {/* Back Button */}
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-300 transition-colors"
              title="Back to Dashboard"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="hidden md:inline">Back</span>
            </button>
            
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">Admin Dashboard</h1>
              <p className="text-gray-400">Transaction Monitoring & Analytics</p>
            </div>
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
              title={autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}
            >
              <RefreshCw className={`h-5 w-5 ${autoRefresh ? 'animate-spin' : ''}`} />
            </button>
            
            {/* Manual refresh */}
            <button
              onClick={() => {
                fetchDashboardData();
                toast.success('Refreshing dashboard...', { duration: 1000 });
              }}
              disabled={loading}
              className={`px-4 py-2 rounded-lg text-white transition-colors flex items-center gap-2 ${
                loading 
                  ? 'bg-gray-600 cursor-not-allowed' 
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
              {loading ? 'Refreshing...' : 'Refresh Now'}
            </button>
          </div>
        </div>
        
        {/* ========== TOP 4 METRICS CARDS (REAL DATA) ========== */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          
          {/* Card 1: Total Transactions */}
          <div className="bg-gradient-to-br from-blue-900/20 to-blue-800/20 border border-blue-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <Activity className="h-8 w-8 text-blue-400" />
              <span className="text-sm text-gray-400">{timeRange}h</span>
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              {metrics?.total_transactions?.toLocaleString() || 0}
            </div>
            <div className="text-sm text-gray-400">Total Transactions</div>
            {loading && <div className="mt-2 h-1 w-full bg-blue-500/20 rounded-full overflow-hidden">
              <div className="h-full w-1/2 bg-blue-500 animate-pulse"></div>
            </div>}
          </div>
          
          {/* Card 2: Success Rate */}
          <div className="bg-gradient-to-br from-green-900/20 to-green-800/20 border border-green-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <CheckCircle className="h-8 w-8 text-green-400" />
              <span className="text-sm text-green-400">
                {metrics?.success_count?.toLocaleString() || 0} completed
              </span>
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              {(metrics?.success_rate || 0).toFixed(1)}%
            </div>
            <div className="text-sm text-gray-400">Success Rate</div>
            {loading && <div className="mt-2 h-1 w-full bg-green-500/20 rounded-full overflow-hidden">
              <div className="h-full w-1/2 bg-green-500 animate-pulse"></div>
            </div>}
          </div>
          
          {/* Card 3: Total Volume */}
          <div className="bg-gradient-to-br from-purple-900/20 to-purple-800/20 border border-purple-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className="h-8 w-8 text-purple-400" />
              <span className="text-sm text-gray-400">USD</span>
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              ${(metrics?.total_volume_usd || 0).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
              })}
            </div>
            <div className="text-sm text-gray-400">Total Volume</div>
            {loading && <div className="mt-2 h-1 w-full bg-purple-500/20 rounded-full overflow-hidden">
              <div className="h-full w-1/2 bg-purple-500 animate-pulse"></div>
            </div>}
          </div>
          
          {/* Card 4: Failed Transactions */}
          <div className="bg-gradient-to-br from-red-900/20 to-red-800/20 border border-red-500/30 rounded-2xl p-6">
            <div className="flex items-center justify-between mb-4">
              <XCircle className="h-8 w-8 text-red-400" />
              <span className="text-sm text-red-400">
                {((metrics?.failed_count || 0) / (metrics?.total_transactions || 1) * 100).toFixed(1)}%
              </span>
            </div>
            <div className="text-3xl font-bold text-white mb-1">
              {metrics?.failed_count?.toLocaleString() || 0}
            </div>
            <div className="text-sm text-gray-400">Failed Transactions</div>
            {loading && <div className="mt-2 h-1 w-full bg-red-500/20 rounded-full overflow-hidden">
              <div className="h-full w-1/2 bg-red-500 animate-pulse"></div>
            </div>}
          </div>
        </div>
        
        {/* ========== REVENUE SUMMARY SECTION ========== */}
        {revenueData && (
          <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6 mb-8">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <DollarSign className="h-6 w-6 text-green-400" />
              Revenue Summary (30 Days)
            </h2>
            
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-2">Total Collected</div>
                <div className="text-2xl font-bold text-green-400">
                  ${(revenueData.revenue_summary?.total_collected || 0).toFixed(2)}
                </div>
              </div>
              
              <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-2">Uncollected</div>
                <div className="text-2xl font-bold text-yellow-400">
                  ${(revenueData.uncollected_fees?.total_usd || 0).toFixed(2)}
                </div>
              </div>
              
              <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-2">Net Position</div>
                <div className="text-2xl font-bold text-blue-400">
                  ${(revenueData.revenue_summary?.net_position || 0).toFixed(2)}
                </div>
              </div>
              
              <div className="bg-purple-900/20 border border-purple-500/30 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-2">Avg Transaction</div>
                <div className="text-2xl font-bold text-purple-400">
                  ${(revenueData.revenue_summary?.avg_transaction_value || 0).toFixed(2)}
                </div>
              </div>
            </div>
            
            <button
              onClick={() => setShowRevenueModal(true)}
              className="mt-4 text-sm text-green-400 hover:text-green-300 transition-colors hover:underline"
            >
              View Detailed Revenue Report →
            </button>
          </div>
        )}

        {/* FAILED TRANSACTIONS TABLE */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6 mb-8">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="h-6 w-6 text-red-400" />
            Recent Failed Transactions
          </h2>
          
          {failedTxs.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              No failed transactions in the selected time range
            </div>
          ) : (
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
          )}
        </div>
        
        {/* LIVE FEED */}
        <div className="bg-gray-800/50 border border-gray-700 rounded-2xl p-6">
          <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
            <Activity className="h-6 w-6 text-blue-400 animate-pulse" />
            Live Transaction Feed
          </h2>
          
          {liveFeed.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              No recent transactions
            </div>
          ) : (
            <div className="space-y-3">
              {liveFeed.map((tx) => (
                <div 
                  key={tx.id} 
                  className="bg-gray-900/50 rounded-lg p-4 flex items-center justify-between hover:bg-gray-900/70 transition-colors group"
                >
                  <div className="flex items-center gap-4 flex-1">
                    <div className={`w-3 h-3 rounded-full ${
                      tx.status === 'completed' ? 'bg-green-400 animate-pulse' :
                      tx.status === 'failed' ? 'bg-red-400' :
                      'bg-yellow-400 animate-pulse'
                    }`}></div>
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <div className="text-white font-medium">{tx.user_email}</div>
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          tx.status === 'completed' ? 'bg-green-900/50 text-green-400' :
                          tx.status === 'failed' ? 'bg-red-900/50 text-red-400' :
                          'bg-yellow-900/50 text-yellow-400'
                        }`}>
                          {tx.status}
                        </span>
                      </div>
                      <div className="text-sm text-gray-400 capitalize">{tx.type.replace('_', ' ')}</div>
                    </div>
                    
                    <div className="text-right">
                      <div className="text-white font-mono font-medium">
                        {tx.amount.toFixed(2)} {tx.currency}
                      </div>
                      <div className="text-xs text-gray-400">
                        {new Date(tx.timestamp).toLocaleDateString()} {new Date(tx.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
        
      </div>
      
      {/* ========== DETAILED REVENUE MODAL ========== */}
      {showRevenueModal && revenueData && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            
            {/* Modal Header */}
            <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-6 flex items-center justify-between">
              <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                <DollarSign className="h-6 w-6 text-green-400" />
                Detailed Revenue Report (30 Days)
              </h2>
              <button
                onClick={() => setShowRevenueModal(false)}
                className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
              >
                <XCircle className="h-6 w-6 text-gray-400" />
              </button>
            </div>
            
            {/* Modal Content */}
            <div className="p-6 space-y-6">
              
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                  <div className="text-sm text-gray-400 mb-2">Total Collected</div>
                  <div className="text-3xl font-bold text-green-400">
                    ${(revenueData.revenue_summary?.total_collected || 0).toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {revenueData.revenue_summary?.total_transactions || 0} transactions
                  </div>
                </div>
                
                <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-xl p-4">
                  <div className="text-sm text-gray-400 mb-2">Uncollected Fees</div>
                  <div className="text-3xl font-bold text-yellow-400">
                    ${(revenueData.uncollected_fees?.total_usd || 0).toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {revenueData.uncollected_fees?.count || 0} pending
                  </div>
                </div>
                
                <div className="bg-blue-900/20 border border-blue-500/30 rounded-xl p-4">
                  <div className="text-sm text-gray-400 mb-2">Net Position</div>
                  <div className="text-3xl font-bold text-blue-400">
                    ${(revenueData.revenue_summary?.net_position || 0).toFixed(2)}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    Collection rate: {(revenueData.revenue_summary?.collection_rate || 0).toFixed(1)}%
                  </div>
                </div>
              </div>
              
              {/* Daily Breakdown Table */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-4">Daily Revenue Breakdown</h3>
                <div className="bg-gray-800/50 rounded-xl overflow-hidden">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-gray-700">
                        <th className="text-left p-4 text-gray-400 text-sm">Date</th>
                        <th className="text-right p-4 text-gray-400 text-sm">Revenue</th>
                        <th className="text-right p-4 text-gray-400 text-sm">Transactions</th>
                        <th className="text-right p-4 text-gray-400 text-sm">Avg Value</th>
                      </tr>
                    </thead>
                    <tbody>
                      {revenueData.revenue_by_date && Object.entries(revenueData.revenue_by_date)
                        .sort(([dateA], [dateB]) => dateB.localeCompare(dateA))
                        .slice(0, 10)
                        .map(([date, data]: [string, any]) => (
                        <tr key={date} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                          <td className="p-4 text-white">
                            {new Date(date).toLocaleDateString('en-US', { 
                              month: 'short', 
                              day: 'numeric',
                              year: 'numeric'
                            })}
                          </td>
                          <td className="p-4 text-right text-green-400 font-mono">
                            ${data.revenue?.toFixed(2) || '0.00'}
                          </td>
                          <td className="p-4 text-right text-gray-300">
                            {data.transactions || 0}
                          </td>
                          <td className="p-4 text-right text-blue-400 font-mono">
                            ${data.avg_value?.toFixed(2) || '0.00'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              
              {/* Uncollected Fees by Chain */}
              {revenueData.uncollected_fees?.by_chain && 
               Object.keys(revenueData.uncollected_fees.by_chain).length > 0 && (
                <div>
                  <h3 className="text-lg font-semibold text-white mb-4">Uncollected Fees by Chain</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {Object.entries(revenueData.uncollected_fees.by_chain).map(([chain, amount]: [string, any]) => (
                      <div key={chain} className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                        <div className="text-sm text-gray-400 mb-1 capitalize">{chain}</div>
                        <div className="text-2xl font-bold text-yellow-400">
                          ${amount.toFixed(2)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 border-t border-gray-700">
                <button
                  onClick={() => {
                    const exportData = Object.entries(revenueData.revenue_by_date || {}).map(([date, data]: [string, any]) => ({
                      date,
                      revenue: data.revenue,
                      transactions: data.transactions,
                      avg_value: data.avg_value
                    }));
                    exportToCSV(exportData, 'revenue_report');
                  }}
                  className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-3 rounded-lg font-medium transition-colors"
                >
                  Export to CSV
                </button>
                <button
                  onClick={() => setShowRevenueModal(false)}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 text-white px-4 py-3 rounded-lg font-medium transition-colors"
                >
                  Close
                </button>
              </div>
              
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;