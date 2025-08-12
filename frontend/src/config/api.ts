import axios from 'axios';
import { supabase } from '../lib/supabase';

const baseURL = import.meta.env.VITE_API_URL || 'https://seamount-api.onrender.com';
const STAGING_TOKEN = import.meta.env.VITE_STAGING_TOKEN || '';

export const apiClient = axios.create({
  baseURL,
});

apiClient.interceptors.request.use(
  async (config) => {
    let token = STAGING_TOKEN;
    if (!token) {
      const { data: { session } } = await supabase.auth.getSession();
      token = session?.access_token || '';
    }
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    console.error('API request error:', error);
    return Promise.reject(error);
  }
);