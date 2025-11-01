// File: frontend/src/hooks/useAutoLogout.ts
// 🔒 SECURITY: Auto-logout after 10 mins inactivity

import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

const TIMEOUT_DURATION = 10 * 60 * 1000; // 10 minutes in milliseconds
const WARNING_DURATION = 2 * 60 * 1000; // Warn 2 minutes before timeout

export const useAutoLogout = () => {
  const { signOut, user } = useAuth();
  const navigate = useNavigate();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const warningRef = useRef<NodeJS.Timeout | null>(null);
  const warningShownRef = useRef(false);

  const clearTimers = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (warningRef.current) clearTimeout(warningRef.current);
    warningShownRef.current = false;
  };

  const handleLogout = async () => {
    toast.error('Session expired due to inactivity. Please sign in again.');
    await signOut();
    navigate('/');
  };

  const showWarning = () => {
    if (!warningShownRef.current) {
      warningShownRef.current = true;
      toast.warning(
        'You will be logged out in 2 minutes due to inactivity',
        { duration: 5000 }
      );
    }
  };

  const resetTimer = () => {
    if (!user) return; // Only run for authenticated users

    clearTimers();

    // Set warning timer (8 minutes)
    warningRef.current = setTimeout(showWarning, TIMEOUT_DURATION - WARNING_DURATION);

    // Set logout timer (10 minutes)
    timeoutRef.current = setTimeout(handleLogout, TIMEOUT_DURATION);
  };

  useEffect(() => {
    if (!user) {
      clearTimers();
      return;
    }

    // Activity events to track
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];

    // Add listeners
    events.forEach(event => {
      document.addEventListener(event, resetTimer, { passive: true });
    });

    // Start initial timer
    resetTimer();

    // Cleanup
    return () => {
      clearTimers();
      events.forEach(event => {
        document.removeEventListener(event, resetTimer);
      });
    };
  }, [user]);

  return { resetTimer };
};