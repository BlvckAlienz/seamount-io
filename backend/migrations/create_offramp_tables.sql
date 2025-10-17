-- File: backend/migrations/create_offramp_tables.sql

CREATE TABLE IF NOT EXISTS offramp_transactions (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),  -- Changed to UUID
    type TEXT NOT NULL DEFAULT 'offramp',
    status TEXT NOT NULL,
    crypto_asset TEXT NOT NULL,
    crypto_amount DECIMAL(18, 8) NOT NULL,
    seamount_fee DECIMAL(18, 8) NOT NULL,
    net_crypto_amount DECIMAL(18, 8) NOT NULL,
    fiat_currency TEXT NOT NULL,
    fiat_amount DECIMAL(18, 2) NOT NULL,
    country TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_tx_id TEXT,
    recipient_details JSONB NOT NULL,
    provider_response JSONB,
    webhook_data JSONB,
    estimated_settlement TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    failed_at TIMESTAMP
);

CREATE INDEX idx_offramp_user ON offramp_transactions(user_id);
CREATE INDEX idx_offramp_status ON offramp_transactions(status);
CREATE INDEX idx_offramp_created ON offramp_transactions(created_at DESC);

ALTER TABLE offramp_transactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY offramp_user_policy ON offramp_transactions
    FOR ALL USING (auth.uid() = user_id);  -- Removed ::text cast