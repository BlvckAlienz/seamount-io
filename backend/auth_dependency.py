# File Location: backend/auth_dependency.py
# Description: The definitive, modern authentication dependency using JWKS for Supabase.

import logging
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from models import UserProfile
from datetime import datetime

# --- DEFINITIVE, CORRECTED IMPORT ---
# Import the singleton accessor function from our central config.
from config import get_settings

# --- Configuration & Initialization ---
# This ensures we use the same, single, validated settings instance across the app.
settings = get_settings()
supabase: Client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
security = HTTPBearer()
logger = logging.getLogger(__name__)

# --- JWKS Client Setup ---
# This client will fetch the public keys from Supabase and cache them for performance.
jwks_uri = settings.SUPABASE_JWKS_URI
if not jwks_uri:
    raise EnvironmentError("SUPABASE_JWKS_URI is not configured in the environment.")
jwks_client = PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=3600)

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """
    Validates a Supabase JWT using the modern JWKS method and fetches the user's profile.
    If the user profile doesn't exist, it automatically creates one from the JWT data.
    This is the secure, up-to-date way to handle Supabase authentication with auto-provisioning.
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
        user_email = payload.get("email")  # Extract email from JWT for profile creation
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID (sub) not found in token.")

        # 3. Try to fetch the user's profile from our public table via the Supabase client.
        try:
            response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
            
            # If we found the user profile, return it
            if response.data:
                logger.info(f"Found existing user profile for user {user_id}")
                return UserProfile(**response.data)
                
        except Exception as fetch_error:
            # Log that we couldn't find the user profile, but don't fail yet
            logger.info(f"User profile not found for {user_id}, will create new profile. Error: {fetch_error}")

        # 4. CRITICAL FIX: If user profile doesn't exist, create it automatically
        # This is where the magic happens - we auto-provision new users
        logger.info(f"Creating new user profile for user {user_id} with email {user_email}")
        
        # Prepare the new user profile data using information from the JWT
        new_profile_data = {
            "id": user_id,
            "email": user_email,
            "updated_at": datetime.utcnow().isoformat(),
            "first_name": None,  # Will be updated later when user completes profile
            "last_name": None,
            "country_code": None,
            "kyc_level": 0,  # Default to no KYC
            "kyc_status": "none",  # Default KYC status
            "algorand_address": None,
            "evm_address": None
        }

        # Insert the new user profile into our database
        create_response = supabase.table("user_profiles").insert(new_profile_data).execute()
        
        if not create_response.data:
            logger.error(f"Failed to create user profile for {user_id}")
            raise HTTPException(status_code=500, detail="Could not create user profile.")
        
        # Log successful profile creation for monitoring
        logger.info(f"Successfully created user profile for {user_id}")
        
        # Return the newly created profile
        return UserProfile(**create_response.data[0])

    except jwt.ExpiredSignatureError:
        # Log the specific user ID if available in the expired token (payload is still accessible)
        try:
            expired_payload = jwt.decode(token.credentials, options={"verify_signature": False})
            logger.warning(f"Authentication failed for sub {expired_payload.get('sub')}: Token has expired.")
        except Exception:
            logger.warning("Authentication failed: An expired token was received that could not be decoded.")
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.exceptions.PyJWTError as e:
        logger.error(f"Authentication failed due to invalid token: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during authentication: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not validate credentials.")