import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Session } from '@supabase/supabase-js';
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
  isDemoMode: boolean;
}

interface AuthContextType extends AuthState {
  signUp: (email: string, password: string, options?: { firstName?: string; lastName?: string; countryCode?: string }) => Promise<{ success: boolean; error?: string }>;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  completeOnboarding: () => Promise<void>;
  triggerWalletCreation: () => Promise<{ success: boolean; mnemonic: string | null }>;
  fetchUserProfile: () => Promise<UserProfile | null>;
  refreshKycStatus: () => Promise<void>;
  skipVerification: () => Promise<void>;
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
    try {
      const { data } = await retryWithBackoff(() => apiClient.get<UserProfile>(API_ENDPOINTS.USER.PROFILE), 2, 1000);
      return data;
    } catch (error: any) {
      console.error('AuthContext: Failed to fetch user profile after retries:', error);
      if (error?.response?.status === 401 || error?.response?.status === 404) {
        toast.error('Your session seems to be invalid. Please sign in again.');
        await supabase.auth.signOut();
      } else {
        toast.error('Could not connect to the server. Please check your connection.');
      }
      return null;
    }
  }, []);

  const refreshKycStatus = useCallback(async () => {
    try {
      const userProfile = await fetchUserProfile();
      if (userProfile) {
        setState(prev => ({ ...prev, user: userProfile }));
      }
    } catch (error) {
      console.error('Failed to refresh KYC status:', error);
    }
  }, [fetchUserProfile]);

  const skipVerification = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true }));
      await apiClient.post('/api/kyc/skip');
      await refreshKycStatus();
      toast.success('Verification skipped. You can complete it later from your profile.');
    } catch (error: any) {
      console.error('Failed to skip verification:', error);
      toast.error(error.response?.data?.detail || 'Failed to skip verification');
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [refreshKycStatus]);

  useEffect(() => {
    setState(prev => ({ ...prev, loading: true }));

    const { data: authListener } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log(`[Auth State Change] Event: ${event}`);
      
      if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') {
        setTimeout(async () => {
            if (session) {
                const userProfile = await fetchUserProfile();
                if (userProfile) {
                    setState(prev => ({ ...prev, session, user: userProfile, loading: false, error: null }));
                    
                    if (userProfile.kyc_status === 'skipped') {
                        navigate('/dashboard');
                    } else if (!userProfile.kyc_status || userProfile.kyc_status === 'unverified' || userProfile.kyc_level === 0) {
                        navigate('/onboarding');
                    } else if (userProfile.kyc_status === 'approved') {
                        navigate('/dashboard');
                    } else {
                        navigate('/onboarding');
                    }
                } else {
                    setState(prev => ({ ...prev, session: null, user: null, loading: false, error: 'Failed to retrieve user profile.' }));
                }
            } else {
                setState(prev => ({ ...prev, session: null, user: null, loading: false, error: null }));
            }
        }, 1000);
      } else if (event === 'SIGNED_OUT') {
        setState({ session: null, user: null, loading: false, error: null, isDemoMode: false });
        navigate('/');
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, [fetchUserProfile, navigate]);

  const signUp = async (
    email: string,
    password: string,
    options: { firstName?: string; lastName?: string; countryCode?: string } = {}
  ) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
        const { error } = await supabase.auth.signUp({
            email,
            password,
            options: {
              data: {
                first_name: options.firstName,
                last_name: options.lastName,
                country_code: options.countryCode
              }
            }
        });
        if (error) throw error;
        toast.success('Sign up successful! Please check your email to verify your account.');
        return { success: true };
    } catch (err: any) {
        console.error('[SignUp Error]', err);
        toast.error(err.message || 'Sign up failed.');
        setState(prev => ({ ...prev, error: err.message, loading: false }));
        return { success: false, error: err.message };
    }
  };

  const signIn = async (email: string, password: string) => {
    setState(prev => ({ ...prev, loading: true, error: null }));
    try {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        return { success: true };
    } catch (err: any) {
        console.error('[SignIn Error]', err);
        toast.error(err.message || 'Sign in failed.');
        setState(prev => ({ ...prev, error: err.message, loading: false }));
        return { success: false, error: err.message };
    }
  };

  const signOut = async () => {
    await supabase.auth.signOut();
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
    toast.success('Setup complete! Welcome to your dashboard.');
    await fetchUserProfile();
    navigate('/dashboard');
  }, [fetchUserProfile, navigate]);

  return (
    <AuthContext.Provider value={{
      ...state,
      signUp,
      signIn,
      signOut,
      completeOnboarding,
      triggerWalletCreation,
      fetchUserProfile,
      refreshKycStatus,
      skipVerification,
    }}>
      {!state.loading ? children : <div>Loading Seamount...</div>}
    </AuthContext.Provider>
  );
};