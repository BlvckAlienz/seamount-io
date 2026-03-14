-- FILE: supabase/migrations/004_merchant_payment_config.sql

ALTER TABLE public.p2p_merchants
  ADD COLUMN IF NOT EXISTS payment_methods_config JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();