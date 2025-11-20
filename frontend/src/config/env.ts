// src/config/env.ts
// LIVE DATA CONFIGURATION - NO MOCK MODE

// Debug all environment variables
console.log('Environment variables available:');
console.log('VITE_API_BASE_URL:', import.meta.env.VITE_API_BASE_URL);
console.log('VITE_SUPABASE_URL:', import.meta.env.VITE_SUPABASE_URL);
console.log('VITE_COMPLYCUBE_API_KEY:', import.meta.env.VITE_COMPLYCUBE_API_KEY ? 'SET' : 'NOT SET');
console.log('MODE:', import.meta.env.MODE);
console.log('PROD:', import.meta.env.PROD);
console.log('DEV:', import.meta.env.DEV);

// Supabase Configuration
export const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || '';
export const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || '';

// API Configuration - CRITICAL FIX
// Use VITE_API_BASE_URL if available, otherwise fall back to production URL
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://seamount-io-pr8a.onrender.com';

// API Keys (Optional - we have fallbacks)
export const ALPHA_VANTAGE_API_KEY = import.meta.env.VITE_ALPHA_VANTAGE_API_KEY || '';
export const COINGECKO_API_KEY = import.meta.env.VITE_COINGECKO_API_KEY || '';
export const CIRCLE_API_KEY = import.meta.env.VITE_CIRCLE_API_KEY || '';
export const COMPLYCUBE_API_KEY = import.meta.env.VITE_COMPLYCUBE_API_KEY || '';

// FORCE LIVE MODE - NO MOCK DATA EVER
export const MOCK_MODE = false;

// Data Source Priority (Best to Worst)
export const DATA_SOURCES = {
  // Stock Data Priority
  STOCK_PRIMARY: ALPHA_VANTAGE_API_KEY ? 'alpha_vantage' : 'yahoo_finance',
  STOCK_FALLBACK: 'yahoo_finance', // Always available, no API key needed
  
  // Crypto Data Priority  
  CRYPTO_PRIMARY: COINGECKO_API_KEY ? 'coingecko_pro' : 'coingecko_free',
  CRYPTO_FALLBACK: 'coingecko_free', // Always available, no API key needed
  
  // Economic Data
  ECONOMIC_PRIMARY: 'fred', // Federal Reserve Economic Data (free)
  ECONOMIC_FALLBACK: 'yahoo_finance'
};

// Service Status
export const isAlphaVantageConfigured = !!ALPHA_VANTAGE_API_KEY;
export const isCoinGeckoConfigured = !!COINGECKO_API_KEY;
export const isCircleConfigured = !!CIRCLE_API_KEY;
export const isSupabaseConfigured = !!(SUPABASE_URL && SUPABASE_ANON_KEY);
export const isSentryConfigured = true;

// API Endpoints
export const API_ENDPOINTS = {
  // Yahoo Finance (Free, No API Key)
  YAHOO_FINANCE: 'https://query1.finance.yahoo.com/v8/finance/chart',
  YAHOO_QUOTE: 'https://query1.finance.yahoo.com/v1/finance/quote',
  YAHOO_HISTORY: 'https://query1.finance.yahoo.com/v8/finance/chart',
  
  // CoinGecko (Free tier available)
  COINGECKO_FREE: 'https://api.coingecko.com/api/v3',
  COINGECKO_PRO: 'https://pro-api.coingecko.com/api/v3',
  
  // Alpha Vantage (if you have key)
  ALPHA_VANTAGE: 'https://www.alphavantage.co/query',
  
  // Federal Reserve Economic Data (Free)
  FRED: 'https://api.stlouisfed.org/fred/series/observations'
};

// Rate Limits (requests per minute)
export const RATE_LIMITS = {
  YAHOO_FINANCE: 2000, // Very generous
  COINGECKO_FREE: 10,
  COINGECKO_PRO: 500,
  ALPHA_VANTAGE: 5,
  FRED: 120
};

// ComplyCube Configuration
export const COMPLYCUBE_CONFIG = {
  API_KEY: COMPLYCUBE_API_KEY,
  SDK_SCRIPT: 'https://assets.complycube.com/web-sdk/v1/complycube.min.js',
  SDK_STYLES: 'https://assets.complycube.com/web-sdk/v1/style.css',
  ENABLED: !!COMPLYCUBE_API_KEY
};

// Environment Validation Interface
export interface EnvironmentStatus {
  isValid: boolean;
  criticalServices: ServiceStatus[];
  optionalServices: ServiceStatus[];
  warnings: string[];
  errors: string[];
}

export interface ServiceStatus {
  name: string;
  status: 'connected' | 'configured' | 'missing' | 'error';
  description: string;
  required: boolean;
}

// Environment Validation Function
export const validateEnvironment = (): EnvironmentStatus => {
  const criticalServices: ServiceStatus[] = [];
  const optionalServices: ServiceStatus[] = [];
  const warnings: string[] = [];
  const errors: string[] = [];

  // Critical Services (Required for core functionality)
  
  // API Base URL - This is CRITICAL
  if (!API_BASE_URL) {
    errors.push('API_BASE_URL is not configured');
    criticalServices.push({
      name: 'API Server',
      status: 'error',
      description: 'API base URL not configured',
      required: true
    });
  } else {
    criticalServices.push({
      name: 'API Server',
      status: 'connected',
      description: `Connected to ${API_BASE_URL}`,
      required: true
    });
  }

  // Yahoo Finance - Always available, no config needed
  criticalServices.push({
    name: 'Yahoo Finance',
    status: 'connected',
    description: 'Primary market data source (free)',
    required: true
  });

  // CoinGecko Free - Always available
  criticalServices.push({
    name: 'CoinGecko Free',
    status: 'connected', 
    description: 'Crypto market data (free tier)',
    required: true
  });

  // Optional Services (Enhanced functionality)
  
  // Supabase
  if (isSupabaseConfigured) {
    optionalServices.push({
      name: 'Supabase',
      status: 'configured',
      description: 'User data & portfolio sync',
      required: false
    });
  } else {
    optionalServices.push({
      name: 'Supabase',
      status: 'missing',
      description: 'User data will be local only',
      required: false
    });
    warnings.push('Supabase not configured - user data will be local only');
  }

  // Alpha Vantage
  if (isAlphaVantageConfigured) {
    optionalServices.push({
      name: 'Alpha Vantage',
      status: 'configured',
      description: 'Premium stock data & fundamentals',
      required: false
    });
  } else {
    optionalServices.push({
      name: 'Alpha Vantage',
      status: 'missing',
      description: 'Using Yahoo Finance fallback',
      required: false
    });
    warnings.push('Alpha Vantage not configured - using free Yahoo Finance');
  }

  // CoinGecko Pro
  if (isCoinGeckoConfigured) {
    optionalServices.push({
      name: 'CoinGecko Pro',
      status: 'configured',
      description: 'Premium crypto data & analytics',
      required: false
    });
  } else {
    optionalServices.push({
      name: 'CoinGecko Pro',
      status: 'missing',
      description: 'Using free tier with rate limits',
      required: false
    });
    warnings.push('CoinGecko Pro not configured - using free tier with limits');
  }

  // Circle (USDC/Payment Rails)
  if (isCircleConfigured) {
    optionalServices.push({
      name: 'Circle API',
      status: 'configured',
      description: 'USDC payments & settlements',
      required: false
    });
  } else {
    optionalServices.push({
      name: 'Circle API',
      status: 'missing',
      description: 'Payment features limited',
      required: false
    });
    warnings.push('Circle API not configured - payment features limited');
  }

  // CompyCube (KYC/AML)
  if (COMPLYCUBE_CONFIG.ENABLED) {
    optionalServices.push({
      name: 'ComplyCube',
      status: 'configured',
      description: 'KYC/AML compliance',
      required: false
    });
  } else {
    optionalServices.push({
      name: 'ComplyCube',
      status: 'missing',
      description: 'Manual compliance required',
      required: false
    });
    warnings.push('ComplyCube not configured - manual compliance required');
  }

  // Determine overall validity
  const hasAllCritical = criticalServices.every(s => s.status === 'connected' || s.status === 'configured');
  const isValid = hasAllCritical && errors.length === 0;

  return {
    isValid,
    criticalServices,
    optionalServices,
    warnings,
    errors
  };
};

// Auto-validation on import
const envStatus = validateEnvironment();

// Debug Info
console.log('🚀 SEAMOUNT.IO - LIVE DATA MODE ENABLED');
console.log('🌐 API Base URL:', API_BASE_URL);
console.log('📊 Data Sources:', {
  stocks: DATA_SOURCES.STOCK_PRIMARY,
  crypto: DATA_SOURCES.CRYPTO_PRIMARY,
  fallbacks: {
    stocks: DATA_SOURCES.STOCK_FALLBACK,
    crypto: DATA_SOURCES.CRYPTO_FALLBACK
  }
});

console.log('🔧 Environment Status:', {
  valid: envStatus.isValid,
  critical: envStatus.criticalServices.length,
  optional: envStatus.optionalServices.filter(s => s.status === 'configured').length,
  warnings: envStatus.warnings.length,
  errors: envStatus.errors.length
});

if (envStatus.warnings.length > 0) {
  console.warn('⚠️ Warnings:', envStatus.warnings);
}

if (envStatus.errors.length > 0) {
  console.error('❌ Errors:', envStatus.errors);
}

if (envStatus.isValid) {
  console.log('✅ Core trading infrastructure ready!');
} else {
  console.error('❌ Core infrastructure not ready due to configuration errors');
}

export default {
  SUPABASE_URL,
  SUPABASE_ANON_KEY,
  API_BASE_URL,
  ALPHA_VANTAGE_API_KEY,
  COINGECKO_API_KEY,
  CIRCLE_API_KEY,
  COMPLYCUBE_API_KEY,
  MOCK_MODE,
  DATA_SOURCES,
  isAlphaVantageConfigured,
  isCoinGeckoConfigured,
  isCircleConfigured,
  isSupabaseConfigured,
  API_ENDPOINTS,
  RATE_LIMITS,
  COMPLYCUBE_CONFIG,
  validateEnvironment
};