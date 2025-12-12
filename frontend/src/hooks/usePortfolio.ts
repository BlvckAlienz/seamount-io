import { useState, useEffect } from 'react';

export interface PortfolioData {
  totalValue: number;
  totalPnL: number;
  // Add more fields as your backend evolves
}

export const usePortfolio = () => {
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const refetch = async () => {
    setLoading(true);
    try {
      // TODO: Replace with actual API call when backend is ready
      // const response = await fetch('/api/portfolio');
      // const data = await response.json();
      // setPortfolio(data);
      
      await new Promise(resolve => setTimeout(resolve, 300));
      setPortfolio(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch portfolio'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refetch();
  }, []);

  return { portfolio, loading, error, refetch };
};