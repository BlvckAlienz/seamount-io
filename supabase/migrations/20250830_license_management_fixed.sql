-- File Location: supabase/migrations/20250830_license_management_fixed.sql
-- License Management Tables with Row Level Security

-- First, ensure user_profiles table exists with the correct structure
DO $$
BEGIN
    -- Check if user_profiles table exists
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_profiles') THEN
        -- Add user_id column if it doesn't exist
        IF NOT EXISTS (SELECT FROM information_schema.columns WHERE table_name = 'user_profiles' AND column_name = 'user_id') THEN
            ALTER TABLE user_profiles ADD COLUMN user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
            
            -- Update existing records to link to auth users
            UPDATE user_profiles up
            SET user_id = au.id
            FROM auth.users au
            WHERE up.email = au.email;
        END IF;
    ELSE
        -- Create user_profiles table if it doesn't exist
        CREATE TABLE user_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            email VARCHAR(255),
            full_name VARCHAR(255),
            role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('user', 'admin', 'super_admin')),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    END IF;
END $$;

-- Enable RLS on user_profiles if not already enabled
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- Basic user_profiles policies (if they don't exist)
DO $$
BEGIN
    CREATE POLICY "Users can view own profile" ON user_profiles
        FOR SELECT USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Users can update own profile" ON user_profiles
        FOR UPDATE USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- SMB Licenses Table
CREATE TABLE IF NOT EXISTS smb_licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL CHECK (tier IN ('basic', 'pro', 'enterprise')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'expired', 'cancelled')),
    employee_count INTEGER,
    license_fee DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    region VARCHAR(50) NOT NULL DEFAULT 'default',
    
    -- Timestamps
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    
    -- Payment tracking
    payment_reference VARCHAR(100) UNIQUE,
    payment_status VARCHAR(20) DEFAULT 'pending' CHECK (payment_status IN ('pending', 'completed', 'failed', 'refunded')),
    payment_provider VARCHAR(50),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- License Usage Tracking
CREATE TABLE IF NOT EXISTS license_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID NOT NULL REFERENCES smb_licenses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    month_year VARCHAR(7) NOT NULL, -- Format: YYYY-MM
    
    -- Usage metrics
    transactions_count INTEGER DEFAULT 0,
    volume_processed DECIMAL(15,2) DEFAULT 0,
    fees_saved DECIMAL(15,2) DEFAULT 0,
    employees_active INTEGER DEFAULT 0,
    
    -- Limits tracking
    transaction_limit INTEGER,
    volume_limit DECIMAL(15,2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(license_id, month_year)
);

-- License Tier History (for upgrades/downgrades)
CREATE TABLE IF NOT EXISTS license_tier_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id UUID NOT NULL REFERENCES smb_licenses(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Tier change details
    from_tier VARCHAR(20),
    to_tier VARCHAR(20) NOT NULL,
    change_type VARCHAR(20) NOT NULL CHECK (change_type IN ('upgrade', 'downgrade', 'initial')),
    
    -- Financial details
    prorated_amount DECIMAL(15,2),
    effective_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Payment tracking for upgrades
    payment_reference VARCHAR(100),
    payment_status VARCHAR(20) DEFAULT 'completed',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- License Benefits/Features Mapping
CREATE TABLE IF NOT EXISTS license_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tier VARCHAR(20) NOT NULL,
    feature_key VARCHAR(100) NOT NULL,
    feature_name VARCHAR(200) NOT NULL,
    feature_description TEXT,
    is_enabled BOOLEAN DEFAULT true,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(tier, feature_key)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_smb_licenses_user_id ON smb_licenses(user_id);
CREATE INDEX IF NOT EXISTS idx_smb_licenses_status ON smb_licenses(status);
CREATE INDEX IF NOT EXISTS idx_smb_licenses_tier ON smb_licenses(tier);
CREATE INDEX IF NOT EXISTS idx_smb_licenses_expires_at ON smb_licenses(expires_at);
CREATE INDEX IF NOT EXISTS idx_smb_licenses_payment_reference ON smb_licenses(payment_reference);

CREATE INDEX IF NOT EXISTS idx_license_usage_license_id ON license_usage(license_id);
CREATE INDEX IF NOT EXISTS idx_license_usage_month_year ON license_usage(month_year);
CREATE INDEX IF NOT EXISTS idx_license_usage_user_month ON license_usage(user_id, month_year);

CREATE INDEX IF NOT EXISTS idx_license_tier_history_license_id ON license_tier_history(license_id);
CREATE INDEX IF NOT EXISTS idx_license_tier_history_user_id ON license_tier_history(user_id);

-- Row Level Security (RLS) Policies

-- Enable RLS on all tables
ALTER TABLE smb_licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE license_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE license_tier_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE license_features ENABLE ROW LEVEL SECURITY;

-- SMB Licenses RLS Policies
DO $$
BEGIN
    CREATE POLICY "Users can view their own licenses" ON smb_licenses
        FOR SELECT USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Users can insert their own licenses" ON smb_licenses
        FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Users can update their own licenses" ON smb_licenses
        FOR UPDATE USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- Admins can view all licenses (adjust role check as needed)
DO $$
BEGIN
    CREATE POLICY "Admins can manage all licenses" ON smb_licenses
        FOR ALL USING (
            EXISTS (
                SELECT 1 FROM user_profiles 
                WHERE user_id = auth.uid() 
                AND role IN ('admin', 'super_admin')
            )
        );
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- License Usage RLS Policies
DO $$
BEGIN
    CREATE POLICY "Users can view their own usage" ON license_usage
        FOR SELECT USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Users can insert their own usage" ON license_usage
        FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Users can update their own usage" ON license_usage
        FOR UPDATE USING (auth.uid() = user_id)
        WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Admins can view all usage" ON license_usage
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM user_profiles 
                WHERE user_id = auth.uid() 
                AND role IN ('admin', 'super_admin')
            )
        );
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- License Tier History RLS Policies
DO $$
BEGIN
    CREATE POLICY "Users can view their own tier history" ON license_tier_history
        FOR SELECT USING (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "System can insert tier history" ON license_tier_history
        FOR INSERT WITH CHECK (auth.uid() = user_id);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Admins can view all tier history" ON license_tier_history
        FOR SELECT USING (
            EXISTS (
                SELECT 1 FROM user_profiles 
                WHERE user_id = auth.uid() 
                AND role IN ('admin', 'super_admin')
            )
        );
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- License Features - Public read access
DO $$
BEGIN
    CREATE POLICY "Anyone can view license features" ON license_features
        FOR SELECT USING (true);
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

DO $$
BEGIN
    CREATE POLICY "Only admins can manage features" ON license_features
        FOR ALL USING (
            EXISTS (
                SELECT 1 FROM user_profiles 
                WHERE user_id = auth.uid() 
                AND role IN ('admin', 'super_admin')
            )
        );
EXCEPTION WHEN duplicate_object THEN
    NULL;
END $$;

-- Triggers for updated_at timestamps - FIXED WITH SEARCH_PATH
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public  -- Fixed search path
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

-- Drop triggers if they exist, then create them
DROP TRIGGER IF EXISTS update_smb_licenses_updated_at ON smb_licenses;
CREATE TRIGGER update_smb_licenses_updated_at 
    BEFORE UPDATE ON smb_licenses 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_license_usage_updated_at ON license_usage;
CREATE TRIGGER update_license_usage_updated_at 
    BEFORE UPDATE ON license_usage 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER update_user_profiles_updated_at 
    BEFORE UPDATE ON user_profiles 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default license features (using ON CONFLICT to avoid duplicates)
INSERT INTO license_features (tier, feature_key, feature_name, feature_description) VALUES
-- Basic tier features
('basic', 'transaction_discount', '20% Transaction Fee Discount', 'Save 20% on every cross-border payment compared to individual rates'),
('basic', 'monthly_volume_limit', 'Monthly Volume: $50K', 'Process up to $50,000 in transactions monthly'),
('basic', 'employee_limit', 'Up to 10 Employees', 'Add up to 10 team members to your business account'),
('basic', 'email_support', 'Email Support', '24/7 email support for all your business needs'),
('basic', 'basic_reporting', 'Basic Reporting', 'Monthly transaction reports and fee summaries'),

-- Pro tier features  
('pro', 'transaction_discount', '30% Transaction Fee Discount', 'Save 30% on every cross-border payment with higher volume benefits'),
('pro', 'monthly_volume_limit', 'Monthly Volume: $200K', 'Process up to $200,000 in transactions monthly'),
('pro', 'employee_limit', 'Up to 50 Employees', 'Scale your team with up to 50 employee accounts'),
('pro', 'priority_support', 'Priority Support', '24/7 priority support via email and chat'),
('pro', 'advanced_reporting', 'Advanced Analytics', 'Detailed transaction analytics, profit/loss tracking, and custom reports'),
('pro', 'api_access', 'API Access', 'Integrate Seamount payments directly into your systems'),
('pro', 'bulk_payments', 'Bulk Payment Processing', 'Process multiple payments simultaneously with CSV upload'),

-- Enterprise tier features
('enterprise', 'transaction_discount', '40% Transaction Fee Discount', 'Maximum savings with 40% discount on all transactions'),
('enterprise', 'monthly_volume_unlimited', 'Unlimited Monthly Volume', 'No limits on your monthly transaction volume'),
('enterprise', 'employee_limit_unlimited', 'Unlimited Employees', 'Add unlimited team members to your enterprise account'),
('enterprise', 'dedicated_support', 'Dedicated Account Manager', 'Personal account manager with phone support and SLA guarantees'),
('enterprise', 'enterprise_reporting', 'Enterprise Analytics Suite', 'Advanced business intelligence, custom dashboards, and real-time monitoring'),
('enterprise', 'advanced_api', 'Advanced API & Webhooks', 'Full API access with webhooks, sandbox environment, and priority rate limits'),
('enterprise', 'white_label', 'White Label Options', 'Customize the platform with your branding for client-facing applications'),
('enterprise', 'custom_integration', 'Custom Integrations', 'Dedicated integration support for ERP, accounting, and other business systems')
ON CONFLICT (tier, feature_key) DO NOTHING;

-- Create function to automatically create usage tracking entry for new licenses - FIXED WITH SEARCH_PATH
CREATE OR REPLACE FUNCTION public.create_initial_usage_tracking()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public  -- Fixed search path
AS $$
BEGIN
    -- Create initial usage tracking for current month when license is activated
    IF NEW.status = 'active' AND (OLD IS NULL OR OLD.status != 'active') THEN
        INSERT INTO license_usage (license_id, user_id, month_year)
        VALUES (NEW.id, NEW.user_id, TO_CHAR(NOW(), 'YYYY-MM'))
        ON CONFLICT (license_id, month_year) DO NOTHING;
    END IF;
    
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trigger_create_initial_usage_tracking ON smb_licenses;
CREATE TRIGGER trigger_create_initial_usage_tracking
    AFTER INSERT OR UPDATE ON smb_licenses
    FOR EACH ROW EXECUTE FUNCTION create_initial_usage_tracking();

-- Views for easier querying - FIXED WITHOUT SECURITY DEFINER
CREATE OR REPLACE VIEW public.active_licenses AS
SELECT 
    l.*,
    CASE 
        WHEN l.expires_at IS NULL THEN true
        WHEN l.expires_at > NOW() THEN true
        ELSE false
    END as is_active,
    COALESCE(u.transactions_count, 0) as current_month_transactions,
    COALESCE(u.volume_processed, 0) as current_month_volume
FROM smb_licenses l
LEFT JOIN license_usage u ON l.id = u.license_id 
    AND u.month_year = TO_CHAR(NOW(), 'YYYY-MM')
WHERE l.status = 'active';

-- Grant appropriate permissions
GRANT SELECT, INSERT, UPDATE ON smb_licenses TO authenticated;
GRANT SELECT, INSERT, UPDATE ON license_usage TO authenticated;
GRANT SELECT, INSERT ON license_tier_history TO authenticated;
GRANT SELECT ON license_features TO authenticated;
GRANT SELECT ON active_licenses TO authenticated;