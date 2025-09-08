// File: frontend/src/config/api.ts
// FIXED: Removed duplicate API_ENDPOINTS export

import axios from 'axios';

// Define the base URL for the API
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://seamount-api.onrender.com';

// Create an axios instance with default config
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('supabase.auth.token');
    if (token) {
      const parsedToken = JSON.parse(token);
      config.headers.Authorization = `Bearer ${parsedToken.access_token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('supabase.auth.token');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// Define the API endpoints - SINGLE DEFINITION
export const API_ENDPOINTS = {
  SESSION: {
    INITIALIZE: '/api/v1/session/initialize',
  },
  USER: {
    PROFILE: '/api/v1/user/profile',
    UPDATE: '/api/v1/user/profile'
  },
  KYC: {
    START_VERIFICATION: '/api/v1/kyc/start-verification',
    STATUS: '/api/v1/kyc/status'
  },
  WALLET: {
    CREATE: '/api/wallet/create'
  }
};

// Function to initialize session
export const initializeSession = async (): Promise<string> => {
  try {
    const response = await apiClient.post(API_ENDPOINTS.SESSION.INITIALIZE);
    return response.data.session_id;
  } catch (error) {
    console.error('Session initialization failed, continuing without cookie banner');
    return 'anonymous-session-fallback';
  }
};

// User API functions
export const userAPI = {
  getProfile: () => apiClient.get(API_ENDPOINTS.USER.PROFILE),
  updateProfile: (data: any) => apiClient.put(API_ENDPOINTS.USER.UPDATE, data),
};

// KYC API functions
export const kycAPI = {
  startVerification: () => apiClient.post(API_ENDPOINTS.KYC.START_VERIFICATION),
  getStatus: () => apiClient.get(API_ENDPOINTS.KYC.STATUS),
};

// Wallet API functions
export const walletAPI = {
  create: () => apiClient.post(API_ENDPOINTS.WALLET.CREATE),
};

// Export everything in a single statement to avoid duplicates
export {
  apiClient,
  // API_ENDPOINTS is already exported above, don't re-export it here
  userAPI,
  kycAPI,
  walletAPI,
  initializeSession,
};