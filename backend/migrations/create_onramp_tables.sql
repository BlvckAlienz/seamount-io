-- File: backend/migrations/create_onramp_tables.sql

CREATE TABLE IF NOT EXISTS onramp_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES user_profiles(id),
    type TEXT NOT NULL DEFAULT 'onramp',
    status TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    currency TEXT NOT NULL,
    crypto_asset TEXT NOT NULL,
    amount_fiat DECIMAL(18, 2) NOT NULL,
    seamount_fee DECIMAL(18, 2) NOT NULL,
    net_to_user DECIMAL(18, 8) NOT NULL,
    wallet_address TEXT NOT NULL,
    checkout_url TEXT NOT NULL,
    user_email TEXT NOT NULL,
    user_country TEXT NOT NULL,
    estimated_settlement TEXT,
    webhook_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    failed_at TIMESTAMP
);

CREATE INDEX idx_onramp_user ON onramp_transactions(user_id);
CREATE INDEX idx_onramp_status ON onramp_transactions(status);
CREATE INDEX idx_onramp_created ON onramp_transactions(created_at DESC);

-- Enable RLS
ALTER TABLE onramp_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY onramp_user_policy ON onramp_transactions
    FOR ALL USING (auth.uid()::text = user_id);