// File Location: /frontend/src/config/api.ts
// Updated to support staging token override for automated smoke tests.
// Fixed baseURL to avoid path duplication.

import axios from 'axios';
import { supabase } from '../lib/supabase';

// Base URL (no trailing /api/v1 – calls will append it)
const baseURL = import.meta.env.VITE_API_URL || '/api';

// Staging override token (optional, only used if no Supabase session)
const STAGING_TOKEN = import.meta.env.VITE_STAGING_TOKEN || '';

export const apiClient = axios.create({
  baseURL: baseURL,
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
  (error) => Promise.reject(error)
);