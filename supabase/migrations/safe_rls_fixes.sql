-- EXECUTE THESE ONE BY ONE IN SUPABASE SQL EDITOR
-- CRITICAL FIX: Break infinite recursion in user_profiles RLS

-- Step 1: Remove the problematic circular policy
DROP POLICY IF EXISTS "Admins can view all profiles" ON user_profiles;

-- Step 2: Create safe admin policy using JWT claims (no table lookups)
CREATE POLICY "Admins can view all profiles via JWT" ON user_profiles
    FOR SELECT
    TO public
    USING (
        auth.jwt() ->> 'user_role' = 'admin' 
        OR auth.role() = 'service_role'
    );

-- Step 3: Ensure backend service has proper access
CREATE POLICY "Backend service full access" ON user_profiles
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Step 4: Test the fix
SELECT 'RLS recursion FIXED!' as status;
SELECT count(*) as profile_count FROM user_profiles;