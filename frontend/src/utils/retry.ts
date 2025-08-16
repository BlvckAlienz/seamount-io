// Enhanced Retry Utilities for Seamount.io
// Location: src/utils/retry.ts
// Version: 2.0 (Tuned for a "Fail-Fast" UI Experience)

// Basic retry with exponential backoff, tuned for a fast UI.
// Will try once, then retry once more after ~500ms. Fails in under a second.
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 2, // Original: 3
  baseDelay: number = 500   // Original: 1000
): Promise<T> {
  let lastError: any;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      if (attempt === maxAttempts) {
        // Don't log on the final attempt, the calling function will handle it.
        throw error;
      }

      // Exponential backoff with jitter
      const delay = baseDelay * Math.pow(2, attempt - 1);
      const jitter = Math.random() * 0.2 * delay; // 20% jitter
      const finalDelay = Math.min(delay + jitter, 5000); // Max delay of 5s

      console.warn(`Request failed. Retrying in ${Math.round(finalDelay)}ms...`);

      await new Promise((resolve) => setTimeout(resolve, finalDelay));
    }
  }
  
  throw lastError; // Should be unreachable, but satisfies TypeScript
}


// --- Advanced Utilities (Circuit Breakers, etc.) ---
// The following advanced tools are solid and do not need modification.
// Their parameters are for more critical, non-UI operations.

export interface RetryOptions {
  maxAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
  retryCondition?: (error: any) => boolean;
}

// Enhanced retry function with comprehensive error handling
export async function enhancedRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  // Tuned defaults for a faster UI experience
  const {
    maxAttempts = 2,
    baseDelay = 500,
    maxDelay = 5000,
    retryCondition = (error) => isRetryableError(error),
  } = options;

  let lastError: any;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (attempt === maxAttempts || !retryCondition(error)) {
        throw error;
      }
      const delay = baseDelay * Math.pow(2, attempt - 1);
      const jitter = Math.random() * 0.2 * delay;
      const finalDelay = Math.min(delay + jitter, maxDelay);
      await new Promise((resolve) => setTimeout(resolve, finalDelay));
    }
  }
  throw lastError;
}

// Determine if an error is retryable (server errors, network issues)
export function isRetryableError(error: any): boolean {
  // Network errors
  if (error.code && ['ECONNRESET', 'ENOTFOUND', 'ETIMEDOUT', 'ERR_NETWORK'].includes(error.code)) {
    return true;
  }
  // Retry on 5xx server errors, but not client errors (4xx) which are usually not temporary
  if (error.response?.status && error.response.status >= 500) {
    return true;
  }
  // Supabase specific network issues
  if (error.message?.includes('network') || error.message?.includes('temporarily unavailable')) {
    return true;
  }
  return false;
}

// Check if error is an authentication error (don't retry these)
export function isAuthenticationError(error: any): boolean {
  return error.response?.status === 401 || error.message?.toLowerCase().includes('invalid credentials');
}

// Check if error is an authorization error (don't retry these)
export function isAuthorizationError(error: any): boolean {
  return error.response?.status === 403 || error.message?.toLowerCase().includes('forbidden');
}