// File Location: frontend/src/types/index.ts

// License Management Types
export * from './licensing';

export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  verified?: boolean;
  lastLogin?: Date;
}

// Add UserProfile interface for Supabase user profiles
export interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  country_code: string;
  kyc_level: number;
  kyc_status: 'not_started' | 'pending' | 'in_progress' | 'under_review' | 'approved' | 'rejected' | 'skipped' | 'verified';
  is_admin: boolean;
  phone?: string;
  date_of_birth?: string;
  address?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  avatar_url?: string;
  created_at: string;
  updated_at?: string;
  wallet_address?: string | null;
  phone_number?: string | null;
  occupation?: string | null;
  source_of_funds?: string | null;
  risk_tolerance?: string;
  notification_preferences?: {
    sms: boolean;
    push: boolean;
    email: boolean;
  };
  settings?: Record<string, any>;
  metadata?: Record<string, any>;
  complycube_applicant_id?: string | null;
  role: string;
  user_id?: string | null;
  kyc_session_id?: string | null;
  kyc_provider?: string;
  security_flags?: Record<string, any>;
  last_login_at?: string | null;
  failed_login_attempts?: number;
  account_locked_until?: string | null;
  // ✅ ADD THESE MISSING FIELDS
  algorand_address?: string | null;
  bvn?: string | null;
  id_number?: string | null;
  id_type?: string | null;
  verification_skipped?: boolean;
  kyc_started_at?: string | null;
  kyc_completed_at?: string | null;
}

export interface Portfolio {
  totalBalance: number;
  totalPnL: number;
  totalPnLPercentage: number;
  usdsBalance: number;
  dayChange: number;
  dayChangePercentage: number;
  weekChange?: number;
  monthChange?: number;
  yearChange?: number;
}

export interface Asset {
  id: string;
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  change24hPercentage: number;
  marketCap?: number;
  volume24h?: number;
  holdings?: number;
  value?: number;
  category?: 'crypto' | 'stock' | 'forex' | 'commodity';
  exchange?: string;
  lastUpdated?: Date;
}

export interface Transaction {
  id: string;
  type: 'buy' | 'sell' | 'transfer' | 'swap' | 'deposit' | 'withdrawal';
  asset: string;
  amount: number;
  price: number;
  total: number;
  fee?: number;
  timestamp: Date;
  status: 'completed' | 'pending' | 'failed' | 'cancelled';
  txHash?: string;
  fromAddress?: string;
  toAddress?: string;
}

export interface Order {
  id: string;
  type: 'buy' | 'sell';
  orderType: 'market' | 'limit' | 'stop' | 'stop-limit';
  asset: string;
  amount: number;
  price: number;
  total: number;
  filled: number;
  status: 'open' | 'filled' | 'cancelled' | 'partially-filled';
  timestamp: Date;
  expiresAt?: Date;
  stopPrice?: number;
  fee?: number;
}

export interface Position {
  id: string;
  asset: string;
  side: 'long' | 'short';
  size: number;
  entryPrice: number;
  markPrice: number;
  liquidationPrice?: number;
  pnl: number;
  pnlPercentage: number;
  margin: number;
  leverage: number;
  timestamp: Date;
}

export interface ChartDataPoint {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  trades?: number;
}

export interface OrderBookEntry {
  price: number;
  size: number;
  total: number;
  count?: number;
}

export interface OrderBook {
  bids: OrderBookEntry[];
  asks: OrderBookEntry[];
  spread?: number;
  lastUpdated?: Date;
}

export interface Contact {
  id: string;
  name: string;
  address: string;
  avatar?: string;
  lastUsed?: Date;
  verified?: boolean;
  network?: string;
}

export interface RiskMetrics {
  var: number; // Value at Risk
  sharpeRatio: number;
  maxDrawdown: number;
  volatility: number;
  beta: number;
  alpha?: number;
  informationRatio?: number;
  calmarRatio?: number;
  sortinoRatio?: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  change24h: number;
  change24hPercentage: number;
  volume24h: number;
  marketCap?: number;
  high24h?: number;
  low24h?: number;
  lastUpdated: Date;
}

export interface TradingSession {
  id: string;
  startTime: Date;
  endTime?: Date;
  totalTrades: number;
  totalVolume: number;
  pnl: number;
  winRate: number;
  status: 'active' | 'closed';
}

export interface APIResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  timestamp: Date;
}

export interface LoadingState {
  isLoading: boolean;
  error?: string | null;
  lastUpdated?: Date;
}