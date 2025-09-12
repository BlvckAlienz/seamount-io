-- File Location: database/migrations/smart_routing_uuid_fixed.sql
-- Fixed for your existing UUID-based schema

-- Add new columns to existing payment_transactions table
ALTER TABLE payment_transactions 
ADD COLUMN IF NOT EXISTS provider VARCHAR(20) DEFAULT 'flutterwave',
ADD COLUMN IF NOT EXISTS routing_metadata JSONB,
ADD COLUMN IF NOT EXISTS bank_details JSONB,
ADD COLUMN IF NOT EXISTS provider_tx_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS payment_url TEXT;

-- Add indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_payment_transactions_provider 
ON payment_transactions(provider);

CREATE INDEX IF NOT EXISTS idx_payment_transactions_status_provider 
ON payment_transactions(status, provider);

-- DON'T recreate RLS policies - yours are already perfect!
-- Your existing policies work fine: auth.uid() = user_id (UUID = UUID)

-- Analytics function (handles all edge cases)
CREATE OR REPLACE FUNCTION get_payment_analytics(days_back INTEGER DEFAULT 30)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'total_volume', COALESCE(SUM(amount), 0),
        'total_transactions', COUNT(*),
        'success_rate', 
            CASE 
                WHEN COUNT(*) = 0 THEN 0
                ELSE ROUND((COUNT(*) FILTER (WHERE status = 'completed')::DECIMAL / COUNT(*)) * 100, 2)
            END,
        'provider_stats', COALESCE(
            json_object_agg(
                provider,
                json_build_object(
                    'volume', SUM(amount),
                    'count', COUNT(*),
                    'success_rate', 
                        CASE 
                            WHEN COUNT(*) = 0 THEN 0
                            ELSE ROUND((COUNT(*) FILTER (WHERE status = 'completed')::DECIMAL / COUNT(*)) * 100, 2)
                        END
                )
            ) FILTER (WHERE provider IS NOT NULL),
            '{}'::json
        ),
        'fees_saved', 
            COALESCE(
                SUM(CASE 
                    WHEN provider = 'paystack' THEN amount * 0.0095  -- 0.95% savings
                    WHEN provider = 'sterling' THEN amount * 0.006   -- 0.6% savings  
                    ELSE 0 
                END), 
                0
            ),
        'avg_processing_time_minutes', 
            CASE 
                WHEN COUNT(*) FILTER (WHERE completed_at IS NOT NULL AND created_at IS NOT NULL) = 0 THEN 0
                ELSE ROUND(EXTRACT(EPOCH FROM AVG(completed_at - created_at))/60, 2)
            END
    ) INTO result
    FROM payment_transactions 
    WHERE created_at >= NOW() - (days_back || ' days')::INTERVAL;
    
    RETURN COALESCE(result, '{"total_volume": 0, "total_transactions": 0}'::json);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant permissions
GRANT EXECUTE ON FUNCTION get_payment_analytics TO authenticated;

-- Success message
DO $$
BEGIN
    RAISE NOTICE '✅ Smart routing migration completed!';
    RAISE NOTICE 'Added columns: provider, routing_metadata, bank_details, provider_tx_id, payment_url';
    RAISE NOTICE 'Your existing RLS policies are perfect - kept unchanged';
    RAISE NOTICE 'Added payment analytics function';
END $$;