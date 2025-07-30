import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { Session } from '@supabase/supabase-js';
import { apiClient } from '../config/api';
import { UserProfile } from '../types';

interface AuthState {
  session: Session | null;
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  isDemoMode: boolean;
}

interface AuthContextType extends AuthState {
  signUp: (email: string, password: string, country_code: string) => Promise<{ success: boolean; error?: string }>;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  enterDemoMode: (navigate: (path: string) => void) => void;
  onboardingStep?: number;
  updateOnboardingStep: (step: number, data: any) => Promise<void>;
  completeOnboarding: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}

// AuthProvider content is now a separate component.
// This allows it to be a child of the Router and use navigation hooks.
const AuthProviderContent: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    session: null,
    user: null,
    loading: true,
    error: null,
    isDemoMode: false,
  });
  
  const fetchUserProfile = useCallback(async () => {
    try {
      const { data } = await apiClient.get<UserProfile>('/api/v1/user/profile');
      setState(prev => ({ ...prev, user: data, loading: false }));
    } catch (error) {
      console.error("AuthContext: Failed to fetch user profile:", error);
      setState(prev => ({ ...prev, user: null, loading: false }));
      await supabase.auth.signOut();
    }
  }, []);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setState(prev => ({ ...prev, session, error: null }));
        if (event === 'SIGNED_IN') {
          await fetchUserProfile();
        }
        if (event === 'SIGNED_OUT') {
          setState({ session: null, user: null, loading: false, error: null, isDemoMode: false });
        }
      }
    );

    const checkInitialSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (session) {
        setState(prev => ({ ...prev, session }));
        await fetchUserProfile();
      } else {
        setState(prev => ({ ...prev, loading: false }));
      }
    }
    checkInitialSession();

    return () => subscription.unsubscribe();
  }, [fetchUserProfile]);

  const signUp = async (email: string, password: string, country_code: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    const { error } = await supabase.auth.signUp({ 
        email, 
        password,
        options: { data: { country_code } }
    });
    if (error) {
      setState(prev => ({ ...prev, error: error.message, loading: false }));
      return { success: false, error: error.message };
    }
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
    return { success: true };
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };
  
  const enterDemoMode = (navigate: (path: string) => void) => {
    setState({
      session: null,
      user: {
        id: 'demo-user-123', email: 'demo@seamount.io', kyc_level: 3,
        kyc_status: 'approved', is_admin: false,
      } as UserProfile,
      loading: false, error: null, isDemoMode: true,
    });
    navigate('/dashboard');
  };

  const updateOnboardingStep = async (step: number, data: any) => {
    console.log("Updating onboarding step:", step, data);
  };
  const completeOnboarding = async () => {
    console.log("Completing onboarding...");
  };

  const value = { 
    ...state, signUp, signIn, signOut, enterDemoMode,
    onboardingStep: state.user?.kyc_level === 0 ? 1 : undefined,
    updateOnboardingStep, completeOnboarding
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// The exported AuthProvider now only wraps the content component.
export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return <AuthProviderContent>{children}</AuthProviderContent>;
};