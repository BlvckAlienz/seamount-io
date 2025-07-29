# File Location: backend/auth_dependency.py
# Description: The definitive, modern authentication dependency using JWKS for Supabase.

import os
import logging
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer
from supabase import create_client, Client
from models import UserProfile

# --- Configuration ---
settings = get_settings() # Assuming you have this pattern in your config
supabase: Client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
security = HTTPBearer()
logger = logging.getLogger(__name__)

# --- JWKS Client Setup ---
# This client will fetch the public keys from Supabase and cache them.
jwks_uri = settings.SUPABASE_JWKS_URI
if not jwks_uri:
    raise EnvironmentError("SUPABASE_JWKS_URI is not configured in the environment.")
jwks_client = PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=3600)

async def get_current_user(token: str = Depends(security)) -> UserProfile:
    """
    Validates a Supabase JWT using the modern JWKS method and fetches the user's profile.
    This is the secure, up-to-date way to handle Supabase authentication.
    """
    try:
        # 1. Get the signing key from the JWKS endpoint.
        # The PyJWTClient handles caching, so it won't hit the URL on every request.
        signing_key = jwks_client.get_signing_key_from_jwt(token.credentials)

        # 2. Decode the token using the fetched public key.
        # It verifies the signature, expiration, and audience.
        payload = jwt.decode(
            token.credentials,
            signing_key.key,
            algorithms=["RS256"], # Supabase uses RS256 for the new format
            audience="authenticated",
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID (sub) not found in token.")

        # 3. Fetch the user's profile from our public table.
        # This part remains the same.
        response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="User profile not found in our database.")

        return UserProfile(**response.data)

    except jwt.ExpiredSignatureError:
        logger.warning("Authentication failed: Token has expired.")
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.exceptions.PyJWTError as e:
        logger.error(f"Authentication failed: Invalid token. Error: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during authentication: {e}")
        raise HTTPException(status_code=500, detail="Could not validate credentials.")