// frontend/src/config/api.ts
// RESILIENT API CLIENT — Primary/Backup failover + cold-start warmup

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import { supabase } from '../lib/supabase';

// ─── Endpoint Registry ─────────────────────────────────────────────────────
const SERVERS = {
  api: {
    primary: import.meta.env.VITE_API_BASE_URL || 'https://seamount-io-pr8a.onrender.com',
    backup:  import.meta.env.VITE_API_BASE_URL_BACKUP || 'https://seamount-api.onrender.com',
  },
};

// ─── Circuit Breaker State (in-memory) ─────────────────────────────────────
interface CircuitState {
  usePrimary: boolean;
  failCount: number;
  lastFailTime: number;
  recovering: boolean;
}

const circuit: CircuitState = {
  usePrimary: true,
  failCount: 0,
  lastFailTime: 0,
  recovering: false,
};

const FAIL_THRESHOLD = 2;         // Switch to backup after N consecutive failures
const RECOVERY_INTERVAL = 60_000; // Re-test primary after 60s

function getActiveBase(): string {
  // Periodically attempt primary recovery
  if (!circuit.usePrimary && Date.now() - circuit.lastFailTime > RECOVERY_INTERVAL && !circuit.recovering) {
    circuit.recovering = true;
    pingPrimary(); // non-blocking
  }
  return circuit.usePrimary ? SERVERS.api.primary : SERVERS.api.backup;
}

function recordSuccess(): void {
  if (!circuit.usePrimary) return;
  circuit.failCount = 0;
  circuit.recovering = false;
}

function recordFailure(): void {
  circuit.failCount++;
  circuit.lastFailTime = Date.now();
  if (circuit.failCount >= FAIL_THRESHOLD) {
    if (circuit.usePrimary) {
      console.warn(`[API] ⚡ Primary down (${circuit.failCount} failures) → switching to backup`);
    }
    circuit.usePrimary = false;
  }
}

async function pingPrimary(): Promise<void> {
  try {
    await fetch(`${SERVERS.api.primary}/api/v1/health`, {
      signal: AbortSignal.timeout(5_000),
      method: 'GET',
    });
    console.info('[API] ✅ Primary recovered — switching back');
    circuit.usePrimary = true;
    circuit.failCount = 0;
    circuit.recovering = false;
  } catch {
    circuit.recovering = false;
  }
}

// ─── Warm-Up (fight Render cold starts) ────────────────────────────────────
let warmedUp = false;

export async function warmUpServer(): Promise<void> {
  if (warmedUp) return;
  warmedUp = true;

  const targets = [SERVERS.api.primary, SERVERS.api.backup];

  for (const url of targets) {
    fetch(`${url}/api/v1/health`, {
      signal: AbortSignal.timeout(35_000), // generous for cold start
      method: 'GET',
    })
      .then(() => console.info(`[WarmUp] ✅ ${url} is awake`))
      .catch(() => console.warn(`[WarmUp] ⚠️ ${url} did not respond`));
  }
}

// Kick off warm-up immediately on import
warmUpServer();

// ─── Axios Factory ─────────────────────────────────────────────────────────
function createAxiosInstance(baseURL: string, timeoutMs = 45_000): AxiosInstance {
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

// ─── Resilient Request Executor ────────────────────────────────────────────
const RETRYABLE_ERRORS = new Set(['ECONNABORTED', 'ETIMEDOUT', 'ERR_NETWORK', 'ERR_NAME_NOT_RESOLVED']);

async function executeWithFallback<T>(
  method: 'get' | 'post' | 'put' | 'patch' | 'delete',
  endpoint: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<{ data: T; status: number }> {

  const authConfig = await injectAuthHeader({ ...(config || {}) });

  // ── Attempt primary (or whichever is currently active) ──
  const activeBase = getActiveBase();
  const instance = createAxiosInstance(activeBase);

  try {
    console.log(`[API] → ${method.toUpperCase()} ${activeBase}${endpoint}`);
    const response = await instance[method]<T>(endpoint, method === 'get' ? authConfig : data, authConfig);
    recordSuccess();
    return { data: response.data, status: response.status };
  } catch (primaryErr: unknown) {
    const axiosErr = primaryErr as { code?: string; response?: { status: number } };
    const isNetworkError = !axiosErr.response || RETRYABLE_ERRORS.has(axiosErr.code || '');

    if (!isNetworkError) {
      // 4xx etc — don't fallback, surface to caller
      throw primaryErr;
    }

    recordFailure();
    console.warn(`[API] ⚡ Primary failed (${axiosErr.code}) — trying backup`);

    // ── Fallback to the OTHER server ──
    const fallbackBase = circuit.usePrimary ? SERVERS.api.primary : SERVERS.api.backup;
    const fallbackInstance = createAxiosInstance(fallbackBase);

    try {
      const fallbackAuthConfig = await injectAuthHeader({ ...(config || {}) });
      const response = await fallbackInstance[method]<T>(endpoint, method === 'get' ? fallbackAuthConfig : data, fallbackAuthConfig);
      console.info(`[API] ✅ Backup responded successfully`);
      return { data: response.data, status: response.status };
    } catch (backupErr) {
      console.error(`[API] ❌ Both servers failed for ${endpoint}`);
      throw backupErr;
    }
  }
}

// ─── Public API Client Interface ───────────────────────────────────────────
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

// ─── Named endpoint modules (unchanged API surface) ───────────────────────
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

export const walletAPI = { create: () => apiClient.post(API_ENDPOINTS.WALLET.CREATE) };
export const portfolioAPI = { getSummary: () => apiClient.get(API_ENDPOINTS.portfolio.SUMMARY) };
export const tradingAPI = {
  swap: (data: unknown) => apiClient.post(API_ENDPOINTS.TRADING.SWAP, data),
  buy:  (data: unknown) => apiClient.post(API_ENDPOINTS.TRADING.BUY, data),
  sell: (data: unknown) => apiClient.post(API_ENDPOINTS.TRADING.SELL, data),
};

export const xrpAPI = {
  getBalances:    () => apiClient.get(API_ENDPOINTS.XRP.BALANCES),
  getDepositInfo: () => apiClient.get(API_ENDPOINTS.XRP.DEPOSIT_INFO),
  transfer:       (data: unknown) => apiClient.post(API_ENDPOINTS.XRP.TRANSFER, data),
  withdraw:       (data: unknown) => apiClient.post(API_ENDPOINTS.XRP.WITHDRAW, data),
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