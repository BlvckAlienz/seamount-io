// File: frontend/src/hooks/useAutoLogout.ts
// 🔒 SECURITY: Auto-logout after 10 mins inactivity
// ✅ FIXED: No crashes, proper cleanup, React-safe

import { useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { toastInfo, toastWarning } from '@/lib/toast-helpers';

const TIMEOUT_DURATION = 10 * 60 * 1000; // 10 minutes
const WARNING_DURATION = 2 * 60 * 1000; // Warn 2 minutes before

export const useAutoLogout = () => {
  const { signOut, user } = useAuth();
  
  // ✅ Browser-safe timer types (number, not NodeJS.Timeout)
  const timeoutRef = useRef<number | null>(null);
  const warningRef = useRef<number | null>(null);
  const warningShownRef = useRef(false);
  const isMountedRef = useRef(true);

  // ✅ Memoized cleanup - prevents stale closures
  const clearTimers = useCallback(() => {
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    if (warningRef.current) {
      window.clearTimeout(warningRef.current);
      warningRef.current = null;
    }
    warningShownRef.current = false;
  }, []);

  // ✅ Async-safe logout - no navigation conflicts
  const handleLogout = useCallback(async () => {
    if (!isMountedRef.current) return; // Guard against unmounted calls
    
    clearTimers();
    
    // Show toast BEFORE logout to ensure user sees it
    toast.error('Session expired due to inactivity. Please sign in again.', {
      duration: 6000,
      id: 'auto-logout' // Prevent duplicate toasts
    });
    
    // Let AuthContext handle ALL navigation/cleanup
    // It already does: window.location.href = '/' in signOut()
    try {
      await signOut();
    } catch (error) {
      console.error('[AutoLogout] Logout failed:', error);
    }
  }, [signOut, clearTimers]);

  // ✅ Memoized warning - prevents duplicate toasts
  const showWarning = useCallback(() => {
    if (!isMountedRef.current || warningShownRef.current) return;
    
    warningShownRef.current = true;
    toast('You will be logged out soon due to inactivity', {
      duration: 5000,
      id: 'auto-logout-warning',
      icon: 'ℹ️'
    });
  }, []);

  // ✅ Memoized resetTimer - safe for dependency arrays
  const resetTimer = useCallback(() => {
    if (!user || !isMountedRef.current) return;

    clearTimers();

    // Set warning timer (8 minutes)
    warningRef.current = window.setTimeout(showWarning, TIMEOUT_DURATION - WARNING_DURATION);

    // Set logout timer (10 minutes)
    timeoutRef.current = window.setTimeout(handleLogout, TIMEOUT_DURATION);
  }, [user, clearTimers, showWarning, handleLogout]);

  useEffect(() => {
    isMountedRef.current = true;
    
    if (!user) {
      clearTimers();
      return;
    }

    // Activity events to track
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];

    // Add listeners with proper options
    events.forEach(event => {
      document.addEventListener(event, resetTimer, { passive: true });
    });

    // Start initial timer
    resetTimer();

    // Cleanup
    return () => {
      isMountedRef.current = false;
      clearTimers();
      events.forEach(event => {
        document.removeEventListener(event, resetTimer);
      });
    };
  }, [user, resetTimer, clearTimers]); // ✅ All deps included

  return { resetTimer };
};