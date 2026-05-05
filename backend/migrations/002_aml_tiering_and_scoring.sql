-- ============================================================
-- FILE: backend/migrations/002_aml_tiering_and_scoring.sql
-- Run in Supabase SQL editor BEFORE backfill script.
-- Idempotent: all statements use IF NOT EXISTS / IF EXISTS.
-- ============================================================

-- ── 1. Remediate aml_fraud_patterns ─────────────────────────
ALTER TABLE public.aml_fraud_patterns
  ADD COLUMN IF NOT EXISTS tier
    SMALLINT NOT NULL DEFAULT 2
    CHECK (tier IN (1, 2, 3)),
  ADD COLUMN IF NOT EXISTS modality
    TEXT NOT NULL DEFAULT 'behavioral'
    CHECK (modality IN ('behavioral','document','entity_name','url')),
  ADD COLUMN IF NOT EXISTS scoring_weight
    REAL NOT NULL DEFAULT 0.5
    CHECK (scoring_weight BETWEEN 0.0 AND 1.0),
  ADD COLUMN IF NOT EXISTS excluded_from_scoring
    BOOLEAN NOT NULL DEFAULT FALSE;

-- Index for fast pattern cache loading
CREATE INDEX IF NOT EXISTS idx_afp_tier_active
  ON public.aml_fraud_patterns(tier, excluded_from_scoring)
  WHERE excluded_from_scoring = FALSE;

-- ── 2. OFAC Sanctions lookup (entity names, fuzzy matching) ──
CREATE TABLE IF NOT EXISTS public.ofac_sanctions (
  id           BIGSERIAL     PRIMARY KEY,
  pattern_id   TEXT          UNIQUE,          -- FK to aml_fraud_patterns for dedup
  sdn_id       TEXT,
  entity_name  TEXT          NOT NULL,
  entity_type  TEXT,
  program      TEXT,
  remarks      TEXT,
  aliases      TEXT[]        DEFAULT '{}',
  source       TEXT          NOT NULL DEFAULT 'ofac_sdn',
  created_at   TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ofac_name_trgm
  ON public.ofac_sanctions(entity_name);

ALTER TABLE public.ofac_sanctions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ofac_service_all" ON public.ofac_sanctions
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "ofac_admin_read" ON public.ofac_sanctions
  FOR SELECT USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );

-- ── 3. AML Risk Scores ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.aml_risk_scores (
  id                    UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  tx_id                 TEXT          NOT NULL,
  user_id               UUID          NOT NULL,
  recipient_address     TEXT,                      -- indexed for counterparty lookup
  combined_score        REAL          NOT NULL CHECK (combined_score BETWEEN 0.0 AND 1.0),
  band                  TEXT          NOT NULL CHECK (band IN ('GREEN','AMBER','RED')),
  factors               JSONB         NOT NULL DEFAULT '{}',
  matched_pattern_id    TEXT,
  matched_pattern_label TEXT,
  pattern_similarity    REAL,
  ofac_match            BOOLEAN       NOT NULL DEFAULT FALSE,
  ofac_matched_name     TEXT,
  str_explanation       TEXT,
  evidence_bundle       JSONB,
  status                TEXT          NOT NULL DEFAULT 'open'
                          CHECK (status IN ('open','confirmed_fraud','dismissed','escalated')),
  reviewed_by           UUID,
  reviewed_at           TIMESTAMPTZ,
  review_note           TEXT,
  scoring_version       TEXT          DEFAULT '1.0.0',
  created_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- One score per transaction (idempotent upsert target)
CREATE UNIQUE INDEX IF NOT EXISTS idx_aml_risk_tx_id
  ON public.aml_risk_scores(tx_id);

-- Dashboard: recent non-GREEN alerts
CREATE INDEX IF NOT EXISTS idx_aml_risk_band_created
  ON public.aml_risk_scores(band, created_at DESC)
  WHERE band IN ('RED','AMBER');

-- Admin: filter by status
CREATE INDEX IF NOT EXISTS idx_aml_risk_status_created
  ON public.aml_risk_scores(status, created_at DESC);

-- Counterparty lookup
CREATE INDEX IF NOT EXISTS idx_aml_risk_recipient
  ON public.aml_risk_scores(recipient_address)
  WHERE recipient_address IS NOT NULL;

-- updated_at auto-trigger
CREATE OR REPLACE FUNCTION public.fn_set_updated_at()
  RETURNS TRIGGER
  LANGUAGE plpgsql
  SECURITY DEFINER
  SET search_path = public, pg_catalog
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_aml_risk_updated ON public.aml_risk_scores;
CREATE TRIGGER trg_aml_risk_updated
  BEFORE UPDATE ON public.aml_risk_scores
  FOR EACH ROW EXECUTE FUNCTION public.fn_set_updated_at();

ALTER TABLE public.aml_risk_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "aml_scores_service_all" ON public.aml_risk_scores
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "aml_scores_admin_read" ON public.aml_risk_scores
  FOR SELECT USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );

CREATE POLICY "aml_scores_admin_update" ON public.aml_risk_scores
  FOR UPDATE USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );

-- ── 4. AML Audit Log ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.aml_audit_log (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id        UUID        REFERENCES public.aml_risk_scores(id) ON DELETE SET NULL,
  tx_id           TEXT,
  action          TEXT        NOT NULL,
  actor_id        UUID,
  actor_email     TEXT,
  previous_status TEXT,
  new_status      TEXT,
  note            TEXT,
  metadata        JSONB       DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aml_audit_alert
  ON public.aml_audit_log(alert_id, created_at DESC);

ALTER TABLE public.aml_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "aml_audit_service_all" ON public.aml_audit_log
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "aml_audit_admin_read" ON public.aml_audit_log
  FOR SELECT USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );

-- ── 5. User Transaction Baselines (velocity anomaly) ─────────
CREATE TABLE IF NOT EXISTS public.user_tx_baselines (
  user_id               UUID        PRIMARY KEY,
  avg_hourly_txns       REAL        NOT NULL DEFAULT 1.0,
  avg_tx_amount_usd     REAL        NOT NULL DEFAULT 100.0,
  typical_hours         INT[]       DEFAULT '{8,9,10,11,12,13,14,15,16,17,18,19,20}',
  baseline_sample_count INT         NOT NULL DEFAULT 0,
  last_updated          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.user_tx_baselines ENABLE ROW LEVEL SECURITY;

CREATE POLICY "baselines_service_all" ON public.user_tx_baselines
  FOR ALL USING (auth.role() = 'service_role');

-- ── 6. Verify ────────────────────────────────────────────────
DO $$
BEGIN
  ASSERT (SELECT COUNT(*) FROM information_schema.columns
          WHERE table_schema = 'public'
            AND table_name = 'aml_fraud_patterns'
            AND column_name = 'tier') = 1,
    'Column tier not found on aml_fraud_patterns';

  ASSERT (SELECT COUNT(*) FROM information_schema.tables
          WHERE table_schema = 'public'
            AND table_name = 'aml_risk_scores') = 1,
    'Table aml_risk_scores not found';

  RAISE NOTICE '✅ Migration 002 verified successfully';
END $$;