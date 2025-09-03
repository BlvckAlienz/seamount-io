# File Location: backend/dependencies.py
# SURGICAL MERGE: Combined advanced JWT verification with critical scoping/import fixes

import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client, create_client  # CRITICAL: Added missing import
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from functools import lru_cache
import aiohttp
from jose import JWTError, jwt
import json

from config import Settings, get_settings
from services.wallet_service import WalletService
from services.notification_service import NotificationService
from models import UserRole

logger = logging.getLogger(__name__)

# CRITICAL FIX: Proper global declarations
_supabase_client: Optional[Client] = None
_wallet_service: Optional[WalletService] = None
_notification_service: Optional[NotificationService] = None
jwks_cache: Dict[str, Any] = {}
jwks_cache_expiry: Optional[datetime] = None

# Security schemes
security = HTTPBearer(auto_error=False)
security_required = HTTPBearer(auto_error=True)

@lru_cache()
def get_settings_cached():
    """Cached settings instance for performance"""
    return get_settings()

def initialize_dependencies(supabase_client: Client, wallet_service: WalletService, notification_service: NotificationService):
    """Initialize dependency services - used in main.py startup"""
    global _supabase_client, _wallet_service, _notification_service
    _supabase_client = supabase_client
    _wallet_service = wallet_service
    _notification_service = notification_service
    logger.info("✅ Dependencies initialized successfully")

def get_supabase_client() -> Client:
    """
    CRITICAL FIX: Proper singleton Supabase client with correct config attributes
    This was the root cause of the UnboundLocalError
    """
    global _supabase_client  # CRITICAL: Must declare global before use
    
    if _supabase_client is None:
        try:
            settings = get_settings_cached()
            # CRITICAL FIX: Use correct attribute names from your config.py
            supabase_url = settings.VITE_SUPABASE_URL  # Not SUPABASE_URL
            supabase_key = settings.SUPABASE_SERVICE_KEY.get_secret_value()  # Not SUPABASE_KEY
            
            _supabase_client = create_client(supabase_url, supabase_key)
            logger.info("✅ Supabase client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ CRITICAL: Supabase client initialization failed: {e}")
            raise RuntimeError(f"Database service unavailable: {e}")
    
    return _supabase_client

def get_wallet_service() -> WalletService:
    """Get wallet service instance"""
    if _wallet_service is None: 
        logger.error("❌ Wallet service not initialized")
        raise HTTPException(status_code=503, detail="Wallet service unavailable")
    return _wallet_service

def get_notification_service() -> NotificationService:
    """Get notification service instance"""
    if _notification_service is None: 
        logger.error("❌ Notification service not initialized")
        raise HTTPException(status_code=503, detail="Notification service unavailable")
    return _notification_service

async def fetch_jwks(settings: Settings = Depends(get_settings_cached)) -> Dict[str, Any]:
    """
    Fetch and cache Supabase JWKS for JWT verification
    Includes retry logic and proper error handling
    """
    global jwks_cache, jwks_cache_expiry
    
    # Return cached JWKS if still valid
    if jwks_cache and jwks_cache_expiry and datetime.utcnow() < jwks_cache_expiry: 
        logger.debug("🔄 Using cached JWKS")
        return jwks_cache
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(settings.SUPABASE_JWKS_URI) as response:
                    response.raise_for_status()
                    jwks_data = await response.json()
                    
                    # Cache for 1 hour
                    jwks_cache = jwks_data
                    jwks_cache_expiry = datetime.utcnow() + timedelta(hours=1)
                    
                    logger.info(f"✅ JWKS fetched successfully (attempt {attempt + 1})")
                    return jwks_data
                    
        except Exception as e:
            logger.warning(f"⚠️ JWKS fetch attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.critical(f"❌ CRITICAL: Could not fetch Supabase JWKS after {max_retries} attempts")
                raise HTTPException(
                    status_code=503, 
                    detail="Authentication service unavailable - JWKS fetch failed"
                )

async def verify_supabase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_required),
    settings: Settings = Depends(get_settings_cached)
) -> Dict[str, Any]:
    """
    Advanced JWT verification using Supabase JWKS
    Includes proper error handling and logging for debugging
    """
    if not credentials:
        logger.error("❌ No authorization credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    try:
        token = credentials.credentials
        logger.debug(f"🔍 Verifying JWT token: {token[:20]}...")
        
        # Get unverified header for key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        alg = unverified_header.get('alg', 'RS256')
        
        if not kid:
            logger.error("❌ Token missing key ID (kid)")
            raise JWTError("Token missing key ID (kid)")
        
        logger.debug(f"🔑 Token KID: {kid}, Algorithm: {alg}")
        
        # Fetch JWKS and find matching key
        jwks = await fetch_jwks(settings)
        
        key = None
        for jwk_key in jwks.get('keys', []):
            if jwk_key.get('kid') == kid:
                key = jwk_key
                break
        
        if not key:
            logger.error(f"❌ Public key for KID {kid} not found in JWKS")
            raise JWTError(f"Public key for KID {kid} not found in JWKS")
        
        logger.debug(f"✅ Found matching key for KID: {kid}")
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256', 'ES256'],
            audience='authenticated',
            issuer=settings.SUPABASE_JWT_ISSUER,
            options={"verify_aud": True, "verify_exp": True, "verify_iss": True}
        )
        
        user_id = payload.get('sub')
        logger.info(f"✅ Token verified successfully for user: {user_id}")
        return payload
        
    except JWTError as e:
        logger.error(f"❌ JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process authentication token"
        )

async def verify_supabase_token_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    settings: Settings = Depends(get_settings_cached)
) -> Optional[Dict[str, Any]]:
    """
    Optional JWT verification - returns None if no token or invalid token
    Used for routes that work with or without authentication
    """
    if not credentials:
        logger.debug("🔓 No authorization credentials provided (optional auth)")
        return None
        
    try:
        # Reuse the main verification logic
        return await verify_supabase_token(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=credentials.credentials),
            settings
        )
    except HTTPException:
        logger.debug("🔓 Token verification failed for optional auth")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Unexpected error in optional token verification: {e}")
        return None

async def get_current_user(
    payload: Dict[str, Any] = Depends(verify_supabase_token),
    supabase: Client = Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Get current user profile with self-healing capabilities
    Creates profile if it doesn't exist (handles new user edge cases)
    """
    user_id = payload.get("sub")
    if not user_id:
        logger.error("❌ Invalid token payload: user ID missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token payload: user ID missing"
        )
    
    try:
        # Fetch user profile from database
        logger.debug(f"🔍 Fetching profile for user: {user_id}")
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).maybe_single().execute()
        
        if profile_res.data:
            logger.debug(f"✅ Profile found for user: {user_id}")
            return profile_res.data
        
        # SELF-HEALING: Create profile if it doesn't exist
        logger.warning(f"⚠️ Profile not found for user {user_id}. Auto-creating from JWT data...")
        
        user_metadata = payload.get('user_metadata', {})
        app_metadata = payload.get('app_metadata', {})
        
        new_profile_data = {
            "id": user_id,
            "email": payload.get('email', ''),
            "first_name": user_metadata.get("first_name", ""),
            "last_name": user_metadata.get("last_name", ""),
            "country_code": user_metadata.get("country_code", "US"),
            "kyc_status": "not_started",
            "access_level": "limited",
            "role": UserRole.ALIEN.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Insert new profile
        insert_res = supabase.from_("user_profiles").insert(new_profile_data).execute()
        
        if not insert_res.data or len(insert_res.data) == 0:
            logger.error(f"❌ Failed to create profile for user {user_id}")
            raise HTTPException(
                status_code=500, 
                detail="Could not create user profile"
            )
        
        logger.info(f"✅ Successfully auto-created profile for user: {user_id}")
        return insert_res.data[0]
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Profile fetch/creation error for user {user_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving user profile: {str(e)}"
        )

async def get_current_user_optional(
    payload: Optional[Dict[str, Any]] = Depends(verify_supabase_token_optional),
    supabase: Client = Depends(get_supabase_client)
) -> Optional[Dict[str, Any]]:
    """
    Optional user profile fetching - returns None if no valid token
    Used for routes that work with or without authentication
    """
    if not payload:
        return None
        
    try:
        user_id = payload.get("sub")
        if not user_id:
            return None
            
        profile_res = supabase.from_("user_profiles").select("*").eq("id", user_id).maybe_single().execute()
        return profile_res.data if profile_res.data else None
        
    except Exception as e:
        logger.warning(f"⚠️ Optional user profile fetch failed: {e}")
        return None

async def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    Verify whitelisted API key for service-to-service communication
    Used for webhook endpoints and internal service calls
    """
    if not api_key:
        return False
        
    try:
        settings = get_settings_cached()
        is_valid = api_key in settings.WHITELISTED_API_KEYS
        
        if is_valid:
            logger.info(f"✅ Valid API key used: {api_key[:8]}...")
        else:
            logger.warning(f"❌ Invalid API key attempted: {api_key[:8]}...")
            
        return is_valid
        
    except Exception as e:
        logger.error(f"❌ API key verification error: {e}")
        return False

# DIAGNOSTIC FUNCTIONS FOR DEBUGGING

async def get_token_info(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """
    Debug function to inspect token without full verification
    Remove in production - useful for troubleshooting auth issues
    """
    if not credentials:
        return {"error": "No token provided"}
        
    try:
        token = credentials.credentials
        unverified_header = jwt.get_unverified_header(token)
        unverified_payload = jwt.get_unverified_claims(token)
        
        return {
            "header": unverified_header,
            "payload": {
                "sub": unverified_payload.get("sub"),
                "email": unverified_payload.get("email"),
                "exp": unverified_payload.get("exp"),
                "iat": unverified_payload.get("iat"),
                "aud": unverified_payload.get("aud"),
                "iss": unverified_payload.get("iss")
            },
            "token_length": len(token)
        }
    except Exception as e:
        return {"error": f"Token inspection failed: {str(e)}"}

# Health check dependency
async def check_dependencies_health() -> Dict[str, str]:
    """Health check for all critical dependencies"""
    health_status = {}
    
    # Check Supabase client
    try:
        supabase = get_supabase_client()
        health_status["supabase"] = "healthy"
    except Exception as e:
        health_status["supabase"] = f"unhealthy: {str(e)}"
    
    # Check services
    try:
        get_wallet_service()
        health_status["wallet_service"] = "healthy"
    except Exception:
        health_status["wallet_service"] = "not initialized"
    
    try:
        get_notification_service()
        health_status["notification_service"] = "healthy"
    except Exception:
        health_status["notification_service"] = "not initialized"
    
    # Check JWKS cache
    health_status["jwks_cache"] = "cached" if jwks_cache else "empty"
    
    return health_status