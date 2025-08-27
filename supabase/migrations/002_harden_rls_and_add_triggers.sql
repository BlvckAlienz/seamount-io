-- ========= SEAMOUNT SCHEMA FIX & ENHANCEMENT SCRIPT V1.2 =========
-- This script hardens security based on Supabase advisor feedback.
-- It is idempotent and can be safely run multiple times.

-- 1. CREATE the 'handle_updated_at' function with a fixed search_path.
-- This function will automatically update the 'updated_at' column on any table it's attached to.
-- Incorporates the security fix for a mutable search_path from the start.
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
-- Set a fixed search path for security and predictability.
SET search_path = public;

COMMENT ON FUNCTION public.handle_updated_at() IS 'Trigger function to automatically update updated_at timestamps.';


-- 2. APPLY the trigger to tables that have an 'updated_at' column.
-- Drop trigger first to ensure the latest function version is used.
DROP TRIGGER IF EXISTS on_user_profiles_update ON public.user_profiles;
CREATE TRIGGER on_user_profiles_update
BEFORE UPDATE ON public.user_profiles
FOR EACH ROW
EXECUTE FUNCTION public.handle_updated_at();

-- The wallet_balances table has 'last_updated', so we'll create a separate trigger for it.
-- First, let's create a function to handle 'last_updated' specifically.
CREATE OR REPLACE FUNCTION public.handle_last_updated()
RETURNS TRIGGER AS $$
BEGIN
  NEW.last_updated = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public;

COMMENT ON FUNCTION public.handle_last_updated() IS 'Trigger function to automatically update last_updated timestamps.';

DROP TRIGGER IF EXISTS on_wallet_balances_update ON public.wallet_balances;
CREATE TRIGGER on_wallet_balances_update
BEFORE UPDATE ON public.wallet_balances
FOR EACH ROW
EXECUTE FUNCTION public.handle_last_updated();


-- 3. ENABLE Row Level Security (RLS) on the 'business_leads' table.
-- This is the primary fix for the first advisor warning.
ALTER TABLE public.business_leads ENABLE ROW LEVEL SECURITY;


-- 4. CREATE a specific, secure policy for the 'business_leads' table.
-- We only want to allow anonymous users to INSERT new leads. All other actions should be blocked.
-- Drop policy first to ensure it can be re-run.
DROP POLICY IF EXISTS "Allow anonymous inserts for new business leads" ON public.business_leads;
CREATE POLICY "Allow anonymous inserts for new business leads"
    ON public.business_leads
    FOR INSERT
    TO anon -- The role for anonymous users
    WITH CHECK (true); -- The check is always true, allowing the insert.

COMMENT ON POLICY "Allow anonymous inserts for new business leads" ON public.business_leads IS 'Permits public users to submit the contact form, but denies read/update/delete access.';

-- By default, once RLS is enabled, all actions are DENIED unless a policy explicitly allows them.
-- Therefore, we do not need to create policies for SELECT, UPDATE, or DELETE, as we want to block them for anonymous users.


-- ========= END OF SCRIPT =========