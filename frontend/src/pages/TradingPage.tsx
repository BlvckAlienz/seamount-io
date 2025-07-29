import React, { useState } from 'react';
import { TrendingUp, TrendingDown, BarChart3, Activity, RefreshCw } from 'lucide-react';
import Card from '../components/Card';
import Button from '../components/Button';
import PriceChart from '../components/PriceChart';
import { mockAssets, mockPositions, mockOrders, mockOrderBook, generateMockChartData } from '../data/mockData';

const Trading: React.FC = () => {
  const [selectedAsset, setSelectedAsset] = useState('BTC');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [amount, setAmount] = useState('');
  const [price, setPrice] = useState('');

  const chartData = generateMockChartData(7);
  const currentAsset = mockAssets.find(asset => asset.symbol === selectedAsset) || mockAssets[0];

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

  return (
    <div className="space-y-6">
      {/* Asset Selection */}
      <Card>
        <div className="flex flex-wrap gap-4">
          {mockAssets.map((asset) => (
            <button
              key={asset.id}
              onClick={() => setSelectedAsset(asset.symbol)}
              className={`p-4 rounded-lg border transition-all ${
                selectedAsset === asset.symbol
                  ? 'border-blue-500 bg-blue-500/10'
                  : 'border-gray-600 hover:border-gray-500'
              }`}
            >
              <div className="text-left">
                <div className="font-semibold text-white">{asset.symbol}</div>
                <div className="text-sm text-gray-400">{asset.name}</div>
                <div className="mt-2">
                  <div className="font-medium text-white">{formatCurrency(asset.price)}</div>
                  <div className={`text-xs ${asset.change24hPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatPercentage(asset.change24hPercentage)}
                  </div>
                </div>
              </div>
            </button>
          ))}
        </div>
      </Card>

      {/* Main Trading Interface */}
      <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
        {/* Chart */}
        <Card className="xl:col-span-3">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-white">{currentAsset.symbol}/USD</h2>
              <div className="flex items-center space-x-4 mt-2">
                <span className="text-2xl font-bold text-white">{formatCurrency(currentAsset.price)}</span>
                <div className={`flex items-center ${currentAsset.change24hPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {currentAsset.change24hPercentage >= 0 ? <TrendingUp className="h-5 w-5 mr-1" /> : <TrendingDown className="h-5 w-5 mr-1" />}
                  {formatCurrency(Math.abs(currentAsset.change24h))} ({formatPercentage(currentAsset.change24hPercentage)})
                </div>
              </div>
            </div>
            <div className="flex space-x-2">
              <Button size="sm" variant="ghost">5m</Button>
              <Button size="sm" variant="ghost">15m</Button>
              <Button size="sm">1h</Button>
              <Button size="sm" variant="ghost">4h</Button>
              <Button size="sm" variant="ghost">1d</Button>
            </div>
          </div>
          <PriceChart data={chartData} height={400} color={currentAsset.change24hPercentage >= 0 ? '#10B981' : '#EF4444'} />
        </Card>

        {/* Order Form */}
        <Card>
          <h3 className="text-lg font-semibold text-white mb-6">Place Order</h3>
          
          {/* Order Side */}
          <div className="flex rounded-lg bg-gray-700 p-1 mb-6">
            <button
              onClick={() => setOrderSide('buy')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                orderSide === 'buy' ? 'bg-green-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              Buy
            </button>
            <button
              onClick={() => setOrderSide('sell')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                orderSide === 'sell' ? 'bg-red-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              Sell
            </button>
          </div>

          {/* Order Type */}
          <div className="flex rounded-lg bg-gray-700 p-1 mb-6">
            <button
              onClick={() => setOrderType('market')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                orderType === 'market' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              Market
            </button>
            <button
              onClick={() => setOrderType('limit')}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                orderType === 'limit' ? 'bg-blue-600 text-white' : 'text-gray-300 hover:text-white'
              }`}
            >
              Limit
            </button>
          </div>

          {/* Order Inputs */}
          <div className="space-y-4">
            {orderType === 'limit' && (
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Price</label>
                <input
                  type="number"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder={formatCurrency(currentAsset.price)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Amount</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder={`0.00 ${currentAsset.symbol}`}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex space-x-2">
              <button className="flex-1 py-2 px-3 text-xs bg-gray-700 hover:bg-gray-600 rounded text-gray-300">25%</button>
              <button className="flex-1 py-2 px-3 text-xs bg-gray-700 hover:bg-gray-600 rounded text-gray-300">50%</button>
              <button className="flex-1 py-2 px-3 text-xs bg-gray-700 hover:bg-gray-600 rounded text-gray-300">75%</button>
              <button className="flex-1 py-2 px-3 text-xs bg-gray-700 hover:bg-gray-600 rounded text-gray-300">Max</button>
            </div>

            <Button 
              className={`w-full ${orderSide === 'buy' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}`}
            >
              {orderSide === 'buy' ? 'Buy' : 'Sell'} {currentAsset.symbol}
            </Button>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-700">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Available Balance</span>
              <span className="text-white">{formatCurrency(15420.50)}</span>
            </div>
            <div className="flex justify-between text-sm mt-2">
              <span className="text-gray-400">Est. Total</span>
              <span className="text-white">{formatCurrency(0)}</span>
            </div>
          </div>
        </Card>
      </div>

      {/* Order Book and Positions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* Order Book */}
        <Card>
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-white">Order Book</h3>
            <Button size="sm" variant="ghost" icon={RefreshCw}>
              Refresh
            </Button>
          </div>
          
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-red-400 mb-2">Asks (Sell Orders)</h4>
              <div className="space-y-1">
                {mockOrderBook.asks.map((order, index) => (
                  <div key={index} className="flex justify-between text-sm">
                    <span className="text-red-400">{formatCurrency(order.price)}</span>
                    <span className="text-white">{order.size.toFixed(4)}</span>
                    <span className="text-gray-400">{formatCurrency(order.total)}</span>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="py-2 border-t border-b border-gray-700">
              <div className="text-center">
                <span className="text-lg font-bold text-white">{formatCurrency(currentAsset.price)}</span>
                <div className={`text-sm ${currentAsset.change24hPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercentage(currentAsset.change24hPercentage)}
                </div>
              </div>
            </div>
            
            <div>
              <h4 className="text-sm font-medium text-green-400 mb-2">Bids (Buy Orders)</h4>
              <div className="space-y-1">
                {mockOrderBook.bids.map((order, index) => (
                  <div key={index} className="flex justify-between text-sm">
                    <span className="text-green-400">{formatCurrency(order.price)}</span>
                    <span className="text-white">{order.size.toFixed(4)}</span>
                    <span className="text-gray-400">{formatCurrency(order.total)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Open Orders */}
        <Card>
          <h3 className="text-lg font-semibold text-white mb-6">Open Orders</h3>
          <div className="space-y-3">
            {mockOrders.length > 0 ? (
              mockOrders.map((order) => (
                <div key={order.id} className="p-3 bg-gray-700/50 rounded-lg">
                  <div className="flex justify-between items-start mb-2">
                    <div className={`text-sm font-medium ${order.type === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                      {order.type.toUpperCase()} {order.asset}
                    </div>
                    <div className="text-xs text-gray-400">{order.orderType}</div>
                  </div>
                  <div className="text-sm text-white">
                    {order.amount} @ {formatCurrency(order.price)}
                  </div>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-xs text-gray-400">
                      Filled: {((order.filled / order.amount) * 100).toFixed(1)}%
                    </span>
                    <Button size="sm" variant="danger" className="text-xs">
                      Cancel
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-8 text-gray-400">
                <BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No open orders</p>
              </div>
            )}
          </div>
        </Card>

        {/* Active Positions */}
        <Card>
          <h3 className="text-lg font-semibold text-white mb-6">Active Positions</h3>
          <div className="space-y-3">
            {mockPositions.map((position) => (
              <div key={position.id} className="p-3 bg-gray-700/50 rounded-lg">
                <div className="flex justify-between items-start mb-2">
                  <div className="font-medium text-white">{position.asset}</div>
                  <div className={`text-sm px-2 py-1 rounded ${
                    position.side === 'long' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {position.side.toUpperCase()}
                  </div>
                </div>
                <div className="text-sm text-gray-300 mb-2">
                  Size: {position.size} | {position.leverage}x
                </div>
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-xs text-gray-400">Entry: {formatCurrency(position.entryPrice)}</div>
                    <div className="text-xs text-gray-400">Mark: {formatCurrency(position.markPrice)}</div>
                  </div>
                  <div className="text-right">
                    <div className={`font-medium ${position.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatCurrency(position.pnl)}
                    </div>
                    <div className={`text-xs ${position.pnlPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {formatPercentage(position.pnlPercentage)}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Trading;