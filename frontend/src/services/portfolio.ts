// File: frontend/src/services/marketData.ts (CREATE THIS FILE)

import { apiClient } from '../config/api';

export const marketDataService = {
  async getmarketData(userId: string) {
    const { data } = await apiClient.get(`/api/v1/marketData/summary`);
    return data;
  },
  
  async getBalances(userId: string) {
    const { data } = await apiClient.get(`/api/v1/user/balances`);
    return data;
  }
};