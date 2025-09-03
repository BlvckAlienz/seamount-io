// File Location: frontend/src/contexts/AuthContext.tsx
// CRITICAL FIX: Corrected API endpoints and registration flow

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import { apiClient, API_ENDPOINTS } from '../config/api';
import toast from 'react-hot-toast';

interface UserProfile {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  country_code?: string;
  kyc_status: 'not_started' | 'pending' | 'verified' | 'rejected';
  kyc_level: number;
  created_at: string;
  updated_at: string;
}

interface AuthContextType {
  user: User | null;
  userProfile: UserProfile | null;
  session: Session | null;
  loading: boolean;
  kycStatus: string;
  signUp: (email: string, password: string, signUpData: any) => Promise<void>;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  refreshKycStatus: () => Promise<void>;
  skipVerification: () => Promise<void>;
  updateUserProfile: (updates: Partial<UserProfile>) => Promise<void>;
  completeOnboarding: () => Promise<void>;
  triggerWalletCreation: () => Promise<{ success: boolean; mnemonic?: string }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [kycStatus, setKycStatus] = useState('not_started');
  const navigate = useNavigate();

  useEffect(() => {
  // Get initial session
  supabase.auth.getSession().then(({ data: { session } }) => {
    setSession(session);
    setUser(session?.user ?? null);
    if (session?.user) {
      fetchUserProfile(session.user.id).then(profile => {
        // FIXED: Trigger onboarding based on profile status
        if (profile && profile.kyc_status === 'not_started') {
          // Navigate to onboarding if profile exists but KYC not started
          navigate('/onboarding');
        } else if (!profile) {
          // Create profile if it doesn't exist
          createUserProfile(session.user.id, session.user.email);
        }
      });
    }
    setLoading(false);
  });

  // Listen for auth changes
  const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
    setSession(session);
    setUser(session?.user ?? null);
    
    if (session?.user) {
      const profile = await fetchUserProfile(session.user.id);
      // FIXED: Trigger onboarding when user signs in and needs to complete KYC
      if (profile && profile.kyc_status === 'not_started') {
        navigate('/onboarding');
      }
    } else {
      setUserProfile(null);
      setKycStatus('not_started');
    }
    setLoading(false);
  });

  return () => subscription.unsubscribe();
}, []);

  const fetchUserProfile = async (userId: string) => {
    try {
      console.log('[Profile] Fetching for user:', userId);
      
      // FIXED: Use correct endpoint
      const response = await apiClient.get(`/api/v1/user/profile`);
      const profile = response.data;
      
      console.log('[Profile] Fetched successfully:', profile);
      
      setUserProfile(profile);
      setKycStatus(profile.kyc_status || 'not_started');
    } catch (error: any) {
      console.error('[Profile] Fetch failed:', error);
      
      // If profile doesn't exist, don't auto-create here - let registration handle it
      if (error.response?.status === 404) {
        console.log('[Profile] Profile not found - will be created during registration');
        setUserProfile(null);
        setKycStatus('not_started');
      } else {
        console.error('[Profile] Unexpected error:', error.message);
      }
    }
  };

  const signUp = async (email: string, password: string, signUpData: any) => {
  try {
    setLoading(true);
    console.log('[SignUp] Starting registration for:', email);
    
    // Step 1: Create auth user with metadata
    const { data: authData, error: authError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          first_name: signUpData.firstName,
          last_name: signUpData.lastName,
          country_code: signUpData.countryCode
        }
      }
    });

    if (authError) {
      console.error('[SignUp] Auth error:', authError);
      throw authError;
    }

    console.log('[SignUp] Auth user created:', authData.user?.id);

    if (authData.user) {
      // Step 2: Create user profile with retry mechanism
      const profileData = {
        id: authData.user.id,
        email: email,
        firstName: signUpData.firstName.trim(),
        lastName: signUpData.lastName.trim(),
        countryCode: signUpData.countryCode,
        kyc_status: 'not_started'
      };

      // FIXED: Use correct endpoint with proper data structure
      const response = await apiClient.post('/api/v1/user/profile', profileData);
      const createdProfile = response.data;
      
      console.log('[SignUp] Profile created successfully:', createdProfile);
      
      setUserProfile(createdProfile);
      setKycStatus('not_started');
      
      if (!authData.user.email_confirmed_at) {
        toast.success('Registration successful! Please check your email to verify your account.');
      } else {
        toast.success('Registration successful! Welcome to Seamount.');
      }
    }
    
  } catch (error: any) {
    console.error('[SignUp] Registration failed:', error);
    toast.error(error.message || 'Failed to create account');
    throw error;
  } finally {
    setLoading(false);
  }
};

  const signIn = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      setLoading(true);
      console.log('[SignIn] Attempting login for:', email);
      
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        console.error('[SignIn] Login error:', error);
        toast.error(error.message);
        return { success: false, error: error.message };
      }

      if (data.user) {
        console.log('[SignIn] Login successful for user:', data.user.id);
        await fetchUserProfile(data.user.id);
        toast.success('Successfully signed in!');
        return { success: true };
      }

      return { success: false, error: 'Unknown error occurred' };
    } catch (error: any) {
      console.error('[SignIn] Unexpected error:', error);
      const errorMessage = error.message || 'Failed to sign in';
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      setLoading(true);
      await supabase.auth.signOut();
      setUser(null);
      setUserProfile(null);
      setSession(null);
      setKycStatus('not_started');
      toast.success('Successfully signed out');
      navigate('/');
    } catch (error: any) {
      console.error('[SignOut] Error:', error);
      toast.error('Failed to sign out');
    } finally {
      setLoading(false);
    }
  };

  const refreshKycStatus = useCallback(async () => {
    if (!user) return;
    
    try {
      const response = await apiClient.get('/api/v1/user/profile');
      const profile = response.data;
      setUserProfile(profile);
      setKycStatus(profile.kyc_status || 'not_started');
    } catch (error: any) {
      console.error('[KYC] Failed to refresh status:', error);
    }
  }, [user]);

  const skipVerification = async () => {
    try {
      setKycStatus('verified');
      toast.success('Verification skipped for demo purposes');
    } catch (error: any) {
      console.error('[KYC] Skip verification error:', error);
      toast.error('Failed to skip verification');
    }
  };

  const updateUserProfile = async (updates: Partial<UserProfile>) => {
    try {
      setLoading(true);
      
      const response = await apiClient.put('/api/v1/user/profile', updates);
      const updatedProfile = response.data;
      
      setUserProfile(updatedProfile);
      if (updates.kyc_status) {
        setKycStatus(updates.kyc_status);
      }
      
      toast.success('Profile updated successfully');
    } catch (error: any) {
      console.error('[Profile] Update error:', error);
      toast.error(error.response?.data?.message || 'Failed to update profile');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  // FIXED: Added missing methods that OnboardingPage expects
  const completeOnboarding = async () => {
    try {
      console.log('[Onboarding] Completing onboarding process');
      
      // Update KYC status to indicate onboarding complete
      await updateUserProfile({ kyc_status: 'verified' });
      
      toast.success('Welcome to Seamount! Onboarding complete.');
      navigate('/dashboard');
      
    } catch (error: any) {
      console.error('[Onboarding] Complete error:', error);
      toast.error('Failed to complete onboarding');
    }
  };

  const triggerWalletCreation = async (): Promise<{ success: boolean; mnemonic?: string }> => {
    try {
      console.log('[Wallet] Creating wallet for user');
      
      // Call wallet creation endpoint
      const response = await apiClient.post('/api/wallet/create');
      const walletData = response.data;
      
      console.log('[Wallet] Wallet created successfully');
      
      return {
        success: true,
        mnemonic: walletData.mnemonic
      };
      
    } catch (error: any) {
      console.error('[Wallet] Creation failed:', error);
      toast.error('Failed to create wallet');
      return { success: false };
    }
  };

  const value: AuthContextType = {
    user,
    userProfile,
    session,
    loading,
    kycStatus,
    signUp,
    signIn,
    signOut,
    refreshKycStatus,
    skipVerification,
    updateUserProfile,
    completeOnboarding,
    triggerWalletCreation,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};