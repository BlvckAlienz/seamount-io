import axios from 'axios';
import { supabase } from '../lib/supabase';

const baseURL = import.meta.env.VITE_API_URL || 'https://seamount-api.onrender.com';

export const apiClient = axios.create({ baseURL });

apiClient.interceptors.request.use(
  async (config) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log('[api] Setting token prefix: ' + token.slice(0,6));
      } else {
        console.warn('[api] no Supabase session token — request will be unauthenticated');
      }
      return config;
    } catch (e) {
      console.error('[api] failed to get session token', e);
      return config;
    }
  },
  (error) => {
    console.error('[api] request setup error:', error);
    return Promise.reject(error);
  }
);