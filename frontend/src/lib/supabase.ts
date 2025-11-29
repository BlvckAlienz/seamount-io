import { createClient } from '@supabase/supabase-js';
import { SUPABASE_URL, SUPABASE_ANON_KEY } from '../config/env';

// Ensure we're not using the database URL directly
let supabaseUrl = SUPABASE_URL || 'https://opqnoficlhbylxfpaehp.supabase.co';

// Make sure we're using https:// URL format, not postgresql:// connection string
if (supabaseUrl.startsWith('postgresql://')) {
  console.error('Invalid Supabase URL format! Using default URL instead.');
  supabaseUrl = 'https://opqnoficlhbylxfpaehp.supabase.co';
}

const supabaseAnonKey = SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9wcW5vZmljbGhieWx4ZnBhZWhwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTAxNzUwNjksImV4cCI6MjA2NTc1MTA2OX0.G0GBnChH_7MugThxXpkYivN_sfBWts6ehaWjtM6B50I';

// ✅ CRITICAL: Configure session persistence
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,           // ✅ Save session to localStorage
    autoRefreshToken: true,          // ✅ Auto-refresh before expiry
    detectSessionInUrl: true,        // ✅ Handle OAuth redirects
    storage: window.localStorage,    // ✅ Use localStorage (NOT sessionStorage)
    storageKey: 'seamount-auth',     // ✅ Custom key to avoid conflicts
  },
});

// Helper function to check if Supabase is available
export const isSupabaseAvailable = (): boolean => {
  return true;
};

// Report if using placeholder credentials
if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
  console.warn('⚠️ Supabase is not configured. Some features will not work.');
  console.warn('Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY environment variables.');
}

// ✅ DEBUG: Log session status on load
supabase.auth.getSession().then(({ data: { session } }) => {
  if (session) {
    console.log('✅ [Supabase] Session found on startup:', {
      userId: session.user.id,
      email: session.user.email,
      expiresAt: new Date(session.expires_at! * 1000).toLocaleString(),
    });
  } else {
    console.warn('⚠️ [Supabase] No session found on startup');
  }
});

export default supabase;