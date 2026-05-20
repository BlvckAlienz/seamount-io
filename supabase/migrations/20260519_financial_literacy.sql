-- ============================================================
-- FILE: supabase/migrations/20260519_financial_literacy.sql
-- Seamount.io Financial Literacy System
-- Loops A (Quest), C (Wellbeing), D (Signal Guild)
-- Run in Supabase SQL Editor
-- ============================================================

-- ── HELPER: ensure search path ───────────────────────────────────────────────
SET search_path = public, pg_catalog;


-- ============================================================
-- LOOP A: FINANCE QUEST
-- ============================================================

CREATE TABLE IF NOT EXISTS public.quest_tracks (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            TEXT        UNIQUE NOT NULL,
    title           TEXT        NOT NULL,
    description     TEXT,
    difficulty      TEXT        NOT NULL CHECK (difficulty IN ('beginner','intermediate','advanced')),
    market_context  TEXT        DEFAULT 'NG,KE',    -- comma-separated country codes
    xp_reward       INTEGER     NOT NULL DEFAULT 500,
    order_index     INTEGER     NOT NULL DEFAULT 0,
    is_active       BOOLEAN     NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.quest_modules (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id        UUID        NOT NULL REFERENCES public.quest_tracks(id) ON DELETE CASCADE,
    title           TEXT        NOT NULL,
    content_json    JSONB       NOT NULL DEFAULT '{}',   -- lesson content, media refs
    order_index     INTEGER     NOT NULL DEFAULT 0,
    xp_reward       INTEGER     NOT NULL DEFAULT 100,
    is_active       BOOLEAN     NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.quest_questions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id       UUID        NOT NULL REFERENCES public.quest_modules(id) ON DELETE CASCADE,
    question        TEXT        NOT NULL,
    options_json    JSONB       NOT NULL DEFAULT '[]',   -- array of option strings
    correct_answer  INTEGER     NOT NULL,                -- index into options_json (0-based)
    explanation     TEXT,                                -- shown after answer
    difficulty      TEXT        NOT NULL DEFAULT 'beginner',
    xp_reward       INTEGER     NOT NULL DEFAULT 50,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.user_quest_progress (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    module_id       UUID        NOT NULL REFERENCES public.quest_modules(id) ON DELETE CASCADE,
    completed       BOOLEAN     NOT NULL DEFAULT false,
    score           INTEGER     DEFAULT 0,              -- correct answers count
    xp_earned       INTEGER     DEFAULT 0,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, module_id)
);

-- Immutable XP event log — source of truth for all XP
CREATE TABLE IF NOT EXISTS public.xp_ledger (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_type      TEXT        NOT NULL,               -- 'quest_complete','quiz_correct','signal_accurate','wellbeing_complete'
    xp_amount       INTEGER     NOT NULL,
    reference_id    UUID,                               -- quest/signal/etc id
    reference_type  TEXT,                               -- 'quest_module','guild_signal','wellbeing_score'
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Computed XP totals view (never query xp_ledger directly in app)
CREATE OR REPLACE VIEW public.user_xp_totals AS
    SELECT
        user_id,
        SUM(xp_amount) AS total_xp,
        COUNT(*)        AS total_events
    FROM public.xp_ledger
    GROUP BY user_id;


-- ============================================================
-- LOOP C: WELLBEING COACH
-- ============================================================

CREATE TABLE IF NOT EXISTS public.user_financial_profiles (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID        UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    country_code            TEXT        NOT NULL DEFAULT 'NG',
    income_range            TEXT,       -- '0-50k','50k-150k','150k-500k','500k+' (local currency)
    income_source           TEXT,       -- 'salary','business','freelance','remittance','mixed'
    debt_total              NUMERIC     DEFAULT 0,
    savings_rate            NUMERIC     DEFAULT 0,   -- percentage of income
    crypto_exposure_pct     NUMERIC     DEFAULT 0,   -- percentage of total assets
    mobile_money_balance    TEXT,       -- range, not exact amount
    remittance_monthly      NUMERIC     DEFAULT 0,   -- amount sent/received monthly
    susu_ajo_participation  BOOLEAN     DEFAULT false,
    chama_participation     BOOLEAN     DEFAULT false,
    goals_json              JSONB       DEFAULT '{}', -- {emergency_fund, house, retirement, education}
    updated_at              TIMESTAMPTZ DEFAULT now(),
    created_at              TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.wellbeing_scores (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    score           INTEGER     NOT NULL CHECK (score BETWEEN 0 AND 100),
    breakdown_json  JSONB       NOT NULL DEFAULT '{}',  -- {savings_health, debt_management, investment_readiness, financial_resilience}
    ai_summary      TEXT,
    top_action      TEXT,
    risk_flags      JSONB       DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.wellbeing_nudges (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    nudge_text      TEXT        NOT NULL,
    category        TEXT        NOT NULL DEFAULT 'general',  -- 'savings','debt','investing','crypto','tax'
    action_type     TEXT,       -- 'view_yield','check_balance','complete_quest','review_credit'
    action_data     JSONB       DEFAULT '{}',
    is_read         BOOLEAN     NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ DEFAULT now()
);


-- ============================================================
-- LOOP D: SIGNAL GUILD
-- ============================================================

CREATE TABLE IF NOT EXISTS public.guild_signals (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    asset_symbol        TEXT        NOT NULL,
    direction           TEXT        NOT NULL CHECK (direction IN ('BUY','SELL')),
    thesis              TEXT        NOT NULL,
    timeframe           TEXT        NOT NULL,           -- '1h','4h','1d','1w'
    entry_price         NUMERIC,
    target_price        NUMERIC,
    stop_loss           NUMERIC,
    status              TEXT        NOT NULL DEFAULT 'pending_review',
    -- QVAC validation output
    qvac_score          INTEGER     CHECK (qvac_score BETWEEN 0 AND 100),
    qvac_explanation    TEXT,
    qvac_recommendation TEXT,       -- STRONG_BUY|BUY|NEUTRAL|AVOID|SCAM_ALERT
    manipulation_flags  JSONB       DEFAULT '[]',
    -- Community stats (denormalised for performance)
    upvotes             INTEGER     DEFAULT 0,
    downvotes           INTEGER     DEFAULT 0,
    flag_count          INTEGER     DEFAULT 0,
    expires_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.guild_signal_votes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id   UUID        NOT NULL REFERENCES public.guild_signals(id) ON DELETE CASCADE,
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    vote_type   TEXT        NOT NULL CHECK (vote_type IN ('up','down','flag')),
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(signal_id, user_id)  -- one vote per user per signal
);

CREATE TABLE IF NOT EXISTS public.guild_reputation (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    total_signals       INTEGER     NOT NULL DEFAULT 0,
    accurate_signals    INTEGER     NOT NULL DEFAULT 0,  -- signals that hit target before stop
    accuracy_rate       NUMERIC     GENERATED ALWAYS AS (
                            CASE WHEN total_signals > 0
                            THEN ROUND((accurate_signals::NUMERIC / total_signals) * 100, 2)
                            ELSE 0 END
                        ) STORED,
    reputation_score    INTEGER     NOT NULL DEFAULT 0,  -- composite: accuracy + xp + tenure
    updated_at          TIMESTAMPTZ DEFAULT now(),
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Access gates — enforced server-side in Python
CREATE TABLE IF NOT EXISTS public.guild_access_gates (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type         TEXT        UNIQUE NOT NULL,   -- 'view_signals','vote','submit_signal','paper_trade'
    min_xp              INTEGER     NOT NULL DEFAULT 0,
    min_wellbeing_score INTEGER,    -- NULL = not required
    description         TEXT,
    created_at          TIMESTAMPTZ DEFAULT now()
);

-- Seed access gates (anti-scam protection)
INSERT INTO public.guild_access_gates (action_type, min_xp, min_wellbeing_score, description)
VALUES
    ('view_signals',   50,   NULL, 'Complete at least 1 quest lesson to view community signals'),
    ('vote',           100,  NULL, 'Complete the Crypto 101 intro module to vote on signals'),
    ('submit_signal',  500,  30,   'Complete 5+ modules AND generate a Wellbeing Score to submit signals'),
    ('paper_trade',    1000, NULL, 'Complete 10+ modules to paper trade based on signals')
ON CONFLICT (action_type) DO NOTHING;


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_xp_ledger_user_id          ON public.xp_ledger(user_id);
CREATE INDEX IF NOT EXISTS idx_xp_ledger_created_at       ON public.xp_ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_user_quest_progress_user    ON public.user_quest_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_wellbeing_scores_user       ON public.wellbeing_scores(user_id);
CREATE INDEX IF NOT EXISTS idx_wellbeing_nudges_user       ON public.wellbeing_nudges(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_guild_signals_user          ON public.guild_signals(user_id);
CREATE INDEX IF NOT EXISTS idx_guild_signals_status        ON public.guild_signals(status);
CREATE INDEX IF NOT EXISTS idx_guild_signals_asset         ON public.guild_signals(asset_symbol);
CREATE INDEX IF NOT EXISTS idx_guild_reputation_user       ON public.guild_reputation(user_id);


-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE public.quest_tracks          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quest_modules         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.quest_questions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_quest_progress   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.xp_ledger             ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_financial_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wellbeing_scores      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wellbeing_nudges      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guild_signals         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guild_signal_votes    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guild_reputation      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guild_access_gates    ENABLE ROW LEVEL SECURITY;

-- Quest content: public read (everyone can view quest structure)
CREATE POLICY "Anyone can view active quest tracks"
    ON public.quest_tracks FOR SELECT USING (is_active = true);

CREATE POLICY "Anyone can view active quest modules"
    ON public.quest_modules FOR SELECT USING (is_active = true);

CREATE POLICY "Anyone can view quest questions"
    ON public.quest_questions FOR SELECT USING (true);

CREATE POLICY "Service role manages quest content"
    ON public.quest_tracks FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role manages quest modules"
    ON public.quest_modules FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role manages quest questions"
    ON public.quest_questions FOR ALL USING (auth.role() = 'service_role');

-- User quest progress: own data only
CREATE POLICY "Users view own quest progress"
    ON public.user_quest_progress FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users insert own quest progress"
    ON public.user_quest_progress FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users update own quest progress"
    ON public.user_quest_progress FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Service role manages all quest progress"
    ON public.user_quest_progress FOR ALL USING (auth.role() = 'service_role');

-- XP ledger: read own, service writes
CREATE POLICY "Users view own XP"
    ON public.xp_ledger FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role manages XP ledger"
    ON public.xp_ledger FOR ALL USING (auth.role() = 'service_role');

-- Financial profiles: strictly own data
CREATE POLICY "Users manage own financial profile"
    ON public.user_financial_profiles FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role manages financial profiles"
    ON public.user_financial_profiles FOR ALL USING (auth.role() = 'service_role');

-- Wellbeing scores: own data + service
CREATE POLICY "Users view own wellbeing scores"
    ON public.wellbeing_scores FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Service role manages wellbeing scores"
    ON public.wellbeing_scores FOR ALL USING (auth.role() = 'service_role');

-- Wellbeing nudges: own data
CREATE POLICY "Users manage own nudges"
    ON public.wellbeing_nudges FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Service role manages nudges"
    ON public.wellbeing_nudges FOR ALL USING (auth.role() = 'service_role');

-- Guild signals: read with XP gate enforced at API level, write own
CREATE POLICY "Users view approved signals"
    ON public.guild_signals FOR SELECT
    USING (status IN ('approved','resolved','expired'));

CREATE POLICY "Users view own signals"
    ON public.guild_signals FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users submit own signals"
    ON public.guild_signals FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users update own pending signals"
    ON public.guild_signals FOR UPDATE
    USING (auth.uid() = user_id AND status = 'pending_review');

CREATE POLICY "Service role manages all signals"
    ON public.guild_signals FOR ALL USING (auth.role() = 'service_role');

-- Signal votes: own + read all
CREATE POLICY "Users view all votes"
    ON public.guild_signal_votes FOR SELECT USING (true);

CREATE POLICY "Users manage own votes"
    ON public.guild_signal_votes FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Service role manages votes"
    ON public.guild_signal_votes FOR ALL USING (auth.role() = 'service_role');

-- Guild reputation: public read (transparency), service writes
CREATE POLICY "Anyone can view guild reputation"
    ON public.guild_reputation FOR SELECT USING (true);

CREATE POLICY "Service role manages reputation"
    ON public.guild_reputation FOR ALL USING (auth.role() = 'service_role');

-- Access gates: public read (users need to know requirements)
CREATE POLICY "Anyone can view access gates"
    ON public.guild_access_gates FOR SELECT USING (true);

CREATE POLICY "Service role manages access gates"
    ON public.guild_access_gates FOR ALL USING (auth.role() = 'service_role');


-- ============================================================
-- SEED: Quest Tracks
-- ============================================================
INSERT INTO public.quest_tracks (slug, title, description, difficulty, market_context, xp_reward, order_index)
VALUES
    ('crypto-basics',        'Crypto 101: From Zero to Blockchain',          'Understand what crypto actually is, how blockchain works, and how to stay safe in a market full of scams.',                         'beginner',     'NG,KE', 500,  1),
    ('yield-farming',        'Yield Farming: Making Your Stablecoins Work',  'Learn how to earn passive income on your USDT/USDC without gambling on volatile tokens.',                                           'intermediate', 'NG,KE', 750,  2),
    ('household-finance',    'Running Your Household: Budgets That Work',    'Build a budget for real African life — including Ajo/Chama, family obligations, and NEPA bills.',                                    'beginner',     'NG,KE', 500,  3),
    ('credit-mastery',       'Credit Without the Trap: Borrowing Smart',     'Understand credit scores, spot predatory lenders, and use leverage without getting burned.',                                        'intermediate', 'NG,KE', 750,  4),
    ('sustainable-investing','Long Game: Investing for the Future You Want', 'From T-Bills to DeFi — build a portfolio strategy that fits your income, goals, and risk tolerance.',                               'advanced',     'NG,KE', 1000, 5),
    ('scam-survival',        'Scam Survival Guide: Protect Your Money',      'Learn every trick scammers use — Ponzi schemes, fake signal sellers, rug pulls — so you never fall victim.',                       'beginner',     'NG,KE', 500,  6)
ON CONFLICT (slug) DO NOTHING;