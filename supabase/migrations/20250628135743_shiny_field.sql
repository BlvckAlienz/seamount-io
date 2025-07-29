-- Add Regulatory Compliance Tables for Seamount.io
-- This migration adds tables for enhanced audit, monitoring, and compliance functionality

-- Immutable Audit Logs Table
-- Stores all system events in a tamper-evident format
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id UUID REFERENCES auth.users(id),
    details JSONB DEFAULT '{}'::jsonb,
    ip_address TEXT,
    resource_id TEXT,
    severity TEXT DEFAULT 'info',
    previous_hash TEXT,
    hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create indexes for audit logs
CREATE INDEX IF NOT EXISTS idx_audit_logs_type ON public.audit_logs(type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON public.audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON public.audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_severity ON public.audit_logs(severity);

-- Continuous Monitoring Alerts Table
-- Stores alerts from the monitoring system
CREATE TABLE IF NOT EXISTS public.monitoring_alerts (
    id TEXT PRIMARY KEY,
    pattern_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    transaction_ids TEXT[],
    details JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'new',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

-- Create indexes for monitoring alerts
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_pattern ON public.monitoring_alerts(pattern_type);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_severity ON public.monitoring_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_user_id ON public.monitoring_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_status ON public.monitoring_alerts(status);
CREATE INDEX IF NOT EXISTS idx_monitoring_alerts_created_at ON public.monitoring_alerts(created_at);

-- Regulatory Reports Table
-- Stores generated regulatory reports
CREATE TABLE IF NOT EXISTS public.regulatory_reports (
    id TEXT PRIMARY KEY,
    report_type TEXT NOT NULL,
    country_code TEXT NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    format TEXT NOT NULL,
    status TEXT NOT NULL,
    file_name TEXT,
    error_message TEXT,
    record_count INTEGER,
    report_content TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Create indexes for regulatory reports
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_type ON public.regulatory_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_country ON public.regulatory_reports(country_code);
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_status ON public.regulatory_reports(status);
CREATE INDEX IF NOT EXISTS idx_regulatory_reports_created_at ON public.regulatory_reports(created_at);

-- Add is_admin field to user_profiles if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'is_admin') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN is_admin BOOLEAN DEFAULT false;
    END IF;
END $$;

-- Add suspended_fields to user_profiles if they don't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'is_active') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN is_active BOOLEAN DEFAULT true;
    END IF;

    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'suspended_reason') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN suspended_reason TEXT;
    END IF;

    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'suspended_at') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN suspended_at TIMESTAMPTZ;
    END IF;

    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'suspended_by') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN suspended_by UUID REFERENCES auth.users(id);
    END IF;
END $$;

-- Add trading_enabled field to user_profiles if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'trading_enabled') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN trading_enabled BOOLEAN DEFAULT false;
    END IF;
END $$;

-- Create verification_sessions table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.verification_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    session_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Create verification_attempts table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.verification_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    check_id TEXT,
    status TEXT NOT NULL,
    document_type TEXT,
    result TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

-- Enable RLS on new tables
ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.monitoring_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regulatory_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_attempts ENABLE ROW LEVEL SECURITY;

-- RLS policies for audit_logs
CREATE POLICY "Only admins can insert audit logs" 
    ON public.audit_logs FOR INSERT TO authenticated 
    WITH CHECK (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()) = true
    );

CREATE POLICY "Only admins can select audit logs" 
    ON public.audit_logs FOR SELECT TO authenticated 
    USING (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()) = true
    );

-- RLS policies for monitoring_alerts
CREATE POLICY "Only admins can insert monitoring alerts" 
    ON public.monitoring_alerts FOR INSERT TO authenticated 
    WITH CHECK (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()) = true
    );

CREATE POLICY "Only admins can update monitoring alerts" 
    ON public.monitoring_alerts FOR UPDATE TO authenticated 
    USING (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()) = true
    );

CREATE POLICY "Only admins can select monitoring alerts" 
    ON public.monitoring_alerts FOR SELECT TO authenticated 
    USING (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()) = true
    );

-- RLS policies for regulatory_reports
CREATE POLICY "Only admins can insert regulatory reports" 
    ON public.regulatory_reports FOR INSERT TO authenticated 
    WITH CHECK (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()) = true
    );

CREATE POLICY "Only admins can update regulatory reports" 
    ON public.regulatory_reports FOR UPDATE TO authenticated 
    USING (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()) = true
    );

CREATE POLICY "Only admins can select regulatory reports" 
    ON public.regulatory_reports FOR SELECT TO authenticated 
    USING (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid()) = true
    );

-- Create functions to generate regulatory reports
CREATE OR REPLACE FUNCTION public.generate_transaction_report(
    country_code TEXT,
    report_date DATE
)
RETURNS JSONB
LANGUAGE SQL
SECURITY DEFINER
AS $$
    WITH daily_txs AS (
        SELECT 
            payment_type,
            COUNT(*) as tx_count,
            SUM(amount) as total_amount,
            SUM(fee) as total_fees
        FROM public.payment_transactions
        WHERE 
            country_code = $1 AND
            DATE(created_at) = $2
        GROUP BY payment_type
    )
    SELECT 
        jsonb_build_object(
            'report_type', 'daily_transactions',
            'country_code', $1,
            'date', $2,
            'total_count', SUM(tx_count),
            'total_volume', SUM(total_amount),
            'total_fees', SUM(total_fees),
            'by_type', jsonb_object_agg(payment_type, jsonb_build_object(
                'count', tx_count,
                'volume', total_amount,
                'fees', total_fees
            ))
        )
    FROM daily_txs
$$;

-- Initialize with compliance admin user
-- This depends on auth.users table existing
INSERT INTO public.user_profiles (id, first_name, last_name, country_code, kyc_level, kyc_verified, is_admin, is_active)
SELECT 
    id, 
    'Compliance', 
    'Officer',
    'KE',
    3,
    true,
    true,
    true
FROM auth.users
WHERE email = 'admin@seamount.io'
ON CONFLICT (id) 
DO UPDATE SET
    is_admin = true,
    kyc_level = 3,
    kyc_verified = true;

-- If using this script directly, uncomment this to grant necessary permissions:
-- GRANT USAGE, SELECT ON SEQUENCE public.regulatory_reports_id_seq TO anon, authenticated;
-- GRANT ALL ON TABLE public.audit_logs TO anon, authenticated;
-- GRANT ALL ON TABLE public.monitoring_alerts TO anon, authenticated;
-- GRANT ALL ON TABLE public.regulatory_reports TO anon, authenticated;