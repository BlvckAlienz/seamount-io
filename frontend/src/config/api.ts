// File Location: frontend/src/config/api.ts
// CRITICAL FIX: Removed duplicate exports

import axios from 'axios';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from './env';

/**
 * CRITICAL FIX: Centralized API client with correct endpoint mappings
 * Fixes 405/403 errors by aligning frontend calls with backend routes
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
  validateStatus: function (status) {
    return status < 500; // Don't retry on server errors
  },
});

/**
 * CRITICAL FIX: Corrected API endpoints that match the actual backend routes
 * This fixes the 405 Method Not Allowed and 403 Forbidden errors
 */
const API_ENDPOINTS = {
  // Lead generation endpoints
  LEADS: {
    BUSINESS_CONTACT: '/api/v1/leads/business-contact',
  },
  
  // FIXED: User endpoints matching backend routes exactly
  USER: {
    PROFILE: '/api/v1/user',           // GET /api/v1/user (not /profile)
    CREATE_PROFILE: '/api/v1/user',    // POST /api/v1/user (not /profile) 
    UPDATE_PROFILE: '/api/v1/user',    // PUT /api/v1/user (not /profile)
    DELETE_PROFILE: '/api/v1/user',    // DELETE /api/v1/user
  },
  
  // Session management
  SESSION: {
    INITIALIZE: '/api/v1/session/initialize',
  },
  
  // Consent management
  CONSENT: {
    UPDATE: '/api/v1/consent/update',
  },
  
  // Wallet operations
  WALLET: {
    CREATE: '/api/v1/wallet/create',     // FIXED: Added v1 prefix
    BALANCE: '/api/v1/wallet/balance',   // FIXED: Added balance endpoint
  },
  
  // FIXED: KYC endpoints matching backend
  KYC: {
    START_VERIFICATION: '/api/v1/kyc/start-verification',
    WEBHOOK: '/api/v1/kyc/webhook',
    STATUS: '/api/v1/kyc/status',
  },
  
  // FIXED: Added missing endpoints that backend provides
  PAYMENTS: {
    CREATE: '/api/v1/payments/create',
    STATUS: '/api/v1/payments/status',
    HISTORY: '/api/v1/payments/history',
  },
  
  PORTFOLIO: {
    OVERVIEW: '/api/v1/portfolio/overview',
    HOLDINGS: '/api/v1/portfolio/holdings',
  }
};

// CRITICAL FIX: Enhanced request interceptor with better error handling
apiClient.interceptors.request.use(
  async (config) => {
    const fullUrl = `${config.baseURL || API_BASE_URL}${config.url}`;
    console.log(`[API Request] --> ${config.method?.toUpperCase()} ${fullUrl}`);
    
    try {
      // Get fresh session token for every request
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log(`[API Auth] Token attached for authenticated request`);
      } else {
        console.log(`[API Auth] No session token - proceeding with unauthenticated request`);
      }
    } catch (error) {
      console.error('[API Auth Error] Failed to get session token:', error);
      // Continue without auth token for public endpoints
    }
    
    return config;
  },
  (error) => {
    console.error('[API Request Error] Request configuration failed:', error);
    return Promise.reject(error);
  }
);

// CRITICAL FIX: Enhanced response interceptor with better error categorization
apiClient.interceptors.response.use(
  (response) => {
    const { status, config } = response;
    const method = config.method?.toUpperCase();
    const url = config.url;
    
    console.log(`[API Response] <-- ${status} ${method} ${url}`);
    
    // Log successful profile operations for debugging
    if (url?.includes('/user') && method && ['GET', 'POST', 'PUT'].includes(method)) {
      console.log(`[API Success] User profile operation completed: ${method} ${url}`);
    }
    
    return response;
  },
  (error) => {
    const { config, response } = error;
    const url = config?.url || 'unknown endpoint';
    const method = config?.method?.toUpperCase() || 'UNKNOWN';
    const status = response?.status || 'Network Error';
    const detail = response?.data?.detail || error.message;

    // CRITICAL: Enhanced error logging for debugging 405/403 issues
    console.error(`[API Error] <-- ${status} ${method} ${url}`);
    console.error(`[API Error] Detail: ${detail}`);
    
    // Log full response for debugging specific endpoint issues
    if (response?.status === 405) {
      console.error(`[405 Error] Method Not Allowed - Check if backend route exists:`, {
        requestedMethod: method,
        requestedUrl: url,
        availableMethods: response.headers?.allow || 'Unknown'
      });
    }
    
    if (response?.status === 403) {
      console.error(`[403 Error] Forbidden - Check authentication and permissions:`, {
        url,
        hasAuthHeader: !!config?.headers?.Authorization,
        tokenPrefix: config?.headers?.Authorization?.substring(0, 20) + '...' || 'None'
      });
    }
    
    return Promise.reject(error);
  }
);

/**
 * CRITICAL FIX: Utility functions for common API operations
 * These use the correct endpoints and handle errors properly
 */

// User profile operations
const userAPI = {
  // Get user profile
  getProfile: async () => {
    const response = await apiClient.get(API_ENDPOINTS.USER.PROFILE);
    return response.data;
  },
  
  // Create user profile
  createProfile: async (profileData: any) => {
    const response = await apiClient.post(API_ENDPOINTS.USER.CREATE_PROFILE, profileData);
    return response.data;
  },
  
  // Update user profile
  updateProfile: async (profileData: any) => {
    const response = await apiClient.put(API_ENDPOINTS.USER.UPDATE_PROFILE, profileData);
    return response.data;
  }
};

// KYC operations
const kycAPI = {
  // Start KYC verification
  startVerification: async (verificationData: any) => {
    const response = await apiClient.post(API_ENDPOINTS.KYC.START_VERIFICATION, verificationData);
    return response.data;
  },
  
  // Get KYC status
  getStatus: async (userId: string) => {
    const response = await apiClient.get(`${API_ENDPOINTS.KYC.STATUS}/${userId}`);
    return response.data;
  }
};

// Lead generation operations
const leadAPI = {
  // Submit business contact form
  submitBusinessContact: async (contactData: any) => {
    const response = await apiClient.post(API_ENDPOINTS.LEADS.BUSINESS_CONTACT, contactData);
    return response.data;
  }
};

// Session management operations
const sessionAPI = {
  // Initialize user session
  initialize: async (sessionData: any) => {
    const response = await apiClient.post(API_ENDPOINTS.SESSION.INITIALIZE, sessionData);
    return response.data;
  }
};

// Consent management operations
const consentAPI = {
  // Update user consent preferences
  update: async (consentData: any) => {
    const response = await apiClient.post(API_ENDPOINTS.CONSENT.UPDATE, consentData);
    return response.data;
  }
};

// Wallet operations
const walletAPI = {
  // Create new wallet
  create: async (walletData: any) => {
    const response = await apiClient.post(API_ENDPOINTS.WALLET.CREATE, walletData);
    return response.data;
  },
  
  // Get wallet balance
  getBalance: async (userId: string) => {
    const response = await apiClient.get(`${API_ENDPOINTS.WALLET.BALANCE}/${userId}`);
    return response.data;
  }
};

// Payment operations
const paymentAPI = {
  // Create new payment
  create: async (paymentData: any) => {
    const response = await apiClient.post(API_ENDPOINTS.PAYMENTS.CREATE, paymentData);
    return response.data;
  },
  
  // Get payment status
  getStatus: async (paymentId: string) => {
    const response = await apiClient.get(`${API_ENDPOINTS.PAYMENTS.STATUS}/${paymentId}`);
    return response.data;
  },
  
  // Get payment history
  getHistory: async (userId: string, limit: number = 50) => {
    const response = await apiClient.get(`${API_ENDPOINTS.PAYMENTS.HISTORY}/${userId}?limit=${limit}`);
    return response.data;
  }
};

// Portfolio operations
const portfolioAPI = {
  // Get portfolio overview
  getOverview: async (userId: string) => {
    const response = await apiClient.get(`${API_ENDPOINTS.PORTFOLIO.OVERVIEW}/${userId}`);
    return response.data;
  },
  
  // Get portfolio holdings
  getHoldings: async (userId: string) => {
    const response = await apiClient.get(`${API_ENDPOINTS.PORTFOLIO.HOLDINGS}/${userId}`);
    return response.data;
  }
};

/**
 * CRITICAL FIX: Enhanced error handling utilities
 */
const handleApiError = (error: any) => {
  const status = error.response?.status;
  const detail = error.response?.data?.detail || error.message;
  
  switch (status) {
    case 400:
      console.error('[API] Bad Request:', detail);
      throw new Error(`Invalid request: ${detail}`);
    case 401:
      console.error('[API] Unauthorized access');
      // Trigger auth refresh or redirect to login
      window.location.href = '/auth';
      throw new Error('Please log in to continue');
    case 403:
      console.error('[API] Forbidden access:', detail);
      throw new Error(`Access denied: ${detail}`);
    case 404:
      console.error('[API] Resource not found:', detail);
      throw new Error(`Resource not found: ${detail}`);
    case 405:
      console.error('[API] Method not allowed:', detail);
      throw new Error(`Operation not supported: ${detail}`);
    case 409:
      console.error('[API] Conflict:', detail);
      throw new Error(`Conflict: ${detail}`);
    case 422:
      console.error('[API] Validation error:', detail);
      throw new Error(`Validation failed: ${detail}`);
    case 429:
      console.error('[API] Rate limit exceeded');
      throw new Error('Too many requests. Please try again later.');
    case 500:
      console.error('[API] Server error:', detail);
      throw new Error('Server error. Please try again later.');
    default:
      console.error('[API] Unknown error:', error);
      throw new Error(`Network error: ${detail || 'Please check your connection'}`);
  }
};

/**
 * CRITICAL FIX: Request retry mechanism with exponential backoff
 */
const retryRequest = async <T>(
  requestFn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> => {
  let lastError: any;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await requestFn();
    } catch (error: any) {
      lastError = error;
      
      // Don't retry on certain error types
      const status = error.response?.status;
      if (status && [400, 401, 403, 404, 422].includes(status)) {
        throw error;
      }
      
      // If this was the last attempt, throw the error
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Calculate delay with exponential backoff and jitter
      const delay = baseDelay * Math.pow(2, attempt) + Math.random() * 1000;
      console.log(`[API Retry] Attempt ${attempt + 1} failed, retrying in ${delay}ms...`);
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
};

/**
 * CRITICAL FIX: Enhanced API client with automatic retry for specific operations
 */
const createRetryableRequest = <T>(requestFn: () => Promise<T>) => {
  return () => retryRequest(requestFn, 3, 1000);
};

// Enhanced user operations with retry logic
const enhancedUserAPI = {
  getProfile: createRetryableRequest(() => userAPI.getProfile()),
  createProfile: createRetryableRequest((data: any) => userAPI.createProfile(data)),
  updateProfile: createRetryableRequest((data: any) => userAPI.updateProfile(data))
};

/**
 * CRITICAL FIX: Debug utilities for troubleshooting API issues
 */
const debugAPI = {
  logEndpoints: () => {
    console.log('[API Debug] Available endpoints:', API_ENDPOINTS);
  },
  
  testConnectivity: async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();
      console.log('[API Debug] Health check:', data);
      return data;
    } catch (error) {
      console.error('[API Debug] Connectivity test failed:', error);
      throw error;
    }
  },
  
  logRequestConfig: (config: any) => {
    console.log('[API Debug] Request config:', {
      method: config.method,
      url: config.url,
      baseURL: config.baseURL,
      headers: Object.keys(config.headers || {}),
      hasAuth: !!config.headers?.Authorization
    });
  }
};

/**
 * CRITICAL FIX: Batch operations for improved performance
 */
const batchAPI = {
  // Batch multiple API calls with proper error handling
  execute: async (requests: Array<() => Promise<any>>) => {
    const results = await Promise.allSettled(requests.map(req => req()));
    
    const successful = results
      .filter((result): result is PromiseFulfilledResult<any> => result.status === 'fulfilled')
      .map(result => result.value);
    
    const failed = results
      .filter((result): result is PromiseRejectedResult => result.status === 'rejected')
      .map(result => result.reason);
    
    if (failed.length > 0) {
      console.warn('[API Batch] Some requests failed:', failed);
    }
    
    return { successful, failed, totalRequests: requests.length };
  }
};

// FIXED: Single export block - no duplicates
export {
  apiClient,
  API_ENDPOINTS,
  userAPI,
  kycAPI,
  leadAPI,
  sessionAPI,
  consentAPI,
  walletAPI,
  paymentAPI,
  portfolioAPI,
  enhancedUserAPI,
  handleApiError,
  retryRequest,
  createRetryableRequest,
  debugAPI,
  batchAPI
};

export default apiClient;