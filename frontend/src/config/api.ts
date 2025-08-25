import axios from 'axios';
import { supabase } from '../lib/supabase';
import { API_BASE_URL } from './env'; // Import the configured base URL

// Create axios instance with configured base URL
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  async (config) => {
    // Add debug info about the request
    console.log(`🔄 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    
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
      return config; // Continue without token rather than failing
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
    
    // Specific handling for 404 errors
    if (error.response?.status === 404) {
      console.error(`🔍 404 Error Details:`, {
        url: error.config.url,
        baseURL: error.config.baseURL,
        method: error.config.method,
        data: error.config.data
      });
    }
    
    return Promise.reject(error);
  }
);

// Add a helper function for API health check
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

// Export a function to get the full URL for debugging
export const getFullUrl = (endpoint: string): string => {
  return `${API_BASE_URL}${endpoint}`;
};

// Perform health check on module load
checkApiHealth().then(healthy => {
  if (healthy) {
    console.log('✅ API connection established successfully');
  } else {
    console.error('❌ API connection failed - check configuration');
  }
});

export default apiClient;