-- Seamount.io Database Schema - KYC & Compliance Tables Only
-- File Location: database/schema_additions.sql
-- Run this in Supabase SQL Editor

-- Create KYC verifications table
CREATE TABLE IF NOT EXISTS kyc_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    document_type TEXT NOT NULL,
    document_number TEXT NOT NULL,
    document_file_url TEXT,
    selfie_file_url TEXT,
    address TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    country TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'reviewing')),
    rejection_reason TEXT,
    verified_at TIMESTAMP WITH TIME ZONE,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_kyc_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE
);

-- Create compliance logs table
CREATE TABLE IF NOT EXISTS compliance_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    transaction_id UUID,
    event_type TEXT NOT NULL,
    event_data JSONB NOT NULL,
    risk_score INTEGER DEFAULT 0,
    flagged BOOLEAN DEFAULT false,
    status TEXT NOT NULL DEFAULT 'logged' CHECK (status IN ('logged', 'reviewed', 'cleared', 'escalated')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_compliance_user FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_kyc_user_id ON kyc_verifications(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_status ON kyc_verifications(status);
CREATE INDEX IF NOT EXISTS idx_compliance_user_id ON compliance_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_compliance_flagged ON compliance_logs(flagged);
CREATE INDEX IF NOT EXISTS idx_compliance_created ON compliance_logs(created_at);

-- Enable RLS (Row Level Security)
ALTER TABLE kyc_verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for KYC verifications
CREATE POLICY "Users can view own KYC records" ON kyc_verifications
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own KYC records" ON kyc_verifications
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own KYC records" ON kyc_verifications
    FOR UPDATE USING (auth.uid() = user_id);

-- RLS Policies for compliance logs (admin only)
CREATE POLICY "Service role can access compliance logs" ON compliance_logs
    FOR ALL USING (auth.role() = 'service_role');

-- Create updated_at trigger function if not exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers
CREATE TRIGGER update_kyc_verifications_updated_at
    BEFORE UPDATE ON kyc_verifications
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();