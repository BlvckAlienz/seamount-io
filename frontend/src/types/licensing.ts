// File Location: frontend/src/types/licensing.ts
// Add these types to your existing types or create this new file

export enum LicenseTier {
  BASIC = 'basic',
  PRO = 'pro',
  ENTERPRISE = 'enterprise'
}

export enum LicenseStatus {
  PENDING = 'pending',
  ACTIVE = 'active',
  EXPIRED = 'expired',
  CANCELLED = 'cancelled'
}

export enum PaymentStatus {
  PENDING = 'pending',
  COMPLETED = 'completed',
  FAILED = 'failed',
  REFUNDED = 'refunded'
}

export enum PricingRegion {
  NIGERIA = 'nigeria',
  KENYA = 'kenya',
  DEFAULT = 'default'
}

// License Information
export interface LicenseInfo {
  id: string;
  user_id: string;
  tier: LicenseTier;
  status: LicenseStatus;
  employee_count?: number;
  license_fee: number;
  currency: string;
  region: string;
  
  // Timestamps
  purchased_at: string;
  activated_at?: string;
  expires_at?: string;
  cancelled_at?: string;
  
  // Payment info
  payment_reference?: string;
  payment_status: PaymentStatus;
  payment_provider?: string;
  
  // Computed fields
  is_active?: boolean;
  days_until_expiry?: number;
}

// License Purchase Request
export interface LicensePurchaseRequest {
  tier: LicenseTier;
  employee_count?: number;
  region?: PricingRegion;
  payment_method?: 'flutterwave' | 'stripe';
  success_url?: string;
  cancel_url?: string;
}

// License Purchase Response
export interface LicensePurchaseResponse {
  license_id: string;
  payment_link: string;
  amount_due: number;
  currency: string;
  expires_at?: string;
}

// Tier Upgrade Request
export interface TierUpgradeRequest {
  target_tier: LicenseTier;
  employee_count?: number;
}

// License Usage Statistics
export interface LicenseUsageStats {
  license_id: string;
  month_year: string;
  transactions_count: number;
  volume_processed: number;
  fees_saved: number;
  employees_active: number;
  
  // Limits
  transaction_limit?: number;
  volume_limit?: number;
  
  // Utilization percentages
  transaction_utilization: number;
  volume_utilization: number;
}

// Transaction Fee Calculation
export interface TransactionFeeCalculation {
  amount: number;
  base_fee: number;
  discounted_fee: number;
  savings: number;
  discount_percentage: number;
  tier: LicenseTier;
}

// Tier Information for Display
export interface TierInfo {
  tier: LicenseTier;
  name: string;
  license_fee: number;
  currency: string;
  transaction_rate: number;
  discount_percentage: number;
  employee_limit?: number;
  features: string[];
  recommended?: boolean;
}

// Pricing Response
export interface PricingResponse {
  tiers: TierInfo[];
  region: string;
  individual_rate: number;
  currency: string;
}

// Savings Calculator Response
export interface SavingsCalculation {
  tier: LicenseTier;
  license_fee: number;
  transaction_cost: number;
  total_first_year_cost: number;
  annual_savings: number;
  net_first_year_savings: number;
  break_even_volume: number;
  transaction_rate: number;
  discount_percentage: number;
}

export interface SavingsCalculatorResponse {
  annual_volume: number;
  individual_annual_cost: number;
  individual_rate: number;
  savings_by_tier: Record<string, SavingsCalculation>;
}

// License Feature
export interface LicenseFeature {
  feature_key: string;
  feature_name: string;
  feature_description?: string;
  is_enabled: boolean;
}

// Admin Statistics
export interface LicensingStats {
  total_licenses: number;
  active_licenses: number;
  licenses_by_tier: Record<LicenseTier, number>;
  monthly_revenue: number;
  total_fees_saved: number;
  average_transaction_volume: number;
}

// Transaction Validation Response
export interface TransactionValidationResponse {
  allowed: boolean;
  message: string;
  requires_upgrade?: boolean;
  fee_calculation?: TransactionFeeCalculation;
}

// License Tier History
export interface LicenseTierHistory {
  id: string;
  license_id: string;
  from_tier?: LicenseTier;
  to_tier: LicenseTier;
  change_type: 'upgrade' | 'downgrade' | 'initial';
  prorated_amount?: number;
  effective_date: string;
  payment_reference?: string;
  payment_status: PaymentStatus;
}

// API Response Wrappers
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// Form State Types for Frontend
export interface LicensePurchaseForm {
  tier: LicenseTier;
  employeeCount: number;
  region: PricingRegion;
  acceptTerms: boolean;
}

export interface TierComparisonProps {
  tiers: TierInfo[];
  currentTier?: LicenseTier;
  onSelectTier: (tier: LicenseTier) => void;
  region: PricingRegion;
}

export interface UsageMetrics {
  current_usage: LicenseUsageStats;
  historical_usage: LicenseUsageStats[];
  projected_savings: number;
  upgrade_recommendations?: {
    recommended_tier: LicenseTier;
    potential_savings: number;
    break_even_months: number;
  };
}

// Payment Modal Props
export interface PaymentModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedTier: LicenseTier;
  employeeCount?: number;
  pricing: TierInfo;
  onSuccess: (licenseId: string) => void;
}

// Usage Chart Data
export interface UsageChartData {
  month: string;
  transactions: number;
  volume: number;
  fees_saved: number;
  limit_transactions?: number;
  limit_volume?: number;
}

// Notification Types for License Events
export interface LicenseNotification {
  type: 'license_activated' | 'license_expiring' | 'upgrade_available' | 'usage_limit_warning';
  title: string;
  message: string;
  license_id: string;
  action_required?: boolean;
  action_url?: string;
}

// Error Types
export interface LicenseError {
  code: string;
  message: string;
  field?: string;
  suggestions?: string[];
}

// Utility type for license status checks
export type LicenseStatusCheck = {
  hasActiveLicense: boolean;
  currentTier?: LicenseTier;
  canUpgrade: boolean;
  isExpiringSoon: boolean;
  daysUntilExpiry?: number;
};