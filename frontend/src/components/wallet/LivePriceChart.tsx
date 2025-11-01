// File: frontend/src/components/wallet/LivePriceChart.tsx
// 📊 FREE: Live price charts using Binance public API

import React, { useEffect, useRef, useState } from 'react';
import { TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';

interface PriceChartProps {
  symbol: string; // e.g., "BTC", "ETH", "ALGO"
  timeframe?: '1h' | '24h' | '7d' | '30d';
}

interface CandleData {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

const LivePriceChart: React.FC<PriceChartProps> = ({ symbol, timeframe = '24h' }) => {
  const [chartData, setChartData] = useState<CandleData[]>([]);
  const [loading, setLoading] = useState(true);
  const [priceChange, setPriceChange] = useState<{ value: number; percent: number } | null>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  // Symbol mapping to Binance pairs
  const getBinanceSymbol = (sym: string): string => {
    const mapping: { [key: string]: string } = {
      'BTC': 'BTCUSDT',
      'ETH': 'ETHUSDT',
      'ALGO': 'ALGOUSDT',
      'MATIC': 'MATICUSDT',
      'TRX': 'TRXUSDT',
      'USDT': 'USDCUSDT',
      'USDC': 'USDCUSDT'
    };
    return mapping[sym] || 'BTCUSDT';
  };

  // Timeframe to Binance interval
  const getInterval = (): string => {
    switch (timeframe) {
      case '1h': return '1m';
      case '24h': return '15m';
      case '7d': return '1h';
      case '30d': return '4h';
      default: return '15m';
    }
  };

  const getLimit = (): number => {
    switch (timeframe) {
      case '1h': return 60;
      case '24h': return 96;
      case '7d': return 168;
      case '30d': return 180;
      default: return 96;
    }
  };

  const fetchChartData = async () => {
    try {
      setLoading(true);
      const binanceSymbol = getBinanceSymbol(symbol);
      const interval = getInterval();
      const limit = getLimit();

      const response = await fetch(
        `https://api.binance.com/api/v3/klines?symbol=${binanceSymbol}&interval=${interval}&limit=${limit}`
      );

      if (!response.ok) throw new Error('Failed to fetch chart data');

      const data = await response.json();
      
      const candles: CandleData[] = data.map((candle: any[]) => ({
        time: candle[0] / 1000, // Convert to seconds
        open: parseFloat(candle[1]),
        high: parseFloat(candle[2]),
        low: parseFloat(candle[3]),
        close: parseFloat(candle[4]),
        volume: parseFloat(candle[5])
      }));

      setChartData(candles);

      // Calculate price change
      if (candles.length > 0) {
        const firstPrice = candles[0].open;
        const lastPrice = candles[candles.length - 1].close;
        const change = lastPrice - firstPrice;
        const percentChange = (change / firstPrice) * 100;
        setPriceChange({ value: change, percent: percentChange });
      }
    } catch (error) {
      console.error('Chart data fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChartData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchChartData, 30000);
    return () => clearInterval(interval);
  }, [symbol, timeframe]);

  // Simple SVG line chart
  const renderChart = () => {
    if (chartData.length === 0) return null;

    const width = 600;
    const height = 300;
    const padding = 40;

    const prices = chartData.map(d => d.close);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice;

    // Generate path points
    const points = chartData.map((data, i) => {
      const x = padding + (i / (chartData.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((data.close - minPrice) / priceRange) * (height - 2 * padding);
      return `${x},${y}`;
    }).join(' ');

    const isPositive = priceChange && priceChange.value >= 0;
    const lineColor = isPositive ? '#10b981' : '#ef4444';
    const fillColor = isPositive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)';

    return (
      <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="w-full h-full">
        {/* Grid lines */}
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#374151" strokeWidth="1" />
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#374151" strokeWidth="1" />
        
        {/* Area fill */}
        <polygon
          points={`${padding},${height - padding} ${points} ${width - padding},${height - padding}`}
          fill={fillColor}
        />
        
        {/* Price line */}
        <polyline
          points={points}
          fill="none"
          stroke={lineColor}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        
        {/* Current price marker */}
        <circle
          cx={width - padding}
          cy={height - padding - ((prices[prices.length - 1] - minPrice) / priceRange) * (height - 2 * padding)}
          r="4"
          fill={lineColor}
          stroke="white"
          strokeWidth="2"
        />
        
        {/* Price labels */}
        <text x={padding - 5} y={padding} fill="#9ca3af" fontSize="12" textAnchor="end">
          ${maxPrice.toFixed(2)}
        </text>
        <text x={padding - 5} y={height - padding} fill="#9ca3af" fontSize="12" textAnchor="end">
          ${minPrice.toFixed(2)}
        </text>
      </svg>
    );
  };

  if (loading) {
    return (
      <div className="bg-gray-800/50 rounded-xl p-6 h-80 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading chart...</p>
        </div>
      </div>
    );
  }

  const isPositive = priceChange && priceChange.value >= 0;

  return (
    <div className="bg-gray-800/50 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-bold text-white">{symbol} Price Chart</h3>
          {priceChange && (
            <div className={`flex items-center gap-2 px-3 py-1 rounded-lg ${
              isPositive ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
            }`}>
              {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              <span className="font-semibold">
                {isPositive ? '+' : ''}{priceChange.percent.toFixed(2)}%
              </span>
            </div>
          )}
        </div>
        <button
          onClick={fetchChartData}
          className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
          title="Refresh chart"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Timeframe selector */}
      <div className="flex items-center gap-2 mb-4">
        {(['1h', '24h', '7d', '30d'] as const).map((tf) => (
          <button
            key={tf}
            onClick={() => window.location.reload()} // Simple reload for now
            className={`px-3 py-1 rounded-lg text-sm font-medium transition-colors ${
              timeframe === tf
                ? 'bg-blue-600 text-white'
                : 'bg-gray-700 text-gray-400 hover:bg-gray-600'
            }`}
          >
            {tf}
          </button>
        ))}
      </div>

      {/* Chart */}
      <div ref={chartContainerRef} className="h-64 w-full">
        {renderChart()}
      </div>

      {/* Stats */}
      {chartData.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-700">
          <div>
            <p className="text-gray-400 text-xs mb-1">High</p>
            <p className="text-white font-semibold">
              ${Math.max(...chartData.map(d => d.high)).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-xs mb-1">Low</p>
            <p className="text-white font-semibold">
              ${Math.min(...chartData.map(d => d.low)).toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-xs mb-1">Volume</p>
            <p className="text-white font-semibold">
              ${(chartData.reduce((sum, d) => sum + d.volume, 0) / 1000000).toFixed(2)}M
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default LivePriceChart;