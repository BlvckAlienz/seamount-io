-- Fix the auth.users query issue by creating a view
CREATE OR REPLACE FUNCTION get_user_count()
RETURNS INTEGER AS $$
BEGIN
  RETURN (SELECT COUNT(*) FROM auth.users);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Ensure your users table has auth_id column
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS auth_id UUID REFERENCES auth.users(id);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS kyc_status VARCHAR(20) DEFAULT 'none';