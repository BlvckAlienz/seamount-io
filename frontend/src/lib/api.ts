import axios, { AxiosInstance, AxiosError } from 'axios';

// 🎯 CRITICAL FIX: Use relative paths in development to leverage Vite proxy
const getBaseURL = () => {
  if (import.meta.env.DEV) {
    console.log('🔧 API: Using relative paths (Vite proxy)');
    return ''; // Empty string = relative to current origin (localhost:5173)
  }
  // Use environment variable in production
  return import.meta.env.VITE_API_URL || 'https://seamount-api.onrender.com';
};

const BASE_URL = getBaseURL();

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });

    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        
        // 🎯 SMART TOKEN LOGIC: Only add token to non-public endpoints
        const isPublicEndpoint = config.url?.includes('/public') || 
                              config.url?.includes('/health') ||
                              config.url?.includes('/session/initialize');
        
        if (token && !isPublicEndpoint) {
          config.headers.Authorization = `Bearer ${token}`;
          console.log(`🔐 API: Token attached to ${config.url}`);
        } else if (!token && !isPublicEndpoint) {
          // Only warn for non-public endpoints that should have tokens
          console.warn(`⚠️ API: No token found for protected endpoint: ${config.url}`);
        } else if (isPublicEndpoint) {
          // Silent for public endpoints - no token needed
          console.log(`🌐 API: Public endpoint - ${config.url}`);
        }
        
        console.log(`🚀 API Call: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => {
        console.log(`✅ API Success: ${response.config.url} - ${response.status}`);
        return response;
      },
      async (error: AxiosError) => {
        console.error(`❌ API Error: ${error.config?.url} - ${error.response?.status}`, error.message);
        
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Generic methods
  async get<T>(url: string, params?: any): Promise<T> {
    const response = await this.client.get<T>(url, { params });
    return response.data;
  }

  async post<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.post<T>(url, data);
    return response.data;
  }

  async put<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.put<T>(url, data);
    return response.data;
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url);
    return response.data;
  }

  async patch<T>(url: string, data?: any): Promise<T> {
    const response = await this.client.patch<T>(url, data);
    return response.data;
  }
}

export const api = new ApiClient();