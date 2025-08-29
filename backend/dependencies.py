import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from jose import JWTError, jwt

# Centralized imports from your project structure
from config import Settings, get_settings
from services.wallet_service import WalletService
from services.notification_service import NotificationService

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
    if not _supabase_client:
        raise HTTPException(status_code=503, detail="Database client service is not available.")
    return _supabase_client

def get_wallet_service() -> WalletService:
    if not _wallet_service:
        raise HTTPException(status_code=503, detail="Wallet service is not available.")
    return _wallet_service

def get_notification_service() -> NotificationService:
    if not _notification_service:
        raise HTTPException(status_code=503, detail="Notification service is not available.")
    return _notification_service

# --- CORE AUTHENTICATION LOGIC ---
async def fetch_jwks(settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    """Fetches and caches Supabase's JSON Web Key Set (JWKS) for token verification."""
    global jwks_cache, jwks_cache_expiry
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry:
        return jwks_cache
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(settings.SUPABASE_JWKS_URI) as response:
                response.raise_for_status()
                jwks_data = await response.json()
                jwks_cache, jwks_cache_expiry = jwks_data, datetime.utcnow() + timedelta(hours=1)
                return jwks_data
    except Exception as e:
        logger.critical(f"CRITICAL: Could not fetch Supabase JWKS. Auth will fail. Error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service is temporarily unavailable.")

async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Verifies the JWT token from the Authorization header using the cached JWKS.
    This logic is robust and handles finding the correct key.
    """
    try:
        token = credentials.credentials
        unverified_header = jwt.get_unverified_header(token)
        jwks = await fetch_jwks(settings)
        
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
                break
        
        if not rsa_key:
            raise JWTError("Unable to find appropriate public key for token verification")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience="authenticated",
            issuer=settings.SUPABASE_JWT_ISSUER
        )
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
    The primary dependency for protected routes. Takes a validated token payload
    and returns the full user profile from the database.
    """
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload: user identifier is missing.")
    try:
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).single().execute()
        if not profile_res.data:
            logger.warning(f"Authenticated user with ID {user_id} not found in user_profiles table.")
            raise HTTPException(status_code=404, detail="User profile not found.")
        return profile_res.data
    except Exception as e:
        logger.error(f"Failed to fetch profile for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving user profile information.")