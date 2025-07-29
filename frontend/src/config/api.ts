// File Location: /frontend/src/config/api.ts
// The definitive, simplified API client for a unified monorepo deployment.

import axios from 'axios';
import { supabase } from '../lib/supabase';

// Vite automatically makes VITE_ variables available via import.meta.env
// The baseURL should be the relative path to our API, as defined in vercel.json rewrites.
const baseURL = import.meta.env.VITE_API_URL || '/api';

export const apiClient = axios.create({
  baseURL: baseURL,
});

// This interceptor is critical. It automatically adds the user's login token
// to every single request sent to our backend.
apiClient.interceptors.request.use(
  async (config) => {
    // Get the active session from Supabase
    const { data: { session } } = await supabase.auth.getSession();
    
    if (session?.access_token) {
      // If a session exists, add the JWT as a Bearer token
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
    
    return config;
  },
  (error) => {
    // Handle any request errors
    return Promise.reject(error);
  }
);

// We no longer need the complex getApiBaseUrl or buildApiUrl functions.
// The setup is now simple, robust, and correct for the Vercel monorepo architecture.