// frontend/src/components/auth/SocialAuthButtons.tsx
// 6 OAuth providers only — Web3 removed (disabled in Supabase)

import React, { useState } from 'react';
import { supabase } from '../../lib/supabase';
import toast from 'react-hot-toast';

type OAuthProvider = 'google' | 'discord' | 'facebook' | 'twitch' | 'spotify';

interface SocialAuthButtonsProps {
  mode: 'login' | 'signup';
}

const OAUTH_PROVIDERS: {
  id: OAuthProvider;
  label: string;
  bgColor: string;
  textColor: string;
  logo: React.ReactNode;
}[] = [
  {
    id: 'google',
    label: 'Google',
    bgColor: 'bg-white hover:bg-gray-50 border-gray-300',
    textColor: 'text-gray-800',
    logo: (
      <svg viewBox="0 0 24 24" className="w-4 h-4 flex-shrink-0">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
    ),
  },
  {
    id: 'discord',
    label: 'Discord',
    bgColor: 'bg-[#5865F2] hover:bg-[#4752C4] border-[#5865F2]',
    textColor: 'text-white',
    logo: (
      <svg viewBox="0 0 24 24" className="w-4 h-4 flex-shrink-0 fill-white">
        <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z"/>
      </svg>
    ),
  },
  {
    id: 'facebook',
    label: 'Facebook',
    bgColor: 'bg-[#1877F2] hover:bg-[#0C63D4] border-[#1877F2]',
    textColor: 'text-white',
    logo: (
      <svg viewBox="0 0 24 24" className="w-4 h-4 flex-shrink-0 fill-white">
        <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
      </svg>
    ),
  },
  {
    id: 'twitch',
    label: 'Twitch',
    bgColor: 'bg-[#9146FF] hover:bg-[#7B2FBE] border-[#9146FF]',
    textColor: 'text-white',
    logo: (
      <svg viewBox="0 0 24 24" className="w-4 h-4 flex-shrink-0 fill-white">
        <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714z"/>
      </svg>
    ),
  },
  {
    id: 'spotify',
    label: 'Spotify',
    bgColor: 'bg-[#1DB954] hover:bg-[#1AA34A] border-[#1DB954]',
    textColor: 'text-white',
    logo: (
      <svg viewBox="0 0 24 24" className="w-4 h-4 flex-shrink-0 fill-white">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
      </svg>
    ),
  },
];

const PROVIDER_SCOPES: Partial<Record<OAuthProvider, string>> = {
  google:  'openid email profile',
  discord: 'identify email',
  spotify: 'user-read-email user-read-private',
};

export const SocialAuthButtons: React.FC<SocialAuthButtonsProps> = ({ mode }) => {
  const [loading, setLoading] = useState<string | null>(null);

  const handleOAuth = async (provider: OAuthProvider) => {
    if (loading) return;
    setLoading(provider);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}/auth/callback`,
          scopes: PROVIDER_SCOPES[provider],
          queryParams: provider === 'google'
            ? { access_type: 'offline', prompt: 'select_account' }
            : undefined,
        },
      });
      if (error) throw error;
    } catch (err: any) {
      console.error(`[OAuth] ${provider} failed:`, err);
      toast.error(`${provider} sign-in failed. Please try again.`);
      setLoading(null);
    }
  };

  const verb = mode === 'signup' ? 'Sign up' : 'Sign in';

  return (
    <div className="w-full mt-4 space-y-3">
      {/* Divider */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        <div className="flex-1 h-px bg-gray-200" />
        <span className="text-[11px] text-gray-400 uppercase tracking-widest font-medium whitespace-nowrap px-1">
          or {verb} with
        </span>
        <div className="flex-1 h-px bg-gray-200" />
      </div>

      {/* 3-column grid — responsive */}
      <div className="grid grid-cols-3 gap-2">
        {OAUTH_PROVIDERS.map(({ id, label, bgColor, textColor, logo }) => (
          <button
            key={id}
            onClick={() => handleOAuth(id)}
            disabled={!!loading}
            title={`${verb} with ${label}`}
            className={`
              flex items-center justify-center gap-1.5
              px-2 py-2.5 rounded-lg border text-xs font-semibold
              transition-all duration-200 min-w-0
              disabled:opacity-40 disabled:cursor-not-allowed
              ${bgColor} ${textColor}
            `}
          >
            {loading === id
              ? <span className="animate-spin text-sm">⟳</span>
              : logo
            }
            {/* Label hidden on very small screens, shown from sm up */}
            <span className="truncate hidden sm:inline">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};