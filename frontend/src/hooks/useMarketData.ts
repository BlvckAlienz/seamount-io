import { useState, useEffect } from 'react';
import { apiClient } from '../config/api';

export const useportfolio = () => {
  const [portfolio, setportfolio] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchportfolio = async () => {
    try {
      setLoading(true);
      // Use the correct endpoint path
      const response = await apiClient.get('/api/v1/portfolio/summary');
      setportfolio(response.data);
      setError(null);
    } catch (err: any) {
      console.error('Market data fetch error:', err);
      setError(err.message);
      // Provide fallback data instead of failing completely
      setportfolio({
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
    fetchportfolio();
  }, []);

  return { portfolio, loading, error, refetch: fetchportfolio };
};