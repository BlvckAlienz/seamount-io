import axios from 'axios';
import { supabase } from '../lib/supabase'; // Adjust path if needed

// Read the environment variable
const baseURL = import.meta.env.VITE_API_URL;

// Critical check: Ensure the variable is set.
if (!baseURL) {
  // This will make it obvious during local development if the .env file is wrong.
  console.error("FATAL ERROR: VITE_API_URL is not defined in your environment variables.");
  // In a deployed environment, we can have a fallback, but the ideal is to fix the env var.
}

export const apiClient = axios.create({
  // Use the variable, or a hardcoded default if it's somehow still missing.
  baseURL: baseURL || 'https://seamount-api.onrender.com', 
});

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