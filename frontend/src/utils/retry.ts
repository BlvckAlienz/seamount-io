// Enhanced Retry Utilities for Seamount.io
// Location: src/utils/retry.ts
// Description: Robust retry mechanisms with exponential backoff and error classification

import { AxiosError } from 'axios';

export interface RetryOptions {
  maxAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
  exponentialBase?: number;
  retryCondition?: (error: any) => boolean;
  onRetry?: (attempt: number, error: any) => void;
  onFinalFailure?: (error: any, attempts: number) => void;
}

export interface RetryResult<T> {
  success: boolean;
  data?: T;
  error?: any;
  attempts: number;
  totalDuration: number;
}

// Basic retry with exponential backoff
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 3,
  baseDelay: number = 1000
): Promise<T> {
  let lastError: any;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      
      if (attempt === maxAttempts) {
        throw error;
      }

      // Exponential backoff with jitter
      const delay = baseDelay * Math.pow(2, attempt - 1);
      const jitter = Math.random() * 0.1 * delay;
      const finalDelay = Math.min(delay + jitter, 30000);

      console.warn(`Retry attempt ${attempt}/${maxAttempts} failed:`, error.message);
      console.warn(`Retrying in ${Math.round(finalDelay)}ms...`);

      await new Promise((resolve) => setTimeout(resolve, finalDelay));
    }
  }
  
  throw lastError;
}

// Enhanced retry function with comprehensive error handling
export async function enhancedRetry<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxAttempts = 3,
    baseDelay = 1000,
    maxDelay = 30000,
    exponentialBase = 2,
    retryCondition = (error) => isRetryableError(error),
    onRetry,
    onFinalFailure
  } = options;

  const startTime = Date.now();
  let lastError: any;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const result = await fn();
      
      if (attempt > 1) {
        console.info(`✅ Operation succeeded on attempt ${attempt}/${maxAttempts}`);
      }
      
      return result;
    } catch (error) {
      lastError = error;
      
      // Don't retry on final attempt
      if (attempt === maxAttempts) {
        const totalDuration = Date.now() - startTime;
        console.error(`❌ Final attempt ${attempt}/${maxAttempts} failed after ${totalDuration}ms:`, error);
        onFinalFailure?.(error, attempt);
        throw error;
      }

      // Check if we should retry this error
      if (!retryCondition(error)) {
        console.error(`🚫 Non-retryable error detected, stopping retries:`, error);
        throw error;
      }

      // Calculate delay with exponential backoff and jitter
      const exponentialDelay = baseDelay * Math.pow(exponentialBase, attempt - 1);
      const jitter = Math.random() * 0.3 * exponentialDelay; // 30% jitter
      const finalDelay = Math.min(exponentialDelay + jitter, maxDelay);

      console.warn(`⚠️  Attempt ${attempt}/${maxAttempts} failed: ${error.message}`);
      console.warn(`🔄 Retrying in ${Math.round(finalDelay)}ms...`);

      // Call retry callback
      onRetry?.(attempt, error);

      await new Promise((resolve) => setTimeout(resolve, finalDelay));
    }
  }
  
  throw lastError;
}

// Determine if an error is retryable
export function isRetryableError(error: any): boolean {
  // Network errors
  if (error.code === 'ECONNRESET' || 
      error.code === 'ENOTFOUND' || 
      error.code === 'ECONNREFUSED' ||
      error.code === 'ETIMEDOUT') {
    return true;
  }

  // HTTP errors that are retryable
  if (error.response?.status) {
    const status = error.response.status;
    // Retry on 5xx server errors, 429 rate limiting, 408 timeout, 502/503/504
    return status >= 500 || status === 429 || status === 408;
  }

  // Axios specific errors
  if (error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED') {
    return true;
  }

  // Supabase specific errors
  if (error.message?.includes('network') || 
      error.message?.includes('timeout') ||
      error.message?.includes('temporarily unavailable')) {
    return true;
  }

  // Database connection errors
  if (error.message?.includes('connection') && 
      error.message?.includes('refused')) {
    return true;
  }

  return false;
}

// Specialized retry for authentication operations
export async function retryAuth<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 2,
  baseDelay: number = 2000
): Promise<T> {
  return enhancedRetry(fn, {
    maxAttempts,
    baseDelay,
    retryCondition: (error) => {
      // Only retry on network errors for auth, not auth failures
      return isRetryableError(error) && 
             !isAuthenticationError(error) &&
             !isAuthorizationError(error);
    },
    onRetry: (attempt, error) => {
      console.warn(`🔐 Auth retry ${attempt}: ${error.message}`);
    }
  });
}

// Specialized retry for blockchain operations
export async function retryBlockchain<T>(
  fn: () => Promise<T>,
  maxAttempts: number = 5,
  baseDelay: number = 3000
): Promise<T> {
  return enhancedRetry(fn, {
    maxAttempts,
    baseDelay,
    exponentialBase: 1.5, // Slower exponential growth for blockchain
    maxDelay: 60000, // Allow longer delays for blockchain
    retryCondition: (error) => {
      // Blockchain specific retryable errors
      return isRetryableError(error) || 
             error.message?.includes('gas') ||
             error.message?.includes('nonce') ||
             error.message?.includes('network congestion');
    },
    onRetry: (attempt, error) => {
      console.warn(`⛓️  Blockchain retry ${attempt}: ${error.message}`);
    }
  });
}

// Check if error is an authentication error (don't retry these)
export function isAuthenticationError(error: any): boolean {
  if (error.response?.status === 401) return true;
  if (error.message?.toLowerCase().includes('invalid_grant')) return true;
  if (error.message?.toLowerCase().includes('invalid credentials')) return true;
  if (error.message?.toLowerCase().includes('unauthorized')) return true;
  return false;
}

// Check if error is an authorization error (don't retry these)
export function isAuthorizationError(error: any): boolean {
  if (error.response?.status === 403) return true;
  if (error.message?.toLowerCase().includes('forbidden')) return true;
  if (error.message?.toLowerCase().includes('insufficient permissions')) return true;
  return false;
}

// Circuit breaker pattern for repeated failures
export class CircuitBreaker<T> {
  private failureCount = 0;
  private lastFailureTime = 0;
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';

  constructor(
    private failureThreshold: number = 5,
    private timeout: number = 60000 // 1 minute
  ) {}

  async execute(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (Date.now() - this.lastFailureTime > this.timeout) {
        this.state = 'HALF_OPEN';
        console.info('🔄 Circuit breaker: HALF_OPEN - Testing...');
      } else {
        throw new Error('Circuit breaker is OPEN - too many recent failures');
      }
    }

    try {
      const result = await fn();
      
      if (this.state === 'HALF_OPEN') {
        this.reset();
        console.info('✅ Circuit breaker: CLOSED - Service recovered');
      }
      
      return result;
    } catch (error) {
      this.recordFailure();
      throw error;
    }
  }

  private recordFailure(): void {
    this.failureCount++;
    this.lastFailureTime = Date.now();

    if (this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
      console.error(`🚫 Circuit breaker: OPEN - Too many failures (${this.failureCount})`);
    }
  }

  private reset(): void {
    this.failureCount = 0;
    this.state = 'CLOSED';
  }

  getState(): string {
    return this.state;
  }
}

// Specialized retry with circuit breaker for critical operations
export async function retryWithCircuitBreaker<T>(
  fn: () => Promise<T>,
  circuitBreaker: CircuitBreaker<T>,
  retryOptions?: RetryOptions
): Promise<T> {
  return circuitBreaker.execute(() => 
    enhancedRetry(fn, retryOptions)
  );
}

// Utility to create pre-configured circuit breakers
export const createCircuitBreaker = <T>(
  failureThreshold: number = 5,
  timeout: number = 60000
): CircuitBreaker<T> => {
  return new CircuitBreaker<T>(failureThreshold, timeout);
};

// Export commonly used circuit breakers
export const authCircuitBreaker = createCircuitBreaker(3, 30000);
export const blockchainCircuitBreaker = createCircuitBreaker(5, 120000);
export const apiCircuitBreaker = createCircuitBreaker(5, 60000);

// Advanced retry with detailed result tracking
export async function retryWithDetails<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<RetryResult<T>> {
  const startTime = Date.now();
  let attempts = 0;

  try {
    const data = await enhancedRetry(async () => {
      attempts++;
      return fn();
    }, options);

    return {
      success: true,
      data,
      attempts,
      totalDuration: Date.now() - startTime
    };
  } catch (error) {
    return {
      success: false,
      error,
      attempts,
      totalDuration: Date.now() - startTime
    };
  }
}

// Exponential backoff with configurable multiplier
export function calculateBackoff(
  attempt: number, 
  baseDelay: number = 1000,
  multiplier: number = 2,
  maxDelay: number = 30000,
  jitterFactor: number = 0.1
): number {
  const exponentialDelay = baseDelay * Math.pow(multiplier, attempt - 1);
  const jitter = Math.random() * jitterFactor * exponentialDelay;
  return Math.min(exponentialDelay + jitter, maxDelay);
}

// Utility function for promise timeout
export function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  timeoutMessage: string = 'Operation timed out'
): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs)
    )
  ]);
}

// Batch retry for multiple operations
export async function retryBatch<T>(
  operations: (() => Promise<T>)[],
  options: RetryOptions = {}
): Promise<RetryResult<T>[]> {
  const results = await Promise.allSettled(
    operations.map(op => retryWithDetails(op, options))
  );

  return results.map(result => 
    result.status === 'fulfilled' 
      ? result.value 
      : { 
          success: false, 
          error: result.reason, 
          attempts: 0, 
          totalDuration: 0 
        }
  );
}