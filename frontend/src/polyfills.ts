// File: src/polyfills.ts
import { Buffer } from 'buffer';

// Polyfill Buffer for browser
(window as any).Buffer = Buffer;
(window as any).global = window;
(window as any).process = {
  env: {},
  version: '',
  nextTick: (callback: () => void) => setTimeout(callback, 0),
};

// BigInt safety fixes
if (typeof BigInt !== 'undefined') {
  // Fix for BigInt JSON serialization
  (BigInt.prototype as any).toJSON = function() {
    return this.toString();
  };

// 🚨 ULTRA-DEFENSIVE Math.pow for BigInt operations
const originalMathPow = Math.pow;
(Math as any).pow = function(base: any, exponent: any): number {
  try {
    // Detect BigInt immediately (before any operations)
    const isBaseBigInt = typeof base === 'bigint';
    const isExpBigInt = typeof exponent === 'bigint';
    
    if (isBaseBigInt || isExpBigInt) {
      console.warn('[Polyfill] Math.pow called with BigInt - converting safely');
      
      // Convert to safe numbers
      const safeBase = isBaseBigInt ? Number(base) : base;
      const safeExp = isExpBigInt ? Number(exponent) : exponent;
      
      // Check for overflow BEFORE calculation
      if (safeBase > Number.MAX_SAFE_INTEGER || safeExp > 1000) {
        console.error('[Polyfill] BigInt too large for Math.pow, returning MAX');
        return Number.MAX_SAFE_INTEGER;
      }
      
      return originalMathPow(safeBase, safeExp);
    }
    
    // Normal numbers - use original function
    return originalMathPow(base, exponent);
    
  } catch (error) {
    console.error('[Polyfill] Math.pow error:', error);
    // Fallback to safe default
    return 1;
  }
};

// 🚨 ALSO override the global Math object (for good measure)
if (typeof window !== 'undefined') {
  (window as any).Math = Math;
}
  
  // Ensure process is available
  if (!window.process) {
    window.process = { env: {}, version: '' };
  }
  
  // Fix for viem/wagmi that might use globalThis.crypto
  if (!globalThis.crypto) {
    console.warn('crypto API not available - polyfilling');
    (globalThis as any).crypto = {
      getRandomValues: (arr: any) => {
        for (let i = 0; i < arr.length; i++) {
          arr[i] = Math.floor(Math.random() * 256);
        }
        return arr;
      }
    };
  }
}

export {};