// File Location: frontend/src/contexts/AuthContext.tsx
// FIXED: Removed undefined 'state' reference and fixed completeOnboarding

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
  role: 'tribe' | 'alien';
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
        if (profile) {
          // FIXED: Proper KYC status-based routing
          if (profile.kyc_status === 'pending') {
            navigate('/onboarding');
          } else if (profile.kyc_status === 'verified') {
            navigate('/dashboard');
          }
          // If kyc_status is 'not_started' or other, stay on current page
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
      if (profile) {
        // FIXED: Consistent KYC status handling
        if (profile.kyc_status === 'pending') {
          navigate('/onboarding');
        } else if (profile.kyc_status === 'verified') {
          navigate('/dashboard');
        }
      }
    } else {
      setUserProfile(null);
      setKycStatus('not_started');
    }
    setLoading(false);
  });

  return () => subscription.unsubscribe();
}, []);

  const createUserProfile = async (userId: string, email: string | undefined) => {
    try {
      console.log('[Profile] Creating new profile for user:', userId);
      
      if (!email) {
        throw new Error('Email is required to create profile');
      }

      const profileData = {
        id: userId,
        email: email,
        first_name: '',
        last_name: '',
        country_code: 'US',
        kyc_status: 'pending',
        kyc_level: 0,
        role: 'alien'
      };

      console.log('[Profile] Creating profile with data:', profileData);
      
      const response = await apiClient.post('/api/v1/user/profile', profileData);
      const createdProfile = response.data;
      
      console.log('[Profile] Profile created successfully:', createdProfile);
      
      setUserProfile(createdProfile);
      setKycStatus(createdProfile.kyc_status || 'pending');
      
    } catch (error: any) {
      console.error('[Profile] Creation failed:', error);
      throw error;
    }
  };

  const fetchUserProfile = async (userId: string) => {
    try {
      console.log('[Profile] Fetching for user:', userId);
      
      const response = await apiClient.get(`/api/v1/user/profile`);
      const profile = response.data;
      
      console.log('[Profile] Fetched successfully:', profile);
      
      setUserProfile(profile);
      setKycStatus(profile.kyc_status || 'pending');
      
      return profile;
    } catch (error: any) {
      console.error('[Profile] Fetch failed:', error);
      
      if (error.response?.status === 404) {
        console.log('[Profile] Profile not found - returning null');
        setUserProfile(null);
        setKycStatus('not_started');
        return null;
      } else {
        console.error('[Profile] Unexpected error:', error.message);
        return null;
      }
    }
  };

  const signUp = async (email: string, password: string, signUpData: any) => {
    try {
      setLoading(true);
      console.log('[SignUp] Starting registration for:', email);
      
      // Step 1: Create auth user
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

      if (authError) throw authError;
      if (!authData.user) throw new Error("No user returned from authentication");

      console.log('[SignUp] Auth user created:', authData.user.id);

      // Step 2: Create user profile using the fixed function
      try {
        await createUserProfile(authData.user.id, email);
        
        // Step 3: Update profile with registration data
        const profileUpdateData = {
          first_name: signUpData.firstName.trim(),
          last_name: signUpData.lastName.trim(),
          country_code: signUpData.countryCode.toUpperCase(),
          kyc_status: 'pending'
        };

        const updateResponse = await apiClient.put('/api/v1/user/profile', profileUpdateData);
        const updatedProfile = updateResponse.data;
        
        console.log('[SignUp] Profile updated successfully:', updatedProfile);
        
        setUserProfile(updatedProfile);
        setKycStatus('pending');
        
        toast.success('Registration successful! Please check your email to verify your account.');
        
      } catch (profileError: any) {
        console.error('[SignUp] Profile creation/update failed:', profileError);
        toast.warning('Account created but profile setup incomplete. You can complete it after email verification.');
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
        
        // Ensure profile exists before proceeding
        let profile = await fetchUserProfile(data.user.id);
        
        // If no profile exists, create one
        if (!profile) {
          console.log('[SignIn] No profile found, creating...');
          try {
            await createUserProfile(data.user.id, data.user.email);
            profile = await fetchUserProfile(data.user.id);
          } catch (createError) {
            console.error('[SignIn] Profile creation failed:', createError);
          }
        }
        
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
      setKycStatus(profile.kyc_status || 'pending');
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

  const completeOnboarding = async () => {
    try {
      console.log('[Onboarding] Completing onboarding process');
      
      // Update user role to tribe after successful KYC
      if (user) {
        const { error } = await supabase
          .from('user_profiles')
          .update({ 
            kyc_status: 'approved',
            kyc_level: 3,
            role: 'tribe',
            updated_at: new Date().toISOString()
          })
          .eq('id', user.id);
          
        if (error) throw error;
      }
      
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

  // Add role check helper function
  const checkUserRole = useCallback((requiredRole: 'tribe' | 'alien') => {
    return userProfile?.role === requiredRole;
  }, [userProfile]);

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