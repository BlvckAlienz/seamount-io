-- File: backend/migrations/create_wallet_connect_tables.sql

CREATE TABLE IF NOT EXISTS pending_deposits (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    wallet_address TEXT NOT NULL,
    asset TEXT NOT NULL,
    asset_id BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'awaiting_deposit',
    tx_id TEXT,
    amount DECIMAL(18, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_deposits (
    tx_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    deposit_id TEXT NOT NULL,
    asset TEXT NOT NULL,
    amount DECIMAL(18, 8) NOT NULL,
    processed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pending_user ON pending_deposits(user_id);
CREATE INDEX idx_pending_status ON pending_deposits(status);
CREATE INDEX idx_pending_address ON pending_deposits(wallet_address);
CREATE INDEX idx_processed_user ON processed_deposits(user_id);

ALTER TABLE pending_deposits ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_deposits ENABLE ROW LEVEL SECURITY;

CREATE POLICY pending_deposits_policy ON pending_deposits
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY processed_deposits_policy ON processed_deposits
    FOR ALL USING (auth.uid() = user_id);-- File: backend/migrations/create_wallet_connect_tables.sql

CREATE TABLE IF NOT EXISTS pending_deposits (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    wallet_address TEXT NOT NULL,
    asset TEXT NOT NULL,
    asset_id BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'awaiting_deposit',
    tx_id TEXT,
    amount DECIMAL(18, 8),
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_deposits (
    tx_id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    deposit_id TEXT NOT NULL,
    asset TEXT NOT NULL,
    amount DECIMAL(18, 8) NOT NULL,
    processed_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_pending_user ON pending_deposits(user_id);
CREATE INDEX idx_pending_status ON pending_deposits(status);
CREATE INDEX idx_pending_address ON pending_deposits(wallet_address);
CREATE INDEX idx_processed_user ON processed_deposits(user_id);

ALTER TABLE pending_deposits ENABLE ROW LEVEL SECURITY;
ALTER TABLE processed_deposits ENABLE ROW LEVEL SECURITY;

CREATE POLICY pending_deposits_policy ON pending_deposits
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY processed_deposits_policy ON processed_deposits
    FOR ALL USING (auth.uid() = user_id);