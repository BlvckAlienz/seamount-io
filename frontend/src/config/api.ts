// frontend/src/config/api.ts
import axios from 'axios';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from './env';

/**
 * A centralized Axios client for all API communications with Seamount backend.
 * It includes interceptors to automatically handle authentication tokens and provide
 * robust, consistent logging for both successful and failed requests.
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30-second timeout for requests
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * A typed object of all API endpoints.
 * Using this ensures type safety and prevents typos in API route strings.
 */
export const API_ENDPOINTS = {
  LEADS: {
    BUSINESS_CONTACT: '/api/v1/leads/business-contact',
  },
  KYC: {
    START_VERIFICATION: '/api/kyc/start-verification',
  },
  WALLET: {
    CREATE: '/api/wallet/create',
  },
  USER: {
    PROFILE: '/api/v1/user/profile',
  },
  SESSION: {
    INITIALIZE: '/api/v1/session/initialize',
  },
  CONSENT: {
    UPDATE: '/api/v1/consent/update',
  },
  HEALTH: '/api/v1/health',
};

// Store the latest token to avoid race conditions
let currentToken: string | null = null;

// Update token function that can be called from outside
export const updateApiClientToken = async () => {
  try {
    const { data: { session } } = await supabase.auth.getSession();
    currentToken = session?.access_token || null;
  } catch (error) {
    console.error('Failed to get session for auth token:', error);
    currentToken = null;
  }
};

// Initial token update
updateApiClientToken();

// Listen for auth state changes
supabase.auth.onAuthStateChange(async (event, session) => {
  if (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED') {
    currentToken = session?.access_token || null;
  } else if (event === 'SIGNED_OUT') {
    currentToken = null;
  }
});

// --- Axios Interceptors ---

// 1. Request Interceptor: Automatically injects the Supabase JWT into every outgoing request.
apiClient.interceptors.request.use(
  async (config) => {
    const fullUrl = `${config.baseURL || API_BASE_URL}${config.url}`;
    console.log(`[API Request] --> ${config.method?.toUpperCase()} ${fullUrl}`);
    
    // Use the current token without making an async call
    if (currentToken) {
      config.headers.Authorization = `Bearer ${currentToken}`;
    } else {
      // This is not an error, just a state for public routes like the contact form.
      console.log(`[API Auth] No active session token found for request.`);
    }
    
    return config;
  },
  (error) => {
    // This part handles errors that happen *before* the request is even sent.
    console.error('[API Request Error] Error creating request:', error);
    return Promise.reject(error);
  }
);

// 2. Response Interceptor: Centralizes logging and error handling for all API responses.
apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API Response] <-- ${response.status} ${response.config.method?.toUpperCase()} ${response.config.url}`);
    return response;
  },
  (error) => {
    const config = error.config;
    const response = error.response;
    const url = config?.url || 'unknown endpoint';
    const status = response?.status || 'Network Error';
    const detail = response?.data?.detail || error.message;

    console.error(`[API Response Error] <-- ${status} on ${url} | Detail: ${detail}`);
    
    return Promise.reject(error);
  }
);

export default apiClient;