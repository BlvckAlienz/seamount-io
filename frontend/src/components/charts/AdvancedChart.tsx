import React, { useState, useMemo } from 'react';
import { 
  ComposedChart, 
  CandlestickChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Area,
  AreaChart,
  ReferenceLine,
  Brush
} from 'recharts';
import { TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react';
import { ChartDataPoint } from '../types';

// --- CORRECTED IMPORT PATH ---
// Using robust, absolute path with the '@' alias from vite.config.ts
import { ChartDataPoint } from '@/types';

interface AdvancedChartProps {
  data: ChartDataPoint[];
  height?: number;
  showVolume?: boolean;
  showMA?: boolean;
  timeframe?: string;
  loading?: boolean;
}

const AdvancedChart: React.FC<AdvancedChartProps> = ({ 
  data, 
  height = 400,
  showVolume = true,
  showMA = true,
  timeframe = '1H',
  loading = false
}) => {
  const [chartType, setChartType] = useState<'candle' | 'line' | 'area'>('line');

  const processedData = useMemo(() => {
    if (!data.length) return [];
    
    return data.map((point, index) => {
      // Calculate moving averages
      const ma20 = index >= 19 ? 
        data.slice(index - 19, index + 1).reduce((sum, p) => sum + p.close, 0) / 20 : null;
      const ma50 = index >= 49 ? 
        data.slice(index - 49, index + 1).reduce((sum, p) => sum + p.close, 0) / 50 : null;

      return {
        ...point,
        timestamp: new Date(point.timestamp).toLocaleTimeString(),
        ma20,
        ma50,
        volumeMA: index >= 9 ? 
          data.slice(index - 9, index + 1).reduce((sum, p) => sum + p.volume, 0) / 10 : point.volume,
      };
    });
  }, [data]);

  const currentPrice = data[data.length - 1]?.close || 0;
  const previousPrice = data[data.length - 2]?.close || 0;
  const priceChange = currentPrice - previousPrice;
  const priceChangePercent = ((priceChange / previousPrice) * 100);

  if (loading) {
    return (
      <div className="relative" style={{ height }}>
        <div className="absolute inset-0 bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 animate-pulse rounded-lg" />
        <div className="absolute inset-0 flex items-center justify-center">
          <Activity className="h-8 w-8 text-blue-500 animate-spin" />
        </div>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-gray-900/95 backdrop-blur-md border border-gray-700 rounded-lg p-4 shadow-xl">
          <p className="text-gray-300 text-sm mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex justify-between items-center space-x-4">
              <span className="text-xs text-gray-400">{entry.name}:</span>
              <span 
                className="font-mono text-sm"
                style={{ color: entry.color }}
              >
                {entry.name === 'Volume' ? 
                  entry.value.toLocaleString() : 
                  `$${entry.value.toLocaleString()}`
                }
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="space-y-4">
      {/* Chart Controls */}
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-6">
          <div>
            <div className="text-2xl font-mono font-bold text-white">
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                ${currentPrice.toLocaleString()}
              </span>
            </div>
            <div className={`flex items-center text-sm font-medium ${priceChange >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
              {priceChange >= 0 ? <TrendingUp className="h-4 w-4 mr-1" /> : <TrendingDown className="h-4 w-4 mr-1" />}
              {priceChange >= 0 ? '+' : ''}{priceChangePercent.toFixed(2)}%
            </div>
          </div>
          
          <div className="flex space-x-1 bg-gradient-to-r from-gray-800/70 to-gray-900/70 backdrop-blur-sm rounded-lg p-1 border border-gray-700/50 shadow-inner">
            {[
              { type: 'line' as const, icon: Activity },
              { type: 'area' as const, icon: BarChart3 },
              { type: 'candle' as const, icon: TrendingUp }
            ].map(({ type, icon: Icon }) => (
              <button
                key={type}
                onClick={() => setChartType(type)}
                className={`p-2 rounded-md transition-all ${
                  chartType === type 
                    ? 'bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg' 
                    : 'text-gray-400 hover:text-white hover:bg-gray-700/70'
                }`}
              >
                <Icon className="h-4 w-4" />
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button className="text-xs px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-md transition-colors">
            MA20
            <div className="h-0.5 w-0 group-hover:w-full bg-blue-500 transition-all duration-300"></div>
          </button>
          <button className="text-xs px-3 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-md transition-colors">
            Volume
            <div className="h-0.5 w-0 group-hover:w-full bg-blue-500 transition-all duration-300"></div>
          </button>
        </div>
      </div>

      {/* Main Chart */}
      <div className="bg-gradient-to-b from-gray-900/70 to-gray-800/40 rounded-lg p-4 border border-gray-800/80 shadow-lg backdrop-blur-sm">
        <ResponsiveContainer width="100%" height={height}>
          {chartType === 'line' ? (
            <ComposedChart data={processedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="1 1" stroke="#374151" opacity={0.3} />
              <XAxis 
                dataKey="timestamp" 
                stroke="#6B7280"
                fontSize={10}
                tick={{ fill: '#6B7280' }}
              />
              <YAxis 
                stroke="#6B7280"
                fontSize={10}
                tick={{ fill: '#6B7280' }}
                domain={['dataMin * 0.999', 'dataMax * 1.001']}
              />
              <Tooltip content={<CustomTooltip />} />
              
              <Area
                type="monotone"
                dataKey="close"
                stroke="#3B82F6"
                strokeWidth={2}
                fill="url(#priceGradient)"
                name="Price"
              />
              
              {showMA && (
                <>
                  <Line
                    type="monotone"
                    dataKey="ma20"
                    stroke="#F59E0B"
                    strokeWidth={1}
                    dot={false}
                    name="MA20"
                    opacity={0.7}
                  />
                  <Line
                    type="monotone"
                    dataKey="ma50"
                    stroke="#EF4444"
                    strokeWidth={1}
                    dot={false}
                    name="MA50"
                    opacity={0.7}
                  />
                </>
              )}
            </ComposedChart>
          ) : chartType === 'area' ? (
            <AreaChart data={processedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <defs>
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10B981" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="1 1" stroke="#374151" opacity={0.3} />
              <XAxis dataKey="timestamp" stroke="#6B7280" fontSize={10} />
              <YAxis stroke="#6B7280" fontSize={10} />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="close"
                stroke="#10B981"
                strokeWidth={2}
                fill="url(#areaGradient)"
                name="Price"
              />
            </AreaChart>
          ) : (
            <ComposedChart data={processedData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="1 1" stroke="#374151" opacity={0.3} />
              <XAxis dataKey="timestamp" stroke="#6B7280" fontSize={10} />
              <YAxis stroke="#6B7280" fontSize={10} />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="close"
                stroke="#3B82F6"
                strokeWidth={2}
                dot={false}
                name="Price"
              />
            </ComposedChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Volume Chart */}
      {showVolume && (
        <div className="bg-gray-900/30 rounded-lg p-4 border border-gray-800">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Volume</h4>
          <ResponsiveContainer width="100%" height={100}>
            <AreaChart data={processedData}>
              <defs>
                <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <XAxis dataKey="timestamp" hide />
              <YAxis hide />
              <Area
                type="monotone"
                dataKey="volume"
                stroke="#8B5CF6"
                strokeWidth={1}
                fill="url(#volumeGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
};

export default AdvancedChart;