-- This function atomically updates the user's profile and inserts into the secure wallet table.
-- It is defined with SECURITY DEFINER to run with elevated privileges.
-- CRITICAL FIX: We explicitly set the search_path to 'public' to prevent search path hijacking attacks.

CREATE OR REPLACE FUNCTION public.provision_user_wallet(
    user_id_input uuid,
    algorand_address_input text,
    encrypted_pk_input text
)
RETURNS void AS $$
BEGIN
    -- Update the public profile with the new address
    UPDATE public.user_profiles
    SET algorand_address = algorand_address_input, updated_at = now()
    WHERE id = user_id_input;

    -- Insert the encrypted private key into the secure table
    INSERT INTO public.user_wallets (user_id, algorand_private_key)
    VALUES (user_id_input, encrypted_pk_input);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;