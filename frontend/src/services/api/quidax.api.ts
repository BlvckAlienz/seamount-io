// File: frontend/src/services/api/quidax.api.ts

import { apiClient } from '@/config/api';
import type {
  QuidaxQuote,
  QuidaxInstantOrder,
  QuidaxOrderStatus,
  QuidaxQuoteRequest,
  QuidaxInstantOrderRequest,
} from '@/types/quidax.types';

export const quidaxApi = {
  /**
   * Get a price quote for buying/selling crypto
   */
  async getQuote(request: QuidaxQuoteRequest): Promise<QuidaxQuote> {
    const response = await apiClient.post('/api/v1/quidax/quote', request);
    return response.data;
  },

  /**
   * Create an instant order from a quote
   * Returns payment URL for user to complete payment
   */
  async createInstantOrder(request: QuidaxInstantOrderRequest): Promise<QuidaxInstantOrder> {
    const response = await apiClient.post('/api/v1/quidax/instant-order', request);
    return response.data;
  },

  /**
   * Get status of an instant order
   */
  async getOrderStatus(orderId: string): Promise<QuidaxOrderStatus> {
    const response = await apiClient.get(`/api/v1/quidax/orders/${orderId}`);
    return response.data;
  },

  /**
   * Get available markets (USDT/NGN, BTC/NGN, etc.)
   */
  async getMarkets(): Promise<any> {
    const response = await apiClient.get('/api/v1/quidax/markets');
    return response.data;
  },

  /**
   * Get current ticker/price for a market
   */
  async getTicker(market: string): Promise<any> {
    const response = await apiClient.get(`/api/v1/quidax/ticker/${market}`);
    return response.data;
  },
};