/// <reference types="vite/client" />

// Vite environment variables
interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  readonly VITE_API_URL: string;
  readonly VITE_APP_URL: string;
  readonly VITE_STRIPE_PUBLISHABLE_KEY: string;
  readonly VITE_FLUTTERWAVE_PUBLIC_KEY: string;
  readonly VITE_COMPLYCUBE_PUBLIC_KEY: string;
  readonly VITE_REVENUECAT_API_KEY: string;
  readonly VITE_SENTRY_DSN: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Third-party module declarations
declare module 'react-select-country-list' {
  const value: any;
  export default value;
}

declare module 'qrcode.react' {
  const QRCode: any;
  export default QRCode;
}

declare module 'express' {
  const express: any;
  export default express;
}

// Global type extensions
declare global {
  interface Window {
    Stripe?: any;
    FlutterwaveCheckout?: any;
  }
}

export {};