-- File: backend/database/migrations/wallet_creation_status.sql
-- Run in Supabase SQL Editor

-- ============================================================================
-- WALLET CREATION STATUS TRACKING
-- ============================================================================

-- Add columns to user_profiles for wallet creation tracking
ALTER TABLE user_profiles
ADD COLUMN IF NOT EXISTS wallet_creation_complete BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS wallet_creation_started_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS wallet_creation_completed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS wallet_creation_retry_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS wallet_creation_last_retry TIMESTAMPTZ;

-- Create table to track individual chain wallet status
CREATE TABLE IF NOT EXISTS wallet_creation_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    chain TEXT NOT NULL, -- 'algorand', 'bitcoin', 'ethereum', 'polygon'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'creating', 'success', 'failed', 'retrying'
    address TEXT,
    encrypted_key TEXT,
    attempt_count INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    error_message TEXT,
    error_code TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, chain)
);

-- Create index for fast lookups
CREATE INDEX IF NOT EXISTS idx_wallet_status_user ON wallet_creation_status(user_id);
CREATE INDEX IF NOT EXISTS idx_wallet_status_status ON wallet_creation_status(status);
CREATE INDEX IF NOT EXISTS idx_wallet_status_retry ON wallet_creation_status(user_id, status) WHERE status IN ('failed', 'retrying');

-- Enable RLS
ALTER TABLE wallet_creation_status ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own wallet status
CREATE POLICY "Users can view their own wallet status"
ON wallet_creation_status FOR SELECT
USING (auth.uid() = user_id);

-- Policy: Service role can manage all
CREATE POLICY "Service role can manage wallet status"
ON wallet_creation_status FOR ALL
USING (auth.role() = 'service_role');

-- Create table for wallet creation retry queue
CREATE TABLE IF NOT EXISTS wallet_creation_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    chain TEXT NOT NULL,
    priority INTEGER DEFAULT 5, -- 1=highest, 10=lowest
    scheduled_for TIMESTAMPTZ DEFAULT NOW(),
    locked_at TIMESTAMPTZ,
    locked_by TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 10,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, chain)
);

CREATE INDEX IF NOT EXISTS idx_queue_scheduled ON wallet_creation_queue(scheduled_for) WHERE locked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_queue_locked ON wallet_creation_queue(locked_at) WHERE locked_at IS NOT NULL;

-- Enable RLS
ALTER TABLE wallet_creation_queue ENABLE ROW LEVEL SECURITY;

-- Policy: Only service role can access queue
CREATE POLICY "Service role can manage queue"
ON wallet_creation_queue FOR ALL
USING (auth.role() = 'service_role');

-- Function to mark user wallet creation as complete
CREATE OR REPLACE FUNCTION check_wallet_creation_complete()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if all 4 chains are successful
    IF (
        SELECT COUNT(*) 
        FROM wallet_creation_status 
        WHERE user_id = NEW.user_id 
        AND status = 'success'
    ) = 4 THEN
        UPDATE user_profiles
        SET wallet_creation_complete = true,
            wallet_creation_completed_at = NOW()
        WHERE id = NEW.user_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-update completion status
CREATE TRIGGER trigger_check_wallet_complete
AFTER INSERT OR UPDATE ON wallet_creation_status
FOR EACH ROW
EXECUTE FUNCTION check_wallet_creation_complete();

-- Function to get incomplete wallet chains for a user
CREATE OR REPLACE FUNCTION get_incomplete_wallet_chains(p_user_id UUID)
RETURNS TABLE(chain TEXT, status TEXT, error_message TEXT, attempt_count INTEGER) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        wcs.chain,
        wcs.status,
        wcs.error_message,
        wcs.attempt_count
    FROM wallet_creation_status wcs
    WHERE wcs.user_id = p_user_id
    AND wcs.status != 'success'
    ORDER BY wcs.created_at;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function to initialize wallet creation status for new user
CREATE OR REPLACE FUNCTION initialize_wallet_status(p_user_id UUID)
RETURNS void AS $$
BEGIN
    INSERT INTO wallet_creation_status (user_id, chain, status)
    VALUES 
        (p_user_id, 'algorand', 'pending'),
        (p_user_id, 'bitcoin', 'pending'),
        (p_user_id, 'ethereum', 'pending'),
        (p_user_id, 'polygon', 'pending')
    ON CONFLICT (user_id, chain) DO NOTHING;
    
    UPDATE user_profiles
    SET wallet_creation_started_at = NOW()
    WHERE id = p_user_id
    AND wallet_creation_started_at IS NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON TABLE wallet_creation_status IS 'Tracks creation status of each blockchain wallet per user';
COMMENT ON TABLE wallet_creation_queue IS 'Background job queue for retrying failed wallet creations';
COMMENT ON FUNCTION check_wallet_creation_complete IS 'Auto-updates user wallet_creation_complete when all 4 chains succeed';
COMMENT ON FUNCTION get_incomplete_wallet_chains IS 'Returns list of failed/pending wallet chains for a user';
COMMENT ON FUNCTION initialize_wallet_status IS 'Creates pending status records for all 4 chains when user signs up';