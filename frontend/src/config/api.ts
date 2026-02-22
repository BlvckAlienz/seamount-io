// File: frontend/src/config/api.ts

import axios from 'axios';
import { supabase } from '../lib/supabase';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "https://seamount-io-pr8a.onrender.com";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
  validateStatus: (status) => status < 500,
});

const API_ENDPOINTS = {
  AUTH:    { RESET_PASSWORD: '/api/v1/auth/reset-password' },
  LEADS:   { BUSINESS_CONTACT: '/api/v1/leads/business-contact' },
  USER:    { PROFILE: '/api/v1/user/profile', PROVISION_WALLETS: '/api/v1/user/provision-wallets' },
  SESSION: { INITIALIZE: '/api/v1/session/initialize' },
  CONSENT: { UPDATE: '/api/v1/consent/update' },
  WALLET:  { CREATE: '/api/wallet/create' },
  KYC: {
    START_VERIFICATION: '/api/v1/kyc/start-verification',
    CHECK_PROFILE:      '/api/v1/kyc/profile-check',
    GET_STATUS:         '/api/v1/kyc/status',
    SKIP_VERIFICATION:  '/api/v1/kyc/skip-verification',
    REQUIREMENTS:       '/api/v1/kyc/requirements',
  },
  portfolio: { SUMMARY: '/api/v1/portfolio/summary' },
  TRADING: {
    SWAP: '/api/v1/trading/swap',
    BUY:  '/api/v1/trading/buy',
    SELL: '/api/v1/trading/sell',
  },
  // ✅ NEW: XRP Ledger endpoints (Phases 2 & 3)
  XRP: {
    BALANCES:          '/api/v1/xrp/balances',
    DEPOSIT_INFO:      '/api/v1/xrp/deposit-info',
    TRANSFER:          '/api/v1/xrp/transfer',
    WITHDRAW:          '/api/v1/xrp/withdraw',
    TRANSACTIONS:      '/api/v1/xrp/transactions',
    HEALTH:            '/api/v1/xrp/health',
    YIELD_POOLS:       '/api/v1/xrp/yield/pools',
    YIELD_POSITIONS:   '/api/v1/xrp/yield/positions',
    YIELD_DEPOSIT:     '/api/v1/xrp/yield/deposit',
    YIELD_WITHDRAW:    '/api/v1/xrp/yield/withdraw',
    YIELD_HISTORY:     '/api/v1/xrp/yield/history',
  },
};

// Request interceptor — attach Supabase auth token
apiClient.interceptors.request.use(async (config) => {
  console.log(`[API Request] --> ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (import.meta.env.DEV) {
      console.log('[API Auth] Session check:', { hasSession: !!session, userId: session?.user?.id, url: config.url });
    }
    if (session?.access_token) {
      if (!config.headers) config.headers = {} as any;
      config.headers['Authorization'] = `Bearer ${session.access_token}`;
      if (import.meta.env.DEV) console.log(`[API Auth] ✅ Token attached for ${config.url}`);
    } else {
      console.error(`[API Auth] ❌ NO TOKEN for ${config.url}`);
    }
  } catch (error) {
    console.error('[API Auth Error]:', error);
  }
  return config;
}, (error) => {
  console.error('[API Request Error]:', error);
  return Promise.reject(error);
});

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API Response] <-- ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    const url = error.config?.url || 'unknown';
    const status = error.response?.status || 'Network Error';
    const detail = error.response?.data?.detail || error.message;
    console.error(`[API Error] <-- ${status} ${url}: ${detail}`);
    return Promise.reject(error);
  }
);

// ─── API modules ──────────────────────────────────────────────────────────────

const userAPI = {
  getProfile:      () => apiClient.get(API_ENDPOINTS.USER.PROFILE),
  updateProfile:   (data: any) => apiClient.put(API_ENDPOINTS.USER.PROFILE, data),
  provisionWallets:() => apiClient.post(API_ENDPOINTS.USER.PROVISION_WALLETS),
};

const kycAPI = {
  checkProfile:     () => apiClient.get(API_ENDPOINTS.KYC.CHECK_PROFILE),
  startVerification:() => apiClient.post(API_ENDPOINTS.KYC.START_VERIFICATION),
  skipVerification: () => apiClient.post(API_ENDPOINTS.KYC.SKIP_VERIFICATION),
  getStatus:        (userId?: string) => apiClient.get(`${API_ENDPOINTS.KYC.GET_STATUS}${userId ? `/${userId}` : ''}`),
  getRequirements:  () => apiClient.get(API_ENDPOINTS.KYC.REQUIREMENTS),
};

const walletAPI = {
  create: () => apiClient.post(API_ENDPOINTS.WALLET.CREATE),
};

const portfolioAPI = {
  getSummary: () => apiClient.get(API_ENDPOINTS.portfolio.SUMMARY),
};

const tradingAPI = {
  swap: (data: any) => apiClient.post(API_ENDPOINTS.TRADING.SWAP, data),
  buy:  (data: any) => apiClient.post(API_ENDPOINTS.TRADING.BUY, data),
  sell: (data: any) => apiClient.post(API_ENDPOINTS.TRADING.SELL, data),
};

// ✅ NEW: XRP API module
const xrpAPI = {
  // Balances & deposit
  getBalances:    () => apiClient.get(API_ENDPOINTS.XRP.BALANCES),
  getDepositInfo: () => apiClient.get(API_ENDPOINTS.XRP.DEPOSIT_INFO),

  // Payments
  transfer: (data: {
    recipient_id: string; symbol: string; amount: string; memo?: string;
  }) => apiClient.post(API_ENDPOINTS.XRP.TRANSFER, data),

  withdraw: (data: {
    symbol: string; amount: string; destination_address: string; destination_tag?: number;
  }) => apiClient.post(API_ENDPOINTS.XRP.WITHDRAW, data),

  getTransactions: (params?: { symbol?: string; limit?: number; offset?: number }) =>
    apiClient.get(API_ENDPOINTS.XRP.TRANSACTIONS, { params }),

  health: () => apiClient.get(API_ENDPOINTS.XRP.HEALTH),

  // Yield farming
  getPools:     () => apiClient.get(API_ENDPOINTS.XRP.YIELD_POOLS),
  getPositions: () => apiClient.get(API_ENDPOINTS.XRP.YIELD_POSITIONS),

  depositYield: (data: { pool: string; amount: string }) =>
    apiClient.post(API_ENDPOINTS.XRP.YIELD_DEPOSIT, data),

  withdrawYield: (data: { position_id: string }) =>
    apiClient.post(API_ENDPOINTS.XRP.YIELD_WITHDRAW, data),

  getYieldHistory: (params?: { pool?: string; limit?: number; offset?: number }) =>
    apiClient.get(API_ENDPOINTS.XRP.YIELD_HISTORY, { params }),
};

const seedAPI = {
  getRecoverySeeds: () => apiClient.get('/api/v1/seeds/recovery'),
  getAccessLog:     () => apiClient.get('/api/v1/seeds/access-log'),
};

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
  xrpAPI,        // ✅ NEW
  seedAPI,
  initializeSession,
};

export default apiClient;