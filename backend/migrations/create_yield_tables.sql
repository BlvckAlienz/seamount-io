-- File: backend/migrations/create_yield_tables.sql

CREATE TABLE IF NOT EXISTS yield_stakes (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id),
    tier TEXT NOT NULL,
    asset TEXT NOT NULL,
    principal_amount DECIMAL(18, 8) NOT NULL,
    current_value DECIMAL(18, 8) NOT NULL,
    target_apy DECIMAL(10, 6) NOT NULL,
    expected_daily_yield DECIMAL(18, 8) NOT NULL,
    total_earned DECIMAL(18, 8) DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    strategies JSONB NOT NULL,
    risk_level TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    last_rebalanced_at TIMESTAMP,
    next_rebalance_date TIMESTAMP,
    unstaked_at TIMESTAMP,
    final_value DECIMAL(18, 8)
);

CREATE TABLE IF NOT EXISTS strategy_allocations (
    id TEXT PRIMARY KEY,
    stake_id TEXT NOT NULL REFERENCES yield_stakes(id),
    strategy TEXT NOT NULL,
    asset TEXT NOT NULL,
    allocated_amount DECIMAL(18, 8) NOT NULL,
    current_value DECIMAL(18, 8) NOT NULL,
    realized_yield DECIMAL(18, 8) DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_stakes_user ON yield_stakes(user_id);
CREATE INDEX idx_stakes_status ON yield_stakes(status);
CREATE INDEX idx_stakes_tier ON yield_stakes(tier);
CREATE INDEX idx_allocations_stake ON strategy_allocations(stake_id);

ALTER TABLE yield_stakes ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategy_allocations ENABLE ROW LEVEL SECURITY;

CREATE POLICY yield_stakes_policy ON yield_stakes
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY strategy_allocations_policy ON strategy_allocations
    FOR ALL USING (
        auth.uid() = (SELECT user_id FROM yield_stakes WHERE id = stake_id)
    );