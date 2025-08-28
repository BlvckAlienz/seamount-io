// frontend/src/components/CookieConsentBanner.tsx (replace entire file)
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
  const { session: authSession } = useAuth();

  useEffect(() => {
    // If user authenticates while banner is shown, wait a moment for token to propagate
    if (authSession) {
      const timer = setTimeout(() => {
        // Retry consent submission if we had previously failed due to auth
        const retryConsent = localStorage.getItem('seamount_consent_retry');
        if (retryConsent) {
          handleConsent(JSON.parse(retryConsent));
          localStorage.removeItem('seamount_consent_retry');
        }
      }, 1000);
      
      return () => clearTimeout(timer);
    }
  }, [authSession]);

  const handleConsent = async (preferences: Record<string, boolean>) => {
    setIsSubmitting(true);
    try {
      await apiClient.post('/api/v1/consent/update', {
        session_id: sessionId,
        preferences,
      });
      onConsentGiven();
    } catch (error: any) {
      console.error("Failed to update consent:", error);
      
      // If it's an authentication error, store the preferences for retry
      if (error.response?.status === 401 || error.response?.status === 403) {
        localStorage.setItem('seamount_consent_retry', JSON.stringify(preferences));
        
        // Wait a bit for auth state to propagate, then retry
        setTimeout(() => {
          handleConsent(preferences);
        }, 1000);
      } else {
        // For other errors, just hide the banner to not block the user
        onConsentGiven();
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