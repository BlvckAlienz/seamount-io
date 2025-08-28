// frontend/src/components/CookieConsentBanner.tsx
import React, { useState, useEffect } from 'react';
import { apiClient } from '../config/api';
import { useAuth } from '../contexts/AuthContext';

interface CookieConsentBannerProps {
  sessionId: string;
  onConsentGiven: () => void;
}

export const CookieConsentBanner: React.FC<CookieConsentBannerProps> = ({ 
  sessionId, 
  onConsentGiven 
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const { session: authSession, user } = useAuth();
  const maxRetries = 3;

  useEffect(() => {
    // Reset retry count when auth state changes
    setRetryCount(0);
  }, [authSession]);

  const handleConsent = async (preferences: Record<string, boolean>) => {
    if (retryCount >= maxRetries) {
      console.error("Max retries exceeded for consent update. Hiding banner.");
      onConsentGiven();
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.post('/api/v1/consent/update', {
        session_id: sessionId,
        preferences,
        user_id: user?.id || null
      });
      onConsentGiven();
    } catch (error: any) {
      console.error("Failed to update consent:", error);
      setRetryCount(prev => prev + 1);
      
      // If it's an authentication error, don't retry indefinitely
      if (error.response?.status === 403 || error.response?.status === 401) {
        console.error("Authentication error. Not retrying.");
        onConsentGiven();
      } else {
        // Retry for other errors (e.g., network issues) after a delay
        setTimeout(() => {
          handleConsent(preferences);
        }, 1000);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      backgroundColor: '#1a202c',
      color: 'white',
      padding: '1.5rem',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }}>
      <p style={{ margin: 0, marginRight: '1rem' }}>
        We use essential cookies for security and analytics to improve your experience.
      </p>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <button 
          onClick={() => handleConsent({ functional: true, analytics: false, marketing: false })}
          disabled={isSubmitting}
          style={{ padding: '0.5rem 1rem', border: '1px solid white', background: 'transparent', color: 'white', cursor: 'pointer' }}
        >
          Accept Essential
        </button>
        <button 
          onClick={() => handleConsent({ functional: true, analytics: true, marketing: true })}
          disabled={isSubmitting}
          style={{ padding: '0.5rem 1rem', background: '#3b82f6', color: 'white', border: 'none', cursor: 'pointer' }}
        >
          Accept All
        </button>
      </div>
    </div>
  );
};