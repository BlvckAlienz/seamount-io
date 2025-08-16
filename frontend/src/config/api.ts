import axios from 'axios';
import { supabase } from '../lib/supabase'; // Adjust path if needed

// This line is critical. It reads the URL of your Render backend from the Vercel env vars.
const baseURL = import.meta.env.VITE_API_URL;

if (!baseURL) {
  console.error("FATAL: VITE_API_URL is not defined. API calls will fail.");
}

export const apiClient = axios.create({ baseURL });

apiClient.interceptors.request.use(
  async (config) => {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);