-- Execute this SQL in Supabase SQL Editor to create all required tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- User profiles table with RLS
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    country_code TEXT,
    kyc_level INTEGER DEFAULT 0,
    kyc_status TEXT DEFAULT 'pending',
    is_admin BOOLEAN DEFAULT FALSE,
    algorand_address TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- RLS policies for user_profiles
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid()::text = id::text);

-- Compliance logs table with RLS
CREATE TABLE IF NOT EXISTS compliance_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    details JSONB,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE compliance_logs ENABLE ROW LEVEL SECURITY;

-- RLS policies for compliance_logs
CREATE POLICY "Service role can manage compliance logs" ON compliance_logs
    FOR ALL USING (true);

-- Investor contacts table with RLS
CREATE TABLE IF NOT EXISTS investor_contacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    checksize TEXT,
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE investor_contacts ENABLE ROW LEVEL SECURITY;

-- RLS policy for investor_contacts
CREATE POLICY "Service role can manage investor contacts" ON investor_contacts
    FOR ALL USING (true);

-- KYC documents table with RLS
CREATE TABLE IF NOT EXISTS kyc_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    document_data TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_at TIMESTAMP WITH TIME ZONE
);

ALTER TABLE kyc_documents ENABLE ROW LEVEL SECURITY;

-- RLS policies for kyc_documents
CREATE POLICY "Users can view own KYC documents" ON kyc_documents
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own KYC documents" ON kyc_documents
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- KYC verifications table with RLS
CREATE TABLE IF NOT EXISTS kyc_verifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending',
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verified_at TIMESTAMP WITH TIME ZONE
);

ALTER TABLE kyc_verifications ENABLE ROW LEVEL SECURITY;

-- RLS policies for kyc_verifications
CREATE POLICY "Users can view own KYC verification" ON kyc_verifications
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Service role can manage KYC verifications" ON kyc_verifications
    FOR ALL USING (true);

-- Transactions table with RLS
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sender_id TEXT NOT NULL,
    recipient_id TEXT NOT NULL,
    amount DECIMAL(18, 6) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USDS',
    transaction_id TEXT UNIQUE NOT NULL,
    status TEXT DEFAULT 'pending',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- RLS policies for transactions
CREATE POLICY "Users can view own transactions" ON transactions
    FOR SELECT USING (
        auth.uid()::text = sender_id OR 
        auth.uid()::text = recipient_id
    );

CREATE POLICY "Service role can manage transactions" ON transactions
    FOR ALL USING (true);

-- Wallet balances table with RLS
CREATE TABLE IF NOT EXISTS wallet_balances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    currency TEXT NOT NULL,
    amount DECIMAL(18, 6) DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, currency)
);

ALTER TABLE wallet_balances ENABLE ROW LEVEL SECURITY;

-- RLS policies for wallet_balances
CREATE POLICY "Users can view own wallet balance" ON wallet_balances
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Service role can manage wallet balances" ON wallet_balances
    FOR ALL USING (true);

-- Backing reserves table with RLS
CREATE TABLE IF NOT EXISTS backing_reserves (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    amount DECIMAL(18, 6) NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('mint', 'burn')),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE backing_reserves ENABLE ROW LEVEL SECURITY;

-- RLS policy for backing_reserves
CREATE POLICY "Service role can manage backing reserves" ON backing_reserves
    FOR ALL USING (true);

-- Exchange rates table with RLS
CREATE TABLE IF NOT EXISTS exchange_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    rate DECIMAL(18, 8) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(from_currency, to_currency)
);

ALTER TABLE exchange_rates ENABLE ROW LEVEL SECURITY;

-- RLS policy for exchange_rates
CREATE POLICY "Anyone can view exchange rates" ON exchange_rates
    FOR SELECT USING (true);

CREATE POLICY "Service role can manage exchange rates" ON exchange_rates
    FOR ALL USING (true);

-- Payment requests table with RLS
CREATE TABLE IF NOT EXISTS payment_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    quote_id TEXT UNIQUE NOT NULL,
    amount DECIMAL(18, 6) NOT NULL,
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    estimated_fee DECIMAL(18, 6),
    converted_amount DECIMAL(18, 6),
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE payment_requests ENABLE ROW LEVEL SECURITY;

-- RLS policy for payment_requests
CREATE POLICY "Service role can manage payment requests" ON payment_requests
    FOR ALL USING (true);

-- User consents table with RLS
CREATE TABLE IF NOT EXISTS user_consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT UNIQUE NOT NULL,
    preferences JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE user_consents ENABLE ROW LEVEL SECURITY;

-- RLS policies for user_consents
CREATE POLICY "Users can view own consent" ON user_consents
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can update own consent" ON user_consents
    FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own consent" ON user_consents
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- marketData holdings table with RLS
CREATE TABLE IF NOT EXISTS marketData_holdings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    asset TEXT NOT NULL,
    amount DECIMAL(18, 6) NOT NULL,
    currency TEXT NOT NULL,
    acquired_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    value_usd DECIMAL(18, 6) DEFAULT 0
);

ALTER TABLE marketData_holdings ENABLE ROW LEVEL SECURITY;

-- RLS policies for marketData_holdings
CREATE POLICY "Users can view own marketData" ON marketData_holdings
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Service role can manage marketData holdings" ON marketData_holdings
    FOR ALL USING (true);

-- User MFA table with RLS
CREATE TABLE IF NOT EXISTS user_mfa (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT UNIQUE NOT NULL,
    secret TEXT NOT NULL,
    is_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    verified_at TIMESTAMP WITH TIME ZONE
);

ALTER TABLE user_mfa ENABLE ROW LEVEL SECURITY;

-- RLS policies for user_mfa
CREATE POLICY "Users can view own MFA" ON user_mfa
    FOR SELECT USING (auth.uid()::text = user_id);

CREATE POLICY "Users can update own MFA" ON user_mfa
    FOR UPDATE USING (auth.uid()::text = user_id);

CREATE POLICY "Users can insert own MFA" ON user_mfa
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);

-- Insert default exchange rates
INSERT INTO exchange_rates (from_currency, to_currency, rate) VALUES
    ('USD', 'USDS', 1.0000),
    ('USDS', 'USD', 1.0000),
    ('USDC', 'USDS', 1.0000),
    ('USDS', 'USDC', 1.0000),
    ('USDT', 'USDS', 1.0000),
    ('USDS', 'USDT', 1.0000)
ON CONFLICT (from_currency, to_currency) DO NOTHING;