// File: frontend/src/components/market/MarketTerminalModal.tsx
// 🏦 Bloomberg-Grade Market Terminal Modal

import React, { useState, useEffect } from 'react';
import { X, TrendingUp, RefreshCw, Activity, ChevronDown } from 'lucide-react';
import { apiClient } from '@/config/api';
import toast from 'react-hot-toast';

import PriceChangeIndicator from './PriceChangeIndicator';
import SparklineChart from './SparklineChart';
import { Sparklines, SparklinesLine } from 'react-sparklines';

interface MarketData {
  crypto: Record<string, number>;
  forex: Record<string, number>;
  commodities: Record<string, number>;
  cross_rates: Record<string, number>;
  timestamp: string;
}

interface MarketTerminalModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const MarketTerminalModal: React.FC<MarketTerminalModalProps> = ({ isOpen, onClose }) => {
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [activeTab, setActiveTab] = useState<'precious' | 'industrial' | 'critical' | 'crypto' | 'forex'>('precious');

  // 📍 Fetch market snapshot
  const fetchMarketData = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/api/v1/market/snapshot');
      
      if (response.data.success) {
        setMarketData(response.data.data);
        setLastUpdate(new Date());
      }
    } catch (error: any) {
      console.error('Market data fetch failed:', error);
      toast.error('Failed to load market data');
    } finally {
      setLoading(false);
    }
  };

  // 📍 Auto-refresh every 30 seconds when modal is open
  useEffect(() => {
    if (isOpen) {
      fetchMarketData();
      const interval = setInterval(fetchMarketData, 30000); // 30s
      return () => clearInterval(interval);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-2 sm:p-4">
      <div className="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl max-w-7xl w-full max-h-[92vh] overflow-hidden border border-blue-500/30 shadow-2xl">
        
        {/* 📍 HEADER */}
        <div className="flex items-center justify-between p-4 sm:p-6 border-b border-gray-700 bg-gradient-to-r from-blue-900/30 to-purple-900/30">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-white flex items-center gap-2">
              <TrendingUp className="h-6 w-6 text-blue-400" />
              Market Terminal
            </h2>
            <p className="text-gray-400 text-sm sm:text-base">Bloomberg-Grade Live Market Data</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Last Update */}
            <div className="hidden sm:block text-right">
              <div className="text-xs text-gray-400">Last Updated</div>
              <div className="text-sm font-mono text-white">
                {lastUpdate?.toLocaleTimeString()}
              </div>
            </div>
            
            {/* Refresh Button */}
            <button
              onClick={fetchMarketData}
              disabled={loading}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white disabled:opacity-50"
              title="Refresh market data"
            >
              <RefreshCw className={`h-5 w-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            
            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
            >
              <X className="h-5 w-5 sm:h-6 sm:w-6" />
            </button>
          </div>
        </div>

        {/* 📍 TABS */}
        <div className="flex gap-2 p-4 border-b border-gray-700 overflow-x-auto">
          {[
            { id: 'precious', label: '🏆 Precious Metals', icon: '🏆' },
            { id: 'industrial', label: '⚙️ Industrial', icon: '⚙️' },
            { id: 'critical', label: '🔋 Battery Metals', icon: '🔋' },
            { id: 'crypto', label: '💰 Crypto', icon: '💰' },
            { id: 'forex', label: '🌍 Forex', icon: '🌍' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.icon}</span>
            </button>
          ))}
        </div>

        {/* 📍 CONTENT */}
        <div className="p-4 sm:p-6 overflow-auto max-h-[calc(92vh-200px)]">
          {loading && !marketData ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-4 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-400">Loading market data...</p>
              </div>
            </div>
          ) : (
            <>
              {/* 🏆 PRECIOUS METALS TAB */}
              {activeTab === 'precious' && marketData && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {['XAU', 'XAG', 'XPT', 'XPD'].map(symbol => {
                    const names = { XAU: 'Gold', XAG: 'Silver', XPT: 'Platinum', XPD: 'Palladium' };
                    const price = marketData.commodities[symbol];
                    
                    return (
                      <div key={symbol} className="bg-gradient-to-br from-yellow-900/30 to-gray-800 rounded-xl p-4 border border-yellow-700/50 hover:shadow-lg hover:shadow-yellow-500/20 transition-all">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-yellow-400 font-bold">{names[symbol as keyof typeof names]}</div>
                          <div className="flex items-center gap-1 text-green-400 text-xs">
                            <Activity className="h-3 w-3" />
                            Live
                          </div>
                        </div>
                        
                        {/* Price */}
                        <div className="text-3xl font-bold text-white mb-1">
                          ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        
                        {/* 📍 NEW: 24h Change */}
                        <PriceChangeIndicator symbol={symbol} />
                        
                        {/* 📍 NEW: Sparkline Chart */}
                        <SparklineChart symbol={symbol} />
                        
                        <div className="text-xs text-gray-400">per troy ounce</div>
                        <div className="text-xs text-gray-500 mt-2">Source: Metals.dev</div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* ⚙️ INDUSTRIAL METALS TAB */}
              {activeTab === 'industrial' && marketData && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {['COPP', 'ALUM', 'NICK', 'ZINC'].map(symbol => {
                    const names = { COPP: 'Copper', ALUM: 'Aluminum', NICK: 'Nickel', ZINC: 'Zinc' };
                    const isLive = ['COPP', 'ALUM'].includes(symbol);
                    const price = marketData.commodities[symbol];
                    
                    return (
                      <div key={symbol} className="bg-gray-800 rounded-xl p-4 border border-gray-700 hover:border-blue-500/50 hover:shadow-lg transition-all">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-gray-300 font-bold">{names[symbol as keyof typeof names]}</div>
                          <div className={`flex items-center gap-1 text-xs ${isLive ? 'text-green-400' : 'text-yellow-400'}`}>
                            {isLive ? <Activity className="h-3 w-3" /> : '◐'}
                            {isLive ? 'Live' : 'Daily'}
                          </div>
                        </div>
                        <div className="text-3xl font-bold text-white mb-1">
                          ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className="text-xs text-gray-400">per metric ton</div>
                        <div className="text-xs text-gray-500 mt-2">
                          {isLive ? 'Source: Yahoo Finance' : 'Source: LME Reference'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* 🔋 CRITICAL MINERALS TAB */}
              {activeTab === 'critical' && marketData && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                  {['LITH', 'COBT', 'MANG', 'GRPH', 'TANT'].map(symbol => {
                    const names = { LITH: 'Lithium', COBT: 'Cobalt', MANG: 'Manganese', GRPH: 'Graphite', TANT: 'Tantalum' };
                    const price = marketData.commodities[symbol];
                    
                    return (
                      <div key={symbol} className="bg-gradient-to-br from-purple-900/30 to-gray-800 rounded-xl p-4 border border-purple-700/50 hover:shadow-lg hover:shadow-purple-500/20 transition-all">
                        <div className="text-purple-400 font-bold mb-2">{names[symbol as keyof typeof names]}</div>
                        <div className="text-2xl font-bold text-white mb-1">
                          ${price.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </div>
                        <div className="text-xs text-gray-400">per metric ton</div>
                        <div className="text-xs text-gray-500 mt-2">Market Reference</div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* 💰 CRYPTO TAB */}
              {activeTab === 'crypto' && marketData && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {Object.entries(marketData.crypto).map(([asset, price]) => (
                    <div key={asset} className="bg-gradient-to-br from-blue-900/30 to-gray-800 rounded-xl p-4 border border-blue-700/50 hover:shadow-lg hover:shadow-blue-500/20 transition-all">
                      <div className="flex items-center justify-between mb-2">
                        <div className="text-blue-400 font-bold uppercase">{asset}</div>
                        <div className="flex items-center gap-1 text-green-400 text-xs">
                          <Activity className="h-3 w-3 animate-pulse" />
                          Live
                        </div>
                      </div>
                      <div className="text-3xl font-bold text-white mb-1">
                        ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </div>
                      <div className="text-xs text-gray-500 mt-2">Source: Live Markets</div>
                    </div>
                  ))}
                </div>
              )}

              {/* 🌍 FOREX TAB */}
              {activeTab === 'forex' && marketData && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {['NGN/USD', 'KES/USD', 'ZAR/USD', 'GHS/USD', 'ETB/USD', 'EGP/USD'].map(pair => {
                    const rate = marketData.forex[pair];
                    const inversePair = pair.split('/').reverse().join('/');
                    const inverseRate = marketData.forex[inversePair];
                    
                    return (
                      <div key={pair} className="bg-gray-800 rounded-xl p-4 border border-gray-700 hover:border-green-500/50 hover:shadow-lg transition-all">
                        <div className="flex items-center justify-between mb-2">
                          <div className="text-gray-300 font-bold">{pair}</div>
                          <div className="flex items-center gap-1 text-green-400 text-xs">
                            <Activity className="h-3 w-3" />
                            Live
                          </div>
                        </div>
                        <div className="text-2xl font-bold text-white mb-1">
                          {rate.toFixed(6)}
                        </div>
                        <div className="text-sm text-gray-400 mt-2">
                          {inversePair}: {inverseRate.toFixed(2)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )}
        </div>

        {/* 📍 FOOTER */}
        <div className="border-t border-gray-700 p-4 bg-gray-800/50">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-gray-400">
            <div>
              Powered by <span className="font-semibold text-white">Seamount.io</span> | 
              Bloomberg-Grade Market Data
            </div>
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Activity className="h-3 w-3 text-green-400" />
                Live = Real-time or 60s delay
              </span>
              <span>◐ Daily = LME Reference</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketTerminalModal;