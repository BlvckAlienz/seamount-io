// File: frontend/src/contexts/AuthContext.tsx
// CRITICAL FIX: Line 223-237 - Bulletproof logout with full session clear

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Session } from '@supabase/supabase-js';
import { apiClient } from '../config/api';
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
  role: 'tribe' | 'alien';
}

interface AuthContextType extends AuthState {
  userProfile: UserProfile | null; // ADD THIS
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
  updateUserRole: (role: 'tribe' | 'alien') => void;
  triggerWalletCreation: () => Promise<boolean>;
  refreshProfile: () => Promise<void>;
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
    role: 'alien',
  });
   
  const navigate = useNavigate();

  const fetchUserProfile = useCallback(async (maxRetries: number = 3, delayMs: number = 1000) => {
    try {
      const { data } = await retryWithBackoff(
        () => apiClient.get<{ success: boolean; profile: UserProfile }>('/api/v1/user/profile'),
        maxRetries,
        delayMs
      );
      setState((prev) => ({ ...prev, user: data.profile, error: null }));
      return data.profile;
    } catch (error: any) {
      console.error('AuthContext: Failed to fetch user profile after retries:', error);
      
      if (error?.response?.status === 401) {
        toast.error('Your session has expired. Please sign in again.');
        await supabase.auth.signOut();
      } else if (error?.response?.status === 404) {
        toast.error('Failed to load user profile. Please try again later.');
        setState((prev) => ({ ...prev, error: 'Profile not found.' }));
      } else {
        toast.error('Could not connect to the server. Some features may be unavailable.');
        setState((prev) => ({ ...prev, error: error.message || 'Profile fetch failed' }));
      }
      
      return null;
    }
  }, []);

  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession();
        setState((prev) => ({ ...prev, session, loading: false }));
      } catch (error) {
        console.error('Auth initialization failed:', error);
        setState((prev) => ({ ...prev, error: 'Authentication initialization failed', loading: false }));
      }
    };

    initializeAuth();

    const { data: authListener } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('Auth state changed:', event, session?.user?.id);
      
      setState((prev) => ({ ...prev, session, loading: true }));
      
      if (session && (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED')) {
        setTimeout(async () => {
          await fetchUserProfile(5, 2000);
        }, 1000);
      } else if (event === 'SIGNED_OUT') {
        setState((prev) => ({ ...prev, user: null, error: null }));
      }
      
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
      const signUpOptions: any = {
        email,
        password,
        options: {
          data: {
            firstName: options.firstName || '',
            lastName: options.lastName || '',
            countryCode: options.countryCode || 'US',
          },
        },
      };
      
      if (options.captchaToken) {
        signUpOptions.options.captchaToken = options.captchaToken;
      }

      const { data, error } = await retryWithBackoff(() =>
        supabase.auth.signUp(signUpOptions)
      );
      
      if (error) throw error;
      
      if (data.user && !data.user.email_confirmed_at) {
        toast.success('Please check your email to confirm your account');
      }
      
      return { success: true };
      
    } catch (err: any) {
      setState((prev) => ({ ...prev, error: err.message }));
      console.error('SignUp error:', err);
      
      if (err.message.includes('User already registered')) {
        toast.error('Email already registered. Try signing in instead.');
      } else if (err.message.includes('Email not confirmed')) {
        toast.error('Please check your email and confirm your account');
      } else if (err.message.includes('Password')) {
        toast.error('Password requirements not met');
      } else {
        toast.error(err.message || 'Sign up failed');
      }
      
      return { success: false, error: err.message };
    } finally {
      setState((prev) => ({ ...prev, loading: false }));
    }
  };

  const signIn = async (email: string, password: string, options: { captchaToken?: string } = {}) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    
    try {
      const signInOptions: any = { email, password };
      if (options.captchaToken) {
        signInOptions.options = { captchaToken: options.captchaToken };
      }

      const { error } = await retryWithBackoff(() =>
        supabase.auth.signInWithPassword(signInOptions)
      );
      
      if (error) throw error;
      
      return { success: true };
      
    } catch (err: any) {
      console.error('SignIn error:', err);
      setState((prev) => ({ ...prev, error: err.message }));
      
      if (err.message.includes('Invalid login credentials')) {
        toast.error('Invalid email or password');
      } else if (err.message.includes('Email not confirmed')) {
        toast.error('Please confirm your email before signing in');
      } else {
        toast.error(err.message || 'Sign in failed');
      }
      
      return { success: false, error: err.message };
    } finally {
      setState((prev) => ({ ...prev, loading: false }));
    }
  };

  // ✅ BULLETPROOF LOGOUT FIX
  const signOut = async () => {
    try {
      // 1. Clear Supabase session (server + client)
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('Supabase signOut error:', error);
      }
      
      // 2. Clear all browser storage
      localStorage.clear();
      sessionStorage.clear();
      
      // 3. Clear cookies (if any auth cookies exist)
      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      
      // 4. Clear state
      setState({
        session: null,
        user: null,
        loading: false,
        error: null,
        isDemoMode: false,
        role: 'alien',
      });
      
      // 5. Force hard navigation to clear memory cache
      window.location.href = '/';
    } catch (error) {
      console.error('Sign out error:', error);
      // Even if error, force logout
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = '/';
    }
  };

  const enterDemoMode = () => {
    setState({
      session: null,
      user: {
        id: 'demo-user-123',
        email: 'demo@seamount.io',
        first_name: 'Demo',
        last_name: 'User',
        kyc_level: 3,
        kyc_status: 'approved',
        is_admin: false,
        country_code: 'US',
        created_at: new Date().toISOString(),
      } as UserProfile,
      loading: false,
      error: null,
      isDemoMode: true,
      role: 'alien',
    });
    navigate('/dashboard');
  };

  const updateOnboardingStep = async (step: number, data: any) => {
    try {
      if (state.user) {
        const { error } = await supabase
          .from('user_profiles')
          .update({ kyc_level: step })
          .eq('id', state.user.id);
          
        if (error) throw error;
        
        await fetchUserProfile(3, 1000);
      }
    } catch (err: any) {
      console.error('Update onboarding error:', err);
      toast.error('Failed to update onboarding step');
    }
  };

  const completeOnboarding = async () => {
    try {
      const currentUser = state.user || state.session?.user;
      if (!currentUser?.id) throw new Error('No user ID');

      // 🔥 CRITICAL: Force profile refresh to get wallet address
      await fetchUserProfile();
      
      // Get fresh profile after wallet creation
      const { data: freshProfile } = await supabase
        .from('user_profiles')
        .select('*, user_wallets!inner(algorand_address)')
        .eq('id', currentUser.id)
        .single();

      if (!freshProfile) throw new Error('Profile not found');

      const hasWallet = freshProfile.algorand_address || freshProfile.user_wallets?.algorand_address;
      const isAlien = freshProfile.role === 'alien';
      const hasSkipped = freshProfile.verification_skipped === true;

      // Update role for verified users only
      if (['pending', 'verified'].includes(freshProfile.kyc_status) && !isAlien) {
        await supabase
          .from('user_profiles')
          .update({ role: 'tribe', updated_at: new Date().toISOString() })
          .eq('id', currentUser.id);
      }

      // 🔥 NEW: Force state update with fresh profile
      setState(prev => ({
        ...prev,
        user: {
          ...freshProfile,
          algorand_address: hasWallet ? (freshProfile.algorand_address || freshProfile.user_wallets?.algorand_address) : null
        }
      }));

      // Navigate based on status
      if (isAlien || hasSkipped) {
        toast('⚠️ Complete verification to unlock all features', { 
          duration: 5000,
          icon: '🔐'
        });
      } else {
        toast.success('Welcome to Seamount!');
      }
      
      navigate('/dashboard');
      
    } catch (error) {
      console.error('Onboarding error:', error);
      toast.error('Setup incomplete');
    }
  };
  
  const refreshProfile = useCallback(async () => {
    const currentUser = state.user || state.session?.user;
    if (currentUser?.id) {
      await fetchUserProfile();
    }
  }, [state.user, state.session, fetchUserProfile]);

  const updateUserRole = useCallback((role: 'tribe' | 'alien') => {
    setState(prev => ({ ...prev, role }));
  }, []);

  useEffect(() => {
    if (state.session && state.user && !state.loading) {
      const kycStatus = state.user.kyc_status || 'not_started';
      const hasWallet = state.user.algorand_address || state.user.wallet_address;
      const isAlien = state.user.role === 'alien';
      const hasSkipped = state.user.verification_skipped === true;
      
      // 🔥 NEW: Check if we're currently in onboarding flow
      const currentPath = window.location.pathname;
      const isOnboardingPage = currentPath === '/onboarding';
      
      // ✅ Tribe users (verified) → Dashboard
      if (kycStatus === 'approved' || kycStatus === 'verified' || state.user.role === 'tribe') {
        if (!isOnboardingPage) {
          navigate('/dashboard');
        }
        return;
      }
      
      // 🔥 NEW: Alien users OR users who skipped → Dashboard if they have wallet
      if ((isAlien || hasSkipped) && hasWallet) {
        if (!isOnboardingPage) {
          navigate('/dashboard');
        }
        return;
      }
      
      // 🔥 NEW: Pending support (non-NG) with wallet → Dashboard
      if (kycStatus === 'pending_support' && hasWallet) {
        if (!isOnboardingPage) {
          navigate('/dashboard');
        }
        return;
      }
      
      // ✅ No wallet → Onboarding
      if (!hasWallet && kycStatus === 'not_started' && !hasSkipped && !isOnboardingPage) {
        navigate('/onboarding');
      }
    }
  }, [state.session, state.user, state.loading, navigate]);

  const triggerWalletCreation = useCallback(async () => {
    try {
      const response = await apiClient.post('/api/wallet/create');
      return response.data.success;
    } catch (error) {
      console.error('Wallet creation failed:', error);
      return false;
    }
  }, []);

  return (
    <AuthContext.Provider value={{
      ...state,
      userProfile: state.user,
      updateUserRole,
      triggerWalletCreation,
      signUp,
      signIn,
      signOut,
      enterDemoMode,
      updateOnboardingStep,
      completeOnboarding,
      refreshProfile
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export { AuthProviderContent as AuthProvider };