-- ============================================================
-- FILE: supabase/migrations/20260519_signal_rpc_functions.sql
-- RPC functions used by learn.py signal voting
-- Run AFTER 20260519_financial_literacy.sql
-- ============================================================

SET search_path = public, pg_catalog;

-- ── Increment upvotes ─────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.increment_signal_upvotes(signal_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
    UPDATE public.guild_signals
    SET upvotes = upvotes + 1,
        updated_at = now()
    WHERE id = signal_id;
END;
$$;

-- ── Increment downvotes ───────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.increment_signal_downvotes(signal_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
    UPDATE public.guild_signals
    SET downvotes = downvotes + 1,
        updated_at = now()
    WHERE id = signal_id;
END;
$$;

-- ── Increment flags ───────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.increment_signal_flags(signal_id UUID)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
BEGIN
    UPDATE public.guild_signals
    SET flag_count = flag_count + 1,
        updated_at = now()
    WHERE id = signal_id;
END;
$$;

-- ── Update guild reputation after signal resolution ───────────────────────────
-- Call this when a signal's outcome is known (hit target = accurate, hit stop = inaccurate)
CREATE OR REPLACE FUNCTION public.resolve_guild_signal(
    p_signal_id  UUID,
    p_accurate   BOOLEAN
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
DECLARE
    v_user_id UUID;
    v_xp      INTEGER;
BEGIN
    -- Get signal owner
    SELECT user_id INTO v_user_id
    FROM public.guild_signals
    WHERE id = p_signal_id;

    IF v_user_id IS NULL THEN RETURN; END IF;

    -- Update signal status
    UPDATE public.guild_signals
    SET status     = 'resolved',
        updated_at = now()
    WHERE id = p_signal_id;

    -- Update reputation
    UPDATE public.guild_reputation
    SET total_signals    = total_signals + 1,
        accurate_signals = accurate_signals + CASE WHEN p_accurate THEN 1 ELSE 0 END,
        updated_at       = now()
    WHERE user_id = v_user_id;

    -- Award XP for accurate signal
    IF p_accurate THEN
        v_xp := 150;
        INSERT INTO public.xp_ledger (user_id, event_type, xp_amount, reference_id, reference_type)
        VALUES (v_user_id, 'signal_accurate', v_xp, p_signal_id, 'guild_signal');
    END IF;
END;
$$;

-- ── Grant execute to authenticated + service role ────────────────────────────
GRANT EXECUTE ON FUNCTION public.increment_signal_upvotes   TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.increment_signal_downvotes TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.increment_signal_flags     TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION public.resolve_guild_signal       TO service_role;