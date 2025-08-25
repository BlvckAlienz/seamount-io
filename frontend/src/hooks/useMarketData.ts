import { useState, useEffect } from 'react';
import { apiClient, API_ENDPOINTS } from '../config/api';

export const useMarketData = () => {
  const [marketData, setMarketData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMarketData = async () => {
    try {
      setLoading(true);
      // Use the properly defined endpoint
      const response = await apiClient.get(API_ENDPOINTS.PORTFOLIO.SUMMARY);
      setMarketData(response.data);
      setError(null);
    } catch (err: any) {
      console.error('Market data fetch error:', err);
      setError(err.message);
      // Provide fallback data instead of failing completely
      setMarketData({
        total_balance: 0,
        usds_balance: 0,
        day_change: 0,
        total_pnl: 0,
        assets: []
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMarketData();
  }, []);

  return { marketData, loading, error, refetch: fetchMarketData };
};