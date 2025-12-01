import React, { useState, useEffect } from 'react';
import { Sparklines, SparklinesLine } from 'react-sparklines';
import { apiClient } from '@/config/api';

interface SparklineChartProps {
  symbol: string;
}

const SparklineChart: React.FC<SparklineChartProps> = ({ symbol }) => {
  const [prices, setPrices] = useState<number[]>([]);

  useEffect(() => {
    const fetchPrices = async () => {
      try {
        const response = await apiClient.get(`/api/v1/market/commodity/${symbol}/history`);
        if (response.data.success) {
          setPrices(response.data.prices);
        }
      } catch (error) {
        console.error('Sparkline fetch failed:', error);
      }
    };

    fetchPrices();
  }, [symbol]);

  if (prices.length === 0) return <div className="h-12"></div>; // Placeholder

  const isPositive = prices[prices.length - 1] >= prices[0];

  return (
    <div className="my-2">
      <Sparklines data={prices} width={150} height={30}>
        <SparklinesLine color={isPositive ? '#22c55e' : '#ef4444'} />
      </Sparklines>
    </div>
  );
};

export default SparklineChart;