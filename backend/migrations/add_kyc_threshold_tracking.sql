-- File: backend/migrations/add_kyc_threshold_tracking.sql
-- Add KYC threshold tracking to user_profiles
-- ✅ FIXED: Proper foreign key references and Supabase RLS syntax

-- 1. Add cumulative volume tracking columns
ALTER TABLE user_profiles 
ADD COLUMN IF NOT EXISTS cumulative_volume_30d DECIMAL(20,2) DEFAULT 0.00,
ADD COLUMN IF NOT EXISTS kyc_prompt_dismissed_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS kyc_grace_period_ends TIMESTAMPTZ;

-- 2. Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_kyc_volume 
ON user_profiles(kyc_status, cumulative_volume_30d);

CREATE INDEX IF NOT EXISTS idx_user_kyc_grace 
ON user_profiles(kyc_status, kyc_grace_period_ends);

-- 3. Create KYC threshold events table (for analytics)
-- ✅ FIXED: References user_profiles(id) instead of user_profiles(user_id)
CREATE TABLE IF NOT EXISTS kyc_threshold_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES user_profiles(id) ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL, 
    -- Possible values: 'warning', 'soft_block', 'hard_block', 'verification_started'
    cumulative_volume DECIMAL(20,2),
    threshold_remaining DECIMAL(20,2),
    transaction_amount DECIMAL(20,2),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Add indexes for kyc_threshold_events
CREATE INDEX IF NOT EXISTS idx_kyc_events_user 
ON kyc_threshold_events(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_kyc_events_type 
ON kyc_threshold_events(event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_kyc_events_created 
ON kyc_threshold_events(created_at DESC);

-- 5. Enable RLS on kyc_threshold_events
ALTER TABLE kyc_threshold_events ENABLE ROW LEVEL SECURITY;

-- 6. Create RLS policies for kyc_threshold_events
-- Policy: Users can read their own events
DROP POLICY IF EXISTS "Users can view their own KYC events" ON kyc_threshold_events;
CREATE POLICY "Users can view their own KYC events"
ON kyc_threshold_events
FOR SELECT
TO authenticated
USING (auth.uid() = user_id);

-- Policy: Service role can insert events
DROP POLICY IF EXISTS "Service can insert KYC events" ON kyc_threshold_events;
CREATE POLICY "Service can insert KYC events"
ON kyc_threshold_events
FOR INSERT
TO service_role
WITH CHECK (true);

-- Policy: Authenticated users can insert their own events (for client-side tracking)
DROP POLICY IF EXISTS "Users can insert their own KYC events" ON kyc_threshold_events;
CREATE POLICY "Users can insert their own KYC events"
ON kyc_threshold_events
FOR INSERT
TO authenticated
WITH CHECK (auth.uid() = user_id);

-- 7. Add transaction volume trigger (auto-update cumulative)
-- ✅ Note: Only create if 'transactions' table exists
DO $$ 
BEGIN
    -- Check if transactions table exists
    IF EXISTS (
        SELECT FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename = 'transactions'
    ) THEN
        
        -- Create or replace the trigger function
        CREATE OR REPLACE FUNCTION update_user_cumulative_volume()
        RETURNS TRIGGER AS $func$
        BEGIN
            -- Update cumulative volume when transaction is completed
            IF NEW.status = 'completed' THEN
                UPDATE user_profiles
                SET cumulative_volume_30d = (
                    SELECT COALESCE(SUM(amount), 0)
                    FROM transactions
                    WHERE user_id = NEW.user_id
                    AND created_at >= NOW() - INTERVAL '30 days'
                    AND status IN ('completed', 'pending')
                )
                WHERE id = NEW.user_id;
            END IF;
            
            RETURN NEW;
        END;
        $func$ LANGUAGE plpgsql SECURITY DEFINER;

        -- Drop trigger if exists and recreate
        DROP TRIGGER IF EXISTS trg_update_cumulative_volume ON transactions;
        
        CREATE TRIGGER trg_update_cumulative_volume
        AFTER INSERT OR UPDATE ON transactions
        FOR EACH ROW
        EXECUTE FUNCTION update_user_cumulative_volume();
        
        RAISE NOTICE 'Transaction volume trigger created successfully';
    ELSE
        RAISE NOTICE 'Transactions table does not exist yet - trigger skipped';
    END IF;
END $$;

-- 8. Backfill existing users (set cumulative to 0)
UPDATE user_profiles 
SET cumulative_volume_30d = 0.00
WHERE cumulative_volume_30d IS NULL;

-- 9. Add helpful comments
COMMENT ON COLUMN user_profiles.cumulative_volume_30d 
IS 'Rolling 30-day transaction volume in USD - triggers KYC at $5,000';

COMMENT ON COLUMN user_profiles.kyc_prompt_dismissed_at 
IS 'Timestamp when user last dismissed KYC prompt';

COMMENT ON COLUMN user_profiles.kyc_grace_period_ends 
IS 'End of grace period after threshold exceeded';

COMMENT ON TABLE kyc_threshold_events 
IS 'Tracks KYC threshold events for analytics and compliance';

-- 10. Grant permissions (Supabase best practice)
GRANT SELECT ON kyc_threshold_events TO authenticated;
GRANT INSERT ON kyc_threshold_events TO authenticated;
GRANT ALL ON kyc_threshold_events TO service_role;

-- 11. Success message
DO $$ 
BEGIN
    RAISE NOTICE '✅ KYC threshold tracking migration completed successfully';
    RAISE NOTICE '📊 Added cumulative_volume_30d column to user_profiles';
    RAISE NOTICE '🔐 RLS policies enabled on kyc_threshold_events';
    RAISE NOTICE '⚡ Automatic volume tracking trigger configured';
END $$;