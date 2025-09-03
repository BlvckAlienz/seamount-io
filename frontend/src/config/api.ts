import axios from 'axios';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from './env';

/**
 * A centralized Axios client for all API communications with the Seamount backend.
 * It includes interceptors to automatically handle authentication tokens and provide
 * robust, consistent logging for both successful and failed requests.
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  // Add this to prevent infinite retries on certain errors
  validateStatus: function (status) {
    return status < 500; // Don't retry on server errors
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
  USER: {
    PROFILE: '/api/v1/user/profile',
    CREATE_PROFILE: '/api/v1/user/profile', // Use same endpoint for create/update
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
    START_VERIFICATION: '/api/kyc/start-verification',
  }
};

// --- Axios Interceptors ---

// 1. Request Interceptor: Automatically injects the Supabase JWT into every outgoing request.
// This is the most reliable pattern as it guarantees the freshest token is used.
apiClient.interceptors.request.use(
  async (config) => {
    const fullUrl = `${config.baseURL || API_BASE_URL}${config.url}`;
    console.log(`[API Request] --> ${config.method?.toUpperCase()} ${fullUrl}`);
    
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      } else {
        // This is normal for public routes (e.g., session initialize, contact form).
        console.log(`[API Auth] No active session token found for request.`);
      }
    } catch (error) {
      console.error('[API Auth Error] Failed to get session for auth token:', error);
      // Proceed with the request without auth if getting the session fails.
    }
    
    return config;
  },
  (error) => {
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