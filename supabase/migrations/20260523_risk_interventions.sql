-- 1️⃣ Database migrations

SET search_path = public, pg_catalog;

CREATE TABLE public.risk_interventions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    risk_tier VARCHAR(10) NOT NULL CHECK (risk_tier IN ('TIER_1', 'TIER_2', 'TIER_3')),
    trigger_context TEXT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 🚨 MISSION CRITICAL: Always enable RLS on new tables
ALTER TABLE public.risk_interventions ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only view and update their own risk interventions
CREATE POLICY "Users can manage own interventions" ON public.risk_interventions
    FOR ALL TO authenticated 
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 🚨 MISSION CRITICAL: Security Definer for elevated admin logging
CREATE FUNCTION public.log_risk_intervention(p_user_id UUID, p_tier VARCHAR, p_context TEXT)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
DECLARE
    v_id UUID;
BEGIN
    INSERT INTO public.risk_interventions (user_id, risk_tier, trigger_context)
    VALUES (p_user_id, p_tier, p_context)
    RETURNING id INTO v_id;
    
    RETURN v_id;
END;
$$;