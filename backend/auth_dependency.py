# backend/auth_dependency.py (replace entire file)
import logging
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from models import UserProfile
from datetime import datetime
from config import get_settings
from services.session_service import SessionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
supabase: Client = create_client(settings.VITE_SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
security = HTTPBearer()
jwks_uri = settings.SUPABASE_JWKS_URI

if not jwks_uri:
    raise EnvironmentError("SUPABASE_JWKS_URI is not configured in the environment.")

jwks_client = PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=3600)

async def get_current_user(
    request: Request,
    token: HTTPAuthorizationCredentials = Depends(security)
) -> UserProfile:
    """
    Validates a Supabase JWT using JWKS and fetches/creates user profile.
    Also creates/updates user session with IPINFO data.
    """
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token.credentials)
        payload = jwt.decode(
            token.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience="authenticated",
        )
        
        user_id = payload.get("sub")
        user_email = payload.get("email")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="User ID (sub) not found in token.")

        # Try to fetch existing user profile
        try:
            response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
            if response.data:
                logger.info(f"Found existing user profile for user {user_id}")
                
                # Update user session with user ID
                session_service = SessionService(supabase)
                session_id = request.headers.get("x-session-id")
                if session_id:
                    await session_service.update_session_user(session_id, user_id)
                
                return UserProfile(**response.data)
                
        except Exception as fetch_error:
            logger.info(f"User profile not found for {user_id}, will create new profile. Error: {fetch_error}")

        # Create new user profile
        logger.info(f"Creating new user profile for user {user_id} with email {user_email}")
        
        new_profile_data = {
            "id": user_id,
            "email": user_email,
            "updated_at": datetime.utcnow().isoformat(),
            "first_name": None,
            "last_name": None,
            "country_code": None,
            "kyc_level": 0,
            "kyc_status": "none",
            "algorand_address": None,
            "evm_address": None
        }

        create_response = supabase.table("user_profiles").insert(new_profile_data).execute()
        
        if not create_response.data:
            logger.error(f"Failed to create user profile for {user_id}")
            raise HTTPException(status_code=500, detail="Could not create user profile.")
        
        logger.info(f"Successfully created user profile for {user_id}")
        return UserProfile(**create_response.data[0])

    except jwt.ExpiredSignatureError:
        logger.warning("Authentication failed: Token has expired.")
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.exceptions.PyJWTError as e:
        logger.error(f"Authentication failed due to invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token.")
    except Exception as e:
        logger.error(f"An unexpected error occurred during authentication: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not validate credentials.")