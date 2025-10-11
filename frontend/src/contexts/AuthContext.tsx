import React, { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import toast from 'react-hot-toast';
import type { User, Session } from '@supabase/supabase-js';

const logger = {
  info: (...args: any[]) => console.log(...args),
  error: (...args: any[]) => console.error(...args)
};

interface AuthContextType {
  user: User | null;
  session: Session | null;
  userProfile: any;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string, userData: any) => Promise<void>;
  signOut: () => Promise<void>;
  refreshProfile: () => Promise<void>;
  completeOnboarding: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) fetchProfile(session.user.id);
      else setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      logger.info('Auth state changed:', _event, session?.user?.id);
      setSession(session);
      setUser(session?.user ?? null);
      if (session?.user) fetchProfile(session.user.id);
      else { setUserProfile(null); setLoading(false); }
    });

    return () => subscription.unsubscribe();
  }, []);

  const fetchProfile = async (userId: string) => {
    try {
      const { data, error } = await supabase
        .from('user_profiles')
        .select('*')
        .eq('id', userId)
        .single();

      if (error) throw error;
      setUserProfile(data);
    } catch (error) {
      logger.error('Profile fetch error:', error);
      setUserProfile(null);
    } finally {
      setLoading(false);
    }
  };

  const refreshProfile = async () => {
    const currentUser = user || session?.user;
    if (currentUser) await fetchProfile(currentUser.id);
  };

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
    toast.success('Signed in successfully');
  };

  const signUp = async (email: string, password: string, userData: any) => {
    const { data: authData, error: authError } = await supabase.auth.signUp({ email, password });
    if (authError) throw authError;

    if (authData.user) {
      const { error: profileError } = await supabase.from('user_profiles').insert({
        id: authData.user.id,
        email,
        ...userData,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      });
      if (profileError) throw profileError;
    }

    toast.success('Account created! Check your email to verify.');
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
    setSession(null);
    setUserProfile(null);
    navigate('/');
    toast.success('Signed out');
  };

  const completeOnboarding = async () => {
    try {
      const currentUser = user || session?.user;
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

      await refreshProfile();
      navigate('/dashboard');
      toast.success('Welcome to Seamount!');
    } catch (error) {
      logger.error('Onboarding error:', error);
      toast.error('Setup incomplete');
    }
  };

  return (
    <AuthContext.Provider value={{
      user, session, userProfile, loading,
      signIn, signUp, signOut, refreshProfile, completeOnboarding
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};