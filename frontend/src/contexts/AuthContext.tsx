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
  refreshUserProfile: () => Promise<UserProfile | null>;
  forceKYCStatus: (status: string) => Promise<void>; // 🚀 NEW: Force status update
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

  const refreshUserProfile = useCallback(async () => {
    try {
      console.log('Refreshing user profile...');
      const profile = await fetchUserProfile(3, 1000);
      console.log('User profile refreshed:', profile);
      return profile;
    } catch (error) {
      console.error('Failed to refresh user profile:', error);
      return null;
    }
  }, [fetchUserProfile]);

  // 🚀 NUCLEAR FIX: Force KYC status update
  const forceKYCStatus = useCallback(async (status: string) => {
    try {
      if (state.user) {
        const { error } = await supabase
          .from('user_profiles')
          .update({ kyc_status: status })
          .eq('id', state.user.id);
          
        if (error) throw error;
        
        await refreshUserProfile();
        toast.success(`KYC status updated to: ${status}`);
      }
    } catch (error) {
      console.error('Force KYC status error:', error);
      toast.error('Failed to update KYC status');
    }
  }, [state.user, refreshUserProfile]);

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

  // 🚀 CRITICAL FIX: SMART KYC ROUTING - NO MORE LOOPS
  useEffect(() => {
    if (state.session && state.user && !state.loading) {
      console.log('🔐 AUTH: Checking KYC status for routing...');
      console.log('📊 User KYC Status:', state.user.kyc_status);
      console.log('🌍 User Country:', state.user.country_code);
      console.log('👤 User Role:', state.user.role);
      
      const kycStatus = state.user.kyc_status || 'not_started';
      const currentPath = window.location.pathname;
      
      // 🎯 INTELLIGENT ROUTING LOGIC
      if (kycStatus === 'verified' || kycStatus === 'approved') {
        console.log('✅ KYC Verified - routing to dashboard');
        updateUserRole('tribe');
        if (currentPath === '/onboarding') {
          navigate('/dashboard');
        }
      } 
      else if (kycStatus === 'skipped') {
        console.log('⏭️ KYC Skipped - routing to dashboard');
        updateUserRole('alien');
        if (currentPath === '/onboarding') {
          navigate('/dashboard');
        }
      }
      else if (kycStatus === 'not_started') {
        console.log('🚀 KYC Not Started - routing to onboarding');
        if (currentPath !== '/onboarding') {
          navigate('/onboarding');
        }
      }
      else if (kycStatus === 'pending' || kycStatus === 'in_progress' || kycStatus === 'under_review') {
        console.log('⏳ KYC In Progress - routing to dashboard with status');
        // User can use platform while KYC is processing
        if (currentPath === '/onboarding') {
          navigate('/dashboard');
        }
      }
      else if (kycStatus === 'rejected') {
        console.log('❌ KYC Rejected - staying on current page for resubmission');
        // Stay on current page, show rejection message
      }
      // For any other status, don't automatically redirect
    }
  }, [state.session, state.user, state.loading, navigate]);

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
      
      console.log('Sign up successful, profile will be created automatically');
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

  const signOut = async () => {
    try {
      await supabase.auth.signOut();
      setState((prev) => ({ 
        ...prev, 
        session: null, 
        user: null, 
        error: null, 
        isDemoMode: false 
      }));
      navigate('/');
    } catch (error) {
      console.error('Sign out error:', error);
      toast.error('Sign out failed');
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
    console.log('Updating onboarding step:', step, data);
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
      if (state.user) {
        const { error } = await supabase
          .from("user_profiles")
          .update({ 
            kyc_status: 'skipped',
            kyc_level: 1,
            role: 'alien'
          })
          .eq("id", state.user.id);
          
        await fetchUserProfile(3, 1000);
        navigate('/dashboard');
        toast.success('Onboarding completed successfully!');
      }
    } catch (err: any) {
      console.error('Complete onboarding error:', err);
      toast.error('Failed to complete onboarding');
    }
  };

  const updateUserRole = useCallback((role: 'tribe' | 'alien') => {
    setState(prev => ({ ...prev, role }));
  }, []);

  const triggerWalletCreation = useCallback(async () => {
    try {
      const response = await apiClient.post('/api/v1/user/provision-wallets');
      return response.data.success;
    } catch (error) {
      console.error('Wallet creation failed:', error);
      return false;
    }
  }, []);

  return (
    <AuthContext.Provider value={{
      ...state,
      refreshUserProfile,
      forceKYCStatus, // 🚀 ADDED
      updateUserRole,
      triggerWalletCreation,
      signUp,
      signIn,
      signOut,
      enterDemoMode,
      updateOnboardingStep,
      completeOnboarding
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export { AuthProviderContent as AuthProvider };