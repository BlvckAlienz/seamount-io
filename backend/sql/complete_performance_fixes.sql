-- Fix Issue 1: compliance_logs RLS policy
DROP POLICY IF EXISTS "Service role can access compliance logs" ON public.compliance_logs;
CREATE POLICY "Service role can access compliance logs" ON public.compliance_logs
  FOR ALL USING ((SELECT auth.role()) = 'service_role');

-- Fix Issue 2: kyc_verifications update policy
DROP POLICY IF EXISTS "Users can update own KYC records" ON public.kyc_verifications;
CREATE POLICY "Users can update own KYC records" ON public.kyc_verifications
  FOR UPDATE USING ((SELECT auth.uid()) = user_id);

-- Fix Issue 3: kyc_verifications insert policy
DROP POLICY IF EXISTS "Users can insert own KYC records" ON public.kyc_verifications;
CREATE POLICY "Users can insert own KYC records" ON public.kyc_verifications
  FOR INSERT WITH CHECK ((SELECT auth.uid()) = user_id);

-- Fix Issue 4: kyc_verifications select policy
DROP POLICY IF EXISTS "Users can view own KYC records" ON public.kyc_verifications;
CREATE POLICY "Users can view own KYC records" ON public.kyc_verifications
  FOR SELECT USING ((SELECT auth.uid()) = user_id);

-- Fix Issue 5: Function with mutable search_path
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;