// File Location: frontend/src/contexts/AuthContext.tsx
// CRITICAL FIX: Added missing API_ENDPOINTS import and proper error handling

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import { apiClient, API_ENDPOINTS } from '../config/api';  // FIXED: Added missing import
import toast from 'react-hot-toast';

interface UserProfile {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  country_code?: string;
  kyc_status: 'pending' | 'verified' | 'rejected' | 'not_started';
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
        fetchUserProfile(session.user.id);
      }
      setLoading(false);
    });

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      
      if (session?.user) {
        await fetchUserProfile(session.user.id);
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
      // FIXED: Using correct endpoint from imported API_ENDPOINTS
      const response = await apiClient.get(API_ENDPOINTS.USER.PROFILE);
      const profile = response.data;
      setUserProfile(profile);
      setKycStatus(profile.kyc_status || 'not_started');
    } catch (error: any) {
      console.error('Failed to fetch user profile:', error);
      
      // If profile doesn't exist, create it
      if (error.response?.status === 404 && user) {
        await createUserProfile(user);
      }
    }
  };

  const createUserProfile = async (authUser: User) => {
    try {
      const profileData = {
        id: authUser.id,
        email: authUser.email || '',
        firstName: '',  // Will be converted to first_name in backend
        lastName: '',   // Will be converted to last_name in backend
        kyc_status: 'not_started'
      };

      // FIXED: Use proper endpoint for profile creation
      const response = await apiClient.post('/api/users/profile', profileData);
      setUserProfile(response.data);
      setKycStatus('not_started');
    } catch (error: any) {
      console.error('Failed to create user profile:', error);
    }
  };

  // FIXED: Updated signUp to match your registration form structure
  const signUp = async (email: string, password: string, signUpData: any) => {
    try {
      setLoading(true);
      
      // Step 1: Create auth user with user metadata
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

      if (authData.user) {
        // Step 2: Create user profile 
        const profileData = {
          id: authData.user.id,
          email: email,
          firstName: signUpData.firstName,
          lastName: signUpData.lastName,
          countryCode: signUpData.countryCode,
          kyc_status: 'not_started'
        };

        try {
          const response = await apiClient.post('/api/users/profile', profileData);
          setUserProfile(response.data);
          setKycStatus('not_started');
          
          toast.success('Account created successfully! Please check your email to verify your account.');
        } catch (profileError: any) {
          console.error('Failed to create user profile:', profileError);
          // Don't fail the signup if profile creation fails - we can create it later
          toast.warning('Account created but profile setup incomplete. Please try logging in.');
        }
      }
    } catch (error: any) {
      console.error('Sign up error:', error);
      toast.error(error.message || 'Failed to create account');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    try {
      setLoading(true);
      
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        console.error('Sign in error:', error);
        toast.error(error.message);
        return { success: false, error: error.message };
      }

      if (data.user) {
        await fetchUserProfile(data.user.id);
        toast.success('Successfully signed in!');
        return { success: true };
      }

      return { success: false, error: 'Unknown error occurred' };
    } catch (error: any) {
      console.error('Sign in error:', error);
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
      console.error('Sign out error:', error);
      toast.error('Failed to sign out');
    } finally {
      setLoading(false);
    }
  };

  const refreshKycStatus = useCallback(async () => {
    if (!user) return;
    
    try {
      const response = await apiClient.get(API_ENDPOINTS.USER.PROFILE);
      const profile = response.data;
      setUserProfile(profile);
      setKycStatus(profile.kyc_status || 'not_started');
    } catch (error: any) {
      console.error('Failed to refresh KYC status:', error);
    }
  }, [user]);

  const skipVerification = async () => {
    try {
      // Update local state temporarily - backend should handle persistence
      setKycStatus('verified');
      toast.success('Verification skipped for demo purposes');
    } catch (error: any) {
      console.error('Skip verification error:', error);
      toast.error('Failed to skip verification');
    }
  };

  const updateUserProfile = async (updates: Partial<UserProfile>) => {
    try {
      setLoading(true);
      
      const response = await apiClient.put(API_ENDPOINTS.USER.PROFILE, updates);
      const updatedProfile = response.data;
      
      setUserProfile(updatedProfile);
      if (updates.kyc_status) {
        setKycStatus(updates.kyc_status);
      }
      
      toast.success('Profile updated successfully');
    } catch (error: any) {
      console.error('Update profile error:', error);
      toast.error(error.response?.data?.message || 'Failed to update profile');
      throw error;
    } finally {
      setLoading(false);
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
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};