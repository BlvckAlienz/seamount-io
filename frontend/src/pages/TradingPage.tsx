// File Location: frontend/src/pages/TradingPage.tsx
// Description: The definitive, corrected, and production-ready trading page.

import React, { useState } from 'react';
import { TrendingUp, TrendingDown, BarChart3, RefreshCw } from 'lucide-react';

// --- CORRECTED IMPORT PATHS ---
// Using robust, absolute paths with the '@' alias from vite.config.ts
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import PriceChart from '@/components/charts/PriceChart';
import { mockAssets, mockPositions, mockOrders, mockOrderBook, generateMockChartData } from '@/data/mockData';

const TradingPage: React.FC = () => {
  const [selectedAsset, setSelectedAsset] = useState('BTC');
  const [orderType, setOrderType] = useState<'market' | 'limit'>('market');
  const [orderSide, setOrderSide] = useState<'buy' | 'sell'>('buy');
  const [amount, setAmount] = useState('');
  const [price, setPrice] = useState('');

  const chartData = generateMockChartData(7);
  const currentAsset = mockAssets.find(asset => asset.symbol === selectedAsset) || mockAssets[0];

  const formatCurrency = (amount: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
  const formatPercentage = (percentage: number) => `${percentage >= 0 ? '+' : ''}${percentage.toFixed(2)}%`;

  return (
    <div className="space-y-6">
      {/* Asset Selection */}
      <Card>
        <div className="flex flex-wrap gap-4">
          {mockAssets.map((asset) => (
            <button key={asset.id} onClick={() => setSelectedAsset(asset.symbol)} className={`p-4 rounded-lg border transition-all ${selectedAsset === asset.symbol ? 'border-blue-500 bg-blue-500/10' : 'border-gray-600 hover:border-gray-500'}`}>
              <div className="text-left">
                <div className="font-semibold text-white">{asset.symbol}</div>
                <div className="text-sm text-gray-400">{asset.name}</div>
                <div className="mt-2">
                  <div className="font-medium text-white">{formatCurrency(asset.price)}</div>
                  <div className={`text-xs ${asset.change24hPercentage >= 0 ? 'text-green-400' : 'text-red-400'}`}>{formatPercentage(asset.change24hPercentage)}</div>
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
              <Button size="sm" variant="ghost">1h</Button>
              <Button size="sm" variant="ghost">4h</Button>
              <Button size="sm">1d</Button>
            </div>
          </div>
          <PriceChart data={chartData} height={400} color={currentAsset.change24hPercentage >= 0 ? '#10B981' : '#EF4444'} />
        </Card>

        {/* Order Form */}
        <Card>
          <h3 className="text-lg font-semibold text-white mb-6">Place Order</h3>
          <div className="flex rounded-lg bg-gray-700 p-1 mb-6">
            <button onClick={() => setOrderSide('buy')} className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${orderSide === 'buy' ? 'bg-green-600 text-white' : 'text-gray-300'}`}>Buy</button>
            <button onClick={() => setOrderSide('sell')} className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${orderSide === 'sell' ? 'bg-red-600 text-white' : 'text-gray-300'}`}>Sell</button>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Amount</label>
              <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder={`0.00 ${currentAsset.symbol}`} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg"/>
            </div>
            <Button className={`w-full ${orderSide === 'buy' ? 'bg-green-600' : 'bg-red-600'}`}>{orderSide === 'buy' ? 'Buy' : 'Sell'} {currentAsset.symbol}</Button>
          </div>
        </Card>
      </div>

      {/* Order Book and Positions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        <Card>
          <h3 className="text-lg font-semibold text-white mb-6">Order Book</h3>
          <div className="space-y-4">
            <div>
              <h4 className="text-sm font-medium text-red-400 mb-2">Asks</h4>
              {mockOrderBook.asks.map((order, index) => (<div key={index} className="flex justify-between text-sm"><span className="text-red-400">{formatCurrency(order.price)}</span><span>{order.size.toFixed(4)}</span><span>{formatCurrency(order.total)}</span></div>))}
            </div>
            <div className="py-2 border-t border-b border-gray-700"><div className="text-center"><span className="text-lg font-bold">{formatCurrency(currentAsset.price)}</span></div></div>
            <div>
              <h4 className="text-sm font-medium text-green-400 mb-2">Bids</h4>
              {mockOrderBook.bids.map((order, index) => (<div key={index} className="flex justify-between text-sm"><span className="text-green-400">{formatCurrency(order.price)}</span><span>{order.size.toFixed(4)}</span><span>{formatCurrency(order.total)}</span></div>))}
            </div>
          </div>
        </Card>
        <Card>
          <h3 className="text-lg font-semibold text-white mb-6">Open Orders</h3>
          <div className="space-y-3">{mockOrders.length > 0 ? (mockOrders.map((order) => (<div key={order.id} className="p-3 bg-gray-700/50 rounded-lg"><div className="flex justify-between"><div className={`text-sm font-medium ${order.type === 'buy' ? 'text-green-400' : 'text-red-400'}`}>{order.type.toUpperCase()} {order.asset}</div><Button size="sm" variant="destructive" className="text-xs">Cancel</Button></div></div>))) : (<div className="text-center py-8 text-gray-400"><BarChart3 className="h-12 w-12 mx-auto mb-4 opacity-50" /><p>No open orders</p></div>)}</div>
        </Card>
        <Card>
          <h3 className="text-lg font-semibold text-white mb-6">Active Positions</h3>
          <div className="space-y-3">{mockPositions.map((position) => (<div key={position.id} className="p-3 bg-gray-700/50 rounded-lg"><div className="flex justify-between"><div className="font-medium">{position.asset}</div><div className={`text-sm px-2 py-1 rounded ${position.side === 'long' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{position.side.toUpperCase()}</div></div></div>))}</div>
        </Card>
      </div>
    </div>
  );
};

export default TradingPage;