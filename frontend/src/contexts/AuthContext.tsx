import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Session, User } from '@supabase/supabase-js';
import { apiClient, API_ENDPOINTS } from '../config/api';
import { UserProfile } from '../types';
import { supabase } from '../lib/supabase';
import { retryWithBackoff } from '../utils/retry';
import toast from 'react-hot-toast';

interface AuthState {
  session: Session | null;
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  isDemoMode: boolean; // Retained for potential future use
}

interface AuthContextType extends AuthState {
  signUp: (email: string, password: string, options?: { firstName?: string; lastName?: string }) => Promise<{ success: boolean; error?: string }>;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  completeOnboarding: () => Promise<void>;
  triggerWalletCreation: () => Promise<{ success: boolean; mnemonic: string | null }>;
  fetchUserProfile: () => Promise<UserProfile | null>;
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

  const fetchUserProfile = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true }));
    try {
      const { data } = await retryWithBackoff(() => apiClient.get<UserProfile>(API_ENDPOINTS.USER.PROFILE));
      setState((prev) => ({ ...prev, user: data, error: null, loading: false }));
      return data;
    } catch (error: any) {
      console.error('AuthContext: Failed to fetch user profile after retries:', error);
      // If profile fetch fails, it's a critical error. Sign out to reset state.
      if (error?.response?.status === 401 || error?.response?.status === 404) {
        toast.error('Your session is invalid. Please sign in again.');
        await supabase.auth.signOut();
      } else {
        toast.error('Could not connect to the server. Please check your connection.');
      }
      setState((prev) => ({ ...prev, user: null, error: 'Profile fetch failed', loading: false }));
      return null;
    }
  }, []);

  useEffect(() => {
    const { data: authListener } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log(`[Auth State Change] Event: ${event}`);
      setState((prev) => ({ ...prev, session, loading: true }));
      
      if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') {
        if (session) {
          const userProfile = await fetchUserProfile();
          // After fetching profile, we determine where the user should go.
          if (userProfile) {
            if (userProfile.kyc_status === 'unverified' && userProfile.kyc_level === 0) {
              navigate('/onboarding');
            } else {
              navigate('/dashboard');
            }
          }
        } else {
          setState((prev) => ({ ...prev, loading: false, user: null }));
        }
      } else if (event === 'SIGNED_OUT') {
        setState({ session: null, user: null, loading: false, error: null, isDemoMode: false });
        navigate('/');
      } else if (event === 'TOKEN_REFRESHED') {
        if (session) await fetchUserProfile();
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [fetchUserProfile, navigate]);

  const signUp = async (
    email: string,
    password: string,
    options: { firstName?: string; lastName?: string } = {}
  ) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            first_name: options.firstName || '', // Match DB column name
            last_name: options.lastName || '',   // Match DB column name
          },
        },
      });
      if (error) throw error;
      toast.success('Sign up successful! Please check your email to verify your account.');
      return { success: true };
    } catch (err: any) {
      console.error('[SignUp Error]', err);
      toast.error(err.message || 'Sign up failed. Please try again.');
      setState((prev) => ({ ...prev, error: err.message, loading: false }));
      return { success: false, error: err.message };
    }
  };

  const signIn = async (email: string, password: string) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      // The onAuthStateChange listener will handle fetching the profile and redirecting.
      return { success: true };
    } catch (err: any) {
      console.error('[SignIn Error]', err);
      toast.error(err.message || 'Sign in failed. Please try again.');
      setState((prev) => ({ ...prev, error: err.message, loading: false }));
      return { success: false, error: err.message };
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    // The onAuthStateChange listener will handle state cleanup and navigation.
  };

  const triggerWalletCreation = useCallback(async () => {
    try {
      const { data } = await apiClient.post<{ success: boolean, mnemonic: string | null }>(API_ENDPOINTS.WALLET.CREATE);
      return data;
    } catch (error) {
      console.error('Wallet creation failed:', error);
      toast.error('A server error occurred while creating your wallet.');
      return { success: false, mnemonic: null };
    }
  }, []);

  const completeOnboarding = useCallback(async () => {
    // This function's main job is now to simply re-fetch the user profile.
    // The backend and KYC flow will have set the correct status.
    // The useEffect listener will then handle the redirect to the dashboard.
    toast.success('Setup complete! Welcome to your dashboard.');
    await fetchUserProfile();
  }, [fetchUserProfile]);

  return (
    <AuthContext.Provider value={{
      ...state,
      signUp,
      signIn,
      signOut,
      completeOnboarding,
      triggerWalletCreation,
      fetchUserProfile,
    }}>
      {!state.loading && children}
    </AuthContext.Provider>
  );
};