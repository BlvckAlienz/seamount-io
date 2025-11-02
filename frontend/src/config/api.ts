// File: frontend/src/config/api.ts
// 🚨 NUCLEAR OPTION: Complete interceptor rewrite

// ============================================
// 📍 REPLACE ENTIRE INTERCEPTOR SECTION
// (Lines 36-66 in your current file)
// ============================================

// Request interceptor - SIMPLIFIED VERSION
apiClient.interceptors.request.use(
  async (config) => {
    try {
      // Log request
      const fullUrl = `${config.baseURL}${config.url}`;
      console.log(`[API] → ${config.method?.toUpperCase()} ${fullUrl}`);
      
      // Get fresh session
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
      
      if (sessionError) {
        console.error('[API Auth] Session error:', sessionError);
        return config;
      }
      
      const token = sessionData?.session?.access_token;
      
      if (token) {
        // Ensure headers exist
        if (!config.headers) {
          config.headers = {};
        }
        
        // Set authorization
        config.headers['Authorization'] = `Bearer ${token}`;
        console.log('[API] ✅ Auth token attached');
      } else {
        console.warn('[API] ⚠️ No auth token (public endpoint?)');
      }
      
      return config;
    } catch (error) {
      console.error('[API] Interceptor error:', error);
      return config;
    }
  },
  (error) => {
    console.error('[API] Request setup failed:', error);
    return Promise.reject(error);
  }
);

// Response interceptor - SIMPLIFIED VERSION
apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API] ← ${response.status} ${response.config.url}`);
    return response;
  },
  async (error) => {
    const status = error.response?.status;
    const url = error.config?.url;
    
    console.error(`[API] ← ${status} ${url}`);
    
    // Handle auth errors
    if (status === 401 || status === 403) {
      console.error('[API] Auth failed - redirecting to login');
      
      // Check if session still exists
      const { data } = await supabase.auth.getSession();
      
      if (!data.session) {
        // Session expired, redirect to login
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

// ============================================
// 🎯 CRITICAL: Verify this import exists at top
// ============================================
// Make sure you have this at the top of api.ts:
// import { supabase } from '../lib/supabase';

// ============================================
// ✅ AFTER APPLYING THIS FIX:
// ============================================
// 1. Save file
// 2. Hard refresh browser (Ctrl+Shift+R)
// 3. Open DevTools → Console
// 4. Refresh dashboard
// 5. Look for: "[API] ✅ Auth token attached"
// 6. If you see it for every request → FIXED!
// 7. If you DON'T see it → Token not being retrieved
// ============================================