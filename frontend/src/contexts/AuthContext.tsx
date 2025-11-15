// File: frontend/src/contexts/AuthContext.tsx
// ✅ PRODUCTION READY - HYBRID WALLET DETECTION
// Fast profile checks + API fallback for accuracy

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Session } from '@supabase/supabase-js';
import { apiClient } from '../config/api';
import { UserProfile } from '../types';
import { supabase } from '../lib/supabase';
import { retryWithBackoff } from '../utils/retry';
import toast from 'react-hot-toast';
import { toastInfo, toastWarning } from '@/lib/toast-helpers';

interface AuthState {
  session: Session | null;
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  isDemoMode: boolean;
  role: 'tribe' | 'alien';
}

interface AuthContextType extends AuthState {
  userProfile: UserProfile | null;
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
  // ADD THESE TWO PROPERTIES:
  kycStatus: string;
  skipVerification: () => void;
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
          
          // ✅ CHECK IF WALLETS NEED TO BE CREATED
          if (event === 'SIGNED_IN') {
            try {
              const walletStatusResponse = await apiClient.get('/api/v1/wallet-creation/status');
              
              if (walletStatusResponse.data.success) {
                const missingWallets = walletStatusResponse.data.summary?.missing_chains || [];
                
                if (missingWallets.length > 0) {
                  console.log('[Auth] 📍 User missing wallets, triggering creation...');
                  
                  setTimeout(async () => {
                    try {
                      const createResponse = await apiClient.post('/api/v1/wallet/create');
                      
                      if (createResponse.data.success) {
                        console.log('[Auth] ✅ Wallets created on login:', createResponse.data.created_chains);
                        
                        sessionStorage.setItem('show_wallet_backup', 'true');
                        sessionStorage.setItem('new_wallets', JSON.stringify(createResponse.data.created_chains));
                        
                        toast.success('🎉 Your wallets are ready! Please back them up.');
                      }
                    } catch (createError) {
                      console.error('[Auth] Wallet creation on login failed:', createError);
                    }
                  }, 1500);
                }
              }
            } catch (statusError) {
              console.error('[Auth] Wallet status check failed:', statusError);
            }
          }
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

      // ✅ CREATE USER PROFILE
      if (data.user) {
        try {
          console.log('[Auth] Creating user profile for:', data.user.id);
          
          const profileData = {
            id: data.user.id,
            email: data.user.email,
            firstName: options.firstName || '',
            lastName: options.lastName || '',
            countryCode: options.countryCode || 'US'
          };
          
          const profileResponse = await apiClient.post('/api/v1/user/profile', profileData);
          
          if (profileResponse.data.success) {
            console.log('[Auth] ✅ Profile created:', profileResponse.data.profile);
            
            if (!data.user.email_confirmed_at) {
              toast.success('Please check your email to confirm your account');
            } else {
              console.log('[Auth] 📍 Triggering wallet creation...');
              
              setTimeout(async () => {
                try {
                  const walletResponse = await apiClient.post('/api/v1/wallet/create');
                  
                  if (walletResponse.data.success) {
                    console.log('[Auth] ✅ Wallets created:', walletResponse.data.created_chains);
                    sessionStorage.setItem('show_wallet_backup', 'true');
                    sessionStorage.setItem('new_wallets', JSON.stringify(walletResponse.data.created_chains));
                  }
                } catch (walletError) {
                  console.error('[Auth] ❌ Wallet creation failed:', walletError);
                }
              }, 2000);
            }
          }
        } catch (profileError) {
          console.error('[Auth] Profile creation failed:', profileError);
          toast.error('Account created but profile incomplete. Please update in settings.');
        }
      }

      if (data.user && !data.user.email_confirmed_at) {
        toast.success('Please check your email to confirm your account');
      }

      return { success: true };

    } catch (error: any) {
      setState((prev) => ({ ...prev, loading: false, error: error.message }));
      toast.error(error.message || 'Sign up failed');
      return { success: false, error: error.message };
    }
  };

  const signIn = async (email: string, password: string, options?: { captchaToken?: string }) => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    
    try {
      const signInOptions: any = { email, password };
      
      if (options?.captchaToken) {
        signInOptions.captchaToken = options.captchaToken;
      }

      const { data, error } = await supabase.auth.signInWithPassword(signInOptions);
      
      if (error) throw error;
      
      setState((prev) => ({ ...prev, session: data.session, loading: false }));
      return { success: true };
      
    } catch (error: any) {
      setState((prev) => ({ ...prev, loading: false, error: error.message }));
      return { success: false, error: error.message };
    }
  };
  
  const resetPassword = async (email: string): Promise<{ success: boolean; error?: string }> => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });

      if (error) {
        console.error('[Auth] Reset password error:', error);
        setState((prev) => ({ ...prev, loading: false, error: error.message }));
        return { success: false, error: error.message };
      }

      console.log('[Auth] Reset password email sent to:', email);
      setState((prev) => ({ ...prev, loading: false, error: null }));
      return { success: true };
      
    } catch (error: any) {
      console.error('[Auth] Reset password exception:', error);
      setState((prev) => ({ ...prev, loading: false, error: error.message }));
      return { success: false, error: error.message };
    }
  };

  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) {
        console.error('Supabase signOut error:', error);
      }
      
      localStorage.clear();
      sessionStorage.clear();
      
      document.cookie.split(";").forEach((c) => {
        document.cookie = c
          .replace(/^ +/, "")
          .replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
      });
      
      setState({
        session: null,
        user: null,
        loading: false,
        error: null,
        isDemoMode: false,
        role: 'alien',
      });
      
      window.location.href = '/';
    } catch (error) {
      console.error('Sign out error:', error);
      localStorage.clear();
      sessionStorage.clear();
      window.location.href = '/';
    }
  };

  const skipVerification = useCallback(() => {
    console.log('[Auth] Skipping verification');
    // This is a no-op for now, just to satisfy the TypeScript interface
    toastInfo('Verification skipped for demo purposes');
  }, []);

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

      const { data: profile } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('id', currentUser.id)
        .single();

      if (!profile) throw new Error('Profile not found');

      if (['pending', 'verified'].includes(profile.kyc_status)) {
        await supabase
          .from('user_profiles')
          .update({ role: 'tribe', updated_at: new Date().toISOString() })
          .eq('id', currentUser.id);
      }

      await fetchUserProfile();
      navigate('/dashboard');
      toast.success('Welcome to Seamount!');
    } catch (error) {
      console.error('Onboarding error:', error);
      toast.error('Setup incomplete');
    }
  };
  
  const checkOnboardingCompletion = useCallback(async () => {
    if (state.session && !state.loading) {
      try {
        const profile = await fetchUserProfile();
        if (profile) {
          const isOnboardingComplete = 
            profile.onboarding_complete === true ||
            profile.kyc_level >= 1;
          
          if (isOnboardingComplete && window.location.pathname === '/onboarding') {
            console.log('✅ Onboarding completed, redirecting to dashboard');
            navigate('/dashboard');
          } else if (!isOnboardingComplete && window.location.pathname === '/dashboard') {
            console.log('🔄 Onboarding not complete, redirecting to onboarding');
            navigate('/onboarding');
          }
        }
      } catch (error) {
        console.error('Onboarding check failed:', error);
      }
    }
  }, [state.session, state.loading, fetchUserProfile, navigate]);

  useEffect(() => {
    checkOnboardingCompletion();
  }, [checkOnboardingCompletion]);

  const refreshProfile = useCallback(async () => {
    const currentUser = state.user || state.session?.user;
    if (currentUser?.id) {
      await fetchUserProfile();
    }
  }, [state.user, state.session, fetchUserProfile]);

  const updateUserRole = useCallback((role: 'tribe' | 'alien') => {
    setState(prev => ({ ...prev, role }));
  }, []);

  // 🎯 HYBRID WALLET DETECTION - Fast profile check + API fallback
  useEffect(() => {
    const evaluateNavigation = async () => {
      if (state.session && state.user && !state.loading) {
        const kycStatus = state.user.kyc_status || 'not_started';
        const currentPath = window.location.pathname;
        
        console.log('[Auth Navigation] Entry:', {
          kycStatus,
          role: state.user.role,
          path: currentPath
        });
        
        // Tribe members always go to dashboard
        if (kycStatus === 'approved' || state.user.role === 'tribe') {
          if (currentPath !== '/dashboard' && !currentPath.startsWith('/settings')) {
            console.log('[Auth] Tribe member → dashboard');
            navigate('/dashboard');
          }
          return;
        }
        
        // 🚀 PHASE 1: Fast profile check (instant, 99% accurate)
        const quickCheck = state.user.onboarding_complete === true || 
                          state.user.kyc_level >= 1;
        
        console.log('[Auth] Quick check:', { quickCheck });
        
        // If profile says user has wallet, trust it (fast path)
        if (quickCheck) {
          if (currentPath === '/' || currentPath === '/landing') {
            console.log('[Auth] ✅ Quick check passed → dashboard');
            navigate('/dashboard');
          }
          return;
        }
        
        // 🔍 PHASE 2: API check only for critical paths (accurate fallback)
        if (currentPath === '/dashboard' || currentPath === '/' || currentPath === '/landing') {
          console.log('[Auth] 🔍 Running API wallet check...');
          
          try {
            const response = await apiClient.get('/api/v1/wallet-creation/status');
            const missingWallets = response.data.summary?.missing_chains || [];
            const hasWallet = missingWallets.length === 0;
            
            console.log('[Auth] API check result:', { 
              hasWallet, 
              missingCount: missingWallets.length 
            });
            
            if (hasWallet) {
              // User has wallets via API - allow dashboard
              if (currentPath === '/' || currentPath === '/landing') {
                console.log('[Auth] ✅ API check passed → dashboard');
                navigate('/dashboard');
              }
            } else {
              // No wallets - force onboarding
              console.log('[Auth] ❌ No wallets detected → onboarding');
              navigate('/onboarding');
            }
          } catch (error) {
            console.error('[Auth] API check failed, using fallback:', error);
            
            // Fallback to profile check if API fails
            if (!quickCheck && (currentPath === '/dashboard' || currentPath === '/' || currentPath === '/landing')) {
              console.log('[Auth] 🔄 Fallback: No wallet → onboarding');
              navigate('/onboarding');
            }
          }
        }
      }
    };
    
    evaluateNavigation();
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
      signUp,
      signIn,
      signOut,
      enterDemoMode,
      updateOnboardingStep,
      completeOnboarding,
      refreshProfile,
      updateUserRole,
      triggerWalletCreation,
      kycStatus: state.user?.kyc_status || 'not_started',
      skipVerification
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export { AuthProviderContent as AuthProvider };