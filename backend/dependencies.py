import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from jose import JWTError, jwt

from config import Settings, get_settings
from services.wallet_service import WalletService
from services.notification_service import NotificationService
from models import UserRole # Import UserRole for profile creation

logger = logging.getLogger(__name__)

# --- GLOBAL STATE & CACHING ---
_supabase_client: Optional[Client] = None
_wallet_service: Optional[WalletService] = None
_notification_service: Optional[NotificationService] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None
security = HTTPBearer()

# --- SERVICE INITIALIZATION (CALLED FROM MAIN.PY LIFESPAN) ---
def initialize_dependencies(
    supabase_client: Client,
    wallet_service: WalletService,
    notification_service: NotificationService
):
    """Sets the global service instances from the main application startup."""
    global _supabase_client, _wallet_service, _notification_service
    _supabase_client = supabase_client
    _wallet_service = wallet_service
    _notification_service = notification_service
    logger.info("Dependencies have been successfully initialized with service instances.")

# --- DEPENDENCY GETTER FUNCTIONS ---
def get_supabase_client() -> Client:
    if not _supabase_client: raise HTTPException(status_code=503, detail="DB service unavailable.")
    return _supabase_client

def get_wallet_service() -> WalletService:
    if not _wallet_service: raise HTTPException(status_code=503, detail="Wallet service unavailable.")
    return _wallet_service

def get_notification_service() -> NotificationService:
    if not _notification_service: raise HTTPException(status_code=503, detail="Notification service unavailable.")
    return _notification_service

# --- CORE AUTHENTICATION LOGIC ---
async def fetch_jwks(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    global jwks_cache, jwks_cache_expiry
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry: return jwks_cache
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(settings.SUPABASE_JWKS_URI) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache, jwks_cache_expiry = jwks_data, datetime.utcnow() + timedelta(hours=1)
                return jwks_data
    except Exception as e:
        logger.critical(f"CRITICAL: Could not fetch Supabase JWKS. Auth will fail. Error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable.")

async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    try:
        token = credentials.credentials
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg")
        allowed_algorithms = ["HS256", "RS256"]
        if alg not in allowed_algorithms:
            raise JWTError("The specified token algorithm is not allowed.")

        if alg == "HS256":
            key = settings.SUPABASE_JWT_SECRET.get_secret_value()
        else: # RS256
            jwks = await fetch_jwks(settings)
            key = next((k for k in jwks["keys"] if k["kid"] == unverified_header.get("kid")), None)
            if not key: raise JWTError("Unable to find appropriate public key for RS256 token")

        payload = jwt.decode(token, key, algorithms=[alg], audience="authenticated", issuer=settings.SUPABASE_JWT_ISSUER)
        return payload
    except JWTError as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not process authentication token.")

async def get_current_user(
    payload: Dict[str, Any] = Depends(verify_supabase_token),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Retrieves the user profile. CRITICAL: If a profile doesn't exist for a valid
    token (i.e., first sign-in after email confirmation), it creates one on-the-fly.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload: user identifier is missing.")
    
    try:
        # Attempt to fetch the user profile from our public.user_profiles table.
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).maybe_single().execute()
        
        # ** THIS IS THE RESTORED, CRITICAL LOGIC **
        if not profile_res.data:
            logger.warning(f"Profile not found for user {user_id}. Attempting to create one from auth details.")
            
            # Fetch the user details directly from Supabase Auth
            auth_user_res = supabase.auth.admin.get_user_by_id(user_id)
            auth_user = auth_user_res.user
            if not auth_user:
                raise HTTPException(status_code=404, detail="User not found in authentication system.")

            # Create the new profile record with default values
            new_profile_data = {
                "id": user_id,
                "email": auth_user.email,
                "first_name": auth_user.user_metadata.get("first_name"),
                "last_name": auth_user.user_metadata.get("last_name"),
                "role": UserRole.ALIEN.value, # Default role from your models.py
            }

            insert_res = supabase.from_("user_profiles").insert(new_profile_data).execute()
            
            if not insert_res.data:
                logger.critical(f"Failed to create user profile for user {user_id} after successful auth.")
                raise HTTPException(status_code=500, detail="Could not create user profile.")
            
            logger.info(f"Successfully created new profile for user {user_id}.")
            return insert_res.data[0]

        # If profile already existed, return it.
        return profile_res.data
        
    except Exception as e:
        logger.error(f"Failed to fetch or create profile for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving user profile information.")