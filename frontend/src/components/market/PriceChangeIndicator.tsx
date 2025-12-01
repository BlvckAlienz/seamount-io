import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { apiClient } from '@/config/api';

interface PriceChangeIndicatorProps {
  symbol: string;
}

const PriceChangeIndicator: React.FC<PriceChangeIndicatorProps> = ({ symbol }) => {
  const [change, setChange] = useState<{ percent: number; value: number } | null>(null);

  useEffect(() => {
    const fetchChange = async () => {
      try {
        const response = await apiClient.get(`/api/v1/market/commodity/${symbol}/history`);
        if (response.data.success) {
          setChange({
            percent: response.data.change_percent,
            value: response.data.change_24h
          });
        }
      } catch (error) {
        console.error('Price change fetch failed:', error);
      }
    };

    fetchChange();
  }, [symbol]);

  if (!change) return <div className="h-5"></div>; // Placeholder

  const isPositive = change.percent >= 0;

  return (
    <div className={`flex items-center gap-1 text-sm font-semibold ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
      {isPositive ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
      {isPositive ? '+' : ''}{change.percent.toFixed(2)}% (24h)
    </div>
  );
};

export default PriceChangeIndicator;