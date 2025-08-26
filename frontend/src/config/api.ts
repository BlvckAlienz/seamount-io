import axios from 'axios';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from './env';

// Create axios instance with configured base URL
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Define API endpoints with proper paths
export const API_ENDPOINTS = {
  PORTFOLIO: {
    SUMMARY: '/api/v1/portfolio/summary',
    HOLDINGS: '/api/v1/portfolio/holdings',
  },
  USER: {
    PROFILE: '/api/v1/user/profile',
    WALLET: '/api/v1/user/wallet',
  },
  KYC: {
    TOKEN: '/api/kyc/token',
    VERIFY: '/api/kyc/verify-documents',
    START_VERIFICATION: '/api/kyc/start-verification',
  },
  INVESTOR: {
    CONTACT: '/api/v1/investor-contact',
  },
  WALLET: {
    CREATE: '/api/wallet/create',
  },
  CONSENT: {
    UPDATE: '/api/v1/consent/update',
    COOKIES: '/api/v1/consent/cookies',
  }
};

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    // FIX: Ensure URL is properly constructed
    if (config.url && !config.url.startsWith('/')) {
      config.url = '/' + config.url;
    }
    
    // Log the full URL being called
    const fullUrl = `${config.baseURL}${config.url}`;
    console.log(`🔄 API Request: ${config.method?.toUpperCase()} ${fullUrl}`);
    
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log(`🔑 Adding auth token to request: ${token.substring(0, 10)}...`);
      } else {
        console.log('⚠️ No auth token available for request');
      }
      
      return config;
    } catch (error) {
      console.error('❌ Failed to get session:', error);
      return config;
    }
  },
  (error) => {
    console.error('❌ Request interceptor error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    const url = error.config?.url || 'unknown';
    const status = error.response?.status || 'no status';
    const message = error.response?.data?.message || error.message;
    
    console.error(`❌ API Request Failed: ${status} ${url} - ${message}`);
    
    if (error.response?.status === 404) {
      console.error(`🔍 404 Error Details:`, {
        fullUrl: `${error.config.baseURL}${error.config.url}`,
        baseURL: error.config.baseURL,
        endpoint: error.config.url,
        method: error.config.method
      });
    }
    
    return Promise.reject(error);
  }
);

// Helper function to get full URL
export const getFullUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};

// Health check
export const checkApiHealth = async (): Promise<boolean> => {
  try {
    const response = await apiClient.get('/api/v1/health');
    console.log('🏥 API Health Check:', response.data);
    return response.status === 200;
  } catch (error) {
    console.error('❌ API Health Check Failed:', error);
    return false;
  }
};

export default apiClient;