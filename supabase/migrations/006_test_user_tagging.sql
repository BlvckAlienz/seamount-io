-- FILE: supabase/migrations/006_test_user_tagging.sql
-- Tags all future transactions from known test accounts as is_test=true automatically.
-- Test user: yungpharoah@gmail.com / 72844868-7efc-406b-b12f-57c4ff0793aa

-- ── STEP 1: Tag existing test user's historical records ───────

UPDATE public.onramp_transactions
SET is_test = true
WHERE user_id = '72844868-7efc-406b-b12f-57c4ff0793aa';

UPDATE public.blockchain_transactions
SET is_test = true
WHERE user_id = '72844868-7efc-406b-b12f-57c4ff0793aa';

UPDATE public.fees_owed
SET is_test = true
WHERE user_id = '72844868-7efc-406b-b12f-57c4ff0793aa';


-- ── STEP 2: Mark the test user's profile ─────────────────────
-- Add is_test flag to user_profiles so the trigger can check it

ALTER TABLE public.user_profiles
  ADD COLUMN IF NOT EXISTS is_test BOOLEAN DEFAULT false;

UPDATE public.user_profiles
SET is_test = true
WHERE user_id = '72844868-7efc-406b-b12f-57c4ff0793aa';


-- ── STEP 3: Trigger function ──────────────────────────────────
-- Fires on INSERT on any transaction table.
-- Checks if the inserting user_id is flagged as test in user_profiles.
-- If yes, sets is_test = true on the new row automatically.

CREATE OR REPLACE FUNCTION public.tag_test_transactions()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.user_profiles
    WHERE user_id = NEW.user_id
      AND is_test = true
  ) THEN
    NEW.is_test := true;
  END IF;
  RETURN NEW;
END;
$$;


-- ── STEP 4: Attach trigger to all 3 transaction tables ────────

-- onramp_transactions
DROP TRIGGER IF EXISTS tag_onramp_test ON public.onramp_transactions;
CREATE TRIGGER tag_onramp_test
  BEFORE INSERT ON public.onramp_transactions
  FOR EACH ROW EXECUTE FUNCTION public.tag_test_transactions();

-- blockchain_transactions
DROP TRIGGER IF EXISTS tag_blockchain_test ON public.blockchain_transactions;
CREATE TRIGGER tag_blockchain_test
  BEFORE INSERT ON public.blockchain_transactions
  FOR EACH ROW EXECUTE FUNCTION public.tag_test_transactions();

-- fees_owed
DROP TRIGGER IF EXISTS tag_fees_test ON public.fees_owed;
CREATE TRIGGER tag_fees_test
  BEFORE INSERT ON public.fees_owed
  FOR EACH ROW EXECUTE FUNCTION public.tag_test_transactions();


-- ── STEP 5: Verify ────────────────────────────────────────────
-- Run this after to confirm everything is tagged correctly.

SELECT 'onramp_transactions' AS tbl,
       COUNT(*) FILTER (WHERE is_test = true)  AS test_rows,
       COUNT(*) FILTER (WHERE is_test = false) AS real_rows,
       COUNT(*) FILTER (WHERE is_test IS NULL) AS untagged_rows
FROM public.onramp_transactions

UNION ALL

SELECT 'blockchain_transactions',
       COUNT(*) FILTER (WHERE is_test = true),
       COUNT(*) FILTER (WHERE is_test = false),
       COUNT(*) FILTER (WHERE is_test IS NULL)
FROM public.blockchain_transactions

UNION ALL

SELECT 'fees_owed',
       COUNT(*) FILTER (WHERE is_test = true),
       COUNT(*) FILTER (WHERE is_test = false),
       COUNT(*) FILTER (WHERE is_test IS NULL)
FROM public.fees_owed;