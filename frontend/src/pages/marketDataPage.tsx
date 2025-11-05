import React from 'react';
import { TrendingUp, DollarSign, Activity } from 'lucide-react';

const MarketDataPage: React.FC = () => {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Market Data</h1>
        <p className="text-gray-400">Real-time cryptocurrency market information</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <span className="text-gray-400">Total Market Cap</span>
            <TrendingUp className="h-5 w-5 text-green-500" />
          </div>
          <p className="text-2xl font-bold text-white">$2.1T</p>
          <p className="text-sm text-green-500 mt-2">+2.4% 24h</p>
        </div>
        
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <span className="text-gray-400">24h Volume</span>
            <Activity className="h-5 w-5 text-blue-500" />
          </div>
          <p className="text-2xl font-bold text-white">$89.2B</p>
          <p className="text-sm text-gray-400 mt-2">Across all chains</p>
        </div>
        
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <span className="text-gray-400">BTC Dominance</span>
            <DollarSign className="h-5 w-5 text-yellow-500" />
          </div>
          <p className="text-2xl font-bold text-white">54.2%</p>
          <p className="text-sm text-gray-400 mt-2">Market share</p>
        </div>
      </div>
      
      <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
        <h2 className="text-xl font-bold text-white mb-4">Coming Soon</h2>
        <p className="text-gray-400">Advanced market analytics and trading insights are currently in development.</p>
      </div>
    </div>
  );
};

export default MarketDataPage;