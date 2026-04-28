// frontend/src/config/api.ts
// RESILIENT API CLIENT — 2-server active pool, fast-fail, deduplication

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { supabase } from '../lib/supabase';

// ─── Active Server Pool — ordered by health ────────────────────────────────
// ONLY servers that are confirmed deployed and active
const API_POOL: string[] = [
  'https://seamount-main.onrender.com',   // PRIMARY — confirmed warm
  'https://seamount-api2.onrender.com',   // BACKUP  — confirmed warm
];

// Dead servers kept here for reference — NOT in the active pool
// 'https://seamount-io-pr8a.onrender.com' — CORS issues, suspended
// 'https://seamount-api.onrender.com'     — CORS issues, suspended
// 'https://seamount-main2.onrender.com'   — unconfirmed
// 'https://seamount-main3.onrender.com'   — unconfirmed
// 'https://seamount-api3.onrender.com'    — unconfirmed

// ─── Pool Health Tracker ───────────────────────────────────────────────────
const poolHealth: Record<string, { failCount: number; deadUntil: number }> = {};
const FAIL_THRESHOLD = 2;
const DEAD_WINDOW_MS = 90_000; // 90s cooldown — longer than WDK cold start

function getHealthyPool(): string[] {
  const now = Date.now();
  return API_POOL.filter(url => {
    const h = poolHealth[url];
    if (!h) return true;
    if (h.deadUntil && now < h.deadUntil) return false;
    return true;
  });
}

function recordServerSuccess(url: string): void {
  poolHealth[url] = { failCount: 0, deadUntil: 0 };
}

function recordServerFailure(url: string): void {
  const h = poolHealth[url] || { failCount: 0, deadUntil: 0 };
  h.failCount++;
  if (h.failCount >= FAIL_THRESHOLD) {
    h.deadUntil = Date.now() + DEAD_WINDOW_MS;
    console.warn(`[API] ⚡ ${url} marked dead for 90s (${h.failCount} failures)`);
  }
  poolHealth[url] = h;
}

export function getActiveBase(): string {
  return getHealthyPool()[0] || API_POOL[0];
}

// ─── Warm-Up — ping both servers + both WDK servers ───────────────────────
const WDK_POOL: string[] = [
  'https://seamount-wdk1.onrender.com',
  'https://seamount-wdk4.onrender.com',  // paired with seamount-api2
];

let warmedUp = false;

export async function warmUpServer(): Promise<void> {
  if (warmedUp) return;
  warmedUp = true;

  // Warm API servers
  API_POOL.forEach(url => {
    fetch(`${url}/ping`, { signal: AbortSignal.timeout(35_000), method: 'GET' })
      .then(() => console.info(`[WarmUp] ✅ ${url} is awake`))
      .catch(() => console.warn(`[WarmUp] ⚠️ ${url} did not respond`));
  });

    // Warm WDK servers — use the /health endpoint that actually exists
  WDK_POOL.forEach(url => {
    fetch(`${url}/health`, { signal: AbortSignal.timeout(35_000), method: 'GET' })
      .then(res => {
        if (res.ok) {
          console.info(`[WarmUp] ✅ WDK ${url} is awake`);
        } else {
          console.warn(`[WarmUp] ⚠️ WDK ${url} responded with ${res.status} – may be unhealthy`);
        }
      })
      .catch(() => console.warn(`[WarmUp] ⚠️ WDK ${url} did not respond`));
  });
}

warmUpServer();

// ─── Axios Factory ─────────────────────────────────────────────────────────
// IMPORTANT: wallet/balances needs longer timeout due to WDK dependency
const SLOW_ENDPOINTS = new Set([
  '/api/v1/wallet/balances',
  '/api/v1/wallet/create',
  '/api/v1/xrp/balances',
]);

function createAxiosInstance(baseURL: string, endpoint: string): AxiosInstance {
  const timeoutMs = SLOW_ENDPOINTS.has(endpoint) ? 30_000 : 20_000;
  return axios.create({
    baseURL,
    timeout: timeoutMs,
    headers: { 'Content-Type': 'application/json' },
    validateStatus: (status) => status < 500,
  });
}

// ─── Auth Token Injector ───────────────────────────────────────────────────
async function injectAuthHeader(config: AxiosRequestConfig): Promise<AxiosRequestConfig> {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${session.access_token}`,
      };
    }
  } catch (err) {
    console.error('[API] Auth header injection failed:', err);
  }
  return config;
}

// ─── In-flight deduplicator ────────────────────────────────────────────────
const inFlight = new Map<string, Promise<{ data: unknown; status: number }>>();

// ─── Resilient Request Executor ────────────────────────────────────────────
const RETRYABLE_ERRORS = new Set([
  'ECONNABORTED', 'ETIMEDOUT', 'ERR_NETWORK', 'ERR_NAME_NOT_RESOLVED'
]);

async function executeWithFallback<T>(
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  endpoint: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<{ data: T; status: number }> {
  if (method === 'get') {
    const key = `GET:${endpoint}`;
    if (inFlight.has(key)) {
      return inFlight.get(key) as Promise<{ data: T; status: number }>;
    }
    const promise = _executeWithFallback<T>(method, endpoint, data, config)
      .finally(() => inFlight.delete(key));
    inFlight.set(key, promise as Promise<{ data: unknown; status: number }>);
    return promise;
  }
  return _executeWithFallback<T>(method, endpoint, data, config);
}

async function _executeWithFallback<T>(
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  endpoint: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<{ data: T; status: number }> {

  const authConfig = await injectAuthHeader({ ...(config || {}) });
  const pool = getHealthyPool().length > 0 ? getHealthyPool() : API_POOL;

  let lastErr: unknown;

  for (const baseUrl of pool) {
    const instance = createAxiosInstance(baseUrl, endpoint);
    try {
      console.log(`[API] → ${method.toUpperCase()} ${baseUrl}${endpoint}`);
      const response = await instance[method]<T>(
        endpoint,
        method === 'get' ? authConfig : data,
        authConfig,
      );
      recordServerSuccess(baseUrl);
      return { data: response.data, status: response.status };

    } catch (err: unknown) {
      const axiosErr = err as { code?: string; response?: { status: number } };
      const isNetworkError = !axiosErr.response || RETRYABLE_ERRORS.has(axiosErr.code || '');

      if (!isNetworkError) {
        throw err; // 4xx — surface immediately
      }

      recordServerFailure(baseUrl);
      console.warn(`[API] ⚡ ${baseUrl} failed (${axiosErr.code}) — trying next server`);
      lastErr = err;
    }
  }

  console.error(`[API] ❌ All ${pool.length} servers failed for ${endpoint}`);
  throw lastErr;
}

// ─── Public API Client ─────────────────────────────────────────────────────
export const apiClient = {
  get: <T = unknown>(endpoint: string, config?: AxiosRequestConfig) =>
    executeWithFallback<T>('get', endpoint, undefined, config),
  post: <T = unknown>(endpoint: string, data?: unknown, config?: AxiosRequestConfig) =>
    executeWithFallback<T>('post', endpoint, data, config),
  put: <T = unknown>(endpoint: string, data?: unknown, config?: AxiosRequestConfig) =>
    executeWithFallback<T>('put', endpoint, data, config),
  patch: <T = unknown>(endpoint: string, data?: unknown, config?: AxiosRequestConfig) =>
    executeWithFallback<T>('patch', endpoint, data, config),
  delete: <T = unknown>(endpoint: string, config?: AxiosRequestConfig) =>
    executeWithFallback<T>('delete', endpoint, undefined, config),
};

// ─── Endpoint Modules ──────────────────────────────────────────────────────
export const API_ENDPOINTS = {
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
  XRP: {
    BALANCES:        '/api/v1/xrp/balances',
    DEPOSIT_INFO:    '/api/v1/xrp/deposit-info',
    TRANSFER:        '/api/v1/xrp/transfer',
    WITHDRAW:        '/api/v1/xrp/withdraw',
    TRANSACTIONS:    '/api/v1/xrp/transactions',
    HEALTH:          '/api/v1/xrp/health',
    YIELD_POOLS:     '/api/v1/xrp/yield/pools',
    YIELD_POSITIONS: '/api/v1/xrp/yield/positions',
    YIELD_DEPOSIT:   '/api/v1/xrp/yield/deposit',
    YIELD_WITHDRAW:  '/api/v1/xrp/yield/withdraw',
    YIELD_HISTORY:   '/api/v1/xrp/yield/history',
  },
};

export const userAPI = {
  getProfile:       () => apiClient.get(API_ENDPOINTS.USER.PROFILE),
  updateProfile:    (data: unknown) => apiClient.put(API_ENDPOINTS.USER.PROFILE, data),
  provisionWallets: () => apiClient.post(API_ENDPOINTS.USER.PROVISION_WALLETS),
};
export const kycAPI = {
  checkProfile:      () => apiClient.get(API_ENDPOINTS.KYC.CHECK_PROFILE),
  startVerification: () => apiClient.post(API_ENDPOINTS.KYC.START_VERIFICATION),
  skipVerification:  () => apiClient.post(API_ENDPOINTS.KYC.SKIP_VERIFICATION),
  getStatus:         (userId?: string) => apiClient.get(`${API_ENDPOINTS.KYC.GET_STATUS}${userId ? `/${userId}` : ''}`),
  getRequirements:   () => apiClient.get(API_ENDPOINTS.KYC.REQUIREMENTS),
};
export const walletAPI    = { create: () => apiClient.post(API_ENDPOINTS.WALLET.CREATE) };
export const portfolioAPI = { getSummary: () => apiClient.get(API_ENDPOINTS.portfolio.SUMMARY) };
export const tradingAPI   = {
  swap: (data: unknown) => apiClient.post(API_ENDPOINTS.TRADING.SWAP, data),
  buy:  (data: unknown) => apiClient.post(API_ENDPOINTS.TRADING.BUY, data),
  sell: (data: unknown) => apiClient.post(API_ENDPOINTS.TRADING.SELL, data),
};
export const xrpAPI = {
  getBalances:     () => apiClient.get(API_ENDPOINTS.XRP.BALANCES),
  getDepositInfo:  () => apiClient.get(API_ENDPOINTS.XRP.DEPOSIT_INFO),
  transfer:        (data: unknown) => apiClient.post(API_ENDPOINTS.XRP.TRANSFER, data),
  withdraw:        (data: unknown) => apiClient.post(API_ENDPOINTS.XRP.WITHDRAW, data),
  getTransactions: (params?: unknown) => apiClient.get(API_ENDPOINTS.XRP.TRANSACTIONS, { params } as AxiosRequestConfig),
  health:          () => apiClient.get(API_ENDPOINTS.XRP.HEALTH),
  getPools:        () => apiClient.get(API_ENDPOINTS.XRP.YIELD_POOLS),
  getPositions:    () => apiClient.get(API_ENDPOINTS.XRP.YIELD_POSITIONS),
  depositYield:    (data: unknown) => apiClient.post(API_ENDPOINTS.XRP.YIELD_DEPOSIT, data),
  withdrawYield:   (data: unknown) => apiClient.post(API_ENDPOINTS.XRP.YIELD_WITHDRAW, data),
  getYieldHistory: (params?: unknown) => apiClient.get(API_ENDPOINTS.XRP.YIELD_HISTORY, { params } as AxiosRequestConfig),
};
export const seedAPI = {
  getRecoverySeeds: () => apiClient.get('/api/v1/seeds/recovery'),
  getAccessLog:     () => apiClient.get('/api/v1/seeds/access-log'),
};
export const initializeSession = async (): Promise<string> => {
  try {
    const response = await apiClient.post<{ session_id: string }>(API_ENDPOINTS.SESSION.INITIALIZE);
    return response.data.session_id;
  } catch {
    return 'anonymous-session-fallback';
  }
};

export default apiClient;