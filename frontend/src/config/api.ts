// File: frontend/src/config/api.ts
// CRITICAL FIX: API base URL configuration

import axios from 'axios';
import { supabase } from '../lib/supabase';

// FIXED: Single source of truth for API base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://seamount-api.onrender.com";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  validateStatus: function (status) {
    return status < 500;
  },
});

// FIXED: Proper API endpoints for Seamount 2.0
const API_ENDPOINTS = {
  LEADS: {
    BUSINESS_CONTACT: '/api/v1/leads/business-contact',
  },
  USER: {
    PROFILE: '/api/v1/user/profile',
    PROVISION_WALLETS: '/api/v1/user/provision-wallets', // FIXED: proper endpoint
  },
  SESSION: {
    INITIALIZE: '/api/v1/session/initialize',
  },
  CONSENT: {
    UPDATE: '/api/v1/consent/update',
  },
  WALLET: {
    CREATE: '/api/wallet/create',
  },
  KYC: {
    START_VERIFICATION: '/api/v1/kyc/start-verification',
    CHECK_PROFILE: '/api/v1/kyc/profile-check',
    GET_STATUS: '/api/v1/kyc/status',
    SKIP_VERIFICATION: '/api/v1/kyc/skip-verification',
    REQUIREMENTS: '/api/v1/kyc/requirements',
  },
  portfolio: {
    SUMMARY: '/api/v1/portfolio/summary', // FIXED: missing endpoint
  },
  TRADING: {
    SWAP: '/api/v1/trading/swap',
    BUY: '/api/v1/trading/buy',
    SELL: '/api/v1/trading/sell',
  }
};

// Request interceptor
apiClient.interceptors.request.use(
  async (config) => {
    const fullUrl = `${config.baseURL}${config.url}`;
    console.log(`[API Request] --> ${config.method?.toUpperCase()} ${fullUrl}`);
    
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (token) {
        // 🔧 FIX: Ensure headers object exists
        if (!config.headers) {
          config.headers = {} as any;
        }
        
        // 🔧 FIX: Force set Authorization header
        config.headers['Authorization'] = `Bearer ${token}`;
        
        console.log(`[API Auth] ✅ Token attached (length: ${token.length})`);
        console.log(`[API Auth] ✅ Authorization header set for ${config.url}`);
      } else {
        console.warn(`[API Auth] ⚠️ NO TOKEN available for ${config.url}`);
      }
    } catch (error) {
      console.error('[API Auth Error] Failed to get session:', error);
    }
    
    // 🔧 DEBUG: Log final headers
    console.log('[API Headers]', config.headers);
    
    return config;
  },
  (error) => {
    console.error('[API Request Error]:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API Response] <-- ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`);
    console.log(`[API Success] ${response.config.url?.split('/').pop() || 'Unknown'} operation completed`);
    return response;
  },
  (error) => {
    const config = error.config;
    const response = error.response;
    const url = config?.url || 'unknown endpoint';
    const status = response?.status || 'Network Error';
    const detail = response?.data?.detail || error.message;

    console.error(`[API Error] <-- ${status} ${config?.method?.toUpperCase()} ${url}`);
    console.error(`[API Error] Detail: ${detail}`);
    
    return Promise.reject(error);
  }
);

// API functions
const userAPI = {
  getProfile: () => apiClient.get(API_ENDPOINTS.USER.PROFILE),
  updateProfile: (data: any) => apiClient.put(API_ENDPOINTS.USER.PROFILE, data),
  provisionWallets: () => apiClient.post(API_ENDPOINTS.USER.PROVISION_WALLETS), // FIXED
};

const kycAPI = {
  checkProfile: () => apiClient.get(API_ENDPOINTS.KYC.CHECK_PROFILE),
  startVerification: () => apiClient.post(API_ENDPOINTS.KYC.START_VERIFICATION),
  skipVerification: () => apiClient.post(API_ENDPOINTS.KYC.SKIP_VERIFICATION),
  getStatus: (userId?: string) => apiClient.get(`${API_ENDPOINTS.KYC.GET_STATUS}${userId ? `/${userId}` : ''}`),
  getRequirements: () => apiClient.get(API_ENDPOINTS.KYC.REQUIREMENTS),
};

const walletAPI = {
  create: () => apiClient.post(API_ENDPOINTS.WALLET.CREATE),
};

const portfolioAPI = {
  getSummary: () => apiClient.get(API_ENDPOINTS.portfolio.SUMMARY), // NEW
};

const tradingAPI = {
  swap: (data: any) => apiClient.post(API_ENDPOINTS.TRADING.SWAP, data), // NEW
  buy: (data: any) => apiClient.post(API_ENDPOINTS.TRADING.BUY, data), // NEW
  sell: (data: any) => apiClient.post(API_ENDPOINTS.TRADING.SELL, data), // NEW
};

// Session initialization
const initializeSession = async (): Promise<string> => {
  try {
    const response = await apiClient.post(API_ENDPOINTS.SESSION.INITIALIZE);
    return response.data.session_id;
  } catch (error) {
    console.error('Session initialization failed:', error);
    return 'anonymous-session-fallback';
  }
};

export {
  apiClient,
  API_ENDPOINTS,
  userAPI,
  kycAPI,
  walletAPI,
  portfolioAPI,
  tradingAPI,
  seedAPI,
  initializeSession,
};

// 🔐 Seed Recovery API
const seedAPI = {
  getRecoverySeeds: () => apiClient.get('/api/v1/seeds/recovery'),
  getAccessLog: () => apiClient.get('/api/v1/seeds/access-log'),
};

export default apiClient;