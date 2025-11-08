import { useEffect } from 'react';
import { api } from '@/lib/api';

export function DebugEnv() {
  useEffect(() => {
    console.log('🔍 ENVIRONMENT DEBUG:');
    console.log('VITE_API_URL:', import.meta.env.VITE_API_URL);
    console.log('NODE_ENV:', import.meta.env.MODE);
    console.log('DEV:', import.meta.env.DEV);
    console.log('PROD:', import.meta.env.PROD);
    
    // Test API connection
    api.get('/api/v1/health').then(() => {
      console.log('✅ API Health Check: SUCCESS');
    }).catch((err) => {
      console.error('❌ API Health Check: FAILED', err);
    });
  }, []);

  return null;
}