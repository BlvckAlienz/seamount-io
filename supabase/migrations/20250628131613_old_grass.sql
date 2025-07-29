-- Create payment corridors table
-- Used to configure available cross-border payment routes
CREATE TABLE public.payment_corridors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_country TEXT NOT NULL,
    to_country TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    fee_rate DECIMAL NOT NULL,
    exchange_rate_type TEXT NOT NULL DEFAULT 'dynamic',
    min_amount DECIMAL NOT NULL DEFAULT 1,
    max_amount DECIMAL,
    estimated_delivery_seconds INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(from_country, to_country)
);

-- Create countries table
-- Stores information about supported countries and their settings
CREATE TABLE public.countries (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    currency TEXT NOT NULL,
    currency_name TEXT NOT NULL,
    payment_methods JSONB,
    flag TEXT,
    dial_code TEXT,
    regulatory_status TEXT DEFAULT 'pending',
    risk_tier TEXT DEFAULT 'tier_2',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Create exchange rates table
-- Stores current and historical exchange rates
CREATE TABLE public.exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    rate DECIMAL NOT NULL,
    source TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT now(),
    UNIQUE(from_currency, to_currency)
);

-- Create fee configuration table
-- Defines fees for different payment types
CREATE TABLE public.fee_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fee_type TEXT NOT NULL,
    rate DECIMAL NOT NULL,
    min_fee DECIMAL NOT NULL DEFAULT 0.01,
    max_fee DECIMAL,
    applies_to JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(fee_type)
);

-- Create user profiles table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id),
    first_name TEXT,
    last_name TEXT,
    country_code TEXT NOT NULL,
    phone TEXT,
    kyc_level INTEGER DEFAULT 0,
    kyc_verified BOOLEAN DEFAULT false,
    risk_score DECIMAL DEFAULT 0,
    algorand_address TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create payment transactions table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    provider TEXT NOT NULL,
    provider_id TEXT,
    reference TEXT,
    amount DECIMAL NOT NULL,
    fee DECIMAL DEFAULT 0,
    currency TEXT NOT NULL,
    status TEXT NOT NULL,
    sender_address TEXT,
    receiver_address TEXT,
    tx_id TEXT,
    payment_type TEXT NOT NULL,
    country_code TEXT,
    exchange_rate DECIMAL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create sanctions list table
-- Used for compliance and anti-money laundering checks
CREATE TABLE IF NOT EXISTS public.sanctions_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    address TEXT,
    reason TEXT NOT NULL,
    source TEXT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id),
    UNIQUE(address)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_payment_transactions_user_id ON public.payment_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON public.payment_transactions(status);
CREATE INDEX IF NOT EXISTS idx_payment_transactions_created_at ON public.payment_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_currencies ON public.exchange_rates(from_currency, to_currency);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_timestamp ON public.exchange_rates(timestamp);
CREATE INDEX IF NOT EXISTS idx_payment_corridors_countries ON public.payment_corridors(from_country, to_country);
CREATE INDEX IF NOT EXISTS idx_payment_corridors_status ON public.payment_corridors(status);
CREATE INDEX IF NOT EXISTS idx_countries_currency ON public.countries(currency);
CREATE INDEX IF NOT EXISTS idx_countries_is_active ON public.countries(is_active);

-- Create RLS policies
ALTER TABLE public.payment_corridors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.countries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exchange_rates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fee_configuration ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sanctions_list ENABLE ROW LEVEL SECURITY;

-- Allow read access to payment corridors
CREATE POLICY "Allow read access to payment corridors" ON public.payment_corridors
    FOR SELECT TO authenticated USING (true);

-- Allow read access to countries
CREATE POLICY "Allow read access to countries" ON public.countries
    FOR SELECT TO authenticated USING (true);

-- Allow read access to exchange rates
CREATE POLICY "Allow read access to exchange rates" ON public.exchange_rates
    FOR SELECT TO authenticated USING (true);

-- Allow read access to fee configuration
CREATE POLICY "Allow read access to fee configuration" ON public.fee_configuration
    FOR SELECT TO authenticated USING (true);