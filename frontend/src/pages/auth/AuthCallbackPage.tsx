// frontend/src/pages/auth/AuthCallbackPage.tsx
// Handles OAuth redirect → profile creation → route to onboarding or dashboard

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../../lib/supabase';
import { apiClient } from '../../config/api';

const AuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState('Completing sign-in...');

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Exchange code for session (Supabase handles PKCE automatically)
        const { data: { session }, error } = await supabase.auth.getSession();
        
        if (error) throw error;
        if (!session) {
          setStatus('No session found. Redirecting...');
          navigate('/');
          return;
        }

        const user = session.user;
        setStatus('Setting up your account...');

        // Check if profile already exists
        try {
          const profileResponse = await apiClient.get('/api/v1/user/profile');
          if (profileResponse.data?.profile) {
            // Existing user — go to dashboard
            setStatus('Welcome back!');
            navigate('/dashboard');
            return;
          }
        } catch {
          // 404 = new user, continue to create profile
        }

        // ── New OAuth user: extract name from provider metadata ──
        const meta = user.user_metadata || {};
        
        // Provider-specific name extraction
        const firstName = meta.given_name       // Google
          || meta.first_name                    // Facebook
          || meta.full_name?.split(' ')[0]      // Discord, Spotify
          || meta.name?.split(' ')[0]           // Apple (first login only), X
          || '';
        
        const lastName = meta.family_name       // Google
          || meta.last_name                     // Facebook
          || meta.full_name?.split(' ').slice(1).join(' ')  // Discord
          || meta.name?.split(' ').slice(1).join(' ')       // X
          || '';

        // Create profile
        await apiClient.post('/api/v1/user/profile', {
          id: user.id,
          email: user.email || `${user.id}@web3.local`, // Web3 users have no email
          firstName,
          lastName,
          countryCode: 'US', // Default — user updates in onboarding
          provider: user.app_metadata?.provider || 'oauth',
        });

        setStatus('Profile created! Setting up wallets...');

        // Trigger wallet creation in background
        apiClient.post('/api/v1/wallet/create').catch(err =>
          console.warn('[Callback] Wallet creation failed (non-fatal):', err)
        );

        // New user → onboarding
        navigate('/onboarding');

      } catch (err: any) {
        console.error('[AuthCallback] Error:', err);
        setStatus('Something went wrong. Redirecting...');
        setTimeout(() => navigate('/'), 2000);
      }
    };

    handleCallback();
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900 flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-500 mx-auto" />
        <p className="text-gray-300 text-lg">{status}</p>
      </div>
    </div>
  );
};

export default AuthCallbackPage;