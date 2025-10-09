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
	role: 'alien', // Default role
  });
   
  const navigate = useNavigate();

	const fetchUserProfile = useCallback(async (maxRetries: number = 3, delayMs: number = 1000) => {
	  try {
		const { data } = await retryWithBackoff(
		  () => apiClient.get<{ success: boolean; profile: UserProfile }>('/api/v1/user/profile'),
		  maxRetries,
		  delayMs
		);
		// FIX: Extract profile from response data
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
        // Add a small delay to ensure tokens are properly processed
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
      
      // Profile will be fetched by the auth state change listener
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
        
        // Fetch updated profile
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
          role: 'alien',
          kyc_provider: null,
          verification_skipped: true
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

// Add these functions
const updateUserRole = useCallback((role: 'tribe' | 'alien') => {
  setState(prev => ({ ...prev, role }));
}, []);

// Replace the problematic useEffect with this corrected version
useEffect(() => {
  if (state.session && state.user && !state.loading) {
    const kycStatus = state.user.kyc_status || 'not_started';
    const hasWallet = state.user.algorand_address;
    
    console.log('Routing check:', { kycStatus, hasWallet, role: state.user.role });
    
    // NEW USER: No wallet yet → force onboarding
    if (!hasWallet || kycStatus === 'not_started') {
      navigate('/onboarding');
      return;
    }
    
    // VERIFIED USER: approved/tribe → dashboard
    if (kycStatus === 'approved' || state.user.role === 'tribe') {
      navigate('/dashboard');
      return;
    }
    
    // PENDING VERIFICATION: Only go to dashboard if wallet exists
    if (['pending', 'in_progress', 'under_review'].includes(kycStatus)) {
      if (hasWallet) {
        navigate('/dashboard');
        toast('Verification in progress');
      } else {
        // Stuck in pending but no wallet - complete onboarding first
        navigate('/onboarding');
      }
      return;
    }
    
    // SKIPPED KYC: wallet exists but skipped → dashboard
    if (kycStatus === 'skipped' && hasWallet) {
      navigate('/dashboard');
      return;
    }
    
    // DEFAULT: Send to onboarding
    navigate('/onboarding');
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

// Add the return statement for the component
return (
  <AuthContext.Provider value={{
    ...state,
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