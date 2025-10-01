// File: frontend/src/services/portfolio.ts (CREATE THIS FILE)

import { apiClient } from '../config/api';

export const portfolioService = {
  async getPortfolio(userId: string) {
    const { data } = await apiClient.get(`/api/v1/portfolio/summary`);
    return data;
  },
  
  async getBalances(userId: string) {
    const { data } = await apiClient.get(`/api/v1/user/balances`);
    return data;
  }
};