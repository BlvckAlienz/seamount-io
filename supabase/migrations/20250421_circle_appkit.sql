-- ============================================================================
-- FILE: supabase/migrations/20250421_circle_appkit.sql
-- Circle App Kit — Bridge & Swap transaction tables
-- Run in Supabase SQL Editor (Dashboard → SQL Editor → New Query → Run)
-- ============================================================================

-- ── 1. Circle Bridge Transactions ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.circle_bridge_transactions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    from_chain       TEXT NOT NULL,
    to_chain         TEXT NOT NULL,
    amount           NUMERIC(20,6) NOT NULL,
    token            TEXT NOT NULL DEFAULT 'USDC',
    seamount_fee     NUMERIC(20,6) NOT NULL DEFAULT 0,
    cctp_fee         NUMERIC(20,6),
    forwarding_fee   NUMERIC(20,6),
    recipient_address TEXT,
    state            TEXT NOT NULL DEFAULT 'pending'
                     CHECK (state IN ('pending','success','error')),
    steps            JSONB NOT NULL DEFAULT '[]'::jsonb,
    provider         TEXT DEFAULT 'circle_cctp',
    transfer_speed   TEXT DEFAULT 'FAST',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at     TIMESTAMPTZ
);

ALTER TABLE public.circle_bridge_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own bridge transactions"
    ON public.circle_bridge_transactions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to bridge transactions"
    ON public.circle_bridge_transactions
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_circle_bridge_user_id
    ON public.circle_bridge_transactions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_circle_bridge_state
    ON public.circle_bridge_transactions (state, created_at DESC);


-- ── 2. Circle Swap Transactions ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.circle_swap_transactions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    chain         TEXT NOT NULL,
    token_in      TEXT NOT NULL,
    token_out     TEXT NOT NULL,
    amount_in     NUMERIC(20,6) NOT NULL,
    amount_out    NUMERIC(20,6),
    seamount_fee  NUMERIC(20,6) NOT NULL DEFAULT 0,
    provider_fee  NUMERIC(20,6),
    tx_hash       TEXT,
    explorer_url  TEXT,
    state         TEXT NOT NULL DEFAULT 'pending'
                  CHECK (state IN ('pending','success','error')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ
);

ALTER TABLE public.circle_swap_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own circle swap transactions"
    ON public.circle_swap_transactions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role full access to circle swap transactions"
    ON public.circle_swap_transactions
    FOR ALL USING (auth.role() = 'service_role');

CREATE INDEX IF NOT EXISTS idx_circle_swap_user_id
    ON public.circle_swap_transactions (user_id, created_at DESC);


-- ── 3. Helper: auto-update updated_at ────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trig_bridge_updated_at ON public.circle_bridge_transactions;
CREATE TRIGGER trig_bridge_updated_at
    BEFORE UPDATE ON public.circle_bridge_transactions
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- ── 4. View: unified Circle App Kit fee revenue (for admin dashboard) ─────────
CREATE OR REPLACE VIEW public.circle_appkit_revenue AS
SELECT
    'bridge'                    AS operation_type,
    user_id,
    seamount_fee                AS fee_usdc,
    amount,
    from_chain || ' → ' || to_chain AS route,
    created_at
FROM public.circle_bridge_transactions
WHERE state = 'success'

UNION ALL

SELECT
    'swap'                      AS operation_type,
    user_id,
    seamount_fee                AS fee_usdc,
    amount_in                   AS amount,
    token_in || ' → ' || token_out AS route,
    created_at
FROM public.circle_swap_transactions
WHERE state = 'success';

-- Grant access to service role
GRANT SELECT ON public.circle_appkit_revenue TO service_role;