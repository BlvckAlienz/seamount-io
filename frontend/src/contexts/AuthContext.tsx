// Location: /frontend/src/contexts/AuthContext.tsx
// Key changes are marked with // <<< CHANGE

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { supabase } from '../lib/supabase';
import { Session, User as SupabaseUser } from '@supabase/supabase-js';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../config/api'; // <<< CHANGE: Import our new apiClient

// Define our UserProfile type, matching the backend model
interface UserProfile {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  country_code?: string;
  kyc_level: number;
  kyc_status: string;
  algorand_address?: string;
}

interface AuthState {
  session: Session | null;
  user: UserProfile | null; // <<< CHANGE: Use our detailed UserProfile type
  loading: boolean;
  error: string | null;
  isDemoMode: boolean;
}

interface AuthContextType extends AuthState {
  signUp: (email: string, password: string, country_code: string) => Promise<{ success: boolean; error?: string }>;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  enterDemoMode: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    session: null,
    user: null,
    loading: true,
    error: null,
    isDemoMode: false,
  });
  const navigate = useNavigate();

  // <<< CHANGE: This function fetches our detailed profile from our backend
  const fetchUserProfile = async () => {
    try {
      const { data } = await apiClient.get<UserProfile>('/api/v1/user/profile');
      setState(prev => ({ ...prev, user: data, loading: false }));
    } catch (error) {
      console.error("Failed to fetch user profile:", error);
      setState(prev => ({ ...prev, user: null, loading: false }));
      // If fetching the profile fails, the session might be invalid, so sign out.
      await supabase.auth.signOut();
    }
  };

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setState(prev => ({ ...prev, session, loading: true }));
        if (event === 'SIGNED_IN') {
          await fetchUserProfile(); // <<< CHANGE: Fetch profile on sign-in
          navigate('/dashboard');
        }
        if (event === 'SIGNED_OUT') {
          setState({ session: null, user: null, loading: false, error: null, isDemoMode: false });
          navigate('/');
        }
      }
    );

    // Check for existing session on initial load
    const checkSession = async () => {
        const { data: { session } } = await supabase.auth.getSession();
        if (session) {
            setState(prev => ({ ...prev, session }));
            await fetchUserProfile();
        } else {
            setState(prev => ({ ...prev, loading: false }));
        }
    }
    checkSession();


    return () => subscription.unsubscribe();
  }, [navigate]);
  
  const signUp = async (email: string, password: string, country_code: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    // <<< CHANGE: Pass metadata during sign-up for the trigger
    const { error } = await supabase.auth.signUp({ 
        email, 
        password,
        options: {
            data: {
                country_code: country_code
            }
        }
    });
    
    if (error) {
      setState(prev => ({ ...prev, error: error.message, loading: false }));
      return { success: false, error: error.message };
    }
    // Supabase will send a confirmation email. The onAuthStateChange listener will handle the rest.
    setState(prev => ({ ...prev, loading: false }));
    return { success: true };
  };

  const signIn = async (email: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    
    if (error) {
      setState(prev => ({ ...prev, error: error.message, loading: false }));
      return { success: false, error: error.message };
    }
    // onAuthStateChange will handle successful login
    return { success: true };
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };
  
  const enterDemoMode = () => {
    setState({
      session: null,
      user: {
        id: 'demo-user-123',
        email: 'demo@seamount.io',
        kyc_level: 3,
        kyc_status: 'approved',
      },
      loading: false,
      error: null,
      isDemoMode: true,
    });
    navigate('/dashboard');
  };

  const value = { ...state, signUp, signIn, signOut, enterDemoMode };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};```
