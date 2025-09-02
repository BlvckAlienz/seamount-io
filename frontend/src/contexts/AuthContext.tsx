// File Location: frontend/src/contexts/AuthContext.tsx
// CRITICAL FIX: Field mapping correction to match database schema

import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '../lib/supabase';
import { apiClient } from '../config/api';
import toast from 'react-hot-toast';

interface UserProfile {
  id: string;
  first_name: string;  // ✅ FIXED: Using underscore format to match database
  last_name: string;   // ✅ FIXED: Using underscore format to match database
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
  signUp: (email: string, password: string, firstName: string, lastName: string, countryCode: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
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
      const response = await apiClient.get(`/api/users/profile/${userId}`);
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
        first_name: '', // ✅ FIXED: Empty string to be filled later
        last_name: '',  // ✅ FIXED: Empty string to be filled later
        kyc_status: 'not_started'
      };

      const response = await apiClient.post('/api/users/profile', profileData);
      setUserProfile(response.data);
      setKycStatus('not_started');
    } catch (error: any) {
      console.error('Failed to create user profile:', error);
    }
  };

  // ✅ CRITICAL FIX: Corrected field mapping in signUp function
  const signUp = async (email: string, password: string, firstName: string, lastName: string, countryCode: string) => {
    try {
      setLoading(true);
      
      // Step 1: Create auth user
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email,
        password,
      });

      if (authError) throw authError;

      if (authData.user) {
        // Step 2: Create user profile with CORRECT field mapping
        const signUpData = {
          id: authData.user.id,
          email: email,
          first_name: firstName,  // ✅ FIXED: Now using first_name (underscore)
          last_name: lastName,    // ✅ FIXED: Now using last_name (underscore)
          country_code: countryCode,
          kyc_status: 'not_started'
        };

        try {
          const response = await apiClient.post('/api/users/profile', signUpData);
          setUserProfile(response.data);
          setKycStatus('not_started');
          
          toast.success('Account created successfully! Please check your email to verify your account.');
        } catch (profileError: any) {
          console.error('Failed to create user profile:', profileError);
          // Don't throw here - user was created successfully, just profile creation failed
          toast.warning('Account created but profile setup incomplete. Please complete your profile.');
        }
      }
    } catch (error: any) {
      console.error('Sign up error:', error);
      if (error.message.includes('already registered')) {
        toast.error('Email already registered. Please sign in instead.');
      } else {
        toast.error(error.message || 'Failed to create account. Please try again.');
      }
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signIn = async (email: string, password: string) => {
    try {
      setLoading(true);
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;
      toast.success('Signed in successfully!');
    } catch (error: any) {
      console.error('Sign in error:', error);
      toast.error(error.message || 'Failed to sign in. Please try again.');
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut();
      if (error) throw error;
      
      setUser(null);
      setUserProfile(null);
      setSession(null);
      setKycStatus('not_started');
      toast.success('Signed out successfully!');
      navigate('/');
    } catch (error: any) {
      console.error('Sign out error:', error);
      toast.error('Failed to sign out. Please try again.');
    }
  };

  const refreshKycStatus = async () => {
    if (!user) return;
    
    try {
      const response = await apiClient.get('/api/kyc/status');
      const newStatus = response.data.kyc_status;
      setKycStatus(newStatus);
      
      if (userProfile) {
        setUserProfile(prev => prev ? { ...prev, kyc_status: newStatus } : null);
      }
    } catch (error: any) {
      console.error('Failed to refresh KYC status:', error);
    }
  };

  const skipVerification = async () => {
    try {
      await apiClient.post('/api/kyc/skip');
      setKycStatus('not_started');
      
      if (userProfile) {
        setUserProfile(prev => prev ? { ...prev, kyc_status: 'not_started' } : null);
      }
      
      toast.info('Verification skipped. You can complete it anytime in settings.');
    } catch (error: any) {
      console.error('Failed to skip verification:', error);
      throw error;
    }
  };

  const updateUserProfile = async (updates: Partial<UserProfile>) => {
    if (!user || !userProfile) return;

    try {
      const response = await apiClient.put(`/api/users/profile/${user.id}`, updates);
      setUserProfile(response.data);
      toast.success('Profile updated successfully!');
    } catch (error: any) {
      console.error('Failed to update user profile:', error);
      toast.error('Failed to update profile. Please try again.');
      throw error;
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