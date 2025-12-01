// File: frontend/src/components/market/LiveMarketPreview.tsx
// 🎯 Live Market Preview for Dashboard

import React, { useState, useEffect } from 'react';
import { TrendingUp, Activity, RefreshCw } from 'lucide-react';
import { apiClient } from '@/config/api';

interface LiveMarketPreviewProps {
  onOpenTerminal: () => void;
}

const LiveMarketPreview: React.FC<LiveMarketPreviewProps> = ({ onOpenTerminal }) => {
  const [liveData, setLiveData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchLivePreview = async () => {
    try {
      const response = await apiClient.get('/api/v1/market/snapshot');
      if (response.data.success) {
        setLiveData(response.data.data);
      }
    } catch (error) {
      console.error('Live preview fetch failed:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLivePreview();
    const interval = setInterval(fetchLivePreview, 30000); // 30s refresh
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!liveData) {
    return (
      <div className="text-center py-8 text-gray-400">
        Unable to load market data. Click "Open Terminal" to retry.
      </div>
    );
  }

  // Top 4 assets to preview
  const previewAssets = [
    { 
      name: 'Gold', 
      symbol: 'XAU', 
      price: liveData.commodities.XAU, 
      unit: '/oz',
      color: 'yellow',
      icon: '🏆'
    },
    { 
      name: 'Bitcoin', 
      symbol: 'BTC', 
      price: liveData.crypto.bitcoin, 
      unit: '',
      color: 'orange',
      icon: '₿'
    },
    { 
      name: 'Copper', 
      symbol: 'COPP', 
      price: liveData.commodities.COPP, 
      unit: '/ton',
      color: 'blue',
      icon: '⚙️'
    },
    { 
      name: 'Lithium', 
      symbol: 'LITH', 
      price: liveData.commodities.LITH, 
      unit: '/ton',
      color: 'purple',
      icon: '🔋'
    }
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {previewAssets.map(asset => (
        <button
          key={asset.symbol}
          onClick={onOpenTerminal}
          className={`bg-gradient-to-br from-${asset.color}-900/30 to-gray-800 border border-${asset.color}-700/50 rounded-xl p-4 hover:shadow-lg hover:shadow-${asset.color}-500/20 transition-all text-left group`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="text-2xl">{asset.icon}</div>
            <Activity className="h-4 w-4 text-green-400 animate-pulse" />
          </div>
          <div className="text-sm text-gray-400 mb-1">{asset.name}</div>
          <div className="text-lg font-bold text-white group-hover:text-blue-400 transition-colors">
            ${asset.price.toLocaleString(undefined, { 
              minimumFractionDigits: asset.unit === '/oz' ? 2 : 0, 
              maximumFractionDigits: asset.unit === '/oz' ? 2 : 0 
            })}
            <span className="text-xs text-gray-400">{asset.unit}</span>
          </div>
        </button>
      ))}
    </div>
  );
};

export default LiveMarketPreview;