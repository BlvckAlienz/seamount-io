-- FILE: supabase/migrations/005_merchant_approval_status.sql

-- Add approval status to merchants
ALTER TABLE public.p2p_merchants
  ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'rejected'));

-- Set existing merchants to approved so current data isn't broken
UPDATE public.p2p_merchants SET status = 'approved' WHERE status = 'pending';

-- Admin approval log
CREATE TABLE IF NOT EXISTS public.p2p_merchant_reviews (
  id           UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  merchant_id  UUID REFERENCES public.p2p_merchants(id) ON DELETE CASCADE,
  admin_id     UUID REFERENCES auth.users(id),
  action       TEXT NOT NULL CHECK (action IN ('approved', 'rejected')),
  note         TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.p2p_merchant_reviews ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins manage merchant reviews"
  ON public.p2p_merchant_reviews FOR ALL
  USING ((auth.jwt() ->> 'role') = 'admin');