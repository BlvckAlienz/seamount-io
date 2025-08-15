-- Creates the user_consent table to store cookie and marketing preferences.
CREATE TABLE IF NOT EXISTS public.user_consent (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    ip_address INET,
    user_agent TEXT,
    consent_type TEXT NOT NULL, -- e.g., 'cookies', 'marketing_emails'
    preferences JSONB NOT NULL, -- Stores detailed choices, e.g., {"analytics": true, "advertising": false}
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Enable Row Level Security
ALTER TABLE public.user_consent ENABLE ROW LEVEL SECURITY;

-- Allow users to view and manage their own consent records.
CREATE POLICY "Users can manage their own consent"
ON public.user_consent
FOR ALL
USING (auth.uid() = user_id);

-- Optional: Create an index for faster lookups
CREATE INDEX IF NOT EXISTS idx_user_consent_user_id ON public.user_consent(user_id);