import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, DollarSign, Activity, BarChart3, PieChart, RefreshCw, ArrowUpRight, ArrowDownRight, Target, Zap } from 'lucide-react';
import Card from './Card';
import Button from './Button';
import AdvancedChart from './AdvancedChart';
import { Skeleton, ChartSkeleton, TableSkeleton } from './LoadingSkeleton';
import { generateMockChartData } from '../data/mockData';
import { useRealMarketData } from '../hooks/useRealMarketData';
import { useBlockchain } from '../hooks/useBlockchain';

interface PortfolioAsset {
  symbol: string;
  name: string;
  quantity: number;
  avgCost: number;
  currentPrice: number;
  totalValue: number;
  pnl: number;
  pnlPercentage: number;
  allocation: number;
}

const Portfolio: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [selectedTimeframe, setSelectedTimeframe] = useState('1M');
  const [portfolioData, setPortfolioData] = useState(generateMockChartData(30));
  
  const { portfolio, assets, loading: marketLoading, error: marketError, refreshData } = useRealMarketData();
  const { balance, connected } = useBlockchain();

  // Mock portfolio assets with real-time updates
  const [portfolioAssets] = useState<PortfolioAsset[]>([
    {
      symbol: 'BTC',
      name: 'Bitcoin',
      quantity: 2.5,
      avgCost: 42000,
      currentPrice: 43500,
      totalValue: 108750,
      pnl: 3750,
      pnlPercentage: 3.57,
      allocation: 45.2
    },
    {
      symbol: 'ETH',
      name: 'Ethereum',
      quantity: 15.8,
      avgCost: 2800,
      currentPrice: 2950,
      totalValue: 46610,
      pnl: 2370,
      pnlPercentage: 5.36,
      allocation: 19.4
    },
    {
      symbol: 'AAPL',
      name: 'Apple Inc.',
      quantity: 200,
      avgCost: 175,
      currentPrice: 182.5,
      totalValue: 36500,
      pnl: 1500,
      pnlPercentage: 4.29,
      allocation: 15.2
    },
    {
      symbol: 'TSLA',
      name: 'Tesla Inc.',
      quantity: 50,
      avgCost: 220,
      currentPrice: 235.8,
      totalValue: 11790,
      pnl: 790,
      pnlPercentage: 7.18,
      allocation: 4.9
    },
    {
      symbol: 'USDS',
      name: 'Seamount USD Stablecoin',
      quantity: 37250,
      avgCost: 1.00,
      currentPrice: 1.00,
      totalValue: 37250,
      pnl: 0,
      pnlPercentage: 0,
      allocation: 15.5
    }
  ]);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 1200);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!loading) {
      const interval = setInterval(() => {
        setPortfolioData(generateMockChartData(30));
      }, 10000);
      return () => clearInterval(interval);
    }
  }, [loading]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercentage = (percentage: number) => {
    return `${percentage >= 0 ? '+' : ''}${percentage.toFixed(2)}%`;
  };

  const totalPortfolioValue = portfolioAssets.reduce((sum, asset) => sum + asset.totalValue, 0);
  const totalPnL = portfolioAssets.reduce((sum, asset) => sum + asset.pnl, 0);
  const totalPnLPercentage = (totalPnL / (totalPortfolioValue - totalPnL)) * 100;

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6">
              <ChartSkeleton height={200} />
            </div>
          ))}
        </div>
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-6">
          <TableSkeleton rows={5} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Portfolio Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card glassy className="relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/20 to-purple-500/10 rounded-full transform translate-x-16 -translate-y-16 group-hover:scale-125 transition-transform duration-700"></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Total Portfolio Value</h3>
              <div className="p-3 bg-blue-500/10 rounded-xl">
                <DollarSign className="h-6 w-6 text-blue-400" />
              </div>
            </div>
            <div className="text-3xl font-bold font-mono text-white mb-2">
              {formatCurrency(totalPortfolioValue)}
            </div>
            <div className={`flex items-center text-sm ${totalPnLPercentage >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {totalPnLPercentage >= 0 ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
              {formatCurrency(Math.abs(totalPnL))} ({formatPercentage(totalPnLPercentage)})
            </div>
          </div>
        </Card>

        <Card glassy className="relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-emerald-500/20 to-teal-500/10 rounded-full transform translate-x-16 -translate-y-16 group-hover:scale-125 transition-transform duration-700"></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Active Positions</h3>
              <div className="p-3 bg-emerald-500/10 rounded-xl">
                <Activity className="h-6 w-6 text-emerald-400" />
              </div>
            </div>
            <div className="text-3xl font-bold font-mono text-white mb-2">
              {portfolioAssets.filter(asset => asset.quantity > 0).length}
            </div>
            <div className="text-sm text-gray-400">
              Assets in portfolio
            </div>
          </div>
        </Card>

        <Card glassy className="relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-purple-500/20 to-pink-500/10 rounded-full transform translate-x-16 -translate-y-16 group-hover:scale-125 transition-transform duration-700"></div>
          <div className="relative">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Performance Score</h3>
              <div className="p-3 bg-purple-500/10 rounded-xl">
                <Target className="h-6 w-6 text-purple-400" />
              </div>
            </div>
            <div className="text-3xl font-bold font-mono text-white mb-2">
              {Math.round(Math.max(0, Math.min(100, 75 + totalPnLPercentage * 2)))}
            </div>
            <div className="text-sm text-purple-400">
              AI Performance Rating
            </div>
          </div>
        </Card>
      </div>

      {/* Portfolio Performance Chart */}
      <Card glassy>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-semibold text-white">Portfolio Performance</h3>
            <p className="text-sm text-gray-400">Powered by Seamount AI Analytics</p>
          </div>
          <div className="flex items-center space-x-3">
            <div className="flex bg-gray-800/50 rounded-lg p-1">
              {['1D', '1W', '1M', '3M', '1Y'].map((timeframe) => (
                <button
                  key={timeframe}
                  onClick={() => setSelectedTimeframe(timeframe)}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-all duration-200 ${
                    selectedTimeframe === timeframe
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white hover:bg-gray-700/50'
                  }`}
                >
                  {timeframe}
                </button>
              ))}
            </div>
            <Button size="sm" variant="ghost" onClick={refreshData} loading={marketLoading}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <AdvancedChart data={portfolioData} height={400} />
      </Card>

      {/* Asset Holdings Table */}
      <Card glassy>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-semibold text-white">Asset Holdings</h3>
            <p className="text-sm text-gray-400">Real-time portfolio breakdown</p>
          </div>
          <div className="flex space-x-2">
            <Button size="sm" variant="ghost" icon={PieChart}>
              Allocation
            </Button>
            <Button size="sm" variant="ghost" icon={BarChart3}>
              Performance
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700/50">
                <th className="text-left py-3 px-4 text-sm font-medium text-gray-400">Asset</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Quantity</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Avg Cost</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Current Price</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Market Value</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">P&L</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Allocation</th>
                <th className="text-right py-3 px-4 text-sm font-medium text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody>
              {portfolioAssets.map((asset, index) => (
                <tr key={asset.symbol} className="border-b border-gray-800/30 hover:bg-gray-800/20 transition-colors">
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white text-sm
                        ${asset.symbol === 'BTC' ? 'bg-gradient-to-br from-orange-500 to-yellow-500' :
                          asset.symbol === 'ETH' ? 'bg-gradient-to-br from-purple-500 to-blue-500' :
                          asset.symbol === 'AAPL' ? 'bg-gradient-to-br from-gray-600 to-gray-800' :
                          asset.symbol === 'TSLA' ? 'bg-gradient-to-br from-red-500 to-pink-500' :
                          'bg-gradient-to-br from-teal-500 to-blue-500'}`}
                      >
                        {asset.symbol.slice(0, 2)}
                      </div>
                      <div>
                        <div className="font-medium text-white">{asset.symbol}</div>
                        <div className="text-xs text-gray-400">{asset.name}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-4 text-right font-mono text-white">
                    {asset.quantity.toLocaleString()}
                  </td>
                  <td className="py-4 px-4 text-right font-mono text-white">
                    {formatCurrency(asset.avgCost)}
                  </td>
                  <td className="py-4 px-4 text-right font-mono text-white">
                    {formatCurrency(asset.currentPrice)}
                  </td>
                  <td className="py-4 px-4 text-right font-mono text-white font-medium">
                    {formatCurrency(asset.totalValue)}
                  </td>
                  <td className={`py-4 px-4 text-right font-mono font-medium ${asset.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    <div className="flex items-center justify-end">
                      {asset.pnl >= 0 ? <ArrowUpRight className="h-4 w-4 mr-1" /> : <ArrowDownRight className="h-4 w-4 mr-1" />}
                      <div>
                        <div>{formatCurrency(Math.abs(asset.pnl))}</div>
                        <div className="text-xs">{formatPercentage(asset.pnlPercentage)}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-4 text-right">
                    <div className="flex items-center justify-end space-x-2">
                      <div className="w-16 bg-gray-700 rounded-full h-2">
                        <div 
                          className="bg-gradient-to-r from-blue-500 to-teal-500 h-2 rounded-full" 
                          style={{ width: `${asset.allocation}%` }}
                        ></div>
                      </div>
                      <span className="text-sm font-mono text-white">{asset.allocation.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="py-4 px-4 text-right">
                    <div className="flex items-center justify-end space-x-1">
                      <Button size="sm" className="text-xs bg-emerald-600 hover:bg-emerald-700">
                        Buy
                      </Button>
                      <Button size="sm" variant="secondary" className="text-xs bg-red-600 hover:bg-red-700">
                        Sell
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* AI Insights Panel */}
      <Card glassy className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/20">
        <div className="flex items-center space-x-3 mb-4">
          <div className="p-3 bg-gradient-to-r from-purple-500/20 to-blue-500/20 rounded-xl">
            <Zap className="h-6 w-6 text-purple-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">AI Portfolio Insights</h3>
            <p className="text-sm text-gray-400">Powered by Seamount Analytics Engine</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-800/30 rounded-lg p-4">
            <h4 className="font-medium text-white mb-2">Risk Assessment</h4>
            <p className="text-sm text-gray-300">
              Your portfolio shows moderate risk with good diversification across crypto and traditional assets. 
              Consider rebalancing if BTC allocation exceeds 50%.
            </p>
          </div>
          <div className="bg-gray-800/30 rounded-lg p-4">
            <h4 className="font-medium text-white mb-2">Optimization Suggestion</h4>
            <p className="text-sm text-gray-300">
              Based on current market trends, consider increasing exposure to AI-focused equities. 
              USDS provides good stability as a base currency.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Portfolio;