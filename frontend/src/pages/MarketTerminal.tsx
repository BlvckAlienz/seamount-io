import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface MarketData {
  crypto: Record<string, number>;
  forex: Record<string, number>;
  commodities: Record<string, number>;
  cross_rates: Record<string, number>;
  timestamp: string;
}

const MarketTerminal: React.FC = () => {
  const [marketData, setMarketData] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Fetch market snapshot
  const fetchMarketData = async () => {
    try {
      setLoading(true);
      const response = await axios.get('http://localhost:8000/api/v1/market/snapshot');
      
      if (response.data.success) {
        setMarketData(response.data.data);
        setLastUpdate(new Date());
        setError(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch market data');
    } finally {
      setLoading(false);
    }
  };

  // Auto-refresh every 30 seconds
  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 30000); // 30s refresh
    return () => clearInterval(interval);
  }, []);

  if (loading && !marketData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading market data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <h3 className="text-red-800 font-semibold mb-2">⚠️ Connection Error</h3>
          <p className="text-red-600">{error}</p>
          <button 
            onClick={fetchMarketData}
            className="mt-4 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">🏦 Seamount Market Terminal</h1>
          <p className="text-gray-400 mt-1">
            Bloomberg-Grade Real-Time Market Data
          </p>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-400">Last Updated</div>
          <div className="text-lg font-mono">
            {lastUpdate?.toLocaleTimeString()}
          </div>
          <button
            onClick={fetchMarketData}
            disabled={loading}
            className="mt-2 bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '⟳ Refreshing...' : '🔄 Refresh Now'}
          </button>
        </div>
      </div>

      {/* Crypto Assets */}
      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-3 flex items-center">
          <span className="mr-2">💰</span> Cryptocurrencies
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {marketData?.crypto && Object.entries(marketData.crypto).map(([asset, price]) => (
            <div key={asset} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="text-gray-400 text-sm uppercase">{asset}</div>
              <div className="text-2xl font-bold mt-1">
                ${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className="text-green-400 text-sm mt-1">● Live</div>
            </div>
          ))}
        </div>
      </section>

      {/* Precious Metals */}
      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-3 flex items-center">
          <span className="mr-2">🏆</span> Precious Metals
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {marketData?.commodities && ['XAU', 'XAG', 'XPT', 'XPD'].map((symbol) => (
            <div key={symbol} className="bg-gradient-to-br from-yellow-900/30 to-gray-800 rounded-lg p-4 border border-yellow-700/50">
              <div className="text-yellow-400 text-sm font-semibold">
                {symbol === 'XAU' ? 'GOLD' : symbol === 'XAG' ? 'SILVER' : symbol === 'XPT' ? 'PLATINUM' : 'PALLADIUM'}
              </div>
              <div className="text-2xl font-bold mt-1">
                ${marketData.commodities[symbol].toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-gray-400 mt-1">per troy ounce</div>
              <div className="text-green-400 text-sm mt-1">● Live (Metals.dev)</div>
            </div>
          ))}
        </div>
      </section>

      {/* Industrial Metals */}
      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-3 flex items-center">
          <span className="mr-2">⚙️</span> Industrial Metals
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {marketData?.commodities && ['COPP', 'ALUM', 'NICK', 'ZINC'].map((symbol) => {
            const names = { COPP: 'Copper', ALUM: 'Aluminum', NICK: 'Nickel', ZINC: 'Zinc' };
            const isLive = ['COPP', 'ALUM'].includes(symbol);
            
            return (
              <div key={symbol} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div className="text-gray-400 text-sm font-semibold">{names[symbol as keyof typeof names]}</div>
                <div className="text-2xl font-bold mt-1">
                  ${marketData.commodities[symbol].toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </div>
                <div className="text-xs text-gray-400 mt-1">per metric ton</div>
                <div className={`text-sm mt-1 ${isLive ? 'text-green-400' : 'text-yellow-400'}`}>
                  {isLive ? '● Live (Yahoo Finance)' : '◐ Daily (LME Reference)'}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Critical Minerals */}
      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-3 flex items-center">
          <span className="mr-2">🔋</span> Critical Minerals (Battery Metals)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          {marketData?.commodities && ['LITH', 'COBT', 'MANG', 'GRPH', 'TANT'].map((symbol) => {
            const names = { LITH: 'Lithium', COBT: 'Cobalt', MANG: 'Manganese', GRPH: 'Graphite', TANT: 'Tantalum' };
            
            return (
              <div key={symbol} className="bg-gradient-to-br from-purple-900/30 to-gray-800 rounded-lg p-4 border border-purple-700/50">
                <div className="text-purple-400 text-sm font-semibold">{names[symbol as keyof typeof names]}</div>
                <div className="text-xl font-bold mt-1">
                  ${marketData.commodities[symbol].toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </div>
                <div className="text-xs text-gray-400 mt-1">per metric ton</div>
                <div className="text-gray-400 text-sm mt-1">◐ Market Reference</div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Forex Rates */}
      <section className="mb-6">
        <h2 className="text-xl font-semibold mb-3 flex items-center">
          <span className="mr-2">🌍</span> African Forex Rates
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {marketData?.forex && ['NGN/USD', 'KES/USD', 'ZAR/USD', 'GHS/USD', 'ETB/USD', 'EGP/USD'].map((pair) => (
            <div key={pair} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
              <div className="text-gray-400 text-sm font-semibold">{pair}</div>
              <div className="text-2xl font-bold mt-1">
                {marketData.forex[pair].toFixed(6)}
              </div>
              <div className="text-green-400 text-sm mt-1">● Live</div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="mt-8 pt-6 border-t border-gray-700 text-center text-gray-400 text-sm">
        <p>
          Powered by <span className="font-semibold text-white">Seamount.io</span> | 
          Data Sources: Metals.dev, Yahoo Finance, LME References
        </p>
        <p className="mt-2">
          ● Live = Real-time or 60s delay | ◐ Daily = LME daily reference | Market Reference = Latest available pricing
        </p>
      </footer>
    </div>
  );
};

export default MarketTerminal;