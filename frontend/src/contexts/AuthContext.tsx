// File Location: frontend/src/contexts/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Session } from '@supabase/supabase-js';
import { apiClient } from '../config/api';
import { UserProfile } from '../types';
import { supabase } from '../lib/supabase';

interface AuthState {
  session: Session | null;
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  isDemoMode: boolean;
}

interface AuthContextType extends AuthState {
  signUp: (email: string, password: string, country_code: string, options?: { captchaToken?: string }) => Promise<{ success: boolean; error?: string }>;
  signIn: (email: string, password: string, options?: { captchaToken?: string }) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  enterDemoMode: () => void;
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

const AuthProviderContent: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AuthState>({
    session: null,
    user: null,
    loading: true,
    error: null,
    isDemoMode: false,
  });
  const navigate = useNavigate();
  
  const fetchUserProfile = useCallback(async () => {
    try {
      const { data } = await apiClient.get<UserProfile>('/api/v1/user/profile');
      setState(prev => ({ ...prev, user: data }));
    } catch (error) {
      console.error("AuthContext: Failed to fetch user profile, signing out.", error);
      await supabase.auth.signOut();
      setState(prev => ({ ...prev, user: null, session: null }));
    }
  }, []);

  useEffect(() => {
    const checkUserSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setState(prev => ({ ...prev, session, loading: !session }));

      if (session) {
        await fetchUserProfile();
      }
      setState(prev => ({ ...prev, loading: false }));
    };
    
    checkUserSession();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (_event === 'SIGNED_OUT') {
          setState({ session: null, user: null, loading: false, error: null, isDemoMode: false });
          navigate('/');
        } else if (session) {
          setState(prev => ({ ...prev, session }));
          fetchUserProfile();
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [fetchUserProfile, navigate]);

  const retryWithBackoff = async (fn: () => Promise<any>, maxRetries = 3) => {
    let attempt = 0;
    while (attempt < maxRetries) {
      try {
        return await fn();
      } catch (err: any) {
        if (err.status >= 400 && err.status < 500) {
          attempt++;
          const delay = Math.pow(2, attempt) * 1000;
          console.error(`Auth retry ${attempt}/${maxRetries} after ${delay}ms: ${err.message}`);
          await new Promise(res => setTimeout(res, delay));
        } else {
          throw err;
        }
      }
    }
    throw new Error('Max retries reached');
  };

  const signUp = async (email: string, password: string, country_code: string, options: { captchaToken?: string } = {}) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const { error } = await retryWithBackoff(() => 
        supabase.auth.signUp({ 
          email, 
          password,
          options: { data: { country_code }, captchaToken: options.captchaToken }
        })
      );
      if (error) throw error;
      return { success: true };
    } catch (err: any) {
      setState(prev => ({ ...prev, error: err.message }));
      console.error('SignUp error:', err);
      return { success: false, error: err.message };
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  };

  const signIn = async (email: string, password: string, options: { captchaToken?: string } = {}) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
      const { error } = await retryWithBackoff(() => 
        supabase.auth.signInWithPassword({ email, password, options })
      );
      if (error) throw error;
      return { success: true };
    } catch (err: any) {
      console.error('SignIn error:', err);
      setState(prev => ({ ...prev, error: err.message }));
      return { success: false, error: err.message };
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
  };
  
  const enterDemoMode = () => {
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

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return <AuthProviderContent>{children}</AuthProviderContent>;
};