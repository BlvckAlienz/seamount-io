import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ChartDataPoint } from '../types';

interface PriceChartProps {
  data: ChartDataPoint[];
  height?: number;
  showGrid?: boolean;
  color?: string;
}

const PriceChart: React.FC<PriceChartProps> = ({ 
  data, 
  height = 300, 
  showGrid = true,
  color = '#3B82F6'
}) => {
  const formatData = data.map(point => ({
    timestamp: new Date(point.timestamp).toLocaleDateString(),
    price: point.close,
    volume: point.volume,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={formatData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
        {showGrid && <CartesianGrid strokeDasharray="3 3" stroke="#374151" />}
        <XAxis 
          dataKey="timestamp" 
          stroke="#9CA3AF"
          fontSize={12}
          tickFormatter={(value) => value.split('/')[1] + '/' + value.split('/')[2]}
        />
        <YAxis 
          stroke="#9CA3AF"
          fontSize={12}
          tickFormatter={(value) => `$${value.toLocaleString()}`}
        />
        <Tooltip 
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid #374151',
            borderRadius: '8px',
            color: '#F9FAFB',
          }}
          formatter={(value: number) => [`$${value.toLocaleString()}`, 'Price']}
          labelStyle={{ color: '#9CA3AF' }}
        />
        <Line 
          type="monotone" 
          dataKey="price" 
          stroke={color}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, stroke: color, strokeWidth: 2 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
};

export default PriceChart;