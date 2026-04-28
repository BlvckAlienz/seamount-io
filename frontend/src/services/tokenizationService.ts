/**
 * Tokenization Service - Frontend API Client
 * Connects to Seamount Protocol backend
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://seamount-main.onrender.com';

export interface TokenizeAssetRequest {
  custodian_id: string;
  symbol: string;
  name?: string;
  quantity: number;
  isin?: string;
  price_per_unit: number;
}

export interface PublishOfferRequest {
  asset_id: string;
  quantity: number;
  price_per_unit: number;
  payment_network: 'usdc_circle' | 'usdt_tron' | 'nibss_nip';
  expires_in_hours?: number;
}

export interface ExecuteTradeRequest {
  offer_id: string;
  payment_network: 'usdc_circle' | 'usdt_tron' | 'nibss_nip';
}

export interface CreateRepoRequest {
  collateral_asset_id: string;
  collateral_quantity: number;
  loan_amount_usd: number;
  repo_rate_percentage: number;
  maturity_days: number;
  lender_id?: string;
}

class TokenizationService {
  private getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    };
  }

  /**
   * Convert traditional asset to digital twin
   */
  async convertAsset(request: TokenizeAssetRequest) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/tokenization/convert-asset`,
        request,
        { headers: this.getAuthHeaders() }
      );
      
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Asset tokenization failed');
    }
  }

  /**
   * Publish asset offer on secondary market
   */
  async publishOffer(request: PublishOfferRequest) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/tokenization/publish-offer`,
        request,
        { headers: this.getAuthHeaders() }
      );
      
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to publish offer');
    }
  }

  /**
   * Execute DVP trade
   */
  async executeTrade(request: ExecuteTradeRequest) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/tokenization/execute-trade`,
        request,
        { headers: this.getAuthHeaders() }
      );
      
      return response.data;
    } catch (error: any) {
      // 🚨 Handle self-trade errors gracefully
      const errorMessage = error.response?.data?.detail?.message 
        || error.response?.data?.detail 
        || 'Trade execution failed';
      
      throw new Error(errorMessage);
    }
  }

  /**
   * Create repo trade
   */
  async createRepo(request: CreateRepoRequest) {
    try {
      const response = await axios.post(
        `${API_BASE_URL}/api/v1/tokenization/create-repo`,
        request,
        { headers: this.getAuthHeaders() }
      );
      
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Repo creation failed');
    }
  }

  /**
   * Get user's tokenized assets
   */
  async getMyAssets() {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/v1/tokenization/my-assets`,
        { headers: this.getAuthHeaders() }
      );
      
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch assets');
    }
  }

  /**
   * Get available market offers
   */
  async getOffers(symbol?: string) {
    try {
      const params = symbol ? { symbol } : {};
      const response = await axios.get(
        `${API_BASE_URL}/api/v1/tokenization/offers`,
        { 
          headers: this.getAuthHeaders(),
          params 
        }
      );
      
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch offers');
    }
  }

  /**
   * Get user's repo trades
   */
  async getMyRepos() {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/v1/tokenization/my-repos`,
        { headers: this.getAuthHeaders() }
      );
      
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to fetch repos');
    }
  }

  /**
   * Get protocol metrics (public)
   */
  async getMetrics() {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/v1/tokenization/metrics`
      );
      
      return response.data;
    } catch (error: any) {
      throw new Error('Failed to fetch metrics');
    }
  }
}

export default new TokenizationService();