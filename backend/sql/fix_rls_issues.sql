-- Fix RLS issues for production tables
-- Run this in your Supabase SQL editor

-- Enable RLS on missing tables
ALTER TABLE backing_reserves ENABLE ROW LEVEL SECURITY;
ALTER TABLE exchange_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_logs ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for backing_reserves (admin only)
CREATE POLICY backing_reserves_admin_policy ON backing_reserves 
    FOR ALL 
    USING (auth.jwt() ->> 'role' = 'admin');

-- Create RLS policies for exchange_rates (read-only for users)
CREATE POLICY exchange_rates_read_policy ON exchange_rates 
    FOR SELECT 
    TO authenticated
    USING (true);

-- Create RLS policies for compliance_logs (admin only)
CREATE POLICY compliance_logs_admin_policy ON compliance_logs 
    FOR ALL 
    USING (auth.jwt() ->> 'role' = 'admin');

-- Fix search_path issue
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc', now());
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

SELECT 'RLS issues fixed successfully!' as message;