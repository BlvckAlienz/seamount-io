/*
# Add KYC fields to user profiles

1. User Profile Updates
   - Add KYC verification fields to user profiles
   - Store verification details and history

2. Security
   - Enable RLS for user profiles table
   - Add policies for appropriate access
*/

-- Add KYC fields to user_profiles table if it exists
DO $$ 
BEGIN
    -- Add kyc_verified field
    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'kyc_verified') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN kyc_verified BOOLEAN DEFAULT false;
    END IF;

    -- Add kyc_level field
    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'kyc_level') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN kyc_level INTEGER DEFAULT 0;
    END IF;

    -- Add kyc_last_verified field
    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'kyc_last_verified') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN kyc_last_verified TIMESTAMPTZ;
    END IF;

    -- Add kyc_details field
    IF NOT EXISTS (SELECT 1 
                  FROM information_schema.columns 
                  WHERE table_schema = 'public' 
                  AND table_name = 'user_profiles' 
                  AND column_name = 'kyc_details') 
    THEN
        ALTER TABLE public.user_profiles ADD COLUMN kyc_details TEXT;
    END IF;
END $$;

-- Create KYC verification history table
CREATE TABLE IF NOT EXISTS public.kyc_verification_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    verification_type TEXT NOT NULL,
    previous_level INTEGER,
    new_level INTEGER,
    verified BOOLEAN,
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on kyc_verification_history
ALTER TABLE public.kyc_verification_history ENABLE ROW LEVEL SECURITY;

-- Create RLS policies for kyc_verification_history
CREATE POLICY "Users can view their own KYC history" 
    ON public.kyc_verification_history
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Only admins can insert KYC history" 
    ON public.kyc_verification_history
    FOR INSERT
    TO authenticated
    WITH CHECK (
        (SELECT is_admin FROM public.user_profiles WHERE id = auth.uid())
        OR user_id = auth.uid()
    );

-- Add index for performance
CREATE INDEX IF NOT EXISTS idx_kyc_verification_user_id
    ON public.kyc_verification_history(user_id);

-- Create function to track KYC level changes
CREATE OR REPLACE FUNCTION public.track_kyc_level_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF (OLD.kyc_level IS DISTINCT FROM NEW.kyc_level OR 
        OLD.kyc_verified IS DISTINCT FROM NEW.kyc_verified)
    THEN
        INSERT INTO public.kyc_verification_history
            (user_id, verification_type, previous_level, new_level, verified, details)
        VALUES
            (NEW.id, 
             'complycube',
             OLD.kyc_level, 
             NEW.kyc_level, 
             NEW.kyc_verified, 
             NEW.kyc_details);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger for KYC tracking
DROP TRIGGER IF EXISTS track_kyc_changes ON public.user_profiles;
CREATE TRIGGER track_kyc_changes
    AFTER UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.track_kyc_level_changes();