-- FILE: supabase/migrations/001_p2p_liquidity_schema.sql

-- ============================================================
-- MERCHANTS
-- ============================================================
CREATE TABLE public.p2p_merchants (
  id                    UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id               UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name          TEXT NOT NULL,
  verified              BOOLEAN DEFAULT false,
  total_orders          INTEGER DEFAULT 0,
  completion_rate       NUMERIC(5,2) DEFAULT 100.00,
  avg_release_time_mins INTEGER DEFAULT 15,
  is_online             BOOLEAN DEFAULT false,
  created_at            TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.p2p_merchants ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Merchants publicly viewable"
  ON public.p2p_merchants FOR SELECT USING (true);
CREATE POLICY "Users manage own merchant profile"
  ON public.p2p_merchants FOR ALL USING (auth.uid() = user_id);

-- ============================================================
-- LISTINGS (what merchants offer)
-- ============================================================
CREATE TABLE public.p2p_listings (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  merchant_id       UUID REFERENCES public.p2p_merchants(id) ON DELETE CASCADE,
  token             TEXT NOT NULL CHECK (token IN ('USDT','USDC')),
  fiat_currency     TEXT NOT NULL,           -- KES, NGN, GHS, GBP, USD, etc.
  price_per_token   NUMERIC(18,6) NOT NULL,  -- e.g. 130.50 KES per USDT
  min_order_fiat    NUMERIC(18,2) NOT NULL,
  max_order_fiat    NUMERIC(18,2) NOT NULL,
  available_amount  NUMERIC(18,6) NOT NULL,  -- tokens merchant has ready
  payment_methods   JSONB NOT NULL,          -- ["M-Pesa","Equity Bank","Airtel Money"]
  payment_details   JSONB NOT NULL,          -- NEVER exposed until order is created
  terms             TEXT,
  is_active         BOOLEAN DEFAULT true,
  created_at        TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.p2p_listings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Active listings publicly viewable"
  ON public.p2p_listings FOR SELECT USING (is_active = true);
CREATE POLICY "Merchant manages own listings"
  ON public.p2p_listings FOR ALL USING (
    merchant_id IN (
      SELECT id FROM public.p2p_merchants WHERE user_id = auth.uid()
    )
  );

-- ============================================================
-- ORDERS
-- idempotency_key: client sends a unique key per order attempt.
-- If the same key arrives twice, we return the existing order —
-- no duplicate payments, ever.
-- ============================================================
CREATE TABLE public.p2p_orders (
  id                  UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  idempotency_key     TEXT UNIQUE NOT NULL,
  order_number        TEXT UNIQUE NOT NULL,
  listing_id          UUID REFERENCES public.p2p_listings(id),
  buyer_id            UUID REFERENCES auth.users(id),
  merchant_id         UUID REFERENCES public.p2p_merchants(id),
  token               TEXT NOT NULL CHECK (token IN ('USDT','USDC')),
  fiat_currency       TEXT NOT NULL,
  fiat_amount         NUMERIC(18,2) NOT NULL,
  token_amount        NUMERIC(18,6) NOT NULL,
  price_per_token     NUMERIC(18,6) NOT NULL,
  payment_method      TEXT NOT NULL,
  status              TEXT NOT NULL DEFAULT 'pending' CHECK (
    status IN (
      'pending',         -- order just created
      'payment_window',  -- 15-min timer running, payment details visible
      'paid',            -- buyer uploaded receipt
      'confirming',      -- merchant reviewing receipt
      'completed',       -- merchant released tokens
      'cancelled',       -- timer expired or user cancelled
      'disputed'         -- escalated to admin
    )
  ),
  payment_deadline    TIMESTAMPTZ,           -- when the 15-min window closes
  payment_receipt_url TEXT,                  -- receipt image uploaded by buyer
  release_tx_hash     TEXT,                  -- on-chain tx when tokens released
  platform_fee_bps    INTEGER DEFAULT 30,    -- 0.30% fee
  created_at          TIMESTAMPTZ DEFAULT now(),
  updated_at          TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.p2p_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Buyers see own orders"
  ON public.p2p_orders FOR SELECT USING (buyer_id = auth.uid());
CREATE POLICY "Merchants see their orders"
  ON public.p2p_orders FOR SELECT USING (
    merchant_id IN (
      SELECT id FROM public.p2p_merchants WHERE user_id = auth.uid()
    )
  );
CREATE POLICY "Buyers create orders"
  ON public.p2p_orders FOR INSERT WITH CHECK (buyer_id = auth.uid());
CREATE POLICY "Parties update orders"
  ON public.p2p_orders FOR UPDATE USING (
    buyer_id = auth.uid() OR
    merchant_id IN (
      SELECT id FROM public.p2p_merchants WHERE user_id = auth.uid()
    )
  );

-- ============================================================
-- ORDER MESSAGES (in-order P2P chat)
-- ============================================================
CREATE TABLE public.p2p_messages (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  order_id   UUID REFERENCES public.p2p_orders(id) ON DELETE CASCADE,
  sender_id  UUID REFERENCES auth.users(id),
  message    TEXT,
  is_system  BOOLEAN DEFAULT false,          -- platform-generated messages
  created_at TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.p2p_messages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Order parties see messages"
  ON public.p2p_messages FOR SELECT USING (
    order_id IN (
      SELECT id FROM public.p2p_orders
      WHERE buyer_id = auth.uid()
      OR merchant_id IN (
        SELECT id FROM public.p2p_merchants WHERE user_id = auth.uid()
      )
    )
  );
CREATE POLICY "Order parties send messages"
  ON public.p2p_messages FOR INSERT WITH CHECK (
    sender_id = auth.uid() AND
    order_id IN (
      SELECT id FROM public.p2p_orders
      WHERE buyer_id = auth.uid()
      OR merchant_id IN (
        SELECT id FROM public.p2p_merchants WHERE user_id = auth.uid()
      )
    )
  );

-- ============================================================
-- SETTLEMENT AUDIT LOG (immutable — every state change recorded)
-- This is your reconciliation backbone. Every event is logged here.
-- ============================================================
CREATE TABLE public.settlement_audit_log (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  order_id    UUID REFERENCES public.p2p_orders(id),
  event_type  TEXT NOT NULL,   -- state_change | fee_captured | tx_broadcast
  prev_status TEXT,
  new_status  TEXT,
  tx_hash     TEXT,
  actor_id    UUID,            -- who triggered this event
  metadata    JSONB,
  created_at  TIMESTAMPTZ DEFAULT now()
);
ALTER TABLE public.settlement_audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins read audit log"
  ON public.settlement_audit_log FOR SELECT USING (
    (auth.jwt() ->> 'role') = 'admin'
  );

-- ============================================================
-- HELPERS
-- ============================================================
CREATE OR REPLACE FUNCTION public.increment_merchant_orders(p_merchant_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
  UPDATE public.p2p_merchants
  SET total_orders = total_orders + 1
  WHERE id = p_merchant_id;
END;
$$;