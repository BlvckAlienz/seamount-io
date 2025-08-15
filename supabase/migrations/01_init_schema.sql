-- Seamount Database Initialization
-- Creates all tables needed for production with RLS enabled
-- File Location: /seamount/database/01_init_schema.sql

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Wallets and addresses
CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    address VARCHAR(42) UNIQUE NOT NULL,
    wallet_type VARCHAR(20) NOT NULL DEFAULT 'standard',
    risk_score DECIMAL(5,4) DEFAULT 0.0000,
    kyc_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);
ALTER TABLE wallets ENABLE ROW LEVEL SECURITY;

-- Transactions
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tx_hash VARCHAR(66) UNIQUE NOT NULL,
    from_address VARCHAR(42) NOT NULL,
    to_address VARCHAR(42) NOT NULL,
    amount DECIMAL(28,8) NOT NULL,
    token_address VARCHAR(42) NOT NULL,
    block_number BIGINT NOT NULL,
    gas_used BIGINT,
    gas_price BIGINT,
    tx_fee DECIMAL(28,18),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    confirmed_at TIMESTAMP WITH TIME ZONE
);
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- Risk assessments
CREATE TABLE risk_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID REFERENCES transactions(id),
    wallet_id UUID REFERENCES wallets(id),
    proximity_score DECIMAL(5,4) NOT NULL,
    velocity_score DECIMAL(5,4) NOT NULL,
    pattern_score DECIMAL(5,4) NOT NULL,
    overall_risk DECIMAL(5,4) NOT NULL,
    risk_factors JSONB,
    flagged BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE risk_assessments ENABLE ROW LEVEL SECURITY;

-- Proximity relationships
CREATE TABLE wallet_proximity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    wallet_a UUID REFERENCES wallets(id),
    wallet_b UUID REFERENCES wallets(id),
    proximity_score DECIMAL(5,4) NOT NULL,
    shared_transactions INTEGER DEFAULT 0,
    first_interaction TIMESTAMP WITH TIME ZONE,
    last_interaction TIMESTAMP WITH TIME ZONE,
    relationship_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(wallet_a, wallet_b)
);
ALTER TABLE wallet_proximity ENABLE ROW LEVEL SECURITY;

-- Trading pairs
CREATE TABLE trading_pairs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    base_token VARCHAR(42) NOT NULL,
    quote_token VARCHAR(42) NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(base_token, quote_token, exchange)
);
ALTER TABLE trading_pairs ENABLE ROW LEVEL SECURITY;

-- Price feeds
CREATE TABLE price_feeds (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pair_id UUID REFERENCES trading_pairs(id),
    price DECIMAL(28,18) NOT NULL,
    volume_24h DECIMAL(28,8),
    bid DECIMAL(28,18),
    ask DECIMAL(28,18),
    spread DECIMAL(10,6),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE price_feeds ENABLE ROW LEVEL SECURITY;

-- Trading positions
CREATE TABLE trading_positions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pair_id UUID REFERENCES trading_pairs(id),
    position_type VARCHAR(10) NOT NULL,
    size DECIMAL(28,8) NOT NULL,
    entry_price DECIMAL(28,18) NOT NULL,
    current_price DECIMAL(28,18),
    unrealized_pnl DECIMAL(28,8),
    status VARCHAR(20) DEFAULT 'open',
    opened_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);
ALTER TABLE trading_positions ENABLE ROW LEVEL SECURITY;

-- USDS minting/burning events
CREATE TABLE usds_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(20) NOT NULL,
    amount DECIMAL(28,8) NOT NULL,
    wallet_address VARCHAR(42) NOT NULL,
    collateral_amount DECIMAL(28,8),
    collateral_type VARCHAR(20),
    tx_hash VARCHAR(66) NOT NULL,
    block_number BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE usds_events ENABLE ROW LEVEL SECURITY;

-- Collateral reserves
CREATE TABLE collateral_reserves (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_type VARCHAR(20) NOT NULL,
    amount DECIMAL(28,8) NOT NULL,
    usd_value DECIMAL(28,8) NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE collateral_reserves ENABLE ROW LEVEL SECURITY;

-- Compliance reports
CREATE TABLE compliance_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_type VARCHAR(50) NOT NULL,
    wallet_address VARCHAR(42),
    transaction_hash VARCHAR(66),
    risk_level VARCHAR(20),
    details JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE
);
ALTER TABLE compliance_reports ENABLE ROW LEVEL SECURITY;

-- System alerts
CREATE TABLE system_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    acknowledged BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE
);
ALTER TABLE system_alerts ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- REVENUE TRACKING TABLES
-- =============================================================================

-- Revenue tracking table
CREATE TABLE revenue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    revenue_type TEXT NOT NULL CHECK (revenue_type IN ('stability_fee', 'transaction_fee')),
    amount DECIMAL(18,6) NOT NULL,
    currency TEXT,
    sender TEXT,
    recipient TEXT,
    usds_amount DECIMAL(18,6),
    transaction_type TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    month INTEGER DEFAULT EXTRACT(MONTH FROM NOW()),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE revenue ENABLE ROW LEVEL SECURITY;

-- Daily revenue aggregation
CREATE TABLE daily_revenue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    date DATE UNIQUE NOT NULL,
    stability_fees DECIMAL(18,6) DEFAULT 0,
    transaction_fees DECIMAL(18,6) DEFAULT 0,
    total DECIMAL(18,6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE daily_revenue ENABLE ROW LEVEL SECURITY;

-- Monthly targets tracking
CREATE TABLE monthly_targets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    target_amount DECIMAL(18,6) NOT NULL,
    actual_amount DECIMAL(18,6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(month, year)
);
ALTER TABLE monthly_targets ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- FRAUD DETECTION TABLES
-- =============================================================================

-- Fraud Graph Nodes Table
CREATE TABLE fraud_graph_nodes (
    address VARCHAR(64) PRIMARY KEY,
    node_type VARCHAR(20) DEFAULT 'wallet',
    risk_score FLOAT DEFAULT 0.0,
    transaction_count INTEGER DEFAULT 0,
    total_volume FLOAT DEFAULT 0.0,
    first_seen TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW(),
    labels JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
ALTER TABLE fraud_graph_nodes ENABLE ROW LEVEL SECURITY;

-- Fraud Graph Edges Table
CREATE TABLE fraud_graph_edges (
    from_address VARCHAR(64),
    to_address VARCHAR(64),
    transaction_count INTEGER DEFAULT 0,
    total_amount FLOAT DEFAULT 0.0,
    avg_amount FLOAT DEFAULT 0.0,
    frequency FLOAT DEFAULT 0.0,
    first_transaction TIMESTAMP DEFAULT NOW(),
    last_transaction TIMESTAMP DEFAULT NOW(),
    risk_flags JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (from_address, to_address)
);
ALTER TABLE fraud_graph_edges ENABLE ROW LEVEL SECURITY;

-- Fraud Clusters Table
CREATE TABLE fraud_clusters (
    cluster_id VARCHAR(64) PRIMARY KEY,
    addresses JSONB,
    risk_level FLOAT,
    pattern_type VARCHAR(50),
    total_volume FLOAT,
    suspicious_indicators JSONB,
    creation_time TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active'
);
ALTER TABLE fraud_clusters ENABLE ROW LEVEL SECURITY;

-- Fraud Anomalies Table
CREATE TABLE fraud_anomalies (
    id SERIAL PRIMARY KEY,
    address VARCHAR(64) NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,
    risk_score FLOAT NOT NULL,
    evidence JSONB NOT NULL,
    confidence FLOAT NOT NULL,
    recommendation VARCHAR(20) NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_at TIMESTAMP,
    reviewer_id VARCHAR(64),
    transaction_hash VARCHAR(66),
    amount FLOAT,
    UNIQUE(address, anomaly_type, detected_at)
);
ALTER TABLE fraud_anomalies ENABLE ROW LEVEL SECURITY;

-- Fraud Rules Table
CREATE TABLE fraud_rules (
    rule_id VARCHAR(64) PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,
    enabled BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
ALTER TABLE fraud_rules ENABLE ROW LEVEL SECURITY;

-- Fraud Whitelist Table
CREATE TABLE fraud_whitelist (
    address VARCHAR(64) PRIMARY KEY,
    reason VARCHAR(200) NOT NULL,
    added_by VARCHAR(64) NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);
ALTER TABLE fraud_whitelist ENABLE ROW LEVEL SECURITY;

-- Fraud Blacklist Table
CREATE TABLE fraud_blacklist (
    address VARCHAR(64) PRIMARY KEY,
    reason VARCHAR(200) NOT NULL,
    risk_level VARCHAR(20) DEFAULT 'high',
    added_by VARCHAR(64) NOT NULL,
    added_at TIMESTAMP DEFAULT NOW(),
    permanent BOOLEAN DEFAULT false
);
ALTER TABLE fraud_blacklist ENABLE ROW LEVEL SECURITY;

-- Transaction Analysis Cache Table
CREATE TABLE fraud_analysis_cache (
    transaction_hash VARCHAR(66) PRIMARY KEY,
    from_address VARCHAR(64) NOT NULL,
    to_address VARCHAR(64) NOT NULL,
    amount FLOAT NOT NULL,
    risk_score FLOAT NOT NULL,
    flags JSONB DEFAULT '[]',
    analysis_timestamp TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '24 hours'
);
ALTER TABLE fraud_analysis_cache ENABLE ROW LEVEL SECURITY;

-- Real-time Risk Scores Table
CREATE TABLE fraud_risk_scores (
    address VARCHAR(64) PRIMARY KEY,
    current_score FLOAT NOT NULL,
    previous_score FLOAT DEFAULT 0.0,
    score_trend VARCHAR(20) DEFAULT 'stable',
    last_updated TIMESTAMP DEFAULT NOW(),
    update_count INTEGER DEFAULT 1
);
ALTER TABLE fraud_risk_scores ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- INDEXES FOR PERFORMANCE
-- =============================================================================

-- Transaction indexes
CREATE INDEX idx_transactions_from_address ON transactions(from_address);
CREATE INDEX idx_transactions_to_address ON transactions(to_address);
CREATE INDEX idx_transactions_block_number ON transactions(block_number);
CREATE INDEX idx_transactions_created_at ON transactions(created_at);
CREATE INDEX idx_transactions_status ON transactions(status);

-- Wallet indexes
CREATE INDEX idx_wallets_address ON wallets(address);
CREATE INDEX idx_wallets_risk_score ON wallets(risk_score);
CREATE INDEX idx_wallets_created_at ON wallets(created_at);

-- Risk assessment indexes
CREATE INDEX idx_risk_assessments_overall_risk ON risk_assessments(overall_risk);
CREATE INDEX idx_risk_assessments_flagged ON risk_assessments(flagged);
CREATE INDEX idx_risk_assessments_created_at ON risk_assessments(created_at);

-- Proximity indexes
CREATE INDEX idx_wallet_proximity_score ON wallet_proximity(proximity_score);
CREATE INDEX idx_wallet_proximity_wallet_a ON wallet_proximity(wallet_a);
CREATE INDEX idx_wallet_proximity_wallet_b ON wallet_proximity(wallet_b);

-- Price feed indexes
CREATE INDEX idx_price_feeds_timestamp ON price_feeds(timestamp);
CREATE INDEX idx_price_feeds_pair_id ON price_feeds(pair_id);

-- Revenue indexes
CREATE INDEX idx_revenue_timestamp ON revenue(timestamp);
CREATE INDEX idx_revenue_type ON revenue(revenue_type);
CREATE INDEX idx_daily_revenue_date ON daily_revenue(date);

-- Fraud indexes
CREATE INDEX idx_fraud_nodes_risk ON fraud_graph_nodes(risk_score DESC);
CREATE INDEX idx_fraud_nodes_active ON fraud_graph_nodes(last_active DESC);
CREATE INDEX idx_fraud_nodes_volume ON fraud_graph_nodes(total_volume DESC);
CREATE INDEX idx_fraud_edges_amount ON fraud_graph_edges(total_amount DESC);
CREATE INDEX idx_fraud_edges_frequency ON fraud_graph_edges(frequency DESC);
CREATE INDEX idx_fraud_anomalies_score ON fraud_anomalies(risk_score DESC);
CREATE INDEX idx_fraud_anomalies_detected ON fraud_anomalies(detected_at DESC);
CREATE INDEX idx_fraud_anomalies_status ON fraud_anomalies(status);
CREATE INDEX idx_fraud_cache_expires ON fraud_analysis_cache(expires_at);
CREATE INDEX idx_fraud_risk_updated ON fraud_risk_scores(last_updated DESC);

-- GIN Indexes for JSONB columns
CREATE INDEX idx_fraud_nodes_labels_gin ON fraud_graph_nodes USING GIN(labels);
CREATE INDEX idx_fraud_edges_flags_gin ON fraud_graph_edges USING GIN(risk_flags);
CREATE INDEX idx_fraud_anomalies_evidence_gin ON fraud_anomalies USING GIN(evidence);

-- =============================================================================
-- FUNCTIONS & TRIGGERS
-- =============================================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers
CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON wallets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Fraud auto-cleanup function
CREATE OR REPLACE FUNCTION cleanup_fraud_cache()
RETURNS void AS $$
BEGIN
    DELETE FROM fraud_analysis_cache WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Fraud refresh function for materialized view
CREATE OR REPLACE FUNCTION refresh_fraud_stats()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW fraud_network_stats;
END;
$$ LANGUAGE plpgsql;

-- Trigger for auto-updating risk scores
CREATE OR REPLACE FUNCTION update_risk_score_trigger()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO fraud_risk_scores (address, current_score, previous_score)
    VALUES (NEW.address, NEW.risk_score, COALESCE(OLD.risk_score, 0.0))
    ON CONFLICT (address) DO UPDATE SET
        previous_score = fraud_risk_scores.current_score,
        current_score = NEW.risk_score,
        score_trend = CASE 
            WHEN NEW.risk_score > fraud_risk_scores.current_score THEN 'rising'
            WHEN NEW.risk_score < fraud_risk_scores.current_score THEN 'falling'
            ELSE 'stable'
        END,
        last_updated = NOW(),
        update_count = fraud_risk_scores.update_count + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER fraud_node_risk_update
    AFTER UPDATE OF risk_score ON fraud_graph_nodes
    FOR EACH ROW
    EXECUTE FUNCTION update_risk_score_trigger();

-- =============================================================================
-- MATERIALIZED VIEWS
-- =============================================================================

CREATE MATERIALIZED VIEW fraud_network_stats AS
SELECT 
    COUNT(*) as total_nodes,
    AVG(risk_score) as avg_risk_score,
    COUNT(*) FILTER (WHERE risk_score > 7.0) as high_risk_nodes,
    SUM(total_volume) as total_network_volume,
    MAX(last_active) as last_network_activity
FROM fraud_graph_nodes;

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Insert USDS token
INSERT INTO trading_pairs (base_token, quote_token, exchange) VALUES
('0x0000000000000000000000000000000000000000', '0xa0b86991c431b9c30e58c55de6e5f4c06f0e2a1b', 'internal');

-- Insert initial collateral reserve
INSERT INTO collateral_reserves (asset_type, amount, usd_value) VALUES
('USDC', 0, 0),
('ETH', 0, 0);

-- Insert initial monthly targets
INSERT INTO monthly_targets (month, year, target_amount) VALUES 
(1, 2025, 5000),
(2, 2025, 7500),
(3, 2025, 10000),
(4, 2025, 15000);

-- Insert critical fraud rules
INSERT INTO fraud_rules (rule_id, rule_name, rule_type, conditions, actions) VALUES
('high_risk_block', 'High Risk Address Block', 'risk_threshold', 
 '{"risk_score_min": 8.0}', 
 '{"action": "block", "notify": true, "escalate": true}'),
('rapid_fire_limit', 'Rapid Fire Transaction Limit', 'velocity', 
 '{"max_tx_per_minute": 50, "time_window": 60}', 
 '{"action": "throttle", "delay": 10, "notify": false}'),
('large_amount_review', 'Large Amount Review', 'amount_threshold', 
 '{"amount_min": 100000}', 
 '{"action": "review", "priority": "high", "notify": true}'),
('circular_pattern_block', 'Circular Pattern Block', 'pattern', 
 '{"pattern_type": "circular_flow", "confidence_min": 0.9}', 
 '{"action": "block", "notify": true, "investigate": true}'),
('mixer_detection', 'Crypto Mixer Detection', 'pattern',
 '{"pattern_type": "mixer", "confidence_min": 0.8}',
 '{"action": "flag", "priority": "critical", "freeze": true}'),
('layering_pattern', 'Transaction Layering Pattern', 'pattern',
 '{"pattern_type": "layering", "min_hops": 5, "time_window": 300}',
 '{"action": "investigate", "priority": "high", "monitor": true}')
ON CONFLICT (rule_id) DO NOTHING;

-- =============================================================================
-- PERMISSIONS
-- =============================================================================

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO seamount_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO seamount_app;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO seamount_app;

COMMIT;
