// File Location: frontend/src/hooks/useUserProfile.ts
// CRITICAL FIX: Enhanced profile management with robust error handling

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../lib/supabase';
import toast from 'react-hot-toast';

interface UserProfile {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  kyc_status: 'not_started' | 'in_progress' | 'completed' | 'rejected';
  kyc_started_at?: string;
  kyc_completed_at?: string;
  kyc_rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

interface ProfileCheck {
  profile_complete: boolean;
  missing_fields: string[];
  errors: string[];
  can_start_kyc: boolean;
  kyc_status: string;
}

interface UseUserProfileReturn {
  profile: UserProfile | null;
  profileCheck: ProfileCheck | null;
  loading: boolean;
  error: string | null;
  updateProfile: (data: Partial<UserProfile>) => Promise<boolean>;
  checkProfileCompleteness: () => Promise<ProfileCheck | null>;
  startKycVerification: () => Promise<boolean>;
  refreshProfile: () => Promise<void>;
}

export const useUserProfile = (): UseUserProfileReturn => {
  const { user } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [profileCheck, setProfileCheck] = useState<ProfileCheck | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // CRITICAL: Fetch profile data with retry mechanism
  const fetchProfile = useCallback(async () => {
    if (!user) return;

    setLoading(true);
    setError(null);

    const maxRetries = 3;
    let attempt = 0;

    while (attempt < maxRetries) {
      try {
        const { data, error: fetchError } = await supabase
          .from('user_profiles')
          .select('*')
          .eq('id', user.id)
          .single();

        if (fetchError) {
          throw new Error(fetchError.message);
        }

        setProfile(data);
        setLoading(false);
        return;

      } catch (err) {
        attempt++;
        const errorMessage = err instanceof Error ? err.message : 'Profile fetch failed';
        
        if (attempt === maxRetries) {
          console.error(`Profile fetch failed after ${maxRetries} attempts:`, err);
          setError(errorMessage);
          setLoading(false);
        } else {
          console.warn(`Profile fetch attempt ${attempt} failed, retrying...`);
          await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        }
      }
    }
  }, [user]);

  // CRITICAL: Check profile completeness with enhanced validation
  const checkProfileCompleteness = useCallback(async (): Promise<ProfileCheck | null> => {
    if (!user) return null;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/kyc/profile-check', {
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Profile check failed: ${response.status} ${response.statusText}`);
      }

      const data: ProfileCheck = await response.json();
      setProfileCheck(data);
      setLoading(false);
      return data;

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Profile check failed';
      console.error('Profile completeness check error:', err);
      setError(errorMessage);
      setLoading(false);
      return null;
    }
  }, [user]);

  // CRITICAL: Update profile with validation and retry logic
  const updateProfile = useCallback(async (data: Partial<UserProfile>): Promise<boolean> => {
    if (!user) return false;

    setLoading(true);
    setError(null);

    try {
      // Client-side validation
      if (data.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
        throw new Error('Invalid email format');
      }

      if (data.first_name && data.first_name.trim().length === 0) {
        throw new Error('First name cannot be empty');
      }

      if (data.last_name && data.last_name.trim().length === 0) {
        throw new Error('Last name cannot be empty');
      }

      const response = await fetch('/api/kyc/update-profile', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Profile update failed: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success && result.profile) {
        setProfile(result.profile);
        
        // Refresh profile check after successful update
        await checkProfileCompleteness();
        
        setLoading(false);
        return true;
      } else {
        throw new Error(result.message || 'Profile update failed');
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Profile update failed';
      console.error('Profile update error:', err);
      setError(errorMessage);
      setLoading(false);
      return false;
    }
  }, [user, checkProfileCompleteness]);

  // CRITICAL: Start KYC verification with prerequisite checks
  const startKycVerification = useCallback(async (): Promise<boolean> => {
    if (!user) return false;

    setLoading(true);
    setError(null);

    try {
      // Double-check profile completeness before starting KYC
      const profileStatus = await checkProfileCompleteness();
      
      if (!profileStatus?.can_start_kyc) {
        throw new Error(`Cannot start KYC: ${profileStatus?.errors.join(', ') || 'Profile incomplete'}`);
      }

      const response = await fetch('/api/kyc/start-verification', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${user.access_token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail?.error || errorData.detail || `KYC start failed: ${response.status}`);
      }

      const result = await response.json();
      
      if (result.success) {
        // Update local profile status
        setProfile(prev => prev ? { ...prev, kyc_status: 'in_progress' } : null);
        setProfileCheck(prev => prev ? { ...prev, kyc_status: 'in_progress' } : null);
        
        setLoading(false);
        return true;
      } else {
        throw new Error(result.message || 'Failed to start KYC verification');
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'KYC initialization failed';
      console.error('KYC start error:', err);
      setError(errorMessage);
      setLoading(false);
      return false;
    }
  }, [user, checkProfileCompleteness]);

  // CRITICAL: Refresh profile data
  const refreshProfile = useCallback(async () => {
    await fetchProfile();
    await checkProfileCompleteness();
  }, [fetchProfile, checkProfileCompleteness]);

  // Load profile data on user change
  useEffect(() => {
    if (user) {
      fetchProfile();
      checkProfileCompleteness();
    } else {
      setProfile(null);
      setProfileCheck(null);
      setError(null);
    }
  }, [user, fetchProfile, checkProfileCompleteness]);

  // Listen for real-time profile changes
  useEffect(() => {
    if (!user) return;

    const subscription = supabase
      .channel(`user_profile:${user.id}`)
      .on('postgres_changes', 
        { event: '*', schema: 'public', table: 'user_profiles', filter: `id=eq.${user.id}` },
        async (payload) => {
          console.log('Profile change detected:', payload);
          
          if (payload.eventType === 'UPDATE' && payload.new) {
            setProfile(payload.new as UserProfile);
            // Re-check profile completeness after update
            await checkProfileCompleteness();
          }
        }
      )
      .subscribe();

    return () => {
      subscription.unsubscribe();
    };
  }, [user, checkProfileCompleteness]);

  return {
    profile,
    profileCheck,
    loading,
    error,
    updateProfile,
    checkProfileCompleteness,
    startKycVerification,
    refreshProfile
  };
};