// File Location: frontend/src/hooks/useMarketData.ts
// Description: The definitive, corrected, and production-ready hook for fetching market and portfolio data.

import { useState, useEffect, useCallback } from 'react';
import { toast } from 'react-hot-toast';

// --- CORRECTED IMPORT PATHS & ARCHITECTURE ---
import { apiClient } from '@/config/api';
import { Portfolio, Asset } from '@/types'; // Assuming types are in src/types

export function useMarketData() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refreshData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // All data fetching now goes through our secure, centralized apiClient.
      // This assumes your backend has an endpoint like '/api/v1/portfolio/summary'
      const response = await apiClient.get('/api/v1/portfolio/summary');
      
      const portfolioData: Portfolio = response.data;
      
      setPortfolio(portfolioData);
      setAssets(portfolioData.assets || []); // Assuming the API returns assets within the portfolio object
      setLastUpdated(new Date());

    } catch (err) {
      const errorMessage = (err as any).response?.data?.detail || (err instanceof Error ? err.message : 'Failed to fetch market data');
      setError(errorMessage);
      console.error('Market data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial data load
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Optional: Auto-refresh data periodically
  useEffect(() => {
    const interval = setInterval(refreshData, 60000); // Refresh every 60 seconds
    return () => clearInterval(interval);
  }, [refreshData]);

  return {
    portfolio,
    assets,
    loading,
    error,
    lastUpdated,
    refreshData,
  };
}