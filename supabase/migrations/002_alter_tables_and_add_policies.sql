-- ========= SEAMOUNT SCHEMA MODIFICATION SCRIPT V1.1 =========
-- This script safely alters existing tables and adds necessary security.
-- It is designed to be run multiple times without causing errors.

-- 1. Alter the existing 'wallet_balances' table to add required columns.
-- We use 'ADD COLUMN IF NOT EXISTS' to prevent errors on re-runs.
ALTER TABLE public.wallet_balances
ADD COLUMN IF NOT EXISTS algorand_private_key TEXT, -- Will be encrypted by the app
ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN public.wallet_balances.algorand_private_key IS 'Stores the application-encrypted Algorand private key.';
COMMENT ON COLUMN public.wallet_balances.is_demo IS 'Flags if the wallet is for demonstration purposes only.';

-- 2. Enable Row Level Security (RLS) on the 'wallet_balances' table.
-- This is a critical security step to ensure users can only access their own data.
ALTER TABLE public.wallet_balances ENABLE ROW LEVEL SECURITY;

-- 3. Create RLS Policies for 'wallet_balances'.
-- These policies enforce the security rules.
-- Drop policies first if they exist to apply updated definitions.
DROP POLICY IF EXISTS "Users can view their own wallet balance" ON public.wallet_balances;
CREATE POLICY "Users can view their own wallet balance"
    ON public.wallet_balances FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own wallet balance" ON public.wallet_balances;
CREATE POLICY "Users can insert their own wallet balance"
    ON public.wallet_balances FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own wallet balance" ON public.wallet_balances;
CREATE POLICY "Users can update their own wallet balance"
    ON public.wallet_balances FOR UPDATE
    USING (auth.uid() = user_id);

-- 4. Create the 'business_leads' table for the landing page contact form.
CREATE TABLE IF NOT EXISTS public.business_leads (
    id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    business_name TEXT,
    email TEXT NOT NULL,
    message TEXT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE public.business_leads IS 'Captures inbound leads from the public-facing business contact form.';

-- 5. Add KYC-related columns to the 'user_profiles' table.
-- Supabase Auth creates user_profiles; we are just extending it.
ALTER TABLE public.user_profiles
ADD COLUMN IF NOT EXISTS complycube_applicant_id TEXT,
ADD COLUMN IF NOT EXISTS kyc_status TEXT NOT NULL DEFAULT 'unverified',
ADD COLUMN IF NOT EXISTS kyc_level INT NOT NULL DEFAULT 0;

-- 6. Grant permissions to roles.
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON TABLE public.wallet_balances TO authenticated;
GRANT ALL ON TABLE public.business_leads TO anon, authenticated;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;

-- ========= END OF SCRIPT =========