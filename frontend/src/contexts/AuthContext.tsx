import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Session, SupabaseClient } from '@supabase/supabase-js';
import { apiClient } from '../config/api';
import { UserProfile } from '../types';
import { supabase } from '../lib/supabase';
import { retryWithBackoff } from '../utils/retry';

interface AuthState {
  session: Session | null;
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  isDemoMode: boolean;
}

interface AuthContextType extends AuthState {
  signUp: (
    email: string,
    password: string,
    options?: { firstName?: string; lastName?: string; countryCode?: string; captchaToken?: string }
  ) => Promise<{ success: boolean; error?: string }>;
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
      setState((prev) => ({ ...prev, user: data }));
    } catch (error) {
      console.error('AuthContext: Failed to fetch user profile, signing out.', error);
      await supabase.auth.signOut();
      setState((prev) => ({ ...prev, user: null, session: null }));
    }
  }, []);

  useEffect(() => {
    const initializeAuth = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setState((prev) => ({ ...prev, session, loading: true }));
      if (session) await fetchUserProfile();
      setState((prev) => ({ ...prev, loading: false }));
    };

    initializeAuth();

    const { data: authListener } = supabase.auth.onAuthStateChange(async (event, session) => {
      setState((prev) => ({ ...prev, session, loading: true }));
      if (session) await fetchUserProfile();
      else setState((prev) => ({ ...prev, user: null }));
      setState((prev) => ({ ...prev, loading: false }));
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [fetchUserProfile]);

  const signUp = async (
    email: string,
    password: string,
    options: { firstName?: string; lastName?: string; countryCode?: string; captchaToken?: string } = {}
  ) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const signUpOptions: any = { email, password };
      if (options.captchaToken) signUpOptions.options = { captchaToken: options.captchaToken };
      const { data, error } = await retryWithBackoff(() =>
        supabase.auth.signUp({
          ...signUpOptions,
          options: {
            ...signUpOptions.options,
            data: {
              firstName: options.firstName || '',
              lastName: options.lastName || '',
              countryCode: options.countryCode || 'US',
            },
          },
        })
      );
      if (error) throw error;
      if (data.user) {
        await supabase.from('user_profiles').insert({
          id: data.user.id,
          email: data.user.email,
          first_name: options.firstName || '',
          last_name: options.lastName || '',
          country_code: options.countryCode || 'US',
          kyc_level: 0,
          kyc_status: 'pending',
          is_admin: false,
          created_at: new Date().toISOString(),
        });
        await fetchUserProfile();
      }
      return { success: true };
    } catch (err: any) {
      setState((prev) => ({ ...prev, error: err.message }));
      console.error('SignUp error:', err);
      return { success: false, error: err.message };
    } finally {
      setState((prev) => ({ ...prev, loading: false }));
    }
  };

  const signIn = async (email: string, password: string, options: { captchaToken?: string } = {}) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const { error } = await retryWithBackoff(() =>
        supabase.auth.signInWithPassword({ email, password, options })
      );
      if (error) throw error;
      await fetchUserProfile();
      return { success: true };
    } catch (err: any) {
      console.error('SignIn error:', err);
      setState((prev) => ({ ...prev, error: err.message }));
      return { success: false, error: err.message };
    } finally {
      setState((prev) => ({ ...prev, loading: false }));
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setState((prev) => ({ ...prev, session: null, user: null, error: null, isDemoMode: false }));
    navigate('/login');
  };

  const enterDemoMode = () => {
    setState({
      session: null,
      user: {
        id: 'demo-user-123',
        email: 'demo@seamount.io',
        kyc_level: 3,
        kyc_status: 'approved',
        is_admin: false,
      } as UserProfile,
      loading: false,
      error: null,
      isDemoMode: true,
    });
    navigate('/dashboard');
  };

  const updateOnboardingStep = async (step: number, data: any) => {
    console.log('Updating onboarding step:', step, data);
    try {
      if (state.user) {
        await supabase.from('user_profiles').update({ kyc_level: step }).eq('id', state.user.id);
        await fetchUserProfile();
      }
    } catch (err) {
      console.error('Update onboarding error:', err);
    }
  };

  const completeOnboarding = async () => {
    console.log('Completing onboarding...');
    try {
      if (state.user) {
        await supabase.from('user_profiles').update({ kyc_status: 'completed', kyc_level: 1 }).eq('id', state.user.id);
        await fetchUserProfile();
        navigate('/dashboard');
      }
    } catch (err) {
      console.error('Complete onboarding error:', err);
    }
  };

  const value = {
    ...state,
    signUp,
    signIn,
    signOut,
    enterDemoMode,
    onboardingStep: state.user?.kyc_level === 0 ? 1 : undefined,
    updateOnboardingStep,
    completeOnboarding,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  return <AuthProviderContent>{children}</AuthProviderContent>;
};