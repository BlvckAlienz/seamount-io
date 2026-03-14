-- FILE: supabase/migrations/002_update_token_constraints.sql
-- Replaces the restrictive USDT/USDC-only CHECK constraints
-- with the full token list matching Seamount.io's enabled assets

-- Drop old constraints
ALTER TABLE public.p2p_listings DROP CONSTRAINT IF EXISTS p2p_listings_token_check;
ALTER TABLE public.p2p_orders   DROP CONSTRAINT IF EXISTS p2p_orders_token_check;

-- Add updated constraints covering all platform tokens
ALTER TABLE public.p2p_listings
  ADD CONSTRAINT p2p_listings_token_check CHECK (token IN (
    -- Algorand
    'ALGO', 'USDT', 'USDCa', 'goBTC', 'goETH',
    -- Bitcoin
    'BTC',
    -- Ethereum
    'ETH', 'USDT_ETH', 'USDC_ETH',
    -- Polygon
    'MATIC', 'USDT_POLYGON', 'USDC_POLYGON',
    -- Tron
    'TRX', 'USDT_TRON',
    -- Solana
    'SOL', 'USDT_SOLANA', 'USDC_SOLANA'
  ));

ALTER TABLE public.p2p_orders
  ADD CONSTRAINT p2p_orders_token_check CHECK (token IN (
    'ALGO', 'USDT', 'USDCa', 'goBTC', 'goETH',
    'BTC',
    'ETH', 'USDT_ETH', 'USDC_ETH',
    'MATIC', 'USDT_POLYGON', 'USDC_POLYGON',
    'TRX', 'USDT_TRON',
    'SOL', 'USDT_SOLANA', 'USDC_SOLANA'
  ));