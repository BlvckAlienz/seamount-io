// File: frontend/src/types/quidax.types.ts

export interface QuidaxQuote {
  success: boolean;
  quote_reference: string;
  market: string;
  quote_type: 'buy' | 'sell';
  unit_price: number;
  crypto_amount: number;
  fiat_amount: number;
  fee: number;
  total: number;
  expires_at: string;
}

export interface QuidaxInstantOrder {
  success: boolean;
  order_id: string;
  payment_url: string;
  status: 'pending' | 'processing' | 'done' | 'cancelled';
  amount: number;
  crypto_amount: number;
}

export interface QuidaxOrderStatus {
  success: boolean;
  order_id: string;
  status: 'pending' | 'processing' | 'done' | 'cancelled';
  type: 'buy' | 'sell';
  market: string;
  price: number;
  total: number;
  filled: number;
}

export interface QuidaxQuoteRequest {
  market: string;
  quote_type: 'buy' | 'sell';
  amount: number;
  amount_type: 'fiat' | 'crypto';
}

export interface QuidaxInstantOrderRequest {
  quote_reference: string;
}