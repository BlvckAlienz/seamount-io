import axios, { AxiosInstance, AxiosError } from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';

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
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired - clear auth and redirect to login
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

  // Auth endpoints
  async login(email: string, password: string) {
    return this.post('/auth/login', { email, password });
  }

  async register(email: string, password: string, fullName: string) {
    return this.post('/auth/register', { email, password, full_name: fullName });
  }

  async logout() {
    return this.post('/auth/logout');
  }

  // Wallet endpoints
  async getWalletBalance() {
    return this.get('/wallet/balance');
  }

  async fundWallet(amount: number, paymentMethod: string) {
    return this.post('/wallet/fund', { amount, payment_method: paymentMethod });
  }

  async withdrawFromWallet(amount: number, destination: string) {
    return this.post('/wallet/withdraw', { amount, destination });
  }

  // Payment endpoints
  async createPayment(data: any) {
    return this.post('/payments/create', data);
  }

  async getPaymentHistory() {
    return this.get('/payments/history');
  }

  async getPaymentById(id: string) {
    return this.get(`/payments/${id}`);
  }
}

export const api = new ApiClient();