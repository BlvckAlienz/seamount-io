// File: frontend/src/contexts/AuthContext.tsx
// CRITICAL FIX: Line 223-237 - Bulletproof logout with full session clear

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Session } from '@supabase/supabase-js';
import { apiClient } from '../config/api';
import { UserProfile } from '../types';
import { supabase } from '../lib/supabase';
import { useAutoLogout } from '../hooks/useAutoLogout';
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
          
          // ✅ CHECK IF WALLETS NEED TO BE CREATED
          // This handles email confirmation flow
          if (event === 'SIGNED_IN') {
            try {
              // Check if user has wallets
              const walletStatusResponse = await apiClient.get('/api/v1/wallet-creation/status');
              
              if (walletStatusResponse.data.success) {
                const missingWallets = walletStatusResponse.data.summary?.missing_chains || [];
                
                if (missingWallets.length > 0) {
                  console.log('[Auth] 🔐 User missing wallets, triggering creation...');
                  
                  // Small delay to ensure profile is ready
                  setTimeout(async () => {
                    try {
                      const createResponse = await apiClient.post('/api/v1/wallet/create');
                      
                      if (createResponse.data.success) {
                        console.log('[Auth] ✅ Wallets created on login:', createResponse.data.created_chains);
                        
                        // Flag to show backup modal
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

    // ✅ CREATE USER PROFILE FIRST
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
  
  // ADD this function to check onboarding completion
  const checkOnboardingCompletion = useCallback(async () => {
    if (state.session && !state.loading) {
      try {
        const profile = await fetchUserProfile();
        if (profile) {
          // ✅ CRITICAL: Check multiple completion indicators
          const isOnboardingComplete = 
            profile.onboarding_complete === true ||
            profile.kyc_level >= 1 || 
            profile.algorand_address ||
            profile.wallet_address;
          
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

  // ADD this useEffect to the AuthContext
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

  useEffect(() => {
    if (state.session && state.user && !state.loading) {
      const kycStatus = state.user.kyc_status || 'not_started';
      const hasWallet = state.user.algorand_address || state.user.wallet_address;
      const currentPath = window.location.pathname;
      
      console.log('[Auth Navigation]', {
        kycStatus,
        hasWallet,
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
      
      // Users with wallets can access dashboard
      if (hasWallet) {
        // Allow them on dashboard, settings, and wallet-recovery pages
        const allowedPaths = ['/dashboard', '/onboarding', '/settings', '/wallet-recovery'];
        const isOnAllowedPath = allowedPaths.some(path => currentPath.startsWith(path));
        
        if (!isOnAllowedPath) {
          console.log('[Auth] User has wallet but on restricted path → dashboard');
          navigate('/dashboard');
        }
        return;
      }
      
      // No wallet yet - must complete onboarding
      if (currentPath === '/' || currentPath === '/landing') {
        console.log('[Auth] No wallet, on landing → onboarding');
        navigate('/onboarding');
      } else if (currentPath === '/dashboard') {
        console.log('[Auth] No wallet, trying dashboard → onboarding');
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

  // Auto-logout on inactivity (must be after all hooks)
  useAutoLogout();

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