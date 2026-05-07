-- ================================================================
-- FILE: backend/migrations/002_aml_pipeline.sql
-- Idempotent: safe to re-run on any state of the DB.
-- Fix: uses CREATE TABLE with minimal schema then
--      ALTER TABLE ADD COLUMN IF NOT EXISTS for all columns,
--      so it works on both fresh installs and pre-existing tables.
-- ================================================================

-- ── 1. aml_fraud_patterns — add tier/modality columns ───────────
ALTER TABLE public.aml_fraud_patterns
  ADD COLUMN IF NOT EXISTS tier SMALLINT DEFAULT 2,
  ADD COLUMN IF NOT EXISTS modality TEXT DEFAULT 'behavioral',
  ADD COLUMN IF NOT EXISTS scoring_weight REAL DEFAULT 0.5,
  ADD COLUMN IF NOT EXISTS excluded_from_scoring BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_afp_scoring
  ON public.aml_fraud_patterns(tier, excluded_from_scoring)
  WHERE excluded_from_scoring = FALSE;

-- ── 2. ofac_sanctions — entity name lookup (fuzzy match) ────────
CREATE TABLE IF NOT EXISTS public.ofac_sanctions (
  id          BIGSERIAL   PRIMARY KEY,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE public.ofac_sanctions
  ADD COLUMN IF NOT EXISTS pattern_id   TEXT UNIQUE,
  ADD COLUMN IF NOT EXISTS sdn_id       TEXT,
  ADD COLUMN IF NOT EXISTS entity_name  TEXT NOT NULL DEFAULT 'UNKNOWN',
  ADD COLUMN IF NOT EXISTS entity_type  TEXT,
  ADD COLUMN IF NOT EXISTS program      TEXT,
  ADD COLUMN IF NOT EXISTS remarks      TEXT,
  ADD COLUMN IF NOT EXISTS aliases      TEXT[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS source       TEXT DEFAULT 'ofac_sdn';

CREATE INDEX IF NOT EXISTS idx_ofac_name
  ON public.ofac_sanctions(entity_name);

ALTER TABLE public.ofac_sanctions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "ofac_service" ON public.ofac_sanctions;
CREATE POLICY "ofac_service" ON public.ofac_sanctions
  FOR ALL USING (auth.role() = 'service_role');
DROP POLICY IF EXISTS "ofac_admin_read" ON public.ofac_sanctions;
CREATE POLICY "ofac_admin_read" ON public.ofac_sanctions
  FOR SELECT USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );

-- ── 3. aml_risk_scores ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.aml_risk_scores (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE public.aml_risk_scores
  ADD COLUMN IF NOT EXISTS tx_id                 TEXT,
  ADD COLUMN IF NOT EXISTS user_id               TEXT,
  ADD COLUMN IF NOT EXISTS recipient_address     TEXT,
  ADD COLUMN IF NOT EXISTS combined_score        REAL    DEFAULT 0.0,
  ADD COLUMN IF NOT EXISTS band                  TEXT    DEFAULT 'GREEN',
  ADD COLUMN IF NOT EXISTS factors               JSONB   DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS matched_pattern_id    TEXT,
  ADD COLUMN IF NOT EXISTS matched_pattern_label TEXT,
  ADD COLUMN IF NOT EXISTS pattern_similarity    REAL,
  ADD COLUMN IF NOT EXISTS ofac_match            BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS ofac_matched_name     TEXT,
  ADD COLUMN IF NOT EXISTS str_explanation       TEXT,
  ADD COLUMN IF NOT EXISTS evidence_bundle       JSONB,
  ADD COLUMN IF NOT EXISTS status                TEXT    DEFAULT 'open',
  ADD COLUMN IF NOT EXISTS reviewed_by           TEXT,
  ADD COLUMN IF NOT EXISTS reviewed_at           TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS review_note           TEXT,
  ADD COLUMN IF NOT EXISTS scoring_version       TEXT    DEFAULT '1.0.0';

-- Add CHECK constraints safely (ignore if already exists)
DO $$ BEGIN
  ALTER TABLE public.aml_risk_scores
    ADD CONSTRAINT chk_aml_band
    CHECK (band IN ('GREEN','AMBER','RED'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE public.aml_risk_scores
    ADD CONSTRAINT chk_aml_status
    CHECK (status IN ('open','confirmed_fraud','dismissed','escalated'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE public.aml_risk_scores
    ADD CONSTRAINT chk_aml_score
    CHECK (combined_score BETWEEN 0.0 AND 1.0);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_aml_risk_tx_id
  ON public.aml_risk_scores(tx_id);
CREATE INDEX IF NOT EXISTS idx_aml_risk_band_created
  ON public.aml_risk_scores(band, created_at DESC)
  WHERE band IN ('RED','AMBER');
CREATE INDEX IF NOT EXISTS idx_aml_risk_status
  ON public.aml_risk_scores(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aml_risk_recipient
  ON public.aml_risk_scores(recipient_address)
  WHERE recipient_address IS NOT NULL;

-- updated_at trigger
CREATE OR REPLACE FUNCTION public.fn_aml_set_updated()
  RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = public, pg_catalog AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

DROP TRIGGER IF EXISTS trg_aml_updated ON public.aml_risk_scores;
CREATE TRIGGER trg_aml_updated
  BEFORE UPDATE ON public.aml_risk_scores
  FOR EACH ROW EXECUTE FUNCTION public.fn_aml_set_updated();

ALTER TABLE public.aml_risk_scores ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "aml_scores_service" ON public.aml_risk_scores;
CREATE POLICY "aml_scores_service" ON public.aml_risk_scores
  FOR ALL USING (auth.role() = 'service_role');
DROP POLICY IF EXISTS "aml_scores_admin_read" ON public.aml_risk_scores;
CREATE POLICY "aml_scores_admin_read" ON public.aml_risk_scores
  FOR SELECT USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );
DROP POLICY IF EXISTS "aml_scores_admin_update" ON public.aml_risk_scores;
CREATE POLICY "aml_scores_admin_update" ON public.aml_risk_scores
  FOR UPDATE USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );

-- ── 4. aml_audit_log ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.aml_audit_log (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE public.aml_audit_log
  ADD COLUMN IF NOT EXISTS alert_id        UUID,
  ADD COLUMN IF NOT EXISTS tx_id           TEXT,
  ADD COLUMN IF NOT EXISTS action          TEXT,
  ADD COLUMN IF NOT EXISTS actor_id        TEXT,
  ADD COLUMN IF NOT EXISTS actor_email     TEXT,
  ADD COLUMN IF NOT EXISTS previous_status TEXT,
  ADD COLUMN IF NOT EXISTS new_status      TEXT,
  ADD COLUMN IF NOT EXISTS note            TEXT,
  ADD COLUMN IF NOT EXISTS metadata        JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_aml_audit_alert
  ON public.aml_audit_log(alert_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aml_audit_tx
  ON public.aml_audit_log(tx_id, created_at DESC);

ALTER TABLE public.aml_audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "aml_audit_service" ON public.aml_audit_log;
CREATE POLICY "aml_audit_service" ON public.aml_audit_log
  FOR ALL USING (auth.role() = 'service_role');
DROP POLICY IF EXISTS "aml_audit_admin" ON public.aml_audit_log;
CREATE POLICY "aml_audit_admin" ON public.aml_audit_log
  FOR SELECT USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );

-- ── 5. user_tx_baselines — velocity anomaly baseline ────────────
CREATE TABLE IF NOT EXISTS public.user_tx_baselines (
  user_id    TEXT        PRIMARY KEY,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
ALTER TABLE public.user_tx_baselines
  ADD COLUMN IF NOT EXISTS avg_hourly_txns      REAL  DEFAULT 2.0,
  ADD COLUMN IF NOT EXISTS avg_tx_amount_usd    REAL  DEFAULT 100.0,
  ADD COLUMN IF NOT EXISTS typical_hours        INT[] DEFAULT '{9,10,11,12,13,14,15,16,17,18,19,20}',
  ADD COLUMN IF NOT EXISTS baseline_sample_count INT  DEFAULT 0;

ALTER TABLE public.user_tx_baselines ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "baselines_service" ON public.user_tx_baselines;
CREATE POLICY "baselines_service" ON public.user_tx_baselines
  FOR ALL USING (auth.role() = 'service_role');

-- ── 6. Verify ───────────────────────────────────────────────────
DO $$ BEGIN
  ASSERT (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema='public' AND table_name='aml_risk_scores'
    AND column_name='tx_id') = 1, 'tx_id missing';
  ASSERT (SELECT COUNT(*) FROM information_schema.columns
    WHERE table_schema='public' AND table_name='aml_fraud_patterns'
    AND column_name='tier') = 1, 'tier missing';
  RAISE NOTICE '✅ Migration 002 verified OK';
END $$;