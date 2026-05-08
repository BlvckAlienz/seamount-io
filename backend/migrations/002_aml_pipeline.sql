-- ── Step 1: Drop legacy tables (SAFE — both are empty) ────────────────────
DROP TABLE IF EXISTS public.aml_audit_log    CASCADE;
DROP TABLE IF EXISTS public.aml_risk_scores  CASCADE;

-- ── Step 2: Recreate aml_risk_scores with the correct schema ───────────────
CREATE TABLE public.aml_risk_scores (
  id                    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  tx_id                 TEXT        NOT NULL,
  user_id               TEXT,
  recipient_address     TEXT,
  combined_score        REAL        NOT NULL CHECK (combined_score BETWEEN 0 AND 1),
  band                  TEXT        NOT NULL CHECK (band IN ('GREEN','AMBER','RED')),
  factors               JSONB       NOT NULL DEFAULT '{}',
  matched_pattern_id    TEXT,
  matched_pattern_label TEXT,
  pattern_similarity    REAL,
  ofac_match            BOOLEAN     NOT NULL DEFAULT FALSE,
  ofac_matched_name     TEXT,
  str_explanation       TEXT,
  evidence_bundle       JSONB,
  status                TEXT        NOT NULL DEFAULT 'open'
                          CHECK (status IN ('open','confirmed_fraud','dismissed','escalated')),
  reviewed_by           TEXT,
  reviewed_at           TIMESTAMPTZ,
  review_note           TEXT,
  scoring_version       TEXT        DEFAULT '1.0.0',
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_aml_risk_tx_id
  ON public.aml_risk_scores(tx_id);

CREATE INDEX idx_aml_risk_band_open
  ON public.aml_risk_scores(band, created_at DESC)
  WHERE band IN ('RED','AMBER');

CREATE INDEX idx_aml_risk_status
  ON public.aml_risk_scores(status, created_at DESC);

CREATE INDEX idx_aml_risk_recipient
  ON public.aml_risk_scores(recipient_address)
  WHERE recipient_address IS NOT NULL;

-- updated_at trigger
CREATE OR REPLACE FUNCTION public.fn_aml_set_updated()
  RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
  SET search_path = public, pg_catalog AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

CREATE TRIGGER trg_aml_updated
  BEFORE UPDATE ON public.aml_risk_scores
  FOR EACH ROW EXECUTE FUNCTION public.fn_aml_set_updated();

ALTER TABLE public.aml_risk_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY "aml_scores_service" ON public.aml_risk_scores
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

-- ── Step 3: Recreate aml_audit_log ─────────────────────────────────────────
CREATE TABLE public.aml_audit_log (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id        UUID        REFERENCES public.aml_risk_scores(id) ON DELETE SET NULL,
  tx_id           TEXT,
  action          TEXT        NOT NULL,
  actor_id        TEXT,
  actor_email     TEXT,
  previous_status TEXT,
  new_status      TEXT,
  note            TEXT,
  metadata        JSONB       DEFAULT '{}',
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_aml_audit_alert
  ON public.aml_audit_log(alert_id, created_at DESC);

ALTER TABLE public.aml_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "aml_audit_service" ON public.aml_audit_log
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "aml_audit_admin" ON public.aml_audit_log
  FOR SELECT USING (
    auth.role() = 'authenticated' AND
    EXISTS (SELECT 1 FROM public.user_profiles
            WHERE user_id = auth.uid() AND is_admin = TRUE)
  );

-- ── Step 4: Fix pattern cache (199 → 2600+ patterns) ──────────────────────
UPDATE public.aml_fraud_patterns
SET excluded_from_scoring = FALSE
WHERE source IN ('manual_typology', 'nigeria', 'kenya')
  AND (excluded_from_scoring IS NULL OR excluded_from_scoring = FALSE);

-- ── Step 5: Verify ─────────────────────────────────────────────────────────
SELECT table_name, COUNT(*) as col_count
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name IN ('aml_risk_scores', 'aml_audit_log')
GROUP BY table_name;

SELECT source, tier, excluded_from_scoring, COUNT(*)
FROM public.aml_fraud_patterns
GROUP BY source, tier, excluded_from_scoring
ORDER BY tier;