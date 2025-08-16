import React, { useState } from 'react';
import { apiClient } from '../config/api';

interface CookieConsentBannerProps {
  sessionId: string;
  onConsentGiven: () => void;
}

export const CookieConsentBanner: React.FC<CookieConsentBannerProps> = ({ sessionId, onConsentGiven }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleConsent = async (preferences: Record<string, boolean>) => {
    setIsSubmitting(true);
    try {
      await apiClient.post('/api/v1/consent/update', {
        session_id: sessionId,
        preferences,
      });
      onConsentGiven();
    } catch (error) {
      console.error("Failed to update consent:", error);
      // Even if it fails, we hide the banner to not block the user.
      // The backend will know consent wasn't given for this session.
      onConsentGiven();
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
      backgroundColor: '#1a202c', // dark gray
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