import { useState, useEffect, useCallback } from 'react';
import { realMarketData } from '../services/realMarketData';
import { Portfolio, Asset } from '../types';

export function useRealMarketData() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refreshData = useCallback(async () => {
    try {
      setError(null);
      const [portfolioData, assetData] = await Promise.all([
        realMarketData.getPortfolioData(),
        realMarketData.getPortfolioData().then(p => p.assets || [])
      ]);
      
      setPortfolio(portfolioData);
      setAssets(assetData);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch market data');
      console.error('Market data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  const getStockData = useCallback(async (symbol: string) => {
    try {
      return await realMarketData.getStockData(symbol);
    } catch (err) {
      console.error(`Failed to fetch ${symbol} data:`, err);
      return null;
    }
  }, []);

  const getCryptoData = useCallback(async (symbol: string) => {
    try {
      return await realMarketData.getCoinbaseData(symbol);
    } catch (err) {
      console.error(`Failed to fetch ${symbol} crypto data:`, err);
      return null;
    }
  }, []);

  // Initial data load
  useEffect(() => {
    refreshData();
  }, [refreshData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(refreshData, 30000);
    return () => clearInterval(interval);
  }, [refreshData]);

  return {
    portfolio,
    assets,
    loading,
    error,
    lastUpdated,
    refreshData,
    getStockData,
    getCryptoData
  };
}