-- File: supabase/migrations/20241201_prediction_markets.sql

-- 1️⃣ PREDICTION MARKETS TABLE
CREATE TABLE public.prediction_markets (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    description TEXT,
    end_time TIMESTAMP NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('sports', 'crypto', 'forex', 'politics')),
    total_yes_bets DECIMAL(20, 6) DEFAULT 0,
    total_no_bets DECIMAL(20, 6) DEFAULT 0,
    total_volume DECIMAL(20, 6) DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    outcome BOOLEAN,  -- TRUE = YES wins, FALSE = NO wins
    contract_market_id INTEGER,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    trending_score INTEGER DEFAULT 0
) SET search_path = public, pg_catalog;

-- 2️⃣ PREDICTION BETS TABLE
CREATE TABLE public.prediction_bets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    market_id INTEGER REFERENCES public.prediction_markets(id) NOT NULL,
    prediction BOOLEAN NOT NULL,  -- TRUE = YES, FALSE = NO
    amount DECIMAL(20, 6) NOT NULL,
    tx_hash TEXT NOT NULL,
    claimed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
) SET search_path = public, pg_catalog;

-- 3️⃣ ENABLE RLS
ALTER TABLE public.prediction_markets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prediction_bets ENABLE ROW LEVEL SECURITY;

-- 4️⃣ RLS POLICIES
-- Markets: Readable by all, writable by admins only
CREATE POLICY "Markets are viewable by everyone"
    ON public.prediction_markets FOR SELECT
    USING (true);

CREATE POLICY "Only admins can create markets"
    ON public.prediction_markets FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.user_profiles 
            WHERE id = auth.uid() AND is_admin = TRUE
        )
    );

-- Bets: Users can view their own bets
CREATE POLICY "Users can view their own bets"
    ON public.prediction_bets FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can place bets"
    ON public.prediction_bets FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- 5️⃣ INDEXES FOR PERFORMANCE
CREATE INDEX idx_markets_end_time ON public.prediction_markets(end_time);
CREATE INDEX idx_markets_resolved ON public.prediction_markets(resolved);
CREATE INDEX idx_bets_user_id ON public.prediction_bets(user_id);
CREATE INDEX idx_bets_market_id ON public.prediction_bets(market_id);

-- 6️⃣ SEED INITIAL 5 MARKETS
INSERT INTO public.prediction_markets (question, description, end_time, category, trending_score, contract_market_id) VALUES
(
    'Will Super Eagles win AFCON 2025 in Morocco?',
    'Nigeria to win Africa Cup of Nations 2025 (Dec 21, 2024 - Jan 18, 2025). Current odds: Favorites after runner-up finish in 2023.',
    '2025-01-18 23:59:59',
    'sports',
    99,
    1
),
(
    'Will Bitcoin hit $150K in Q1 2026?',
    'BTC price prediction for Jan-Mar 2026 (current: ~$95K)',
    '2026-03-31 23:59:59',
    'crypto',
    92,
    2
),
(
    'Will NGN exchange rate go below ₦1,350/USD by end of Q1 2026?',
    'Naira devaluation prediction (current: ~₦1,500/USD)',
    '2026-03-31 23:59:59',
    'forex',
    95,
    3
),
(
    'Will Arsenal win the 2025/2026 UEFA Champions League?',
    'Arsenal to win UCL final on June 7, 2026',
    '2026-06-07 23:59:59',
    'sports',
    88,
    4
),
(
    'Will Goodluck Jonathan contest 2027 Presidential Election under PDP?',
    'Former President Goodluck Jonathan to run under PDP in Feb 2027',
    '2027-01-31 23:59:59',
    'politics',
    96,
    5
);