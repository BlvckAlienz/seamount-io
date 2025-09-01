import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import aiohttp
from jose import JWTError, jwt
import json

from config import Settings, get_settings
from services.wallet_service import WalletService
from services.notification_service import NotificationService
from models import UserRole

logger = logging.getLogger(__name__)

# (Global state and service getters remain the same)
_supabase_client: Optional[Client] = None
_wallet_service: Optional[WalletService] = None
_notification_service: Optional[NotificationService] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None
security = HTTPBearer()

def initialize_dependencies(supabase_client: Client, wallet_service: WalletService, notification_service: NotificationService):
    global _supabase_client, _wallet_service, _notification_service
    _supabase_client, _wallet_service, _notification_service = supabase_client, wallet_service, notification_service
    logger.info("Dependencies have been successfully initialized.")

def get_supabase_client() -> Client:
    if not _supabase_client: raise HTTPException(status_code=503, detail="DB service unavailable.")
    return _supabase_client

def get_wallet_service() -> WalletService:
    if not _wallet_service: raise HTTPException(status_code=503, detail="Wallet service unavailable.")
    return _wallet_service

def get_notification_service() -> NotificationService:
    if not _notification_service: raise HTTPException(status_code=503, detail="Notification service unavailable.")
    return _notification_service

async def fetch_jwks(settings: Settings = Depends(get_settings)):
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
        logger.critical(f"CRITICAL: Could not fetch Supabase JWKS. Error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service unavailable.")

# --- FIXED TOKEN VERIFICATION FOR ES256 ALGORITHM ---
async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    Properly verify Supabase JWT tokens using their JWKS
    """
    try:
        token = credentials.credentials
        logger.info(f"Starting JWT verification for token: {token[:20]}...")
        
        # Get unverified header to extract key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        alg = unverified_header.get('alg', 'RS256')
        
        if not kid:
            logger.error("Token missing key ID (kid)")
            raise JWTError("Token missing key ID (kid)")
        
        logger.info(f"Token KID: {kid}, Algorithm: {alg}")
        
        # Fetch JWKS
        jwks = await fetch_jwks(settings)
        
        # Find the matching key
        key = None
        for jwk_key in jwks.get('keys', []):
            if jwk_key.get('kid') == kid:
                key = jwk_key
                break
        
        if not key:
            logger.error(f"Public key for KID {kid} not found in JWKS")
            raise JWTError(f"Public key for KID {kid} not found in JWKS")
        
        logger.info(f"Found matching key for KID: {kid}")
        
        # Verify and decode token using the correct key
        # ADDED ES256 to the allowed algorithms
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256', 'ES256'],  # Added ES256 support
            audience='authenticated',
            options={"verify_aud": True, "verify_exp": True}
        )
        
        logger.info(f"Token verified successfully for user: {payload.get('sub')}")
        return payload
        
    except JWTError as e:
        logger.error(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error in token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process token"
        )

async def get_current_user(
    payload: Dict[str, Any] = Depends(verify_supabase_token),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    user_id = payload.get("sub")
    if not user_id: raise HTTPException(status_code=401, detail="Invalid token payload: user ID is missing.")
    try:
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).maybe_single().execute()
        
        # FIX: Handle cases where response.data might be None
        if not profile_res or not hasattr(profile_res, 'data') or profile_res.data is None:
            logger.warning(f"Profile not found or empty response for user {user_id}. Creating one from auth details.")
            # Corrected method: use get_user instead of get_user_by_id
            auth_user_res = supabase.auth.admin.get_user(user_id)
            if not auth_user_res.user: raise HTTPException(status_code=404, detail="User not found in auth system.")
            
            new_profile_data = {
                "id": user_id,
                "email": auth_user_res.user.email,
                "first_name": auth_user_res.user.user_metadata.get("first_name"),
                "last_name": auth_user_res.user.user_metadata.get("last_name"),
                "role": UserRole.ALIEN.value,
            }
            insert_res = supabase.from_("user_profiles").insert(new_profile_data).execute()
            if not insert_res.data: raise HTTPException(status_code=500, detail="Could not create user profile.")
            
            logger.info(f"Successfully created new profile for user {user_id}.")
            return insert_res.data[0]
        
        return profile_res.data
    except Exception as e:
        logger.error(f"Failed to fetch or create profile for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving user profile.")