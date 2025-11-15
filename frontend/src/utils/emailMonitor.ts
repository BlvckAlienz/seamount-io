// File: frontend/src/utils/emailMonitor.ts
/**
 * Email Delivery Monitor
 * 
 * Supabase doesn't provide email delivery confirmations, so we can't know
 * if emails actually arrived. This utility provides client-side tracking
 * and fallback suggestions for users.
 */

interface EmailAttempt {
  email: string;
  timestamp: number;
  type: 'password_reset' | 'verification';
}

const EMAIL_STORAGE_KEY = 'seamount_email_attempts';
const RATE_LIMIT_WINDOW = 5 * 60 * 1000; // 5 minutes
const MAX_ATTEMPTS = 3;

export const emailMonitor = {
  /**
   * Track an email send attempt
   */
  recordAttempt(email: string, type: 'password_reset' | 'verification') {
    const attempts = this.getAttempts();
    attempts.push({
      email: email.toLowerCase(),
      timestamp: Date.now(),
      type,
    });
    
    // Clean old attempts (older than rate limit window)
    const cutoff = Date.now() - RATE_LIMIT_WINDOW;
    const filtered = attempts.filter(a => a.timestamp > cutoff);
    
    localStorage.setItem(EMAIL_STORAGE_KEY, JSON.stringify(filtered));
  },

  /**
   * Check if email has been attempted too many times
   */
  isRateLimited(email: string): boolean {
    const attempts = this.getAttempts();
    const cutoff = Date.now() - RATE_LIMIT_WINDOW;
    
    const recentAttempts = attempts.filter(
      a => a.email === email.toLowerCase() && a.timestamp > cutoff
    );
    
    return recentAttempts.length >= MAX_ATTEMPTS;
  },

  /**
   * Get time remaining until rate limit expires
   */
  getRateLimitRemaining(email: string): number {
    const attempts = this.getAttempts();
    const emailAttempts = attempts.filter(
      a => a.email === email.toLowerCase()
    );
    
    if (emailAttempts.length === 0) return 0;
    
    const oldestAttempt = Math.min(...emailAttempts.map(a => a.timestamp));
    const expiresAt = oldestAttempt + RATE_LIMIT_WINDOW;
    const remaining = expiresAt - Date.now();
    
    return Math.max(0, Math.ceil(remaining / 1000)); // seconds
  },

  /**
   * Get all recent attempts (for debugging)
   */
  getAttempts(): EmailAttempt[] {
    try {
      const stored = localStorage.getItem(EMAIL_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  },

  /**
   * Clear all tracked attempts (admin/debug only)
   */
  clearAttempts() {
    localStorage.removeItem(EMAIL_STORAGE_KEY);
  },
};