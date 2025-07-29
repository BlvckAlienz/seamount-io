/*
# Authentication and KYC Tables

This migration adds the necessary tables and functions for user authentication and KYC verification.

1. Tables
   - verification_sessions: Tracks KYC verification sessions
   - verification_attempts: Records individual verification attempts
   - user_settings: User preference settings

2. RLS Policies
   - Added appropriate row level security policies
   
3. Functions
   - update_user_kyc_level: Function to update KYC level
*/

-- Create verification_sessions table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.verification_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    session_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create verification_attempts table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.verification_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    check_id TEXT,
    status TEXT NOT NULL,
    document_type TEXT,
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Create user_settings table if it doesn't exist
CREATE TABLE IF NOT EXISTS public.user_settings (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id),
    notification_preferences JSONB DEFAULT '{"email": true, "push": false, "sms": false}'::jsonb,
    ui_preferences JSONB DEFAULT '{"theme": "dark", "language": "en"}'::jsonb,
    trading_preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add the login_timestamps column to the auth.users table if it doesn't exist
DO $$ 
BEGIN
    ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS login_timestamps TIMESTAMPTZ[];
    ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS last_sign_in_at TIMESTAMPTZ;
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE 'Could not alter auth.users table due to permissions';
END $$;

-- Create function to update user's KYC level
CREATE OR REPLACE FUNCTION public.update_user_kyc_level(
    user_id UUID,
    new_level INTEGER,
    is_verified BOOLEAN,
    details TEXT DEFAULT NULL
)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    current_level INTEGER;
    success BOOLEAN;
BEGIN
    -- Get current KYC level
    SELECT kyc_level INTO current_level FROM public.user_profiles WHERE id = user_id;
    
    -- Update user profile with new KYC level
    UPDATE public.user_profiles
    SET 
        kyc_level = new_level,
        kyc_verified = is_verified,
        kyc_last_verified = CASE WHEN is_verified THEN NOW() ELSE kyc_last_verified END,
        kyc_details = details,
        updated_at = NOW()
    WHERE id = user_id;
    
    -- Insert into verification history
    INSERT INTO public.kyc_verification_history
        (user_id, verification_type, previous_level, new_level, verified, details)
    VALUES
        (user_id, 'complycube', current_level, new_level, is_verified, details);
    
    RETURN FOUND;
END;
$$;

-- Enable RLS on verification tables
ALTER TABLE public.verification_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verification_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

-- RLS policies for verification_sessions
CREATE POLICY "Users can view their own verification sessions"
    ON public.verification_sessions
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own verification sessions"
    ON public.verification_sessions
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- RLS policies for verification_attempts
CREATE POLICY "Users can view their own verification attempts"
    ON public.verification_attempts
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own verification attempts"
    ON public.verification_attempts
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

-- RLS policies for user_settings
CREATE POLICY "Users can view their own settings"
    ON public.user_settings
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own settings"
    ON public.user_settings
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own settings"
    ON public.user_settings
    FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id);

-- Create or update function to handle new user registration
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS TRIGGER AS $$
BEGIN
    -- Insert a new row into public.user_profiles
    INSERT INTO public.user_profiles (
        id,
        kyc_level,
        kyc_verified,
        country_code,
        created_at,
        updated_at
    ) VALUES (
        NEW.id,
        0, -- Default KYC level 0
        false, -- Not verified by default
        'US', -- Default country code
        NOW(),
        NOW()
    );
    
    -- Create user settings entry
    INSERT INTO public.user_settings (
        user_id,
        created_at,
        updated_at
    ) VALUES (
        NEW.id,
        NOW(),
        NOW()
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create the trigger if it doesn't exist
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_verification_sessions_user_id ON public.verification_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_verification_attempts_user_id ON public.verification_attempts(user_id);
CREATE INDEX IF NOT EXISTS idx_verification_attempts_status ON public.verification_attempts(status);