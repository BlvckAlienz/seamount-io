-- Create user_wallets table with correct Supabase references
CREATE TABLE IF NOT EXISTS user_wallets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    algorand_address TEXT NOT NULL,
    algorand_private_key TEXT NOT NULL,
    usds_balance DECIMAL(18, 6) DEFAULT 0.0,
    is_demo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_user_wallets_user_id ON user_wallets(user_id);
CREATE INDEX IF NOT EXISTS idx_user_wallets_algorand_address ON user_wallets(algorand_address);

-- Enable Row Level Security
ALTER TABLE user_wallets ENABLE ROW LEVEL SECURITY;

-- Create policies for RLS
CREATE POLICY "Users can view their own wallet" 
    ON user_wallets FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own wallet" 
    ON user_wallets FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own wallet" 
    ON user_wallets FOR UPDATE 
    USING (auth.uid() = user_id);

-- Create investor_contacts table
CREATE TABLE IF NOT EXISTS investor_contacts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT,
    check_size TEXT,
    message TEXT,
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for investor contacts
CREATE INDEX IF NOT EXISTS idx_investor_contacts_email ON investor_contacts(email);
CREATE INDEX IF NOT EXISTS idx_investor_contacts_user_id ON investor_contacts(user_id);

-- Add complycube_applicant_id to user_profiles if it doesn't exist
ALTER TABLE IF EXISTS user_profiles 
ADD COLUMN IF NOT EXISTS complycube_applicant_id TEXT;

-- Add kyc_status to user_profiles if it doesn't exist
ALTER TABLE IF EXISTS user_profiles 
ADD COLUMN IF NOT EXISTS kyc_status TEXT DEFAULT 'pending';

-- Add kyc_level to user_profiles if it doesn't exist
ALTER TABLE IF EXISTS user_profiles 
ADD COLUMN IF NOT EXISTS kyc_level INTEGER DEFAULT 0;