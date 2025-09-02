-- File Location: supabase/migrations/20240902_enhanced_security_and_audit.sql
-- CRITICAL: Enhanced security policies and audit tables with RLS

-- Enable RLS on all existing tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Create enhanced audit logs table if not exists
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Create index for efficient queries
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create index for efficient audit log queries
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Enhanced user_profiles table with additional security fields
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS kyc_session_id VARCHAR(255);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS kyc_provider VARCHAR(50) DEFAULT 'complycube';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS security_flags JSONB DEFAULT '{}';
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0;
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS account_locked_until TIMESTAMP WITH TIME ZONE;

-- Create secure RLS policies for user_profiles
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
CREATE POLICY "Users can view own profile" ON user_profiles
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
CREATE POLICY "Users can update own profile" ON user_profiles
    FOR UPDATE USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
CREATE POLICY "Users can insert own profile" ON user_profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- Admin can view all profiles
DROP POLICY IF EXISTS "Admins can view all profiles" ON user_profiles;
CREATE POLICY "Admins can view all profiles" ON user_profiles
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE id = auth.uid() 
            AND (security_flags->>'is_admin')::boolean = true
        )
    );

-- RLS policies for audit_logs
DROP POLICY IF EXISTS "Users can view own audit logs" ON audit_logs;
CREATE POLICY "Users can view own audit logs" ON audit_logs
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "System can insert audit logs" ON audit_logs;
CREATE POLICY "System can insert audit logs" ON audit_logs
    FOR INSERT WITH CHECK (true);
	
-- Admin can view all audit logs
DROP POLICY IF EXISTS "Admins can view all audit logs" ON audit_logs;
CREATE POLICY "Admins can view all audit logs" ON audit_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE id = auth.uid() 
            AND (security_flags->>'is_admin')::boolean = true
        )
    );

-- Create payment_transactions table with RLS
CREATE TABLE IF NOT EXISTS payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(20,6) NOT NULL,
    currency_code VARCHAR(10) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    recipient_address TEXT,
    sender_address TEXT,
    tx_hash TEXT,
    network VARCHAR(50),
    gas_fee DECIMAL(20,6),
    exchange_rate DECIMAL(20,6),
    provider VARCHAR(50),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT fk_payment_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Enable RLS on payment_transactions
ALTER TABLE payment_transactions ENABLE ROW LEVEL SECURITY;

-- Create indexes for efficient payment queries
CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id ON payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_created_at ON payment_transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_tx_hash ON payment_transactions(tx_hash);

-- RLS policies for payment_transactions
DROP POLICY IF EXISTS "Users can view own payment transactions" ON payment_transactions;
CREATE POLICY "Users can view own payment transactions" ON payment_transactions
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own payment transactions" ON payment_transactions;
CREATE POLICY "Users can insert own payment transactions" ON payment_transactions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own payment transactions" ON payment_transactions;
CREATE POLICY "Users can update own payment transactions" ON payment_transactions
    FOR UPDATE USING (auth.uid() = user_id);

-- Admin can view all payment transactions
DROP POLICY IF EXISTS "Admins can view all payment transactions" ON payment_transactions;
CREATE POLICY "Admins can view all payment transactions" ON payment_transactions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE id = auth.uid() 
            AND (security_flags->>'is_admin')::boolean = true
        )
    );

-- Create user_wallets table with enhanced security
CREATE TABLE IF NOT EXISTS user_wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    algorand_address TEXT NOT NULL,
    algorand_private_key TEXT NOT NULL, -- Encrypted
    wallet_type VARCHAR(50) DEFAULT 'algorand',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_wallet_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Enable RLS on user_wallets
ALTER TABLE user_wallets ENABLE ROW LEVEL SECURITY;

-- Create secure RLS policies for user_wallets
DROP POLICY IF EXISTS "Users can view own wallet" ON user_wallets;
CREATE POLICY "Users can view own wallet" ON user_wallets
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own wallet" ON user_wallets;
CREATE POLICY "Users can insert own wallet" ON user_wallets
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own wallet" ON user_wallets;
CREATE POLICY "Users can update own wallet" ON user_wallets
    FOR UPDATE USING (auth.uid() = user_id);

-- Create session_logs table for session management
CREATE TABLE IF NOT EXISTS session_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_id TEXT NOT NULL,
    action VARCHAR(100) NOT NULL,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Enable RLS on session_logs
ALTER TABLE session_logs ENABLE ROW LEVEL SECURITY;

-- Create index for efficient session queries
CREATE INDEX IF NOT EXISTS idx_session_logs_user_id ON session_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_session_logs_session_id ON session_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_session_logs_created_at ON session_logs(created_at DESC);

-- RLS policies for session_logs
DROP POLICY IF EXISTS "Users can view own session logs" ON session_logs;
CREATE POLICY "Users can view own session logs" ON session_logs
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "System can insert session logs" ON session_logs;
CREATE POLICY "System can insert session logs" ON session_logs
    FOR INSERT WITH CHECK (true);

-- Create compliance_checks table
CREATE TABLE IF NOT EXISTS compliance_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    check_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,
    result_data JSONB DEFAULT '{}',
    provider VARCHAR(50),
    external_reference TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT fk_compliance_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Enable RLS on compliance_checks
ALTER TABLE compliance_checks ENABLE ROW LEVEL SECURITY;

-- Create index for efficient compliance queries
CREATE INDEX IF NOT EXISTS idx_compliance_checks_user_id ON compliance_checks(user_id);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_type ON compliance_checks(check_type);
CREATE INDEX IF NOT EXISTS idx_compliance_checks_status ON compliance_checks(status);

-- RLS policies for compliance_checks
DROP POLICY IF EXISTS "Users can view own compliance checks" ON compliance_checks;
CREATE POLICY "Users can view own compliance checks" ON compliance_checks
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "System can manage compliance checks" ON compliance_checks;
CREATE POLICY "System can manage compliance checks" ON compliance_checks
    FOR ALL WITH CHECK (true);

-- Admin can view all compliance checks
DROP POLICY IF EXISTS "Admins can view all compliance checks" ON compliance_checks;
CREATE POLICY "Admins can view all compliance checks" ON compliance_checks
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM user_profiles 
            WHERE id = auth.uid() 
            AND (security_flags->>'is_admin')::boolean = true
        )
    );

-- Update existing user_profiles table with enhanced audit trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply the trigger to all relevant tables
DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_payment_transactions_updated_at ON payment_transactions;
CREATE TRIGGER update_payment_transactions_updated_at
    BEFORE UPDATE ON payment_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_wallets_updated_at ON user_wallets;
CREATE TRIGGER update_user_wallets_updated_at
    BEFORE UPDATE ON user_wallets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for admin dashboard
CREATE OR REPLACE VIEW admin_user_overview AS
SELECT 
    up.id,
    up.first_name,
    up.last_name,
    up.email,
    up.kyc_status,
    up.kyc_level,
    up.created_at,
    up.last_login_at,
    up.failed_login_attempts,
    up.account_locked_until,
    uw.algorand_address,
    COUNT(pt.id) as transaction_count,
    COALESCE(SUM(pt.amount), 0) as total_transaction_volume
FROM user_profiles up
LEFT JOIN user_wallets uw ON up.id = uw.user_id
LEFT JOIN payment_transactions pt ON up.id = pt.user_id AND pt.status = 'completed'
GROUP BY up.id, uw.algorand_address;

-- Grant necessary permissions
GRANT SELECT ON admin_user_overview TO authenticated;

-- Create function to check user permissions
CREATE OR REPLACE FUNCTION check_user_permission(user_uuid UUID, permission_type TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM user_profiles
        WHERE id = user_uuid 
        AND (security_flags->>permission_type)::boolean = true
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;