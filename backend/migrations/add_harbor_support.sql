-- File: backend/migrations/add_harbor_support.sql
-- Harbor transaction tracking and webhook management
-- FIXED: Separated index creation from table definition

-- ============================================================================
-- TABLE: harbor_transactions
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.harbor_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Harbor identifiers
    harbor_payment_id TEXT UNIQUE NOT NULL,
    harbor_reference TEXT,
    
    -- Transaction metadata
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('on-ramp', 'off-ramp', 'swap', 'transfer')),
    blockchain TEXT NOT NULL CHECK (blockchain IN ('ethereum', 'polygon', 'solana', 'bitcoin', 'tron', 'algorand')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')),
    
    -- Amounts
    amount DECIMAL(20,8) NOT NULL,
    currency TEXT NOT NULL,
    crypto_asset TEXT,
    
    -- Fees
    harbor_fee DECIMAL(10,2),
    seamount_fee DECIMAL(10,2),
    network_fee DECIMAL(10,2),
    
    -- Addresses
    from_address TEXT,
    to_address TEXT,
    wallet_address TEXT,
    
    -- Webhook data
    webhook_data JSONB,
    webhook_received_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create indexes AFTER table creation
CREATE INDEX IF NOT EXISTS idx_harbor_user_id ON public.harbor_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_harbor_payment_id ON public.harbor_transactions(harbor_payment_id);
CREATE INDEX IF NOT EXISTS idx_harbor_status ON public.harbor_transactions(status);
CREATE INDEX IF NOT EXISTS idx_harbor_blockchain ON public.harbor_transactions(blockchain);
CREATE INDEX IF NOT EXISTS idx_harbor_created_at ON public.harbor_transactions(created_at DESC);

-- Enable RLS
ALTER TABLE public.harbor_transactions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can view their own Harbor transactions"
    ON public.harbor_transactions
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can manage all Harbor transactions"
    ON public.harbor_transactions
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================================================
-- TABLE: harbor_webhook_logs
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.harbor_webhook_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Webhook metadata
    event_type TEXT NOT NULL,
    harbor_payment_id TEXT,
    
    -- Request data
    payload JSONB NOT NULL,
    headers JSONB,
    signature TEXT,
    signature_valid BOOLEAN,
    
    -- Processing
    processed BOOLEAN DEFAULT FALSE,
    processing_error TEXT,
    
    -- Timestamps
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Create indexes for webhook logs
CREATE INDEX IF NOT EXISTS idx_webhook_event_type ON public.harbor_webhook_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_payment_id ON public.harbor_webhook_logs(harbor_payment_id);
CREATE INDEX IF NOT EXISTS idx_webhook_processed ON public.harbor_webhook_logs(processed);
CREATE INDEX IF NOT EXISTS idx_webhook_received_at ON public.harbor_webhook_logs(received_at DESC);

-- Enable RLS
ALTER TABLE public.harbor_webhook_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policy (admin only)
CREATE POLICY "Only service role can access webhook logs"
    ON public.harbor_webhook_logs
    FOR ALL
    USING (auth.jwt() ->> 'role' = 'service_role');

-- ============================================================================
-- FUNCTION: Update timestamp trigger
-- ============================================================================

CREATE OR REPLACE FUNCTION public.update_harbor_transaction_timestamp()
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

-- Attach trigger to table
DROP TRIGGER IF EXISTS trigger_update_harbor_transaction_timestamp ON public.harbor_transactions;

CREATE TRIGGER trigger_update_harbor_transaction_timestamp
    BEFORE UPDATE ON public.harbor_transactions
    FOR EACH ROW
    EXECUTE FUNCTION public.update_harbor_transaction_timestamp();

-- ============================================================================
-- GRANTS
-- ============================================================================

GRANT SELECT, INSERT, UPDATE ON public.harbor_transactions TO authenticated;
GRANT ALL ON public.harbor_transactions TO service_role;
GRANT ALL ON public.harbor_webhook_logs TO service_role;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Run these to verify migration succeeded:
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename LIKE 'harbor%';
-- SELECT indexname FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'harbor_transactions';