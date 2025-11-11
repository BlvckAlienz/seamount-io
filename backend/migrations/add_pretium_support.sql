-- File: backend/migrations/add_pretium_support.sql
-- Migration: Add Pretium transaction tracking (NON-DESTRUCTIVE)
-- Run in Supabase SQL Editor
-- Version: 2.0 (Fixed RLS syntax)

-- ============================================================================
-- STEP 1: Add Pretium columns (only if they don't exist)
-- ============================================================================

DO $$
BEGIN
    -- Add pretium_txn_code column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' 
        AND column_name = 'pretium_txn_code'
    ) THEN
        ALTER TABLE transactions ADD COLUMN pretium_txn_code VARCHAR(50);
        RAISE NOTICE '✅ Added pretium_txn_code column';
    ELSE
        RAISE NOTICE '⚠️ pretium_txn_code already exists, skipping';
    END IF;

    -- Add pretium_reference column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' 
        AND column_name = 'pretium_reference'
    ) THEN
        ALTER TABLE transactions ADD COLUMN pretium_reference VARCHAR(100);
        RAISE NOTICE '✅ Added pretium_reference column';
    ELSE
        RAISE NOTICE '⚠️ pretium_reference already exists, skipping';
    END IF;

    -- Add pretium_settlement_status column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'transactions' 
        AND column_name = 'pretium_settlement_status'
    ) THEN
        ALTER TABLE transactions ADD COLUMN pretium_settlement_status VARCHAR(50);
        RAISE NOTICE '✅ Added pretium_settlement_status column';
    ELSE
        RAISE NOTICE '⚠️ pretium_settlement_status already exists, skipping';
    END IF;
END $$;

-- ============================================================================
-- STEP 2: Create indexes (only if they don't exist)
-- ============================================================================

DO $$
BEGIN
    -- Index for Pretium transaction code lookups
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_transactions_pretium_code'
    ) THEN
        CREATE INDEX idx_transactions_pretium_code 
        ON transactions(pretium_txn_code) 
        WHERE pretium_txn_code IS NOT NULL;
        RAISE NOTICE '✅ Created index idx_transactions_pretium_code';
    ELSE
        RAISE NOTICE '⚠️ Index idx_transactions_pretium_code already exists, skipping';
    END IF;

    -- Index for Pretium reference lookups
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE indexname = 'idx_transactions_pretium_ref'
    ) THEN
        CREATE INDEX idx_transactions_pretium_ref 
        ON transactions(pretium_reference) 
        WHERE pretium_reference IS NOT NULL;
        RAISE NOTICE '✅ Created index idx_transactions_pretium_ref';
    ELSE
        RAISE NOTICE '⚠️ Index idx_transactions_pretium_ref already exists, skipping';
    END IF;
END $$;

-- ============================================================================
-- STEP 3: Update metadata column comment
-- ============================================================================

COMMENT ON COLUMN transactions.metadata IS 
'JSONB containing provider-specific data (Paystack, Flutterwave, Cashramp, Pretium)';

-- ============================================================================
-- STEP 4: RLS Policies (FIXED SYNTAX)
-- ============================================================================

-- Enable RLS if not already enabled
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Drop existing policy if it exists (to avoid conflicts)
DROP POLICY IF EXISTS "Users can view own Pretium transactions" ON transactions;

-- Create policy with correct syntax
CREATE POLICY "Users can view own Pretium transactions"
ON transactions
FOR SELECT
USING (auth.uid() = user_id);

-- ============================================================================
-- STEP 5: Fee collection tracking function
-- ============================================================================

-- Drop existing function/trigger if they exist
DROP TRIGGER IF EXISTS track_pretium_fees ON transactions;
DROP FUNCTION IF EXISTS log_pretium_fee_collection();

-- Create fee tracking function
CREATE OR REPLACE FUNCTION log_pretium_fee_collection()
RETURNS TRIGGER AS $$
BEGIN
  -- If Pretium transaction completed, log fee collection
  IF NEW.metadata->>'provider' = 'pretium' 
     AND NEW.status = 'completed' 
     AND NEW.fee_amount IS NOT NULL THEN
    
    -- Check if revenue table exists before inserting
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'revenue'
    ) THEN
        INSERT INTO revenue (
            user_id,
            transaction_id,
            amount,
            source,
            timestamp
        ) VALUES (
            NEW.user_id,
            NEW.id,
            NEW.fee_amount,
            'pretium_fee',
            NOW()
        );
        RAISE NOTICE '✅ Logged Pretium fee to revenue table';
    ELSE
        RAISE NOTICE '⚠️ Revenue table does not exist, skipping fee logging';
    END IF;
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic fee tracking
CREATE TRIGGER track_pretium_fees
AFTER UPDATE ON transactions
FOR EACH ROW
WHEN (NEW.status = 'completed' AND OLD.status != 'completed')
EXECUTE FUNCTION log_pretium_fee_collection();

-- ============================================================================
-- FINAL SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
  RAISE NOTICE '✅ Pretium migration completed successfully';
  RAISE NOTICE 'Added columns: pretium_txn_code, pretium_reference, pretium_settlement_status';
  RAISE NOTICE 'Created indexes for fast lookups';
  RAISE NOTICE 'Enabled RLS with user-level access control';
  RAISE NOTICE 'Added automatic fee tracking trigger';
END $$;