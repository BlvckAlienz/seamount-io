-- File: backend/migrations/fix_multi_chain_tables.sql
-- Supabase Compatible - Run in SQL Editor

-- 1. Create multi_chain_addresses table
CREATE TABLE IF NOT EXISTS multi_chain_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    blockchain TEXT NOT NULL,
    address TEXT NOT NULL,
    encrypted_seed TEXT,
    wallet_type TEXT DEFAULT 'wdk',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT unique_user_blockchain UNIQUE (user_id, blockchain)
);

CREATE INDEX IF NOT EXISTS idx_multi_chain_user_id ON multi_chain_addresses(user_id);
CREATE INDEX IF NOT EXISTS idx_multi_chain_blockchain ON multi_chain_addresses(blockchain);

-- 2. Enable RLS
ALTER TABLE multi_chain_addresses ENABLE ROW LEVEL SECURITY;

-- Drop existing policies (avoid conflicts)
DROP POLICY IF EXISTS "Users can view own addresses" ON multi_chain_addresses;
DROP POLICY IF EXISTS "Users can create own addresses" ON multi_chain_addresses;
DROP POLICY IF EXISTS "Users can update own addresses" ON multi_chain_addresses;
DROP POLICY IF EXISTS "Service role full access" ON multi_chain_addresses;

-- Create RLS policies
CREATE POLICY "Users can view own addresses"
    ON multi_chain_addresses FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own addresses"
    ON multi_chain_addresses FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own addresses"
    ON multi_chain_addresses FOR UPDATE
    USING (auth.uid() = user_id);

-- ✅ FIX: Supabase uses 'service_role' in JWT claims
CREATE POLICY "Service role full access"
    ON multi_chain_addresses FOR ALL
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
    );

-- 3. Fix user_wallets table (add Algorand columns if missing)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_wallets' AND column_name = 'algorand_address'
    ) THEN
        ALTER TABLE user_wallets ADD COLUMN algorand_address TEXT;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_wallets' AND column_name = 'algorand_private_key'
    ) THEN
        ALTER TABLE user_wallets ADD COLUMN algorand_private_key TEXT;
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'user_wallets' AND column_name = 'algorand_mnemonic'
    ) THEN
        ALTER TABLE user_wallets ADD COLUMN algorand_mnemonic TEXT;
    END IF;
END $$;

-- 4. Create fee_calculations table
CREATE TABLE IF NOT EXISTS fee_calculations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quote_id TEXT UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    fee_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fee_calc_quote_id ON fee_calculations(quote_id);
CREATE INDEX IF NOT EXISTS idx_fee_calc_user_id ON fee_calculations(user_id);

ALTER TABLE fee_calculations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own fee calculations" ON fee_calculations;
DROP POLICY IF EXISTS "Service role can insert fee calculations" ON fee_calculations;

CREATE POLICY "Users can view own fee calculations"
    ON fee_calculations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Service role can insert fee calculations"
    ON fee_calculations FOR INSERT
    WITH CHECK (true);

-- 5. Fix user_wallets RLS
ALTER TABLE user_wallets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own wallet" ON user_wallets;
DROP POLICY IF EXISTS "Users can update own wallet" ON user_wallets;
DROP POLICY IF EXISTS "Service role full wallet access" ON user_wallets;

CREATE POLICY "Users can view own wallet"
    ON user_wallets FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update own wallet"
    ON user_wallets FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Service role full wallet access"
    ON user_wallets FOR ALL
    USING (
        current_setting('request.jwt.claims', true)::json->>'role' = 'service_role'
    );

-- 6. Updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_multi_chain_addresses_updated_at ON multi_chain_addresses;

CREATE TRIGGER update_multi_chain_addresses_updated_at
    BEFORE UPDATE ON multi_chain_addresses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- SUCCESS
SELECT 'Database schema fixed successfully!' AS status;